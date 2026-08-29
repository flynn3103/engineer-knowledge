# Memory-Safety Mechanisms — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Memory-Safety Mechanisms** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Shadow Memory: The Universal Bookkeeping Trick

The core problem for a detector is: *for any address the program touches, is that address currently legal to access?* You can't store a flag *inside* each byte (that byte holds the user's data). So tools keep a parallel **shadow memory** — a separate region that records metadata for application memory.

ASan's scheme is elegant: **1 shadow byte describes 8 application bytes.** Because allocations are 8-byte aligned, each 8-byte slot is either fully addressable (shadow = 0), fully poisoned (shadow = negative), or *partially* addressable (shadow = k means "the first k of these 8 bytes are valid"). The shadow address is computed by a cheap formula: `shadow = (addr >> 3) + offset`. So checking an access is:

```text
shadow_value = *((addr >> 3) + Offset);
if (shadow_value != 0 && (addr & 7) >= shadow_value)
    report_error();    // this byte is poisoned -> bug
```

A shift, an add, a load, a compare, a branch — a handful of instructions per memory access. That's the ~2× slowdown ASan costs. Cheap enough for testing, too much for production.

### 2. Redzones: Catching Spatial Bugs

Around every allocation, ASan inserts **redzones** — extra bytes that are poisoned in shadow memory. Heap allocations get redzones on both sides; stack arrays and globals get them too. The layout looks like:

```text
[ left redzone (poison) ][ your 16 bytes (valid) ][ right redzone (poison) ]
```

Now an off-by-one write to `arr[16]` lands in the right redzone. The shadow byte for that address is non-zero, the check fires, and ASan prints `heap-buffer-overflow` with the exact line, the allocation site, and how far out of bounds you went. The redzone is *why* ASan can describe the overflow so precisely — it caught the *first* byte over the line, not a downstream symptom.

The blind spot: a wild access that *jumps over* the redzone (e.g. `arr[1000000]`) may land in genuinely-valid memory and not be caught. Redzones catch *adjacent* overflows, which is the overwhelming majority of real bugs.

### 3. Quarantine: Catching Temporal Bugs

