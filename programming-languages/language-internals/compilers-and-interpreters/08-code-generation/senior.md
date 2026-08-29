# Code Generation — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Code Generation** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. LLVM's Two Selection Paths: SelectionDAG vs GlobalISel

**SelectionDAG** is LLVM's mature path. For each basic block, LLVM builds a **DAG** (not a tree — shared subexpressions are shared nodes) of target-independent operations, then:

1. **Type and operation legalization** — eliminate types and operations the target can't handle directly. An `i128` add on x86-64 becomes a sequence of `i64` operations with carry; an unsupported vector width is split or widened.
2. **DAG combine** — peephole rewrites on the DAG (fold `(add x (mul y z))` into an FMA node if the target has FMA; collapse address computations).
3. **Instruction selection** — pattern-match DAG nodes against target patterns (mostly generated from TableGen), producing target `MachineSDNode`s. This is DP-style tiling generalized to a DAG.
4. **Scheduling** — order the selected nodes into a linear sequence of `MachineInstr`s, with a pre-RA scheduler that's pressure-aware.

The downside: SelectionDAG is **per-basic-block**, so it can't do cross-block selection, and building/legalizing the DAG is a real compile-time cost.

**GlobalISel** is the newer path, designed to be **global** and **SSA-based**, working directly on Machine IR rather than a separate DAG:

- **IRTranslator** — LLVM IR → generic Machine IR (gMIR), one-to-one, SSA, virtual registers.
- **Legalizer** — make gMIR legal for the target.
- **RegBankSelect** — assign each virtual register a **register bank** (GPR vs vector).
- **InstructionSelect** — select target instructions on gMIR.

GlobalISel's bets: lower compile time at `-O0` (no DAG construction), better support for global optimizations, and a cleaner, more debuggable pipeline. It's the default for AArch64 at `-O0` and growing elsewhere. The two paths coexist because each wins different trade-offs.

### 2. Why DAG (not Tree) Selection Matters

