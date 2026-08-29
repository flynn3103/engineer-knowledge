# Boxing, Tagging & NaN-Boxing — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Boxing, Tagging & NaN-Boxing** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Two Load-Bearing Assumptions, Stated Precisely

Every inline encoding depends on some subset of:

1. **Alignment (low bits free):** heap objects are N-byte aligned ⇒ low log₂(N) bits of every pointer are zero. Used by pointer tagging.
2. **Narrow addresses (high bits free/predictable):** userspace pointers fit in ≤48 bits ⇒ bits 48–63 are sign-extension filler ⇒ a pointer fits in a NaN payload or a tagged high field. Used by NaN-boxing.

These are **ABI/OS guarantees**, not CPU laws. Alignment holds because *your* allocator promises it. Narrowness holds because the *OS* configures paging that way — and the OS can change it.

### 2. 5-Level Paging Breaks the High-Bit Assumption

Intel's LA57 and the corresponding Linux support extend user virtual addresses to 57 bits. A pointer can now legitimately have bits set in positions 48–56 — bits a NaN-box assumed were zero filler. If your `unbox_ptr` masks to 48 bits, a 57-bit pointer is silently truncated to a *different, wrong* address: memory corruption, not a crash you can catch.

Linux mitigates this for legacy software: by default it returns addresses *below* the 48-bit line and only hands out high addresses when the program passes an explicit `mmap` hint above `0x7fffffffffff`. So a runtime that **never requests high addresses** is usually safe today — but "usually" and "today" are exactly the words a professional distrusts. The disciplined answer is to *reserve* or *constrain* the address space the VM allocates from, so its pointers provably fit the tag budget.

### 3. ARM Pointer Authentication (PAC) Colonizes the High Bits

PAC (ARMv8.3) signs a pointer by computing a MAC over it and a context, then writing that MAC into the pointer's *unused high bits* — precisely the region NaN-boxing and high-bit tagging use. A signed pointer is not directly dereferenceable; you must `AUT*` it first to verify and strip the signature. Two consequences for a runtime:

- **You cannot store a raw PAC-signed pointer in a NaN payload** and later mask it as if the high bits were zero — they hold the signature.
- A runtime on a PAC platform must either authenticate/strip pointers *before* boxing them (storing the bare address) and re-sign on use, or carve its tag out of bits PAC doesn't touch, coordinating with the number of signature bits (which varies with the VA width — fewer address bits ⇒ more signature bits).

This is the cleanest modern example of the hardware reclaiming "your" spare bits.

### 4. Top-Byte-Ignore and MTE: More Claims on High Bits

ARM's **TBI** lets software store an 8-bit tag in the top byte of a pointer; the CPU ignores it on dereference. That *sounds* like a gift to tagging — and it is, if you control it. But **MTE** (Memory Tagging Extension) uses those same top-byte bits for hardware memory-safety tags. If your runtime stores its own tag in the top byte while MTE is active, you collide with the hardware's safety mechanism. The bits are contested resources; a professional negotiates which subsystem owns which bits, on which platform.

### 5. How Real Engines Encode Values (Production Reality)

- **LuaJIT (`TValue`):** classic NaN-boxing. Doubles are themselves; everything else lives in NaN payloads with a small itype tag in the high bits and a 47-bit pointer/payload. Mike Pall's design deliberately keeps pointers within the assumed range.
- **SpiderMonkey:** historically two schemes — **PunBox** (64-bit NaN-boxing, payload inside the NaN) and **NunBox** (32-bit builds: a separate 32-bit tag word beside a 32-bit payload). The names are an in-joke; the engineering is real.
- **JavaScriptCore (`EncodedJSValue`):** the **offset-double** ("nun-boxing"-spirit) scheme — integers carry a tag in high bits, pointers are "low" untagged values, and doubles are stored with a constant **added** so they never collide with the int/pointer/immediate ranges. This makes pointer and int access mask-free.
- **V8:** **SMI tagging** (low-bit int vs HeapObject) plus **HeapNumber** boxing for non-SMI numbers, plus **pointer compression** (32-bit base-relative references) on 64-bit builds. V8 deliberately did *not* go full NaN-boxing; it bet on tagged small ints + compressed pointers.

The lesson: there is no single industry answer. Each engine picked a point on the design space and then engineered hard around the platform assumptions that point requires.

### 6. Defending the 48-Bit Assumption in Production

A NaN-boxing runtime that must remain correct across paging configurations defends the assumption explicitly:

- **Constrain allocation.** Use `mmap` *without* high-address hints, and on Linux optionally reserve the high region so the allocator can't stray above 48 bits.
- **Assert on box.** In debug builds, assert every boxed pointer fits the payload (`(ptr & ~PAYLOAD) == 0` after sign handling). A failed assert in CI beats corruption in the field.
- **Feature-detect at startup.** Detect LA57 / PAC / TBI / MTE and either adjust masks or fall back to a safe representation (e.g., split tag, or boxing).
- **Provide a portable fallback.** Keep a NaN-boxing-free representation (tagging or boxed) compilable behind a flag for hostile platforms.

### 7. ABI Stability and Snapshots

