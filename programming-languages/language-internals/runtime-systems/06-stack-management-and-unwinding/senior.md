# Stack Management & Unwinding — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Stack Management & Unwinding** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. CFI: A Table That Says "How Do I Undo This Frame"

For each function, the compiler emits an unwind *program* keyed by instruction address. At any program counter, the unwinder can ask the table three questions:

1. **What is the CFA here?** Usually expressed as "`rsp + N`" or "`rbp + 16`". The CFA is the anchor; once you have it, everything else is an offset from it.
2. **Where is the return address?** Typically "CFA − 8" on SysV. Reading it gives the caller's PC.
3. **Where are the callee-saved registers I clobbered?** E.g. "`rbx` is saved at CFA − 24." The unwinder restores them so the caller's state is correct.

Crucially, the answers *change across the function body*. Right at function entry, before `sub rsp, 32`, the CFA is `rsp + 8`; after the subtraction it's `rsp + 40`. CFI is therefore a piecewise description: "from offset 0 to 4, CFA = rsp+8; from offset 4 onward, CFA = rsp+40," and so on. The compiler tracks this with **CFI directives** (`.cfi_def_cfa_offset`, `.cfi_offset rbx, -24`, …) that the assembler turns into the FDE bytecode.

Stepping one frame = "read CFA → read return address at CFA−8 → restore saved registers → set `rsp` = CFA → set PC = return address." Repeat until you reach the top. **No frame pointer required.**

### 2. `.eh_frame` Structure: CIE and FDE

`.eh_frame` is a list of two record types:

- **CIE (Common Information Entry):** shared settings for a group of functions — the code/data alignment factors, the return-address register, the pointer encoding, and a pointer to the personality routine and LSDA for exception-bearing functions.
- **FDE (Frame Description Entry):** one per function, pointing at its CIE and carrying the per-instruction CFI program (a sequence of `DW_CFA_*` opcodes) for that function's address range.

`.eh_frame` is kept even in stripped, optimized release binaries, because the C++ runtime *needs* it to throw exceptions. `.debug_frame` is the same information for debuggers and can be stripped. This is why exceptions still work in a `strip`ped binary but `gdb` backtraces may degrade.

### 3. Windows x64: `.pdata` / `.xdata`

Windows takes a more *structured*, less general approach. Every non-leaf function has a `RUNTIME_FUNCTION` entry in `.pdata` giving its start/end addresses and a pointer to `UNWIND_INFO` in `.xdata`. The `UNWIND_INFO` is a compact list of **unwind codes** that describe exactly what the prologue did (`UWOP_PUSH_NONVOL`, `UWOP_ALLOC_SMALL`, `UWOP_SET_FPREG`, …). To unwind, the OS runtime (`RtlVirtualUnwind`) *replays the prologue in reverse* using these codes. Because the prologue is required to follow strict rules (all stack allocation and register saves up front, no interleaving), this is simpler and faster to interpret than general DWARF — but less flexible. Exceptions on Windows (SEH and C++ on top of it) drive this same table.

### 4. Two-Phase Unwinding: Search, Then Cleanup

When C++ `throw`s, control enters `__cxa_throw` → `_Unwind_RaiseException`, and the **two-phase** protocol begins:

- **Phase 1 — Search.** The unwinder walks up the stack (using CFI) *without modifying it*, calling each frame's **personality routine** to ask "does this frame have a handler for this exception type?" It keeps walking until a personality routine says "yes, I'll catch it" (or it runs off the top → `std::terminate`). Critically, *nothing is destroyed yet*. This matters: if no handler exists, the standard lets the implementation call `terminate` *with the stack intact*, so a debugger sees the original throw site — not a half-unwound stack.

- **Phase 2 — Cleanup.** Now the unwinder walks up *again*, this time actually unwinding each frame. At each frame the personality routine identifies the **landing pad** to run — code that destroys the frame's locals (RAII destructors) and, at the handler frame, transfers into the `catch` block. The unwinder restores registers and `rsp` per CFI as it goes.

The two passes exist precisely so that "is there a handler at all?" is decided *before* any destructor runs.

### 5. Personality Routine, Landing Pads, and the LSDA

The **personality routine** (for C++ on Itanium ABI: `__gxx_personality_v0`) is the language-specific brain of unwinding. At each frame the generic unwinder hands it the exception and the current PC; the personality routine consults that function's **LSDA** (Language-Specific Data Area) to decide:

- Is the current PC inside a `try` region that catches this type? (→ phase 1 says "handler found.")
- What **landing pad** should run here for cleanup? (→ phase 2 runs destructors / enters `catch`.)
- Which `catch` clause matches, by RTTI type comparison?

The LSDA is a call-site table: ranges of PCs → landing pad addresses → action records (which catch types apply). The compiler generates all of it from your `try`/`catch` and from the implicit destructors of locals. This is why exceptions are "zero-cost" on the happy path: the *only* thing in the hot path is the normal code; the entire decision apparatus sits in `.eh_frame` + LSDA, consulted only on `throw`.

