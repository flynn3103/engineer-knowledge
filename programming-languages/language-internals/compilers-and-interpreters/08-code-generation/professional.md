# Code Generation — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Code Generation** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Table-Driven Back Ends: TableGen

A back end describes thousands of instructions, dozens of registers, multiple calling conventions, and a scheduling model. Hand-writing the C++ for all of that is unmaintainable, so LLVM uses **TableGen**, a declarative DSL. You write records describing:

- **Registers and register classes:** which physical registers exist, how they alias (e.g. `al`/`ax`/`eax`/`rax` overlap), and which classes are allocatable.
- **Instructions:** operands, the **bit-level encoding**, assembly syntax, and **selection patterns** (the IR DAG shape this instruction matches, e.g. `(add GPR:$a, GPR:$b)`).
- **Calling conventions:** which registers carry which argument/return classes, declaratively.
- **Scheduling model:** per-instruction latency and functional-unit (port) usage for each subtarget.

The build runs `llvm-tblgen` to generate C++: the instruction selector's matcher tables, the encoder/decoder, the register info, and the scheduling tables. The payoff: **adding an ISA extension** (say a new RISC-V vector instruction) is mostly *adding TableGen records*, and the matcher, encoder, and disassembler regenerate consistently. The cost: TableGen is its own learning curve, and a wrong encoding record produces bytes that *assemble* but execute as the wrong instruction — a particularly nasty miscompile.

### 2. JIT Code Generation: Compile Time Is Run Time

A JIT generates machine code while the program runs. The defining constraint is that **compilation time is part of execution time** — every cycle spent compiling is a cycle not spent running. This reshapes every earlier decision:

- **Tiered compilation.** Start interpreting or compiling with a fast, low-quality compiler (HotSpot C1, V8 Sparkplug/Maglev), and only invest in expensive optimization (HotSpot C2, V8 TurboFan) for code proven *hot* by profiling. The first tier uses cheap codegen — **linear-scan allocation**, minimal scheduling — precisely because compile speed dominates.
- **Code cache management.** Generated code lives in an executable region (the **code cache**). It must be allocated, made executable, kept within a budget (evicting cold code), and protected. Modern OSes enforce **W^X**: you write code to a writable mapping, then flip it to executable (or use dual mappings), never both at once — a security requirement (and an Apple Silicon hard rule).
- **Instruction-cache coherence.** After writing new code, you must flush/invalidate the instruction cache on architectures where I-cache and D-cache aren't coherent (ARM needs explicit cache maintenance + `isb`; x86 is largely coherent for this). Forget it and the CPU executes stale bytes.

### 3. JIT Patching: Inline Caches, OSR, Deopt

JITs don't just emit code once — they **patch** it as the program's behavior is observed:

- **Inline caches** at dynamic call sites: the first time a `obj.method()` resolves, the JIT patches the call site to a fast path assuming that receiver type, with a guard. Monomorphic → polymorphic → megamorphic transitions are patches to live code.
- **On-Stack Replacement (OSR):** a long-running loop in interpreted code can be swapped to optimized code *mid-execution*, reconstructing the optimized frame from the interpreter state. The reverse, **deoptimization**, swaps optimized back to safe code when a speculative assumption (a guard) fails.
- **Patching live code is concurrency-hard.** Other threads may be executing the very instructions you're rewriting. Techniques: patch only at safepoints, use atomically-writable patch points (a single aligned instruction-sized write), or stop the world. A torn patch — another thread fetching a half-written instruction — is catastrophic.

### 4. Position-Independent Code

Shared libraries and ASLR-enabled executables must run at any address. The back end can't bake absolute addresses into the code, so it emits **position-independent** references:

- **`rip`-relative addressing** (x86-64): reference a global as an offset from the current instruction pointer, so the same bytes work at any load address. AArch64 uses `adrp`+`add` (page-relative).
- **GOT (Global Offset Table):** for symbols whose address isn't known until load time, the code reads the address from a per-process table the loader fills in.
- **PLT (Procedure Linkage Table):** lazy-bound stubs for cross-library calls.