When you `free(p)`, a normal allocator immediately makes that block available for reuse — which is exactly why use-after-free is so dangerous (the memory becomes something else's). ASan instead poisons the freed block and puts it in a **quarantine**: a FIFO queue of freed blocks that are *not reused* until the queue fills up and the oldest are released.

While a block sits in quarantine, its shadow is poisoned. Any read or write through a dangling pointer hits poison → `heap-use-after-free`, with *two* stack traces: where it was freed and where it's now being used. That paired report is the gift of quarantine.

The blind spot, and it's important: quarantine is *finite*. If enough other frees happen, your freed block leaves quarantine, gets reused, unpoisoned, and a later use-after-free will *not* be caught (the memory is legal again — just holding the wrong object). So ASan finding *no* UAF doesn't *prove* there isn't one. This is a fundamental limit of detection-by-poisoning, and a key reason temporal safety is harder than spatial.

### 4. The Sanitizer Family — Different Tools for Different Bugs

They are *not* interchangeable. Each targets a class:

- **ASan** — *addressability*: OOB (spatial) and UAF/double-free (temporal). The default first reach. ~2× slow, ~3× memory.
- **MSan** — *uninitialized reads*. It tracks, bit by bit, whether each value has been written before it's used in a way that affects program behavior. Catches "read garbage" bugs ASan can't. Requirement: ideally the *entire* program (incl. libraries) is instrumented, or MSan reports false positives from uninstrumented code that "wrote" the memory invisibly.
- **UBSan** — a grab-bag of *undefined behavior*: signed integer overflow, shift-by-too-much, misaligned pointers, null dereference, invalid enum/bool values, and (with `-fsanitize=bounds`) OOB on objects whose size the compiler knows. Very cheap; turn on broadly.
- **TSan** — *data races*. Relevant here because in many languages a data race is itself undefined behavior and can corrupt memory. (Detailed in concurrency topics.)

You typically can't run ASan and MSan together (their shadow schemes conflict); you run them in separate CI jobs.

### 5. Valgrind/Memcheck — Detection Without Recompiling

Valgrind takes a completely different approach. Instead of the *compiler* inserting checks, Valgrind runs your **unmodified binary** on a synthetic CPU via dynamic binary translation. Memcheck (its main tool) tracks two things per byte: **addressable?** (A-bits) and **defined?** (V-bits). Every memory access and every use of a value is checked against this shadow state.

Trade-offs versus ASan:

- ✅ No recompile, works on any binary, catches uninitialized reads *and* OOB *and* leaks in one tool.
- ✅ Catches some bugs in third-party libraries you can't rebuild.
- ❌ Much slower — often **10–50×** — because every instruction is interpreted.
- ❌ Doesn't catch *stack* or *global* OOB well (no redzones around stack arrays), where ASan shines.

Rule of thumb: **ASan for speed and stack/global coverage; Valgrind when you can't recompile or need its leak detection on an arbitrary binary.**

### 6. Hardened Allocators — Mitigation in Production

In production you can't afford ASan's overhead, but you can use a **hardened allocator** that costs little and removes common exploitation primitives:

- **Free-list hardening** — encrypt/checksum the pointers in the free-list so an attacker who corrupts a freed chunk can't redirect a future allocation to an address of their choosing. Also detect double-free by checking whether a chunk is already free.
- **Metadata separation** — keep allocator bookkeeping *out-of-line*, away from user data, so a heap overflow corrupts (poisoned/guarded) padding instead of the size/next fields the allocator trusts.
- **Randomization** — randomize where allocations land so heap layout isn't predictable (defeats "groom the heap so object B sits right after A").
- **Delayed/randomized reuse** — like a lightweight quarantine, reduces UAF reliability.

Two notable systems:

- **Scudo** — the default hardened allocator on Android (and available in LLVM). Adds chunk headers with checksums, randomization, and quarantine, at modest cost.
- **GWP-ASan** — "Guard-page-Without-Performance-cost ASan." A *sampling* detector for production: it places a small fraction of allocations on **guard pages** (real OS no-access pages on either side), so the rare overflow or UAF that hits one of those allocations triggers a hardware fault and a precise crash report from a real user. By sampling (e.g. 1 in 10,000 allocations), the average overhead is negligible, yet across a billion devices it catches bugs ASan never saw in the lab.

### 7. Guard Pages — Hardware-Enforced Spatial Safety

A **guard page** is a whole memory page the OS marks no-access. Place an allocation so its end abuts a guard page, and any overflow into it triggers an immediate hardware fault — no shadow memory, no instrumentation, the MMU does the work for free. The cost is granularity: pages are ~4 KiB and you "waste" a page per guarded allocation, so you can't guard *every* allocation this way (that's why GWP-ASan *samples*). Electric Fence (`efence`) was the classic all-allocations-on-guard-pages debug allocator; GWP-ASan is its production-viable, sampled descendant.

### 8. C-Level Defenses: `_FORTIFY_SOURCE`, Canaries, Annotated APIs

You can harden C source *without* changing your code much:

- **`_FORTIFY_SOURCE=2`/`=3`** — when the compiler can determine the destination buffer's size at compile time, it replaces `memcpy`/`strcpy`/`sprintf`/`snprintf`/... with `__*_chk` variants that verify the copy fits, aborting on overflow. Free at runtime when sizes are known; does nothing when they aren't (its blind spot). `=3` extends coverage to more cases via `__builtin_dynamic_object_size`.
- **Stack canaries (`-fstack-protector-strong`)** — a random value between local buffers and the saved return address, verified on return. A linear stack overflow that overwrites the return address must pass *through* the canary, corrupting it, which the check detects → abort before the corrupted return is used. Defeats the classic "smash the stack" pattern.
- **Annotated / checked APIs** — design functions that take a buffer *and its size* (`void f(char *buf, size_t cap)`), and use compiler attributes (`__attribute__((access(write_only, 1, 2)))`, `__counted_by__`) to let the compiler reason about bounds. This is "make the size impossible to forget."

None of these makes C *safe*; together they turn many silent corruptions into clean aborts and shrink the exploitable surface.

### 9. Spatial Is Cheap, Temporal Is Expensive