In a mature engine, the value layout is part of an **ABI**: embedders read raw `Value`s through the C API, the JIT emits machine code that hard-codes tag masks, and some engines **serialize the heap** (V8 snapshots) with values encoded. Changing the representation therefore breaks: embedder code, cached JIT output, and serialized snapshots. This is why representation changes in shipping engines are rare, version-gated, and accompanied by migration machinery. The bit layout is not an implementation detail you can refactor freely — it's a contract with everything around it.

---

## Code Examples

### C — Asserting the 48-bit assumption at box time (debug builds)

```c
#include <assert.h>
#include <stdint.h>

#define PAYLOAD 0x0000FFFFFFFFFFFFULL   // 48-bit
#define TAG_PTR 0xFFFC000000000000ULL   // sign + qNaN region (illustrative)

static inline uint64_t box_ptr_checked(void *p) {
    uint64_t a = (uint64_t)(uintptr_t)p;
#ifndef NDEBUG
    // If any bit above 48 is set, our NaN payload would truncate the pointer.
    assert((a & ~PAYLOAD) == 0 && "pointer exceeds 48-bit NaN-box budget");
#endif
    return TAG_PTR | (a & PAYLOAD);
}
```

A failed assert in CI is cheap; the same situation in production is silent corruption. This single guard catches 5-level-paging and high-mmap surprises before they ship.

### C — Constraining the allocator's address range (Linux)

```c
#include <sys/mman.h>
#include <stdint.h>
#include <stdio.h>

// Request memory WITHOUT a high-address hint so Linux stays below the 48-bit line.
// (Passing a hint above 0x7fffffffffff is what opts into 5-level-paging addresses.)
void *vm_map(size_t bytes) {
    void *p = mmap(NULL, bytes, PROT_READ | PROT_WRITE,
                   MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) return NULL;
    if (((uint64_t)(uintptr_t)p) >> 48) {
        // We got a >48-bit address anyway: refuse to NaN-box on this config.
        fprintf(stderr, "VM: high VA detected; disable NaN-boxing\n");
    }
    return p;
}
```

By never hinting a high address, the VM normally stays within budget; the check is the safety net for unusual kernel configs.

### C — Startup feature detection (sketch)

```c
#include <stdbool.h>

typedef struct {
    bool la57;   // 5-level paging (57-bit VA) in use
    bool pac;    // ARM pointer authentication available/active
    bool tbi;    // top-byte-ignore enabled
    bool mte;    // memory tagging active
} PlatformCaps;

// Detect once; choose the representation accordingly.
enum Repr { REPR_NANBOX, REPR_TAGGED, REPR_BOXED };

enum Repr choose_repr(PlatformCaps c) {
    if (c.la57 || c.pac || c.mte)
        return REPR_TAGGED;   // high bits contested → avoid NaN payload pointers
    return REPR_NANBOX;       // classic assumptions hold
}
```

Real engines bake the choice at build time for the JIT's sake, but the *principle* — detect, then pick a representation whose assumptions hold — is the professional posture.

### C — Handling PAC: strip before boxing, re-sign on use (conceptual)

```c
// On ARM PAC, a live pointer carries a signature in high bits.
// Box the BARE address; re-authenticate when you dereference.

static inline void *strip_pac(void *p) {
#if defined(__ARM_FEATURE_PAC_DEFAULT)
    __asm__("xpaci %0" : "+r"(p));   // strip data-pointer auth code
#endif
    return p;
}

static inline uint64_t box_ptr_pac(void *p) {
    void *bare = strip_pac(p);            // high bits now zero → fits payload
    return TAG_PTR | ((uint64_t)(uintptr_t)bare & PAYLOAD);
}
// On unbox you must re-sign (PACIA/AUTIA) before calling through the pointer.
```

The point isn't the exact instruction — it's that **PAC and NaN-boxing both want the high bits, so the runtime must explicitly mediate**: store bare, sign on use.

### C — A serialization/ABI guard

```c
// Embedders and snapshots depend on this layout. Version it.
#define VALUE_LAYOUT_VERSION 3

_Static_assert(VALUE_LAYOUT_VERSION == 3,
    "Value bit layout changed: bump version, migrate snapshots, "
    "recompile embedders and JIT code caches.");
```

A loud, compile-time reminder that the layout is a contract, not a free variable.

---

## Coding Patterns

### Pattern 1: Enumerate and assert every assumption

```c
_Static_assert(sizeof(void *) == 8, "64-bit only");
#ifndef NDEBUG
  assert((ptr & ~PAYLOAD) == 0);   // 48-bit budget
  assert((heap_obj & 0x7) == 0);   // alignment
#endif
```

### Pattern 2: Detect-then-choose at startup (or build time)

```c
enum Repr r = choose_repr(detect_platform_caps());
```

### Pattern 3: Store bare pointers; sign/tag on the boundary

```c
Value box   = TAG_PTR | (strip_high_bits(p) & PAYLOAD);
void *live  = reauth(unbox_payload(box));   // re-sign before deref on PAC
```

### Pattern 4: Reserve the address space the tag budget allows

