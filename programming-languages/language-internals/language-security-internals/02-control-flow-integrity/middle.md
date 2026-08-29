# Control-Flow Integrity — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Control-Flow Integrity** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Gadget: Why "Ending in `ret`" Is the Whole Trick

NX guarantees the attacker can only jump to *existing executable code*. ROP turns that constraint into a feature. Scattered through any large binary are millions of short instruction sequences that happen to **end in a `ret`**. A few examples of the *kinds* of useful sequences (described, not weaponized):

```text
gadget A:  pop rdi ; ret        -> loads a value from the stack into rdi, then "returns"
gadget B:  pop rsi ; ret        -> loads a value into rsi, then "returns"
gadget C:  mov [rax], rbx ; ret -> stores rbx into memory at rax, then "returns"
```

Each gadget is two or three instructions and then `ret`. Here's the key insight: **`ret` pops the next address off the stack and jumps to it.** So if the attacker controls the stack (which they do — that's the original overflow), they can lay out a *list of gadget addresses*. Gadget A runs, hits `ret`, which jumps to gadget B, which hits `ret`, which jumps to gadget C... The stack becomes a *program*, and the gadgets are its instructions.

### 2. The Chain: A Stack-Driven Program

A ROP "chain" is just the attacker's stack layout:

```text
   stack (attacker-controlled after overflow)
   +------------------+
   | addr of gadget A |  -> initial ret lands here: pop rdi; ret
   +------------------+
   | value for rdi    |  <- gadget A pops this
   +------------------+
   | addr of gadget B |  -> next ret lands here: pop rsi; ret
   +------------------+
   | value for rsi    |  <- gadget B pops this
   +------------------+
   | addr of gadget C |  -> ... and so on
   +------------------+
```

With enough gadgets, the attacker can perform *arbitrary computation* — set registers, write memory, call functions — without ever supplying a single byte of executable code. NX is fully satisfied: every address is in legitimate executable memory. This is why **NX alone is not enough**, and why the security community needed something that checks *which existing code* a branch may reach.

### 3. JOP and COP: When You Run Out of `ret`s

If a defense specifically watches returns (shadow stacks do this — see `senior.md`), attackers can pivot to gadgets ending in indirect `jmp` (**JOP**) or indirect `call` (**COP**). These don't use the stack's `ret` mechanism; instead a **dispatcher gadget** acts like a little interpreter, advancing through a table of gadget addresses. The takeaway: **protecting only the backward edge isn't enough**, because JOP/COP attack the *forward* edge. You need defenses on both edges. This bidirectional pressure is exactly why modern systems pair shadow stacks (backward) with forward-edge CFI.

### 4. vtable Hijacking: The Forward Edge in C++

The most common real-world forward-edge target is the **C++ vtable**. A virtual call looks like:

```text
object -> [ vtable pointer ] -> [ method0, method1, method2, ... ]
call: load vtable pointer from object, load method from vtable, call it
```

If an attacker corrupts the **vtable pointer** in an object (via a heap overflow or use-after-free), they can point it at a fake table full of attacker-chosen addresses. The next virtual call jumps wherever they want. Crucially, the vtable pointer lives in *data* (the object on the heap), so a data-corruption bug becomes a control-flow hijack. Microsoft's early **vtguard** and modern forward-edge CFI both exist largely to stop this.

### 5. Coarse vs Fine-Grained CFI — and Why Coarse Fell

The first wave of practical CFI was **coarse-grained**: cheap, approximate policies like:

- "An indirect call may only target a *function entry point*."
- "A `ret` may only land *just after some `call` instruction*."

These cut the attack surface, but researchers showed they were **bypassable**: there are *so many* legal function entries and call-preceded addresses in a real binary that you can still assemble a useful gadget chain entirely from "allowed" targets. The defense allowed too much. The lesson reshaped the field:

> **Coarse CFI restricts the *kind* of target; fine-grained CFI restricts the *specific set* of targets per call site.** Only the latter meaningfully shrinks the gadget space.

Modern CFI (LLVM CFI, XFG) is fine-grained: each call site gets a *small, type-derived* set of legal targets, not "any function."

### 6. Forward-Edge CFI Mechanism 1: LLVM CFI (Type-Based Sets)

Clang/LLVM's CFI (`-fsanitize=cfi`) is **compiler-based** and uses **type signatures**. The compiler knows the type of every function pointer and the type of every function. For an indirect call through a `int (*)(char*)` pointer, the legal targets are *only functions whose type matches* `int(char*)`. The compiler:

1. Groups functions by type signature into sets.
2. Lays them out so a fast range/bitmask check can answer "is this target in the set?"
3. Inserts that check before each indirect call (and before each vtable dispatch — `-fsanitize=cfi-vcall`).

If the target isn't in the type set, the program traps. This is far tighter than "any function entry" — typically a handful of targets per site. Its **precision limit**: all functions sharing a type are mutually substitutable, so if many functions share a signature (very common with `void(void)` or `void*(void*)`), the set is still larger than the *one* legitimate target. Type-based CFI shrinks but does not eliminate the gadget space.

### 7. Forward-Edge CFI Mechanism 2: Microsoft CFG and XFG

Windows uses a different design. **Control Flow Guard (CFG)** is supported by the compiler *and the OS loader*:

- The compiler emits, for each module, a **bitmap of valid indirect-call targets** (every legitimate function entry).
- Before each indirect call, the compiler inserts a call to a guard check that consults the bitmap: "is this address a valid call target?"
- The OS maintains the bitmap and the check function.

CFG is *coarser* than LLVM CFI — its set is essentially "any address marked as a valid function start," not a per-type set — which is why it was shown bypassable in practice. **XFG (eXtended Flow Guard)** tightens it by adding a **type hash**: each valid target is tagged with a hash of its function prototype, and the check verifies *both* "valid target" *and* "matching type hash." That moves Windows toward LLVM-CFI-style fine granularity.

### 8. Related Hardening: RELRO and the GOT/PLT

A program's indirect calls into shared libraries route through the **GOT** (Global Offset Table) and **PLT**. The GOT is a table of function pointers the dynamic linker fills in. Historically, overwriting a GOT entry was a clean way to hijack a call. **RELRO** ("RELocation Read-Only") hardens this:

- **Partial RELRO** reorders sections so the GOT is less exposed.
- **Full RELRO** resolves all symbols at startup and then marks the GOT **read-only**, so an overflow can't rewrite those pointers.

RELRO isn't CFI per se, but it removes a major forward-edge corruption target, and you'll always see it discussed alongside CFI in hardening checklists.

---

## Code Examples

> Defensive/illustrative only. We show how to *enable and reason about* defenses, and the *shape* of vulnerable patterns — never working exploits.

### 1. Enabling LLVM CFI (Clang)

```bash
# Forward-edge CFI: indirect-call and vtable checks.
# Requires LTO (whole-program visibility to compute type sets).
$ clang++ -flto -fvisibility=hidden \
          -fsanitize=cfi \
          app.cpp -o app

# Narrow to specific schemes if needed:
#   -fsanitize=cfi-icall   (indirect function-pointer calls)
#   -fsanitize=cfi-vcall   (C++ virtual calls / vtable integrity)
#   -fsanitize=cfi-nvcall  (non-virtual member calls)

# Diagnose violations instead of trapping (development only):
$ clang++ -flto -fsanitize=cfi -fno-sanitize-trap=cfi \
          -fsanitize-recover=cfi app.cpp -o app
```

Why `-flto`? Type-based CFI needs to see *all* functions of a given type across the whole program to build the target set. Without whole-program visibility, the sets would be incomplete and either over-restrictive (false traps) or unsound.

### 2. The pattern CFI protects: an indirect call

```c
typedef int (*handler_t)(const char *);

struct request {
    handler_t handler;   // a function pointer stored in data
    char payload[256];   // ... right next to a buffer (BUG bait)
};

void dispatch(struct request *r, const char *msg) {
    // If a bug let an attacker overwrite r->handler, this indirect
    // call would jump wherever they chose. CFI checks, before the
    // call, that r->handler is a function of type int(const char*).
    r->handler(msg);
}
```

With `-fsanitize=cfi-icall`, the compiler inserts: *"is `r->handler` in the set of `int(const char*)` functions? If not, trap."* The attacker can still corrupt the pointer, but they can only redirect to a *type-matching* function — a drastically smaller set than "anywhere."

### 3. vtable integrity (C++)

```cpp
struct Codec {
    virtual int decode(const char *in) = 0;
    virtual ~Codec() = default;
};

void run(Codec *c, const char *in) {
    // Virtual dispatch reads c's vtable pointer (in heap data) and
    // calls through it. If a use-after-free or heap overflow swapped
    // the vtable pointer, this would be a hijack.
    // -fsanitize=cfi-vcall verifies the vtable belongs to a class
    // in Codec's hierarchy before dispatching.
    int n = c->decode(in);
    (void)n;
}
```

