# Intermediate Representations — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Intermediate Representations** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Progressive lowering: one IR is rarely enough

A production compiler does not translate AST → assembly in one leap, and usually not even AST → one IR → assembly. It **lowers progressively** through a stack of representations, each more machine-specific and less language-specific than the last:

```text
   AST  --(front end)-->  HIGH-LEVEL IR    (close to source; types, high-level ops)
                                 |
                              lower
                                 v
                          MID-LEVEL IR      (three-address, SSA, target-independent opts)
                                 |
                              lower
                                 v
                          LOW-LEVEL IR      (machine-near; address modes, calling conv)
                                 |
                       instruction selection
                                 v
                            MACHINE CODE
```

Each level is the right altitude for a class of optimizations. High-level IR keeps enough structure for language-specific checks (Rust's borrow check on MIR, devirtualization, exception handling). Mid-level IR (typed SSA) is where the big target-independent optimizations live — inlining, GVN, LICM, vectorization. Low-level IR exposes machine reality — registers, addressing modes, ABI — so the back end can do instruction selection, register allocation, and scheduling. Trying to do everything at one level either loses information you need (too low) or can't express what the machine costs (too high). GCC, LLVM (with MLIR), and rustc all embrace this; the only debate is *how many* levels and *which framework* expresses them.

### 2. What makes an IR "good"

Across every real IR, the same properties recur as design goals:

| Property | Why it matters |
|----------|----------------|
| **Target-independent** (at the mid level) | One optimizer serves all back ends; the M+N narrow waist holds only if the IR doesn't bake in one machine's assumptions. |
| **Analyzable / regular** | Few, orthogonal instruction forms make writing correct passes feasible. Irregularity multiplies pass complexity. |
| **SSA** | Single definitions make use-def trivial and enable sparse, fast analyses. Nearly every optimizing mid-level IR is SSA. |
| **Typed** | Types catch malformed transforms in the verifier and drive correct lowering (size, alignment, signedness). |
| **Verifiable** | A cheap checker that rejects malformed IR turns "wrong-code miscompile" into "loud assertion at the offending pass." |
| **Explicit control flow** | A real CFG (not nested syntax) is required for dataflow; high-level loops/exceptions must be lowered to edges. |
| **Stable, documented contract** | The IR is the interface between front and back ends and between passes; if it drifts silently, everything downstream breaks. |

LLVM IR hits all of these deliberately; it is the canonical "good IR." Bytecode trades target-independence-for-optimization in favor of compactness-and-verifiability-for-distribution, then a JIT rebuilds a "good IR" in memory.

### 3. SSA construction in practice: Cytron's algorithm

The middle level sketched φ placement at the iterated dominance frontier; here is the production shape. Given a CFG:

1. **Compute dominators** (Lengauer–Tarjan, or a simple iterative algorithm for teaching) → build the **dominator tree** and **dominance frontiers**.
2. **Place φ-functions**: for each variable `v`, for each block defining `v`, insert φ for `v` at every block in the iterated dominance frontier of those defs. A φ is itself a def, so iterate (worklist).
3. **Rename**: walk the dominator tree, maintaining a version stack per variable; rewrite uses to the current version, push a fresh version on each def, and fill successor φ-arguments per edge; pop on the way back up.

This yields **minimal** SSA; adding a liveness filter yields **pruned** SSA (no φ for variables dead past the merge). LLVM builds SSA differently for some cases (`mem2reg`/`SROA` promote stack `alloca` slots to SSA registers), but the underlying theory is Cytron. Knowing this lets you read a `-print-after=mem2reg` dump and recognize the φ-functions for what they are.

### 4. Verification: the cheapest insurance in a compiler

Every serious IR ships a **verifier**. LLVM's `llvm::verifyModule` checks, among many things: every basic block ends in exactly one terminator; every use is dominated by its def; φ has one incoming value per predecessor; types match across operands; intrinsics are well-formed. GCC verifies GIMPLE/SSA invariants between passes under checking builds. The discipline is: **a transform that violates an invariant should fail loudly in the verifier at that pass, not produce wrong code three passes later.** When you add a pass, run the verifier after it during development; it converts the worst class of compiler bug (silent miscompile) into the best class (immediate, localized assertion).

### 5. Intrinsics and the IR's "escape hatch"

Real IRs can't have an opcode for everything (`memcpy`, overflow-checked add, vector shuffles, atomic fences, target-specific instructions). Instead they use **intrinsics** — pseudo-functions the optimizer understands (it knows `llvm.memcpy` has no side effects beyond the copy, can be inlined, vectorized, or lowered to a `rep movsb` or a libcall). Intrinsics keep the core IR small and regular while still letting the front end express rich operations, and they give the back end a per-target lowering point. When you see `call void @llvm.memcpy.p0.p0.i64(...)` in a dump, that's the IR's escape hatch, not a real function call.

---

## Real IRs, Surveyed

### LLVM IR — typed SSA, the canonical narrow waist

LLVM IR is register-based, fully typed, in SSA form, and exists in three isomorphic encodings: in-memory C++ objects (what passes manipulate), textual `.ll` (human-readable, `-emit-llvm -S`), and `.bc` bitcode (compact, serializable). Hierarchy: a **Module** holds **Functions**, a function holds **BasicBlocks**, a block holds **Instructions** ending in a terminator (`ret`, `br`, `switch`, `unreachable`, …). Virtual registers are SSA values written `%name`/`%0`; globals are `@name`. Types are explicit (`i32`, `i64`, `double`, `ptr`, `[4 x i32]`, `{i32, ptr}`). φ-functions are first-class (`phi`). This is the IR Clang, rustc, Swift, Julia, and many others all target — the M+N narrow waist made real.

### GCC: GENERIC → GIMPLE → RTL

GCC uses three IRs at descending altitude:

- **GENERIC** — a language-independent *tree* IR; each front end (C, C++, Fortran, Ada, …) produces it. Close to the AST; the unifying high-level form.
- **GIMPLE** — a *three-address* IR; "gimplification" flattens GENERIC into it (temporaries for subexpressions, explicit control flow). GIMPLE has a plain form and an **SSA form** where the bulk of GCC's machine-independent optimization happens (`-fdump-tree-*`).
- **RTL** (Register Transfer Language) — a *low-level*, machine-near IR written as Lisp-like s-expressions, modeling registers and machine operations. Register allocation, instruction scheduling, and final code emission happen here (`-fdump-rtl-*`).

The three-IR design predates LLVM and embodies progressive lowering: language-neutral tree → target-neutral SSA → machine-near RTL.

### JVM bytecode — stack-based, verified, for distribution

JVM bytecode is **stack-based**: instructions push/pop an implicit operand stack (`iload`, `iadd`, `invokevirtual`). It is the JVM's IR *and* its distribution format (`.class` files), chosen for compactness and **verifiability** — the bytecode verifier proves type and stack-depth consistency before any code runs. Crucially, bytecode is *not* the form the JIT optimizes: HotSpot's C1/C2 decode bytecode, simulate the operand stack to recover dataflow, and build an in-memory SSA IR (C2's is sea-of-nodes). The same pattern holds for .NET CIL and WebAssembly: a stack IR ships, a register/SSA IR optimizes.

### rustc MIR — control-flow-explicit, for analysis first

rustc's **MIR** is a CFG of basic blocks over a radically simplified Rust (no nested expressions; explicit places, moves, drops, and `Terminator`s). It was introduced not chiefly to optimize but because **borrow checking** needed a control-flow-explicit form to run dataflow (the borrow checker, later NLL/Polonius, computes liveness and region constraints over MIR). MIR also drives drop elaboration, const evaluation (the const-eval interpreter runs MIR), exhaustiveness, and a growing set of MIR optimizations. It then lowers to LLVM IR (or Cranelift IR). MIR is the textbook case that **an IR's primary purpose can be analysis, not optimization** (`rustc --emit=mir`, `-Z dump-mir=all`).

### Cranelift (CLIF) — fast, predictable compilation

Cranelift is an SSA, register-based IR/back end designed for **compile-time speed and predictability** rather than peak runtime performance: Wasmtime's Wasm JIT, rustc's debug-build back end, and others use it. CLIF is SSA with block parameters *instead of* φ-functions (an increasingly popular alternative encoding: each basic block takes arguments, and predecessors pass values — semantically equivalent to φ but cleaner to manipulate). The lesson: optimizing for *fast compilation* is a legitimate IR design axis, not just optimizing for fast output.

### Sea of nodes — V8 TurboFan, HotSpot C2

**Sea of nodes** (Cliff Click, 1995) is a graph IR that merges data-flow and control-flow into a single graph: a node is an operation; edges are *dependencies* (data and control). Unlike a CFG-of-blocks, instructions are not pinned to a block until a final **scheduling** (global code motion) phase places each node as late/early as legality allows. This freedom enables aggressive, global optimization (GVN across the whole graph, free code motion), at the cost of a more complex mental model. HotSpot's top-tier C2 and V8's TurboFan both use sea-of-nodes; their power *and* their notorious debugging difficulty both stem from it. (Note: V8 has been migrating TurboFan's frontend tiers toward a more conventional CFG IR, Turboshaft, partly because sea-of-nodes was hard to maintain — itself a senior-level lesson about IR trade-offs.)

### MLIR — many IRs, one framework

**MLIR** (Multi-Level IR) generalizes "use several IRs" into a framework where many **dialects** coexist in one module and lower into each other. A dialect is a namespaced set of ops/types (`affine`, `scf`, `linalg`, `gpu`, `llvm`, `tensor`). A machine-learning compiler might start in a high-level `tosa`/`linalg` dialect, lower through `affine` (loop nests) and `scf` (structured control flow) to the `llvm` dialect, then hand off to LLVM IR — each lowering a small, verifiable step. MLIR's bet is that the right number of IR levels is "as many as your domain needs, expressed uniformly," and it now underpins TensorFlow/IREE, Flang, and parts of the LLVM ecosystem. It is progressive lowering taken to its logical conclusion.

---

## Code Examples

### Example 1: One C function across LLVM IR

```c
int add_if_pos(int a, int b) {
    int r;
    if (a > 0) r = a + b; else r = b;
    return r;
}
```

LLVM IR after `mem2reg` (SSA, typed, φ at the merge), shape faithful to `clang -O1 -S -emit-llvm`:

```llvm
define i32 @add_if_pos(i32 %a, i32 %b) {
entry:
  %cmp = icmp sgt i32 %a, 0
  br i1 %cmp, label %then, label %else

then:
  %sum = add nsw i32 %a, %b
  br label %merge

else:
  br label %merge

merge:
  %r = phi i32 [ %sum, %then ], [ %b, %else ]
  ret i32 %r
}
```

Note: typed (`i32`, `i1`), SSA (`%cmp`, `%sum`, `%r` each defined once), explicit CFG (`br`), φ at `merge` with one `[value, pred]` pair per predecessor, and `nsw` (no-signed-wrap) flags carrying UB facts the optimizer exploits.

### Example 2: The same function as JVM bytecode (stack-based)

```text
javap -c shape:

  iload_0            // push a
  ifle else          // if a <= 0 goto else
  iload_0            // push a
  iload_1            // push b
  iadd               // a + b
  istore_2           // r = a + b
  goto end
 else:
  iload_1            // push b
  istore_2           // r = b
 end:
  iload_2            // push r
  ireturn            // return r
```

No named temporaries — values live on the operand stack. A JIT decodes this, simulates the stack (`iadd` consumes the top two pushes), and reconstructs the same dataflow LLVM had explicitly, then builds SSA.

### Example 3: GIMPLE (mid-level, three-address)

```text
-fdump-tree-gimple shape:

add_if_pos (int a, int b)
{
  int r;
  int D.1;

  if (a > 0) goto <D.2>; else goto <D.3>;
  <D.2>:
  r = a + b;
  goto <D.4>;
  <D.3>:
  r = b;
  <D.4>:
  D.1 = r;
  return D.1;
}
```

Three-address, explicit gotos, compiler temporaries (`D.1`). In *SSA* GIMPLE (`-fdump-tree-ssa`) you'd see `r_1`, `r_2`, and `r_3 = PHI <r_1(D.2), r_2(D.3)>` at the merge — GCC's φ spelled `PHI`.

### Example 4: rustc MIR (control-flow-explicit, for borrow check)

```rust
fn add_if_pos(a: i32, b: i32) -> i32 {
    if a > 0 { a + b } else { b }
}
```

```text
rustc --emit=mir shape:

fn add_if_pos(_1: i32, _2: i32) -> i32 {
    let mut _0: i32;            // return place
    let mut _3: bool;

    bb0: {
        _3 = Gt(copy _1, const 0_i32);
        switchInt(move _3) -> [0: bb2, otherwise: bb1];
    }
    bb1: {
        _0 = Add(copy _1, copy _2);  // (with overflow check in debug)
        goto -> bb3;
    }
    bb2: {
        _0 = copy _2;
        goto -> bb3;
    }
    bb3: {
        return;
    }
}
```

Places (`_0`, `_1`), `Terminator`s (`switchInt`, `goto`, `return`), explicit CFG. This is the form the borrow checker runs liveness/region dataflow over — its *reason to exist*.

### Example 5: Reading a dump to answer a real question

Suppose a hot loop isn't vectorizing. You don't guess — you dump:

```text
clang -O3 -Rpass=loop-vectorize -Rpass-missed=loop-vectorize \
      -S -emit-llvm hot.c -o hot.ll
```

Then read `hot.ll`: is the loop in canonical form (a single loop-header φ for the induction variable)? Are there loop-carried dependencies the φ-chain reveals? Is there a call inside the loop that blocks vectorization? Is a bounds check (a `br` to a trap block) still present, implying the optimizer couldn't prove the access safe? **The IR is where the answer lives.** A senior engineer reaches for the IR dump the way a junior reaches for a `printf`.

### Example 6: Cranelift CLIF — block parameters instead of φ

```text
function %add_if_pos(i32, i32) -> i32 {
block0(v0: i32, v1: i32):
    v2 = icmp sgt v0, 0
    brif v2, block1, block2

block1:
    v3 = iadd v0, v1
    jump block3(v3)        ; pass the value as a block argument

block2:
    jump block3(v1)

block3(v4: i32):           ; v4 is the "phi" — a block parameter
    return v4
}
```

CLIF encodes the merge value as a **block parameter** `v4` rather than a φ-instruction. Predecessors pass arguments on their jumps. Semantically identical to φ, but uniform with normal arguments — a clean, increasingly common SSA encoding.

---

## Coding Patterns

### Pattern 1: Drive the IR dumps before theorizing

```text
LLVM   : clang -O2 -S -emit-llvm f.c -o f.ll ; opt -print-after-all
GCC    : gcc -O2 -fdump-tree-all -fdump-rtl-all f.c   # writes f.c.NNN.<pass>
JVM    : javap -c -p Class.class
rustc  : rustc --emit=mir f.rs ; rustc -Z dump-mir=all
Cranelift: enable CLIF dumps (e.g. cargo build with the right flag / wasmtime --emit-clif)
```

Reading the actual IR beats reasoning about what you assume the compiler did.

### Pattern 2: Verify after every transform (in your own compiler)

```text
for pass in pipeline:
    pass.run(module)
    if DEBUG: verify(module)   # fail loudly here, not 3 passes later
```

### Pattern 3: Progressive lowering, one altitude at a time

```text
HIR  --lower-->  MIR/GIMPLE(SSA)  --lower-->  LIR/RTL/LLVM  --isel-->  machine
```

Each arrow is a small, separately testable lowering. Resist "lower in one giant pass."

### Pattern 4: Prefer intrinsics over new core opcodes

When the front end needs a rich operation (overflow-checked add, memcpy, a vector shuffle), emit an **intrinsic** the optimizer understands rather than bloating the core instruction set. Keeps the IR regular and gives the back end a per-target lowering hook.

### Pattern 5: Choose your SSA encoding deliberately

φ-functions (LLVM, GCC `PHI`) and block parameters (Cranelift, MLIR, Swift SIL) are equivalent. Block parameters compose better with generic argument handling and avoid special-casing φ in every pass; φ is the historical default. Pick one and be consistent.

---

## Best Practices

- **Run the IR verifier in CI and after each pass in debug builds.** It is the single highest-leverage correctness tool in a compiler.
- **Keep the mid-level IR target-independent.** The moment it encodes one machine's word size, endianness, or ABI, the narrow waist leaks and back ends diverge.
- **Lower progressively; don't skip altitudes.** Each level should be small enough to verify and test in isolation.
- **Type your IR and check types in the verifier.** Most malformed-transform bugs are type or dominance violations the verifier can catch instantly.
- **Preserve analysis-required structure until you're done with it.** Don't destroy high-level loop/exception/borrow information before the passes that need it have run.
- **Make IR printing lossless and re-parseable.** Print→parse→print should be a fixpoint; it powers tests, bug reports, and differential fuzzing.
- **Treat the IR as a versioned contract.** Between front/back ends and between passes, document invariants; silent IR drift is how multi-team compilers break.
- **Track analysis invalidation explicitly.** A pass that changes the CFG must invalidate cached dominator trees, loop info, and alias analysis, or downstream passes act on lies.

---

## Edge Cases & Pitfalls

- **Stale dominator tree / loop info after a CFG change.** Caching analyses is essential for speed and lethal if a transform forgets to invalidate them.
- **Undefined behavior modeling.** LLVM's `undef`/`poison` are not "garbage we ignore"; they encode UB so the optimizer can reason soundly. Misusing them (or front ends emitting UB the optimizer then "exploits") produces baffling miscompiles.
- **Irreducible control flow** from `goto`/computed jumps breaks the clean reducible-loop assumptions some passes make; compilers node-split or bail.
- **Bytecode verification at merges**: every path to a join must agree on operand-stack depth and types, or the JVM/CLR verifier rejects the class. A lowering bug surfaces as a verify error, not a wrong result.
- **Sea-of-nodes debuggability**: with nodes floating until scheduling, "where did this come from?" has no line number; reproductions are hard and tooling is specialized.
- **Intrinsic lowering gaps**: a target with no efficient lowering for an intrinsic falls back to a libcall, silently regressing performance you assumed was inlined.
- **MIR vs final codegen divergence**: optimizing on MIR and again on LLVM IR means a behavior can depend on which level a pass ran; keep the contract between levels precise (e.g., overflow checks are debug-only and must be consistently inserted/elided).
- **φ vs block-param mismatch when interoperating**: bridging an IR that uses φ with one that uses block parameters requires a faithful translation of merge semantics, including critical-edge handling.

---

## Common Mistakes

1. Reasoning about "what the compiler did" instead of dumping the IR and reading it.
2. Skipping the verifier, then chasing a miscompile across five passes instead of catching it at one.
3. Baking target details into the mid-level IR and wondering why a new back end misbehaves.
4. Optimizing stack bytecode directly instead of lifting to a register/SSA IR.
5. Forgetting to invalidate dominator/loop/alias analyses after a CFG-mutating pass.
6. Treating `undef`/`poison` as "don't care" rather than precise UB markers.
7. Adding a bespoke core opcode where an intrinsic would have kept the IR regular.
8. Assuming one IR level suffices; cramming machine-specific and language-specific concerns into the same form.
9. Mishandling critical edges when bridging φ-based and block-parameter IRs.
10. Believing sea-of-nodes is strictly superior; ignoring the maintainability cost that pushed V8 toward Turboshaft.
11. Reading `-O0` IR to judge optimization (it's deliberately un-optimized; promote with `mem2reg`/`-O1`+).
12. Forgetting MIR's main job is analysis (borrow check), then being confused that MIR optimizations are comparatively modest.

---

## Tricky Points

- **LLVM IR is three encodings of one thing.** `.ll` text, `.bc` bitcode, and in-memory objects are isomorphic; passes work on the objects, you read the text.
- **GCC's `PHI` and LLVM's `phi` are the same φ;** GIMPLE-SSA and LLVM IR are both mid-level typed-ish SSA, arrived at independently.
- **Bytecode is an IR *and* a wire format;** its design optimizes the second job, which is why JITs rebuild a different IR for the first.
- **MIR proves the point that IRs exist for analysis, not only optimization.** Borrow checking is the reason MIR exists; optimization came later.
- **Block parameters == φ-functions.** Two encodings, identical semantics; Cranelift/MLIR/Swift-SIL chose block params for uniformity.
- **Sea-of-nodes' superpower (floating nodes) is also its kryptonite (no fixed positions to debug).** The same property explains both its peak performance and its maintenance burden.
- **MLIR doesn't replace LLVM IR;** it lowers *to* the `llvm` dialect and then to LLVM IR. It's an additional, multi-level front of the same pipeline.
- **`nsw`/`nuw`/`exact`/`fast` flags on LLVM instructions carry UB/semantic facts** the optimizer relies on; they're not decoration.

---

## Apply it

1. State the system invariant that **Intermediate Representations** must protect.
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

- Which invariant must remain true when Intermediate Representations fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