### 6. Zero-Cost vs `setjmp`/`longjmp`

The older exception model used **`setjmp`/`longjmp`**: entering a protected scope ran `setjmp` (saving registers into a jmp_buf) and registered a cleanup handler on a runtime-maintained linked list; `throw` did a `longjmp` back. The cost was paid *on every protected scope, every time, even when nothing throws* — runtime work on the happy path, plus a chain of registrations.

**Table-based zero-cost** exceptions move *all* of that into static tables. The non-throwing path executes exactly the instructions it would without exceptions. You pay only when you actually throw (and then you pay a lot — unwinding is slow). This is the right trade for the common case (throws are rare), and it's why "exceptions are free until you use them" is literally true for the normal path — though the *binary* pays in size (the tables) and *throwing* pays in latency.

### 7. The Same Machinery Walks Stacks for Profilers and GC

Backtraces, sampling profilers, and garbage-collector root scanning all need to enumerate live frames — the same problem exceptions solve. A profiler interrupting a thread can unwind via CFI to attribute a sample to a call chain (or use frame pointers, or hardware LBR, if available — see the trade-offs below). A precise GC needs to find every pointer in every live frame to scan roots; it uses **stack maps** (per-safepoint metadata saying "at this PC, slots X, Y hold pointers"), conceptually a cousin of CFI but for *pointer liveness* rather than register restoration. (Stack maps and GC roots are detailed in `professional.md` and in the garbage-collection topic.)

### 8. Async-Signal-Safe Walking Is Hard

