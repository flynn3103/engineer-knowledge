# Control-Flow Integrity — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Control-Flow Integrity** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Why Canaries Aren't Integrity

A stack canary is a *tripwire*: it detects a *contiguous* overwrite that crosses it, and only just before `ret`. It does not protect the return address itself — it protects a value *near* it, and only against one corruption shape. Targeted writes (precise heap-to-stack, format-string writes, non-contiguous overflows), and info-leak-then-rewrite (read the canary, write it back correctly) all defeat it. **Integrity** means: even if the attacker can write the return-address slot, the program won't *use* a forged value. Shadow stacks provide that; canaries don't.

### 2. Shadow Stacks: A Second, Protected Copy

A **shadow stack** is a separate region holding *only* return addresses. The contract:

- On `call`: push the return address to the *regular* stack **and** to the shadow stack.
- On `ret`: pop from the regular stack, and compare it to the top of the shadow stack. **If they differ, fault.**

Because the attacker's overflow corrupts the *regular* stack but not the (separately located, hardware-protected) shadow stack, a forged return address no longer matches and the `ret` traps. This directly kills ROP's core mechanism: you can pile addresses on the regular stack all you like, but each `ret` is now validated against an untouched record of where it should go.

Shadow stacks come in two forms:

- **Software shadow stacks** (compiler-instrumented). Sound but costly, and the protection of the shadow region itself is the hard part — if it's just normal memory, a write primitive can corrupt it too. Various tricks (segment isolation, randomization, info-hiding) were used, with mixed durability.
- **Hardware shadow stacks** (Intel CET, ARM GCS). The CPU manages a shadow stack pointer and enforces that shadow-stack pages are only writable by `call`/`ret` and dedicated instructions — *not* by ordinary stores. This is the version that scales: cheap and genuinely tamper-resistant.

### 3. Intel CET: Shadow Stack + IBT

**Intel CET** ("Control-flow Enforcement Technology") brings both edges into silicon:

**Shadow stack (backward edge).** As above, hardware-managed. The shadow-stack pages have a special memory type that ordinary writes can't modify; only `call`/`ret` and shadow-stack instructions touch them. A mismatch on `ret` raises a control-protection fault. This is the strong backward-edge guarantee.

**IBT — Indirect Branch Tracking (forward edge).** Every legal target of an indirect `call`/`jmp` must begin with an **`endbranch`** instruction (`ENDBR64` on x86-64). After an indirect branch, the CPU enters a "wait-for-endbranch" state; if the very next instruction isn't `endbranch`, it faults. This means an attacker can only redirect an indirect branch to an address that *starts with `endbranch`* — i.e., a deliberately-marked function entry, not the middle of a gadget. IBT is *coarse* on its own (any `endbranch` is allowed), which is why it's often combined with a software type check (**FineIBT**) for fine granularity.

### 4. ARM Pointer Authentication (PAC): Sign the Pointer Itself

ARM takes a different, cryptographic approach. On a 64-bit ARM core, virtual addresses don't use all 64 bits — the high bits are unused. **PAC** stuffs a **cryptographic signature** (a PAC) into those spare bits:

- `PAC*` instructions compute a keyed MAC over the pointer value (and a *context* / modifier, often the stack-pointer value) and write the truncated MAC into the pointer's high bits.
- `AUT*` instructions recompute the MAC and verify it; on success they strip the signature back to a usable address, on failure they *poison* the pointer so any use faults.

The **key** lives in privileged system registers and is **not readable by user code**. So for the backward edge: at function entry, sign the return address (`PACIASP`); before returning, authenticate it (`AUTIASP`). An attacker who overwrites the return address can't produce a valid signature (they don't have the key), so the `AUT*`/`ret` faults. PAC also protects forward-edge pointers (signed function pointers, signed C++ vtable entries) — this is the basis of Apple's pervasive use in iOS/macOS on Apple Silicon.

PAC's elegance is that it needs *no extra memory region* — the integrity check rides in the pointer's spare bits. Its key residual risks: **signing oracles** (a bug that signs attacker-chosen pointers), **PAC value reuse** across contexts if the modifier is weak, and **brute force** of the short MAC if an attacker has an authentication oracle and the PAC field is small.

### 5. ARM BTI: Landing Pads for the Forward Edge

**BTI (Branch Target Identification)**, from ARMv8.5, is ARM's analog of Intel IBT: indirect branches must land on a **`BTI`** landing-pad instruction, or the CPU faults. Like IBT, it's coarse on its own (any valid landing pad is allowed) but eliminates "land in the middle of a gadget." BTI and PAC are complementary: BTI restricts *where* an indirect branch may land; PAC ensures the *pointer* used to get there is authentic. Together they sharply constrain forward-edge code reuse.

### 6. Kernel CFI: kCFI and FineIBT

The kernel is the prize target, so CFI inside the kernel matters most. Two notable schemes:

- **kCFI (KCFI)** — Clang's kernel-oriented CFI: before each indirect call, check a **type hash** stored just before the target function. It's a fine-grained, software, type-based forward-edge check designed to be small and robust enough for kernel code (no LTO-wide assumptions, works with the kernel's calling patterns).
- **FineIBT** — combines hardware **IBT landing pads** (so the branch can only reach marked entries cheaply) with a **software type check** at the landing pad (so among marked entries, only the type-correct one is allowed). It gets IBT's hardware coarse filter *and* fine-grained type precision, at low cost. Linux uses FineIBT on CET-capable CPUs.

### 7. The Honest Boundary: What None of This Stops

Every mechanism here protects *control data* — return addresses and code pointers. **None of them stops a data-only attack**, where the attacker corrupts *non-control* data (a privilege flag, a length, a file path, an `is_admin` boolean) to change behavior without ever redirecting a branch. Shadow stacks, CET, PAC, and BTI all see a perfectly legal control flow in that case. That residual is the subject of `professional.md`, and it's the senior engineer's job never to overclaim: "CET + PAC enabled" means "control-flow hijacking is hard," not "the process is secure."

---

## Code Examples

> Mechanisms and enablement only — no working oracles or signing gadgets.

### 1. Enabling Intel CET (shadow stack + IBT)

```bash
# GCC/Clang: emit CET-compatible code (endbranch + shadow-stack support).
$ gcc -fcf-protection=full app.c -o app
#   =branch  -> IBT only
#   =return  -> shadow stack only
#   =full    -> both

# Verify the marking is present in the binary:
$ readelf -n ./app | grep -i 'SHSTK\|IBT'   # GNU property notes for CET
```

What the compiler emits, conceptually:

```text
function entry:    ENDBR64            ; legal indirect-branch landing pad (IBT)
call somewhere:    (CPU pushes return addr to BOTH normal + shadow stack)
function return:   RET                ; CPU compares normal-stack addr to shadow top
                                      ; mismatch -> #CP control-protection fault
```

### 2. Enabling ARM Pointer Authentication and BTI

```bash
# Sign return addresses (PAC) and require BTI landing pads.
$ clang -mbranch-protection=standard app.c -o app
#   pac-ret        -> sign/auth return addresses
#   bti            -> require BTI landing pads
#   standard       -> pac-ret + bti
```

What the compiler emits, conceptually:

```text
function entry:    PACIASP            ; sign return addr (LR) with key + SP as context
                   BTI c              ; legal indirect-call landing pad
... body ...
function return:   AUTIASP            ; verify+strip signature; poison on mismatch
                   RET                ; ret on a poisoned pointer faults
```

The PAC key is loaded by the OS into privileged registers per context; user code can sign/auth but **cannot read the key**.

### 3. The guarantee, stated as an invariant

```text
Backward-edge invariant (shadow stack / PAC-ret):
    The address `ret` jumps to == the address the matching `call` pushed.
    Any tampering between call and ret is detected and faults.

Forward-edge invariant (IBT / BTI [+ type check]):
    An indirect call/jmp lands only on a marked entry (endbranch/BTI),
    and (with FineIBT/KCFI/CFI) only on a type-compatible one.
```

### 4. Kernel CFI knobs (Linux, conceptual)

```text
# Clang KCFI: per-call type-hash check in front of indirect calls.
CONFIG_CFI_CLANG=y

# On CET-capable x86-64, the kernel can use FineIBT:
#   hardware IBT landing pads + software type check at the pad.
CONFIG_FINEIBT=y     # (selected with X86_KERNEL_IBT + CFI_CLANG)
```

### 5. Detecting a violation at runtime

```text
# A backward-edge violation under CET surfaces as a control-protection fault:
#   signal SIGSEGV with si_code = SEGV_CPERR (control protection)
# A PAC auth failure surfaces as a fault when the poisoned pointer is used.
# Treat either as "an exploit attempt was just stopped," not a normal bug.
```

---

## Trade-offs

**Shadow stacks (hardware, CET)**

| Pros | Cons |
|------|------|
| True backward-edge *integrity*, not a tripwire. | Requires CET-capable CPU + OS support. |
| Near-zero runtime cost (hardware-managed). | Edge cases with stack-switching, `setjmp`/`longjmp`, unwinding need special handling. |
| Kills ROP's `ret`-chaining mechanism. | Doesn't touch the forward edge or data-only attacks. |

**Intel IBT**

| Pros | Cons |
|------|------|
| Cheap forward-edge coarse filter (land only on `endbranch`). | Coarse alone — needs FineIBT/type check for precision. |
| Hardware-enforced. | Requires recompilation with `endbranch` emission. |

**ARM PAC**

| Pros | Cons |
|------|------|
| No extra memory region; signature rides in spare VA bits. | Short MAC ⇒ brute-forceable *if* an auth oracle exists. |
| Key unreadable by user code; protects both edges. | **Signing oracles** (sign attacker-chosen pointers) undermine it. |
| Deployed at huge scale (Apple Silicon). | Context/modifier choice matters; weak modifiers enable reuse. |

**ARM BTI** — same shape as IBT: cheap, coarse, needs a type check for fine granularity.

---

## Coding Patterns

**Pattern: Build with full protection and verify it landed.** `-fcf-protection=full` (x86) / `-mbranch-protection=standard` (ARM), then check GNU property notes (`readelf -n`). A binary missing the notes silently runs without CET/PAC even on capable hardware.

**Pattern: Make the whole dependency chain participate.** Hardware CFI is only as strong as its weakest linked object. A single library compiled without `endbranch`/BTI marks creates "legacy" regions where enforcement is relaxed. Audit third-party binaries.

**Pattern: Handle the legitimate control-flow oddities explicitly.** `setjmp`/`longjmp`, exception unwinding, fiber/coroutine stack switches, and JITs all move or rewrite return state; they need CET/PAC-aware support or they'll fault. Use the platform's sanctioned APIs, don't hand-roll stack switches.

**Pattern: Treat a control-protection / PAC fault as an attack signal.** Log it, alert on it, and crash safely — it usually means a mitigation just stopped an exploitation attempt.

---

## Best Practices

1. **Prefer integrity over tripwires for the backward edge.** Where the platform supports it, enable hardware shadow stacks (CET) or PAC-ret instead of relying on canaries alone.
2. **Enable both edges:** shadow stack/PAC-ret (backward) *and* IBT/BTI + a type check (forward). One edge protected just relocates the attacker.
3. **Use FineIBT/KCFI/XFG for fine granularity** — landing pads alone are coarse.
4. **Audit the full binary closure for participation.** Mixed CET/non-CET or BTI/non-BTI objects weaken the guarantee.
5. **Never overclaim.** Document explicitly that these stop control-flow hijacking, not data-only attacks.
6. **Watch PAC's oracle surface.** Avoid code that signs attacker-influenced pointers; choose strong signing modifiers (e.g., SP-based context).

---

## Edge Cases & Pitfalls

- **`setjmp`/`longjmp` and C++ unwinding** legitimately change the return target; CET shadow stacks and PAC need special handling so unwinding doesn't look like an attack.
- **JIT compilers** generate code and indirect-call targets at runtime; they must emit landing pads and (for PAC) sign pointers correctly, or fault.
- **PAC signing oracles** are the dominant real-world PAC weakness: if any code path signs a pointer the attacker controls, PAC's protection collapses for that pointer type.
- **Short PAC fields + an auth oracle ⇒ brute force.** The MAC is only as many bits as the spare VA space allows; repeated authentication attempts can leak validity.
- **Coarse IBT/BTI misconception.** Landing-pad enforcement alone still allows reaching *any* marked entry; without a type check it doesn't pin down the single intended target.
- **GNU property notes missing** ⇒ silent downgrade. Capable hardware won't enforce CET/PAC on an unmarked binary.

---

## Common Mistakes

- Equating stack canaries with backward-edge *integrity*. They're a tripwire.
- Enabling forward-edge landing pads (IBT/BTI) and assuming the forward edge is "fine-grained protected" without a type check.
- Shipping a binary without verifying the CET/PAC property notes are present.
- Linking one un-instrumented library and assuming whole-program enforcement.
- Claiming hardware CFI defeats data-only attacks. It does not.
- Hand-rolling stack switches or `longjmp`-like control flow that breaks shadow-stack/PAC assumptions.

---

## Tricky Points

- **PAC needs no shadow region** because the integrity check lives *in the pointer*; the secret is the key, not a separate memory copy.
- **The shadow-stack security depends on the shadow region being unwritable by ordinary stores** — that protection is exactly what hardware (CET) provides and what software shadow stacks struggled to guarantee.
- **IBT/BTI is intentionally coarse** — it's a cheap *filter*, designed to be paired with a software type check (FineIBT/KCFI), not used alone.
- **A signing oracle is to PAC what an info leak is to a canary** — it hands the attacker the one secret the scheme relied on.
- **Backward-edge integrity does not stop JOP/COP** (no `ret` involved); you still need forward-edge enforcement.

---

## Apply it

1. State the system invariant that **Control-Flow Integrity** must protect.
2. Mark ownership, state, and failure propagation at each boundary.
3. Compare two designs under load, dependency failure, and future change.
4. Define recovery and compatibility behavior before implementation.
5. Test the riskiest assumption with a focused experiment.

## Verify your work

- The experiment supports the design with evidence, not preference.
- Failure injection shows the blast radius and recovery path.
- Compatibility checks cover old and new callers or data.
- Operational signals reveal invariant violations and recovery progress.

## Review questions

- Which invariant must remain true when Control-Flow Integrity fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