Tree covering assumes each value is used once (a tree). Real code has **shared subexpressions** — a value computed once, used several times — making the IR a DAG. Optimal *DAG* covering is NP-hard (unlike trees), so DAG selectors use heuristics and accept suboptimality. The shared node also forces a decision: do you **rematerialize** the subexpression at each use (cheap if it's a constant or address) or **compute once and keep in a register** (cheap if the value is expensive but register pressure allows)? This rematerialization-vs-reuse choice is a recurring back-end theme that trees never expose.

### 3. SSA-Based Register Allocation

The classical Chaitin insight predates a key theorem: **the interference graph of a program in SSA form is chordal**, and **chordal graphs are optimally colorable in polynomial time**. This reframed allocation:

- Under SSA, you can compute the exact **register pressure** (max number of simultaneously live values) at every program point, and you *know* you can color with that many registers — no iterative spill-and-retry needed to find the chromatic number.
- Allocation splits into two cleaner phases: **spilling** (decide which values live in memory to get pressure ≤ K everywhere) and **coloring** (assign registers, guaranteed to succeed once pressure ≤ K, because the SSA graph is chordal).
- After allocation, **SSA must be destroyed**: `phi` nodes become **parallel copies** on the predecessor edges. Doing this correctly (handling swap cycles among registers, e.g. needing a temp or `xchg`) is the subtle part — the "lost copy" and "swap" problems.

This is why modern allocators (LLVM's greedy allocator, and research allocators) think in terms of **live-range splitting** and **pressure** rather than a monolithic interference graph: split a long live range so it occupies a register where it's hot and spills where it's cold, instead of spilling the whole thing.

### 4. LLVM's Greedy Allocator and Live-Range Splitting

LLVM's default allocator (`greedy`) is not pure linear scan and not pure graph coloring — it's a priority-based allocator built on live-interval analysis with aggressive **live-range splitting**:

- Live ranges are prioritized (longer/hotter first) and assigned registers.
- When a range can't get a register, the allocator tries **splitting** it (around a loop, at a block boundary, around a call) before spilling, so only the genuinely cold parts go to memory.
- **Rematerialization** is preferred over spill/reload whenever the value is cheap to recompute (constants, simple address arithmetic), avoiding memory traffic entirely.

This captures the practical truth that all-or-nothing spilling is too coarse; the granularity of the *split* is where modern allocation quality comes from.

### 5. Scheduling in a Modern Back End

Production scheduling happens in (up to) three places:

- **Pre-RA scheduling** (on the SelectionDAG or MIR) — order to expose ILP while **tracking register pressure**, throttling parallelism before it forces spills. This directly addresses the phase-ordering conflict by making the scheduler *pressure-aware*.
- **Post-RA scheduling** — after allocation, re-order to fix false dependences introduced by register reuse and to fill latency gaps now that real registers are known.
- **Machine pipeliner** (software pipelining / modulo scheduling) for hot loops on in-order or VLIW targets.

The scheduler is driven by a **machine model** (per-instruction latency, throughput, functional-unit/port usage) — in LLVM, this is the per-subtarget scheduling model (itineraries or the newer per-subtarget `SchedMachineModel`). The model is *microarchitecture-specific*: scheduling for a Cortex-A53 (in-order) differs sharply from scheduling for a modern out-of-order x86 core, where the hardware reorders and the compiler's job narrows mostly to *not creating long dependence chains* and *not over-pressuring registers*.

### 6. The Phase-Ordering Battle, at Production Scale

The middle page framed the scheduling-vs-allocation conflict. At senior scale, the resolution strategies are concrete:

- **Pressure-aware pre-RA scheduling.** Bound ILP exposure by tracking how close pressure is to K; back off when near the cliff.
- **Live-range splitting instead of spilling.** Reduces the cost of having lost the phase-ordering bet — the spill is surgical, not wholesale.
- **Post-RA re-scheduling.** Recover scheduling freedom lost to allocation's false dependences.
- **Integrated approaches** (research and some production): combine selection/scheduling or scheduling/allocation into one ILP/heuristic formulation. Expensive; used selectively.

There is still no global optimum. The senior skill is knowing *which* compromise a given compiler made and how to nudge it (pass ordering, pressure thresholds, target hints).

### 7. Calling-Convention Lowering as a Back-End Pass

ABI lowering is a substantial, target-specific back-end stage, not a detail. It materializes:

- **Argument and return placement** per the target ABI (System V AMD64, AAPCS64 for AArch64, the RISC-V calling convention). This includes classifying aggregates (split a struct across registers vs pass by hidden pointer), `sret` for large returns, and varargs handling.
- **Prologue/epilogue** generation: claim the frame, align the stack to the ABI requirement, save callee-saved registers actually used, set up (or omit) the frame pointer, and emit the matching teardown.
- **Stack frame layout**: spill slots, local variables, the red zone (System V allows 128 bytes below `rsp` without adjustment), and shadow space (Windows x64). Mistakes here corrupt the stack silently. (The cross-language consequences of this are the subject of the FFI section of this roadmap.)

### 8. Targets Shape Everything

- **x86-64 (CISC):** variable-length encoding (1–15 bytes), two-operand destructive instructions (`add dst, src` overwrites `dst`), rich addressing modes and `lea`, few GPRs (16, several reserved), strong (TSO) memory model. Selection is high-payoff (big tiles); allocation is tight (register-poor); the assembler is complex.
- **AArch64 (RISC):** fixed 4-byte instructions, 31 GPRs + 32 vector registers, three-operand non-destructive form, shifted-register and extended-register operands, no condition-code-laden every instruction (ARM64 dropped most predication that ARM32 had). Register-rich → fewer spills; clean selection; scheduling matters on in-order cores.
- **RISC-V (clean RISC):** deliberately minimal base ISA with optional extensions (M, A, F, D, C, V). Selection is simple and uniform; the compressed (C) extension brings back some size optimization; the modularity means the back end must respect which extensions the subtarget has.
- **WebAssembly (structured stack machine):** *not a register machine at all*. Code generation targets a stack of operands and **structured control flow** (`block`/`loop`/`if`/`br` to labels, no arbitrary jumps). There's effectively **no register allocation in the classical sense** — values live on the operand stack and in locals; the Wasm engine's *own* JIT does real register allocation when it compiles Wasm to machine code. Emitting Wasm means reconstructing structured control flow (the relooper / stackifier problem) and managing the operand stack, a fundamentally different codegen shape.

---

## Code Examples

### Inspecting LLVM's SelectionDAG

```bash
# Emit LLVM IR, then watch the back end pick instructions on the DAG.
clang -O2 -S -emit-llvm dot.c -o dot.ll
llc -O2 -march=x86-64 dot.ll -o dot.s

# See the SelectionDAG before/after selection (graphviz):
llc -O2 -view-isel-dags dot.ll       # opens DAG visualizations (needs Graphviz)
# Or dump textually with debug output:
llc -O2 -debug-only=isel dot.ll 2>&1 | less
```

`-view-isel-dags` (and `-view-legalize-dags`, `-view-sched-dags`) literally shows you the DAG the selector tiles — the senior-level "look under the hood."

### Forcing SSA-Based / GlobalISel Path on AArch64

```bash
# GlobalISel is the default at -O0 for AArch64; force it explicitly at any level:
clang --target=aarch64-linux-gnu -O0 -mllvm -global-isel -S dot.c -o dot_gisel.s
# Inspect the generic Machine IR stages:
llc -march=aarch64 -global-isel -stop-after=legalizer dot.ll -o dot.legal.mir
```

`-stop-after` lets you freeze the pipeline at any stage and read the MIR — invaluable for understanding where a decision was made.

### Watching Live-Range Splitting and Spills

```bash
# Show register-allocation decisions from the greedy allocator:
llc -O2 -debug-only=regalloc dot.ll 2>&1 | grep -E "split|spill|remat" | head
```

You'll see lines reporting live-range *splits* around loops and *rematerialization* of constants — the modern alternative to wholesale spilling.

### The Phi/Swap Problem (SSA Destruction)

When SSA is destroyed, `phi`s become parallel copies. If two values must swap registers across an edge, a naive sequential copy clobbers one:

```text
;; Needed on a loop back-edge:  r1 <- r2 ,  r2 <- r1   (a swap)

;; WRONG (sequential): clobbers r2's old value
mov r1, r2        ; r1 now holds old r2
mov r2, r1        ; r2 = r1 = old r2   -- old r1 is LOST

;; CORRECT: break the cycle with a temp (or xchg on x86)
mov tmp, r1
mov r1,  r2
mov r2,  tmp
;; x86 alternative:
xchg r1, r2
```

Detecting copy cycles and inserting the temp (or `xchg`) is exactly what a correct parallel-copy sequentializer does. Getting it wrong is a classic, subtle miscompile.

### Pressure-Aware Scheduling, Observed

```c
// Unrolling exposes ILP but raises pressure. Compare schedulers' choices.
void axpy(float *y, const float *x, float a, long n) {
    for (long i = 0; i < n; i++) y[i] = a * x[i] + y[i];   // FMA candidate
}
```

```bash
clang -O3 -march=native -S axpy.c -o axpy.s      # look for vfmadd + unroll
# Compare with pressure tracking disabled vs enabled (illustrative flags vary):
llc -O3 -mcpu=generic axpy.ll -o axpy_generic.s
```

On a FMA-capable target you'll see `vfmadd...` instructions (selection fusing `a*x + y`) and the loop unrolled with multiple vector accumulators — the scheduler exposing ILP up to the register budget.

### WebAssembly Codegen Is a Different Shape

```bash
clang --target=wasm32 -O2 -S axpy.c -o axpy.wat   # textual Wasm
```

The output uses `local.get`, `f32.mul`, `f32.add`, `local.set`, and structured `loop`/`block`/`br_if` — an operand stack and labeled structured control flow, with *no register names at all*. Real register allocation happens later inside the Wasm engine's own JIT. This is the "different kind of codegen target" made concrete.

---

## Coding Patterns

### Pattern 1: Locate the Decision with `-stop-after` / `-print-after-all`

When a back-end result surprises you, bisect the pipeline. `llc -stop-after=<pass>` and `-print-after-all` let you read the MIR at each stage and pinpoint where the value spilled, the instruction was selected, or the schedule changed.

### Pattern 2: Express Patterns in TableGen, Not Hand-Code

For target-specific selection, encode the IR→instruction patterns declaratively (TableGen) so the generated matcher stays consistent and complete. Hand-written selection rots and misses cases. (TableGen detail lives in `professional.md`.)

### Pattern 3: Prefer Rematerialization Hints for Cheap Values

When defining instructions, mark constants and simple address computations as rematerializable so the allocator recomputes rather than spills them. This is one of the highest-leverage quality levers.

### Pattern 4: Provide an Accurate Scheduling Model

A back end is only as good as its machine model. Supply correct per-instruction latency and port/throughput data for the subtarget; the scheduler's pressure-vs-ILP decisions depend on it.

### Pattern 5: Get SSA Destruction Right First

Before optimizing allocation quality, ensure parallel-copy sequentialization handles swap cycles correctly. A fast allocator that miscompiles a swap is worthless. Correctness, then quality.

---

## Best Practices

- **Reason in pressure, splits, and remats — not monolithic interference graphs.** That's how modern allocators actually behave; your mental model should match.
- **Make the scheduler pressure-aware.** Exposing ILP blindly trades scheduling wins for spill losses. Bound parallelism by the register budget.
- **Pick the selection path by opt level.** GlobalISel for fast `-O0` builds; SelectionDAG (today) for top-tier optimized output, where supported.
- **Treat ABI lowering as a first-class, target-specific pass.** Aggregate classification, varargs, red zone, callee-saved selection, and stack alignment are where silent corruption hides.
- **Respect the target's nature.** Don't impose register-allocation thinking on a Wasm back end, or RISC simplicity assumptions on x86's CISC tiling.
- **Use the framework's introspection.** `-view-*-dags`, `-debug-only=isel/regalloc/misched`, `-stop-after` — these are how seniors verify, not guess.
- **Validate against the machine model and real hardware.** Scheduling decisions are microarchitecture-specific; confirm on the actual core, especially for in-order/VLIW targets where the schedule is load-bearing.

---

## Edge Cases & Pitfalls

- **SelectionDAG's per-block scope hides cross-block wins.** A subexpression spanning two blocks won't be selected together; don't expect global instruction selection from the DAG path.
- **Legalization can balloon code.** Splitting an illegal wide type or vector into many legal operations can produce far more instructions than the IR suggested. The blowup is legalization, not your code.
- **SSA destruction swap cycles.** Parallel copies that form a cycle (r1↔r2) need a temp or `xchg`; a naive sequential lowering silently corrupts a value. This is a top-tier miscompile source.
- **Rematerialization needs a faithful cost model.** Recomputing something that's secretly expensive (a load that aliases, a value with side effects) is wrong or slow. Only genuinely cheap, side-effect-free values qualify.
- **Pressure estimates lie under aliasing/calls.** Calls clobber caller-saved registers and create pressure spikes the naive estimate may miss; values live across calls force callee-saved usage or spilling.
- **GlobalISel maturity gaps.** Outside well-supported targets (AArch64), GlobalISel may fall back to SelectionDAG or generate lower-quality code at high opt. Don't assume parity everywhere.
- **Wasm has no `goto`.** Back ends targeting Wasm must reconstruct structured control flow from an arbitrary CFG (the relooper/stackify problem); irreducible control flow needs extra machinery. Classical jump-based codegen doesn't translate directly.
- **The machine model drives everything — and is often wrong.** Inaccurate latencies/ports make the scheduler optimize for a CPU that doesn't exist. On out-of-order cores the error is hidden; on in-order cores it directly hurts.
- **Pre-colored ABI registers constrain selection and allocation.** Argument/return/`rsp` registers are fixed; the allocator and selector must route around them, and forgetting one corrupts the call.
- **`-O3` vectorization changes what the back end sees.** Wide vector types and FMA candidates arrive from the middle end; a "missed" FMA may actually be a legalization or target-support issue, not a selection bug. Check the type legality before blaming selection.
- **Frame-pointer omission breaks naive unwinding.** At high opt the FP is often gone; debuggers and profilers must use unwind tables (DWARF CFI). Tools that assume an FP chain will misread optimized stacks.

---

## Apply it

1. State the system invariant that **Code Generation** must protect.
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

- Which invariant must remain true when Code Generation fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