A theme worth internalizing: **spatial safety is much cheaper to enforce than temporal safety.**

- Spatial: you need *bounds* (base + length) at the access. That's local information — carry a length, check an index. A predictable branch the CPU mostly predicts correctly, often eliminated by the optimizer.
- Temporal: you need to know whether the pointed-to object is *still the same live object* it was when the pointer was made. That's a *global, time-dependent* fact. Detecting it requires either never reusing memory (GC, quarantine — costly in memory) or per-object liveness tracking. There is no cheap local check for "is this still alive?" This is why GC and quarantine exist, why UAF is the hardest class to mitigate, and why hardware temporal-safety mechanisms (MTE — `professional.md`) are such a big deal.

---

## Code Examples

> Defensive/educational only. These show how the *tools* report, and how to *write checkable* code — no exploits.

### Seeing ASan's redzone catch an off-by-one

```c
// fortify.c
#include <stdlib.h>
int main(void) {
    int *a = malloc(4 * sizeof(int));  // valid: a[0..3]
    a[4] = 42;                         // right-redzone write -> ASan fires
    free(a);
    return 0;
}
```

```bash
clang -fsanitize=address -g fortify.c -o fortify && ./fortify
# ==..==ERROR: AddressSanitizer: heap-buffer-overflow ... WRITE of size 4
#   #0 ... in main fortify.c:5
#   0x... is located 0 bytes to the right of 16-byte region [0x..,0x..)
#   allocated by thread T0 here: ... malloc ... fortify.c:4
```

Note the precision: "0 bytes to the right of a 16-byte region," plus the allocation site. That's the redzone + shadow memory working.

### Quarantine catching use-after-free (and its limit)

```c
// uaf.c
#include <stdlib.h>
int main(void) {
    int *p = malloc(sizeof(int));
    *p = 7;
    free(p);          // ASan poisons + quarantines
    return *p;        // heap-use-after-free: reports BOTH free site and use site
}
```

If you inserted *thousands* of unrelated `malloc/free` between the `free(p)` and the `return *p`, the quarantine might evict `p`'s block and ASan would no longer catch it — the mechanism's honest limit.

### MSan catching an uninitialized read

```c
// msan.c (compile every TU with -fsanitize=memory for accurate results)
#include <stdio.h>
int main(void) {
    int x;                 // never written
    if (x == 0)            // use of uninitialized value
        printf("zero\n");
    return 0;
}
```

```bash
clang -fsanitize=memory -fsanitize-memory-track-origins -g msan.c -o msan && ./msan
# ==..==WARNING: MemorySanitizer: use-of-uninitialized-value
#   #0 ... in main msan.c:5
#   Uninitialized value was created by an allocation of 'x' ...
```

### `_FORTIFY_SOURCE` aborting a provable overflow

```c
// fs.c  -- compile: gcc -O2 -D_FORTIFY_SOURCE=2 fs.c
#include <string.h>
int main(void) {
    char buf[8];
    // Compiler KNOWS buf is 8 bytes; this copies 16 -> __memcpy_chk aborts.
    memcpy(buf, "0123456789ABCDEF", 16);
    return buf[0];
}
// Runtime: *** buffer overflow detected ***: terminated (abort, not corruption)
```

When the destination size is *not* known at compile time, `_FORTIFY_SOURCE` cannot help — that's the case to be aware of.

### Annotating an API so size can't be forgotten

```c
// Carry capacity; tell the compiler about it so it can warn/check.
#include <stddef.h>

__attribute__((access(write_only, 1, 2)))     // ptr=arg1, size=arg2
void fill(char *dst, size_t cap, char c) {
    for (size_t i = 0; i < cap; i++) dst[i] = c;   // bounded by cap
}
```

---

## Coding Patterns

```text
CI matrix for C/C++:
  job: build+test with -fsanitize=address,undefined
  job: build+test with -fsanitize=memory          (if deps instrumented)
  job: fuzz target  with -fsanitize=address,fuzzer (libFuzzer)
  job: valgrind --leak-check=full ./tests          (slow; nightly)

Production build flags (defense in depth):
  -O2 -D_FORTIFY_SOURCE=3 -fstack-protector-strong -fstack-clash-protection
  link a hardened allocator (Scudo) + enable GWP-ASan sampling
```