The back end's job is to emit the right *relocation* for each reference so the assembler/linker/loader can complete it. (The full dynamic-linking mechanics — lazy binding, symbol interposition — are covered elsewhere in this roadmap.) PIC has a small cost (an extra indirection for GOT accesses) that the back end and ABI try to minimize.

### 5. Machine-Level Peephole Optimization

After selection, allocation, and scheduling, a final **peephole** pass scans short windows of real instructions and rewrites obvious waste:

- Delete a `mov rax, rax` or a `mov` whose result is immediately overwritten.
- Combine `shl` + `add` into `lea`, or two adds into one.
- Replace `cmp x, 0; je` with `test x, x; jz`, or fold a compare into a flag-setting arithmetic instruction.
- Strength-reduce a multiply-by-constant into shifts/`lea` if selection missed it.
- Simplify branch chains and remove jumps to the next instruction.

Peephole is *local* (a few instructions) and *target-specific* (it knows the ISA's idioms). It's a cheap, high-yield cleanup that catches what the bigger passes left behind.

### 6. DWARF Debug-Info Generation

Debuggers and profilers need to map machine code back to source — and the back end must produce that mapping *as it generates code*, accurately even after optimization. DWARF carries:

- **Line table:** which source line each instruction address belongs to. Optimization scrambles this (scheduling reorders, inlining mixes functions), so the line table is intricate and approximate at `-O2`.
- **Variable location lists:** *where* each variable lives over each instruction range. Because the allocator splits live ranges, a single variable may be in `rax` here, on the stack there, and **`<optimized out>`** where it's dead. The location *list* (not a single location) encodes this movement.
- **Call Frame Information (CFI):** how to unwind the stack at every instruction — where the return address and saved registers are *right now*, accounting for prologue/epilogue and frame-pointer omission. This is what makes backtraces work when there's no frame-pointer chain.

DWARF is generated by the back end because only the back end knows the final code layout, the register/stack assignments, and the schedule. Keeping it correct under optimization is a continuous engineering tax — and a wrong location list means a debugger confidently shows you the *wrong value*.

### 7. The Full Emit Path: From `MachineInstr` to Bytes

The endgame: selected, allocated, scheduled `MachineInstr`s become bytes via the **MC layer**. It lowers each to an `MCInst`, the encoder produces the instruction bytes (using the TableGen-generated encoder), unresolved references become **relocations**, and the result is written into an object file (ELF/Mach-O/COFF) with its sections (`.text`, `.data`, `.rodata`), symbol table, and the DWARF sections. A JIT does the same in memory, then links and finalizes (resolves relocations against the running process) before flipping the page executable. This integrated-assembler path is why modern compilers don't shell out to a separate `as` — they emit object code directly, faster and with full control over relocations and debug info.

---

## Code Examples

### Reading TableGen-Described Instructions

```bash
# LLVM ships the target descriptions; inspect what a target's instructions look like:
# (in an LLVM checkout)
less llvm/lib/Target/X86/X86InstrArithmetic.td      # x86 arithmetic instrs + patterns
less llvm/lib/Target/AArch64/AArch64InstrInfo.td
less llvm/lib/Target/RISCV/RISCVInstrInfo.td

# See the generated matcher/encoder tables:
llvm-tblgen -gen-instr-info  -I llvm/include llvm/lib/Target/RISCV/RISCV.td | less
```

A simplified TableGen instruction record (illustrative) shows the encoding *and* the selection pattern together:

```text
def ADD : RVInstR<0b0000000, 0b000, OPC_OP, (outs GPR:$rd),
                  (ins GPR:$rs1, GPR:$rs2), "add", "$rd, $rs1, $rs2",
                  [(set GPR:$rd, (add GPR:$rs1, GPR:$rs2))]>;
//                  ^encoding fields                  ^selection pattern: matches (add a b)
```

The last bracket is the **DAG pattern** the selector matches; the leading fields are the **bit encoding** the MC layer emits. One record drives selection, encoding, and disassembly.

### A Minimal LLVM ORC JIT (compile and run code at runtime)

```cpp
// Sketch: take an LLVM module, JIT it, run it. (LLVM ORC v2 API, abbreviated.)
auto JIT = cantFail(LLJITBuilder().create());
cantFail(JIT->addIRModule(std::move(ThreadSafeModuleWithMyFunc)));
auto sym = cantFail(JIT->lookup("my_func"));        // triggers codegen on demand
auto *fp = sym.toPtr<int(*)(int)>();
int result = fp(41);                                // runs freshly generated machine code
```

`lookup` is where the back end runs *at runtime*: ORC compiles the requested symbol on demand, writes it into the code cache, resolves relocations against the process, and hands you a callable pointer.

### W^X and I-Cache Flush When Writing Code Yourself

```c
// The bare mechanics a JIT must handle when emitting code into memory.
#include <sys/mman.h>
#include <string.h>

void *emit(const uint8_t *code, size_t n) {
    // 1. Map writable (NOT executable yet) — W^X.
    void *mem = mmap(NULL, n, PROT_READ | PROT_WRITE,
                     MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    memcpy(mem, code, n);
    // 2. Flip to executable (drop write).
    mprotect(mem, n, PROT_READ | PROT_EXEC);
    // 3. On ARM/AArch64, the I-cache is NOT coherent with writes — flush it:
    __builtin___clear_cache((char *)mem, (char *)mem + n);   // no-op on x86, real on ARM
    return mem;   // now safely callable
}
```

Skipping step 3 on AArch64 lets the CPU execute stale instruction bytes — a classic, hard-to-debug JIT failure that "works on x86."

### Seeing PIC vs Non-PIC Codegen

```c
extern int g;
int read_global(void) { return g; }
```

```bash
gcc -O2 -fno-pic -S pic.c -o nopic.s     # absolute: mov eax, [g]
gcc -O2 -fPIC   -S pic.c -o pic.s        # rip-relative / GOT: mov rax, [rip + g@GOTPCREL]; mov eax, [rax]
```

The `-fPIC` version reaches the global through a `rip`-relative GOT load — that extra indirection is the cost of being position-independent.

### Inspecting Generated DWARF

```bash
gcc -O2 -g -c func.c -o func.o
objdump --dwarf=info       func.o | less     # variable/type/scope info
objdump --dwarf=decodedline func.o | less    # the line table (addr -> source line)
readelf --debug-dump=frames func.o | less    # CFI / unwind tables
llvm-dwarfdump --debug-loc func.o            # variable LOCATION LISTS (where each var lives)
```

In `--debug-loc` you'll see a variable described by *multiple* ranges — `DW_OP_reg` (in a register) for one address range, `DW_OP_fbreg` (on the stack) for another, and gaps where it's `<optimized out>`. That movement is live-range splitting reflected into debug info.

### Peephole, Before and After

```text
;; Pre-peephole (selection/allocation left some waste):
    mov   eax, edi
    mov   eax, eax        ; redundant self-move
    add   eax, eax        ; x + x
    cmp   eax, 0
    je    .L1

;; Post-peephole:
    lea   eax, [rdi + rdi] ; x*2 in one instruction
    test  eax, eax         ; cmp-with-0 -> test
    jz    .L1
```

The peephole pass deletes the self-move, strength-reduces `x+x` into a `lea`, and rewrites `cmp ...,0` into the cheaper `test`.

---

## Coding Patterns

### Pattern 1: Describe the Target, Don't Hand-Code It

Encode new instructions as TableGen records (encoding + pattern + scheduling) so selection, encoding, and disassembly stay in sync. Resist one-off C++ special cases; they drift.

### Pattern 2: Make the Fast JIT Tier Genuinely Fast

In the first tier, use linear-scan allocation, skip expensive scheduling, and compile lazily. Spend optimization budget only on profiled-hot code in upper tiers. The tier boundary is where the run-time budget is enforced.

### Pattern 3: Patch Only at Safe, Atomic Points

Design patch points so a rewrite is a single aligned, atomically-visible store (or only happens at a safepoint where no thread is mid-instruction). Never tear an instruction another thread can fetch.

### Pattern 4: Always Flush the I-Cache After Emitting Code

On non-x86 targets, follow every code write with an I-cache clear/`isb` (`__builtin___clear_cache` or the platform call). Bake it into the emit primitive so it's never forgotten.

### Pattern 5: Generate DWARF Alongside Code, Not After

Emit line, location, and CFI info *as* you lay out instructions and assign registers, when the truth is known. Reconstructing it afterward is lossy — especially location lists across split live ranges.

### Pattern 6: Keep Peephole Rules Verified

Each peephole rewrite must be provably semantics-preserving on the target (flags, side effects, encodings). Test them with differential execution; a "clever" peephole that drops a flag side effect is a miscompile.

---

## Best Practices

- **Treat the back end as emitting a consistent triple:** code, relocations, debug/unwind info. A change to one demands updating the others.
- **For JITs, budget compile time explicitly.** Tier, profile, and compile lazily; never run an AOT-grade optimizer on cold code at runtime.
- **Honor W^X and I-cache coherence unconditionally.** They're not optional on modern OSes/CPUs; encode them in the emit path, not as afterthoughts.
- **Make patch points atomic and safepoint-aware.** Concurrency correctness of live-code patching outranks its performance.
- **Emit PIC by default for libraries;** minimize GOT indirections via `rip`-relative/`adrp` where the symbol is local.
- **Run a final peephole, but verify every rule.** Cheap wins, but only if each rewrite is proven on the target ISA.
- **Keep DWARF honest under optimization.** A location list that says a value is in `rax` when it's actually spilled makes the debugger lie — worse than no info. Test debug info, not just code.
- **Validate encodings against a disassembler.** Round-trip every TableGen-described instruction (assemble → disassemble) to catch wrong encoding fields before they ship as silent miscompiles.

---

## Edge Cases & Pitfalls

- **A wrong TableGen encoding assembles fine and runs wrong.** The bytes are valid for *some* instruction — just not the one you meant. Round-trip testing (assemble/disassemble) is the only reliable guard.
- **JIT patching races.** Rewriting code another thread is executing, without atomicity or a safepoint, lets that thread fetch a half-written instruction — an unreproducible crash. The bug is timing, not logic.
- **Forgetting the I-cache flush.** Works on x86 (coherent), crashes mysteriously on ARM/AArch64/RISC-V where I-cache isn't coherent with stores. "Works on my Intel laptop, fails on the phone" is the signature.
- **W^X violations on hardened platforms.** Allocating RWX memory fails outright on Apple Silicon and hardened Linux. The JIT must use write-then-protect or dual mappings; assuming RWX is a portability landmine.
- **Stale or absolute addresses break PIC.** Baking an absolute address into code that's loaded at a random address (ASLR) crashes. Every cross-module reference needs the right relocation, not a constant.
- **DWARF location lists go stale.** If the allocator splits a range but the location list isn't updated, the debugger shows the wrong register's contents as the variable — confidently and silently. Worse than `<optimized out>`.
- **CFI must be correct at *every* instruction, including mid-prologue.** An exception or signal during the prologue (before the frame is fully set up) must still unwind. Coarse, function-granularity CFI is wrong; it must track each prologue/epilogue step.
- **Frame-pointer omission + bad CFI = unwindable.** At `-O2` the FP is often gone, so unwinding *depends* entirely on CFI. If the CFI is wrong, profilers and crash reporters produce garbage stacks.
- **Peephole rules that ignore flags.** Rewriting an instruction that sets condition flags into one that doesn't (or vice versa) silently breaks a downstream branch. Flag liveness must be respected.
- **Code-cache exhaustion.** A long-running JIT that never evicts cold code runs out of code-cache space and either stops optimizing (silent perf cliff) or crashes. Eviction policy is mandatory, not optional.
- **Relocation type mismatches.** Emitting the wrong relocation kind (e.g. a 32-bit PC-relative where the displacement can exceed 2GB) produces link errors or runtime truncation — common when bringing up large-memory or large-code-model builds.

---

## Apply it

1. Define the user or business outcome that **Code Generation** should improve.
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

- Which measurable outcome justifies investing in Code Generation?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