```c
// Reserve low VA so the allocator's pointers provably fit the payload.
reserve_low_address_space(BUDGET_BYTES);
```

### Pattern 5: Version the layout; gate changes behind migration

```c
#define VALUE_LAYOUT_VERSION 3   // bump → migrate snapshots + recompile embedders
```

---

## Best Practices

- **Treat alignment and address-width as *guarantees you must enforce*, not facts you may assume.** Constrain the allocator; assert on box; detect the platform.
- **Default to the most portable representation that meets your perf bar.** Tagging (alignment-only) ports more safely than NaN-boxing (address-width-dependent). V8's choice is instructive.
- **Coexist with PAC/TBI/MTE deliberately.** Decide, per platform, which bits the hardware owns and which you own; strip/re-sign pointers at the boxing boundary.
- **Make the layout an ABI artifact.** Version it, document the masks in one place, and gate changes behind snapshot migration and embedder/JIT recompilation.
- **Fuzz across configurations.** Round-trip random doubles/ints/pointers/immediates, *including* high addresses and signaling NaNs, on each target.
- **Keep a fallback representation compilable.** A flag that switches NaN-boxing off to tagging/boxing is cheap insurance for a hostile new platform.
- **Measure the real cost on real silicon.** PAC stripping, masking, and decompression have measurable cost on ARM; don't assume the x86 cost model transfers.

---

## Edge Cases & Pitfalls

- **A pointer above the 48-bit line silently truncates.** No fault, no crash — a *different* valid-looking address. The worst class of bug: silent corruption.
- **PAC-signed pointers stored raw.** Masking a signed pointer to 48 bits destroys the address *and* the signature; dereferencing the result faults or corrupts.
- **MTE collides with a top-byte software tag.** If you store a tag in the top byte while MTE is enabled, the hardware's tag check fails or your tag is clobbered.
- **`mmap` hint accidentally opting into high addresses.** Passing a hint above the 48-bit line on Linux can hand you a 57-bit pointer you can't box.
- **ASLR / sandbox placing the heap high.** Some sandboxes deliberately use high VA; your VM's pointers then don't fit the budget.
- **Snapshot loaded by a binary with a different layout version.** A serialized value decoded under the wrong masks is corruption from the first access.
- **JIT code cache outliving a layout change.** Cached machine code hard-codes the old masks; running it after an upgrade is undefined.
- **Pointer compression base mismatch.** A compressed pointer is meaningless without its base; cross-process or cross-heap mixing corrupts.

---

## Common Mistakes

1. **Assuming "48-bit pointers" is a CPU law.** It's an OS/ABI configuration that LA57 and sandboxes break.
2. **Masking PAC-signed pointers as if the high bits were free.** Destroys both address and signature.
3. **Storing a software tag in the top byte without checking for MTE.** Hardware/software tag collision.
4. **Shipping NaN-boxing with no high-address assertion or allocator constraint.** The latent corruption waits for the wrong host.
5. **Treating the value layout as a private implementation detail.** It's an ABI consumed by embedders, snapshots, and the JIT.
6. **Porting the x86 representation to ARM unchanged.** Different address features; the bit budget differs.
7. **No fallback representation.** When a new platform breaks your assumptions, you have no safe mode to ship.
8. **Skipping cross-config fuzzing.** The bugs live exactly in the configurations your dev machine doesn't run.

---

## Tricky Points

- **"It works on my machine" is maximally dangerous here.** Your laptop runs 4-level paging, maybe no PAC; the corruption appears only on the host that breaks an assumption. The absence of a crash proves nothing.
- **The high bits are a moving target.** Each CPU generation may claim more of them (PAC width grows as VA width shrinks; MTE arrives; LA57 spreads). A representation safe today may be unsafe on next year's silicon.
- **Pointer compression is a different answer to the same pressure.** V8 sidesteps NaN-boxing's address-width fragility by storing 32-bit base-relative pointers — trading max heap size for portability and density. There's more than one way to spend the budget.
- **TBI is both gift and trap.** It legitimizes a software top-byte tag — until MTE wants the same byte. A feature that helps tagging on one ARM config breaks it on another.
- **The fallback path is rarely exercised, so it rots.** Keep the non-NaN-boxing representation *building and tested in CI*, or it won't actually work the day you need it.
- **Snapshots freeze the representation in serialized form.** You can change the live layout but old snapshots still carry the old encoding; migration, not refactoring, is the tool.

---

## Apply it

1. Define the user or business outcome that **Boxing, Tagging & NaN-Boxing** should improve.
2. Assign one owner for code, contracts, operations, and incidents.
3. Split delivery into reversible increments that produce evidence early.
4. Publish responsibilities, escalation paths, and compatibility windows.
5. Stop or expand only when the agreed measures support that decision.

## Verify your work

- Each increment has an owner, rollback path, and observable exit condition.
- Adoption, reliability, delivery time, and coordination cost are measured.
- Incident and migration exercises prove that responsibility is executable.
- The old path is removed only after telemetry proves it is unused.

## Review questions

- Which measurable outcome justifies investing in Boxing, Tagging & NaN-Boxing?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