### 4. Enabling Microsoft CFG / XFG (MSVC)

```text
# CFG: compiler emits the valid-target bitmap; loader enforces it.
cl /guard:cf app.cpp /link /guard:cf

# XFG (newer toolchains): adds type-hash checks on top of CFG.
cl /guard:xfg app.cpp /link /guard:xfg
```

### 5. Verifying mitigations are present

```bash
# Linux: confirm NX, canary, PIE, and Full RELRO.
$ checksec --file=./app
RELRO      STACK CANARY  NX     PIE  ...
Full RELRO   Canary found  NX enabled  PIE enabled
```

```text
# Windows: dumpbin shows whether CFG is on.
dumpbin /headers /loadconfig app.exe   # look for "Guard CF" flags
```

---

## Coding Patterns

**Pattern: Minimize and type-narrow your function pointers.** Distinct, specific signatures yield smaller CFI target sets than a sea of `void(void)` callbacks.

```c
// Weaker for CFI: everything is the same type.
typedef void (*generic_cb)(void *);

// Stronger: specific types create smaller, distinct target sets.
typedef int  (*parse_cb)(const struct packet *);
typedef void (*log_cb)(int level, const char *msg);
```

**Pattern: Don't store hot function pointers next to attacker-reachable buffers.** Layout matters; a function pointer adjacent to an input buffer is a corruption magnet.

**Pattern: Build with LTO when using LLVM CFI.** Without it, sets are incomplete.

**Pattern: Keep Full RELRO and PIE on.** They're free defense-in-depth that close adjacent doors (GOT overwrite, fixed addresses).

---

## Best Practices

1. **Enable forward-edge CFI on C/C++ that handles untrusted input** (`-fsanitize=cfi` with LTO on Clang; `/guard:xfg` on MSVC).
2. **Prefer XFG over plain CFG** where your toolchain supports it — type hashes close coarse-CFI bypasses.
3. **Use Full RELRO and PIE/ASLR** so forward-edge CFI isn't undermined by GOT overwrites or known addresses.
4. **Type your function pointers precisely** — vague signatures inflate CFI target sets.
5. **Test under `-fno-sanitize-trap=cfi` first** to find legitimate type mismatches (common with casts/`dlsym`) before shipping the trapping build.
6. **Remember CFI is forward-edge only here** — you still need shadow-stack/backward-edge protection (`senior.md`).

---

## Edge Cases & Pitfalls

- **Casting function pointers breaks type-based CFI.** Calling a function through a mismatched-type pointer (even a "harmless" cast) trips `cfi-icall`. Often this surfaces real type confusion; sometimes it's legacy code that needs a clean signature.
- **`dlsym`/`GetProcAddress` and JIT'd code** produce pointers the compiler never saw, so they're outside the type sets. They need explicit handling (e.g., `no_sanitize` annotations, or CFI-aware JIT support).
- **Shared-library boundaries weaken LLVM CFI.** Type sets are computed per LTO unit; calls crossing into a separately built `.so` may not be fully checked.
- **Plain CFG ≈ coarse CFI.** Treating "CFG enabled" as strong is a mistake; without XFG it allows any valid function entry.
- **Forward-edge CFI does nothing for returns.** JOP/COP and return-address attacks route around it; you need shadow stacks too.

---

## Common Mistakes

- Enabling `-fsanitize=cfi` without `-flto` and getting incomplete (or noisy) protection.
- Treating CFG as equivalent to fine-grained CFI.
- Using a single `void(void)` callback type everywhere, collapsing all target sets into one big set.
- Forgetting RELRO/PIE, leaving GOT overwrite and fixed addresses as easy paths around CFI.
- Assuming forward-edge CFI also covers the backward edge.

---

## Tricky Points

- **A ROP chain supplies no code — only addresses.** That's why NX, which only forbids new code, can't stop it.
- **Coarse CFI fails not because the check is wrong but because the *set is too big*.** Security scales with set tightness.
- **Type-based CFI's blind spot is type aliasing.** Many functions with the same signature ⇒ they're mutually substitutable under CFI.
- **Defending the backward edge pushes attackers to the forward edge and vice versa.** This is why both shadow stacks and forward-edge CFI ship together.
- **vtable hijacking is a *data* bug with a *control-flow* consequence** — corrupt the vtable pointer (data), hijack a virtual call (control).

---

## Apply it

1. Find a real component where **Control-Flow Integrity** affects an interface or dependency.
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

- Which boundary is most affected by Control-Flow Integrity?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