---

## Best Practices

- **Run ASan + UBSan on every CI build of the test suite.** Treat any finding as a build failure, not a warning.
- **Pair sanitizers with fuzzing.** Sanitizers find the bug; fuzzers find the *input* that triggers it. Together they're far stronger than either alone.
- **Don't trust a clean ASan run as proof of absence** — remember quarantine eviction and the input dependence. Raise quarantine size (`ASAN_OPTIONS=quarantine_size_mb=...`) when hunting hard UAF.
- **Build production with `_FORTIFY_SOURCE`, stack protector, and a hardened allocator.** These are nearly free and routinely turn an exploitable bug into a clean crash.
- **Carry sizes in your APIs and annotate them.** Make "forgot the length" a compile-time-detectable mistake.
- **Use the right tool for the location:** ASan for stack/global/heap with recompile; Valgrind when you can't recompile or want leak detection on an arbitrary binary.

---

## Edge Cases & Pitfalls

- **ASan and MSan can't share a process** — separate CI jobs.
- **MSan needs full instrumentation.** An uninstrumented library that "initializes" your buffer looks uninitialized to MSan → false positives. Instrument deps or use interceptors.
- **`_FORTIFY_SOURCE` is a no-op when the size isn't compile-time known.** Don't assume it covers dynamic-size copies.
- **Quarantine memory cost.** A large quarantine catches more UAF but uses more RAM; it's a knob, not free.
- **Guard pages waste a page per guarded allocation** — that's why only a *sample* can use them in production.
- **Stack canaries don't stop *targeted* writes** that skip over the canary (e.g. an indexed write to exactly the return address); they stop *linear* overflows.
- **Sanitizer builds change timing and layout** — a race that reproduces without ASan may hide under it (use TSan for races).

---

## Common Mistakes

- Treating Valgrind and ASan as the same tool. They have different coverage (Valgrind weak on stack/global OOB; ASan strong there).
- Shipping a sanitizer build to production "for safety." Sanitizers are detectors, not mitigations, and the slowdown is unacceptable in prod.
- Concluding "ASan is clean, so we're memory-safe." It's clean *on the inputs you ran*, within quarantine limits, in instrumented code.
- Relying on `_FORTIFY_SOURCE` alone and assuming it covers all `memcpy` calls (only the compile-time-sized ones).
- Forgetting that `malloc` doesn't zero memory and then having MSan (correctly) flag the uninitialized read you didn't notice.

---

## Tricky Points

- **Why 1 shadow byte per 8 app bytes?** Allocations are 8-byte aligned, so a single byte can encode the three relevant states (fully valid / fully poisoned / first-k-valid) for an 8-byte chunk, and the address math is a single shift. It's the sweet spot of memory cost vs. precision.
- **Why does ASan need *both* redzones and quarantine?** Redzones handle *spatial* (adjacent overflow); quarantine handles *temporal* (UAF). They're orthogonal mechanisms for the two halves of safety, and ASan does both at once.
- **Why is GWP-ASan "without performance cost" if guard pages are expensive?** Because it *samples* — only a tiny fraction of allocations get guard pages, so average overhead is negligible, while the huge install base still surfaces real bugs statistically.
- **Why can't sanitizers give temporal safety in production?** The quarantine/shadow overhead is too high to keep memory poisoned forever; you'd need *hardware* help (MTE) to make per-access temporal checks cheap — that's the `professional.md` story.

---

## Apply it

1. Find a real component where **Memory-Safety Mechanisms** affects an interface or dependency.
2. Write two plausible choices and the constraint that favors each one.
3. Make the smallest reversible change at that boundary.
4. Exercise the component alone, then exercise the integrated flow.
5. Keep the decision note with the evidence that selected the option.

## Verify your work

- A focused check proves the local behavior.
- An integrated check proves callers and dependencies still agree.
- Logs, traces, compiler output, or benchmarks expose the boundary.
- Reverting the change restores the previous behavior without unrelated edits.

## Review questions

- Which boundary is most affected by Memory-Safety Mechanisms?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