A profiler typically samples by delivering a signal and unwinding inside the handler. But full DWARF interpretation can `malloc`, take locks, or touch non-reentrant state — none of which is async-signal-safe. So in-handler unwinders must use restricted, allocation-free fast paths (frame-pointer walking, or precomputed/`mmap`'d unwind info, or hardware mechanisms). This is a core reason `-fno-omit-frame-pointer` is back in favor: frame-pointer walking is trivially signal-safe and fast, whereas DWARF unwinding in a signal handler is fragile.

---

## Code Examples

### Example 1: Look at the unwind tables in a real binary

```bash
cat > ex.cpp <<'EOF'
#include <cstdio>
struct Guard { ~Guard() { printf("cleanup\n"); } };
void inner() { Guard g; throw 42; }     // destructor must run during unwind
int main() {
    try { inner(); }
    catch (int e) { printf("caught %d\n", e); }
}
EOF
g++ -O2 ex.cpp -o ex
./ex                              # prints: cleanup / caught 42

readelf -S ex | grep -E 'eh_frame|gcc_except'   # the unwind + LSDA sections
objdump --dwarf=frames ex | head -40            # decoded CIE/FDE / CFI program
```

`objdump --dwarf=frames` shows the CIE (shared settings, return-address register, personality pointer) and one FDE per function with `DW_CFA_*` opcodes like `DW_CFA_def_cfa_offset` and `DW_CFA_offset`.

### Example 2: See the CFI directives the compiler emits

```bash
g++ -O2 -S ex.cpp -o ex.s
grep -n 'cfi_' ex.s | head -20
```

You'll see lines like:

```asm
inner:
    .cfi_startproc
    push  %rbx
    .cfi_def_cfa_offset 16     ; pushing rbx moved the CFA
    .cfi_offset 3, -16         ; rbx (DWARF reg 3) saved at CFA-16
    ; ... body, the throw ...
    .cfi_endproc
```

These directives are the *source* of the FDE bytecode. They tell the unwinder how to recompute the CFA and where `rbx` was saved at each point.

### Example 3: A leak that proves destructors run during unwind

```cpp
// If exception unwinding did NOT run destructors, this would leak.
// RAII works precisely because phase-2 cleanup invokes ~unique_ptr.
#include <memory>
#include <stdexcept>

void may_throw(bool boom) {
    auto p = std::make_unique<int[]>(1'000'000);   // owns heap memory
    if (boom) throw std::runtime_error("boom");    // unwind runs ~unique_ptr
    // ... normal use of p ...
}                                                  // ~unique_ptr also runs here
```

The single most important practical consequence of this whole topic: **C++ RAII safety is exception unwinding doing its job.** A landing pad runs `~unique_ptr`, which frees the array, as the frame is destroyed during phase 2.

### Example 4: `noexcept` changes the failure mode

```cpp
#include <stdexcept>
void leaf() { throw std::runtime_error("x"); }

void promised_safe() noexcept {
    leaf();   // if this throws, std::terminate is called immediately.
}
// `noexcept` lets the compiler emit NO unwind path through this frame.
// A throw that escapes it -> terminate(), often without unwinding above.
```

`noexcept` is a contract that lets the compiler omit unwind machinery for that frame, enabling optimizations — but a violated `noexcept` is fatal: `std::terminate`, typically with the stack *not* unwound past the violation.

### Example 5: Why a profiler shows `[unknown]` (the FPO + no-DWARF case)

```bash
# Build with FPO (default at -O2) and strip eh_frame access for the profiler:
g++ -O2 hot.cpp -o hot          # -fomit-frame-pointer is implied at -O2
perf record -g ./hot            # default 'fp' call-graph mode
perf report                     # many frames collapse to [unknown]

# Fixes:
g++ -O2 -fno-omit-frame-pointer hot.cpp -o hot   # FP walking works
# or tell perf to use DWARF (heavier; copies stack at each sample):
perf record --call-graph dwarf ./hot
# or use hardware last-branch records:
perf record --call-graph lbr ./hot
```

This is the canonical "make flame graphs work" decision tree: frame pointers (cheap, needs rebuild), DWARF (works on FPO builds, expensive per-sample), or LBR (hardware, limited depth).

---

## Coding Patterns

**Pattern: Make stacks walkable for production profiling.** For server fleets, compile with `-fno-omit-frame-pointer` (or ensure good DWARF + a DWARF-capable profiler, or rely on LBR). Decide deliberately; don't discover at incident time that your flame graphs are `[unknown]`.

**Pattern: Keep `.eh_frame` even when stripping.** Strip debug info (`.debug_*`) for size, but never strip `.eh_frame` from a binary that throws — you'll break exceptions and crash-reporter backtraces. `strip` preserves `.eh_frame` by default; custom linker scripts can wrongly drop it.

**Pattern: Annotate hand-written assembly with CFI directives.**

```asm
my_asm:
    .cfi_startproc
    push %rbp
    .cfi_def_cfa_offset 16
    .cfi_offset %rbp, -16
    mov  %rsp, %rbp
    .cfi_def_cfa_register %rbp
    ; ... body ...
    pop  %rbp
    .cfi_def_cfa %rsp, 8
    ret
    .cfi_endproc
```

Without these directives, your assembly is a black hole for unwinding: backtraces stop dead at it, and an exception propagating *through* it will fail to find the caller and call `terminate`.

**Pattern: Use `noexcept` to mark truly-non-throwing leaf code**, enabling the compiler to omit unwind paths — but only when you can *guarantee* it, since a violation is `terminate`.

**Pattern: Prefer FP-based or LBR-based sampling for low-overhead, signal-safe profiling**; reserve DWARF call graphs for one-off deep dives where FPO binaries leave you no choice.

---

## Best Practices

1. **Decide your stack-walkability strategy before you need it.** Frame pointers, DWARF, or LBR — pick one and verify flame graphs are populated in staging.
2. **Never strip `.eh_frame` from exception-bearing or crash-reported binaries.** It's a runtime requirement, not debug info.
3. **CFI-annotate every hand-written assembly routine** (`.cfi_*`). Unannotated asm breaks unwinding and exception propagation through it.
4. **Treat `noexcept` as a real contract.** Only mark code `noexcept` you can prove won't throw; a violation aborts the process.
5. **Don't do full DWARF unwinding inside a signal handler.** Use a signal-safe fast path (FP walking) or a deferred/snapshot approach.
6. **Remember that throwing is expensive.** Don't use exceptions for ordinary control flow on hot paths — the unwind cost (two passes, table interpretation) is large compared to a return code.
7. **Verify cross-language unwinding paths.** If exceptions can cross an FFI boundary, ensure every frame in between has correct unwind info, or contain throws to one side.

---

## Edge Cases & Pitfalls

- **Throwing through a C frame with no unwind info.** If an exception must propagate through C code compiled without `-fexceptions`, the unwinder may not find a path and calls `terminate`. Compile interposed C with unwind tables if exceptions cross it.
- **`noexcept` violation = `terminate`.** A function marked `noexcept` that lets an exception escape calls `std::terminate` immediately — often *without* unwinding the frames above, so destructors above don't run.
- **Destructors that throw during unwinding.** If a destructor throws *while* the stack is already unwinding for another exception, you have two active exceptions → `std::terminate`. Never let destructors throw.
- **JIT'd / dynamically generated code without registered unwind info.** A JIT must register `.eh_frame` (e.g. via `__register_frame`) or Windows function tables, or the unwinder stops at the JIT frame — breaking both exceptions and profiler backtraces.
- **DWARF unwinding in a signal handler.** Not async-signal-safe in general; can deadlock on a lock the interrupted thread already holds, or call `malloc`.
- **Tail-call elimination removes a frame.** A tail call replaces the current frame; the eliminated caller simply isn't on the stack, so backtraces legitimately omit it. This is correct behavior, not a bug — but it surprises people debugging "where did my caller go?"
- **Mismatched `.eh_frame` after binary patching / hot-patching.** If you rewrite code without updating CFI, the unwinder's offsets no longer match the prologue, producing wrong CFAs.
- **`-funwind-tables` vs `-fasynchronous-unwind-tables`.** The async variant emits CFI valid at *every* instruction (needed for signal-interrupted unwinding and profiling), not just at call sites. Profilable builds need the async tables.

---

## Apply it

1. State the system invariant that **Stack Management & Unwinding** must protect.
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

- Which invariant must remain true when Stack Management & Unwinding fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
