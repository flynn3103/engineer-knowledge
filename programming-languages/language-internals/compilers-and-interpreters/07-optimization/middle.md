# Optimization — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Optimization** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The CFG and Basic Blocks

Optimizers don't work on source text; they work on an **intermediate representation** arranged as a **control-flow graph**. First, the linear instruction stream is chopped into **basic blocks** — straight-line runs with a single entry and single exit. A block ends at any branch, jump, return, or label that's a branch target. Then directed edges connect a block to every block control can flow to next.

```
        ┌──────────────┐
        │ B0: a = 1     │
        │     b = 2     │
        │  if a<b goto  │
        └───┬───────┬───┘
            │true   │false
        ┌───▼──┐ ┌──▼────┐
        │B1:   │ │B2:     │
        │ x=10 │ │ x=20   │
        └───┬──┘ └──┬─────┘
            └───┬───┘
         ┌──────▼──────┐
         │ B3: use x    │  ← merge point
         └─────────────┘
```

Every dataflow analysis is "walk this graph, carrying facts, until they settle." The graph structure — especially merge points like B3 where two paths join — is the whole reason analysis is non-trivial: at a merge, you must *combine* the facts arriving from different predecessors.

### 2. The Four Canonical Analyses

Four classic analyses cover most of what optimizers need. They differ along two axes — **direction** (forward/backward) and **combination** (may/must) — and that's the whole taxonomy.

**Reaching definitions (forward, may).** At each point, which assignments *could* be the source of a variable's current value? Used by constant propagation (if exactly one definition reaches, and it's a constant, propagate it). A definition "reaches" if there's *some* path from it to the use with no intervening redefinition — hence **may** (union at merges).

**Live variables (backward, may).** At each point, which variables *may* be read later before being overwritten? Flows **backward** (a variable is live if a *future* use exists). The foundation of **dead store elimination** (a store to a non-live variable is dead) and **register allocation** (only live variables need registers). May-analysis: live on *some* future path.

**Available expressions (forward, must).** At each point, which expressions are already computed on *every* path to here, with operands unchanged since? The basis for **common subexpression elimination** — if `a+b` is available, don't recompute it. **Must**-analysis: available on *all* paths, so it uses **intersection** at merges.

**Very-busy / anticipated expressions (backward, must).** Expressions that *will* be computed on every path forward before their operands change. Used for **code hoisting** (compute once early instead of in multiple successors).

| Analysis | Direction | Combine (meet) | Enables |
|----------|-----------|----------------|---------|
| Reaching definitions | Forward | Union (may) | Constant/copy propagation |
| Live variables | Backward | Union (may) | Dead store elim, register alloc |
| Available expressions | Forward | Intersection (must) | CSE |
| Very-busy expressions | Backward | Intersection (must) | Code hoisting |

That 2×2 (forward/backward × may/must) is the entire conceptual map. Learn it and every dataflow analysis you meet slots into a corner.

### 3. The Lattice / Fixpoint Framework

Here's *why* iterating to a fixpoint works and terminates.

The set of possible dataflow facts at a point forms a **lattice**: a partially ordered set where any two elements have a greatest-lower-bound (**meet**) and least-upper-bound (**join**). For "available expressions," the lattice elements are sets of expressions ordered by ⊆, meet is ∩. For constant propagation, each variable's lattice is `⊤ (unknown) → constants → ⊥ (not-a-constant)`.

Each basic block has a **transfer function** `OUT = gen ∪ (IN − kill)` (for the classic bit-vector analyses): the block *generates* some facts and *kills* others. At a merge, the **meet operator** combines predecessors' OUT sets into the successor's IN.

The algorithm: initialize every block's facts to the lattice top (or bottom), then repeatedly apply transfer functions and meets until **nothing changes** — the **fixpoint**. Termination is guaranteed because the lattice has **finite height** and the transfer/meet functions are **monotone** (they only move facts in one direction along the lattice). A monotone function on a finite-height lattice *must* converge. This is the theoretical backbone (Kildall's framework, 1973); it's the reason the loop "iterate until stable" always halts.

```
worklist ← all blocks
while worklist not empty:
    B ← pop()
    IN[B]  = meet over predecessors of OUT[p]
    OUT[B] = transfer(B, IN[B])
    if OUT[B] changed:
        push all successors of B   # their inputs may now differ
```

The **worklist** variant only re-visits blocks whose inputs changed — the efficient form used in practice.

### 4. SSA Form: One Assignment Per Variable

The classic analyses above are *correct* but can be *slow* and imprecise (they track facts per program point, and "which definition reaches" requires chasing all paths). **SSA form** fixes this structurally.

In SSA, **every variable is assigned exactly once.** When source code reassigns `x`, SSA renames each assignment: `x1`, `x2`, `x3`. Now each *use* refers to exactly one definition — no analysis needed to find "the reaching definition," it's literally the name. Use-def chains become trivial.

The catch is merge points. If `x` is assigned in two branches and used after they join, *which* version does the use see? SSA inserts a **phi node** (φ) at the merge:

```
B1: x1 = 10
B2: x2 = 20
B3: x3 = φ(x1 from B1, x2 from B2)   ← selects based on which edge was taken
    use x3
```

A phi is a pseudo-instruction meaning "x3 is x1 if we came from B1, x2 if from B2." It restores single-assignment at merges. Phi placement is computed from **dominance frontiers** (the precise boundary where a definition's influence meets other definitions) — Cytron et al.'s classic algorithm. Phis are conceptual; they're lowered back to real moves before codegen ("out-of-SSA").

Why this matters: in SSA, **every variable has one definition**, so constant propagation, value numbering, and dead-code elimination become nearly local — walk the use-def edges directly instead of solving a global dataflow problem. This is why SSA is universal in modern optimizers.

### 5. SSA-Powered Optimizations

**Sparse Conditional Constant Propagation (SCCP).** The killer SSA optimization. It propagates constants *and* discovers unreachable branches *at the same time* — and that combination finds constants neither would find alone. If `x3 = φ(x1, x2)` but the analysis proves the edge feeding `x2` is unreachable (because a branch condition folded to a constant), then `x3 = x1`; if `x1` is constant, `x3` is too. Doing constant propagation and reachability *separately* misses these; SCCP fuses them into one fixpoint over the SSA graph. This is strictly more powerful than plain constant propagation.

**Global Value Numbering (GVN).** Assigns a "value number" to every computation such that two computations with the same number are *guaranteed* equal. Then redundant ones are eliminated — a smarter, global CSE. In SSA, `a1 = b + c` and `a2 = b + c` (same `b`, same `c`) get the same value number and the second is replaced by the first. GVN can see equalities across branches that local CSE misses.

**Sparse / aggressive DCE.** In SSA, a definition is dead iff it has no uses (trivially checkable). Aggressive DCE assumes everything is dead unless proven needed (transitively from observable effects backward), deleting more than conservative DCE — including whole computation chains feeding only-dead values.

These all rely on SSA's single-definition property to be cheap. That's the payoff.

---

## Code Examples

### Reaching definitions enabling constant propagation

```c
int f(int cond) {
    int x = 5;          // d1: x = 5
    if (cond) x = 7;    // d2: x = 7
    return x + 1;       // which definitions reach here? {d1, d2}
}
```

Reaching-definitions says **both** `d1` and `d2` reach the `return` (it's a *may* analysis, union at the merge). Because two *different* constants reach, constant propagation **cannot** replace `x` with a single constant here — it must keep `x`. Contrast: if both branches set `x = 5`, only the constant 5 reaches and the return folds to `6`. The analysis result directly gates the optimization.

### Live variables enabling dead-store elimination

```c
int g(int a) {
    int x = a * a;   // store 1
    x = a + 1;       // store 2 — store 1 was never read: DEAD
    return x;
}
```

Backward live-variable analysis finds that `x` is **not live** immediately after store 1 (its value is overwritten by store 2 before any read). So store 1 (`x = a*a`) is a **dead store** and is eliminated, along with the multiply that feeds it (via DCE).

### SSA form with a phi node

```
;; source: int x; if (c) x = 10; else x = 20; return x;
B_entry:
    br c, B_then, B_else
B_then:
    x_1 = 10
    br B_merge
B_else:
    x_2 = 20
    br B_merge
B_merge:
    x_3 = phi [x_1, B_then], [x_2, B_else]
    ret x_3
```

The phi at `B_merge` selects `x_1` or `x_2` based on the incoming edge. Every use (`ret x_3`) now references exactly one definition.

### SCCP beating plain constant propagation

```c
int h(void) {
    int flag = 1;          // constant
    int x;
    if (flag) x = 42;      // flag folds to true → else branch unreachable
    else      x = compute_something();
    return x;
}
```

Plain constant propagation sees `x` could be `42` *or* `compute_something()` and gives up. **SCCP** proves `flag == 1`, marks the `else` edge **unreachable**, so only `x = 42` reaches the (implicit) phi — and returns the constant `42`, deleting `compute_something()` entirely. Fusing constant-propagation with reachability is what makes the difference.

### Inspecting LLVM IR after passes (command line)

```bash
# Emit unoptimized LLVM IR, then run mem2reg to build SSA, then SCCP:
clang -O0 -S -emit-llvm -Xclang -disable-O0-optnone f.c -o f.ll
opt -passes='mem2reg,sccp,instcombine,dce' -S f.ll -o f.opt.ll

# See exactly which transformations fired:
opt -passes='sccp' -S f.ll -print-changed -o /dev/null
```

`mem2reg` is the pass that *promotes stack slots into SSA registers* — it's where phi nodes get created. Reading `f.opt.ll` shows the phi nodes and the propagated constants directly.

---

## Coding Patterns

- **Shrink the live range of values the optimizer must track.** Compute close to use; don't keep a value live across an opaque call if you can recompute it cheaply. Smaller live ranges = simpler analysis = better register allocation.
- **Break aliasing the analysis can't see through.** Load a field into a local at the top of a hot loop; if the analysis can prove the local doesn't alias the memory written inside, it keeps the value in a register (this is hand-LICM when the compiler can't prove invariance).
- **Make branches statically decidable.** If a condition is a compile-time constant, SCCP can prune the dead branch and cascade. Hiding the constant behind a function call or non-`const` global blocks it.
- **Prefer single-assignment style in source too.** Code that assigns each logical value once (rather than reusing one mutable variable for many purposes) maps cleanly to SSA and is easier for *both* the compiler and the reader.

---

## Best Practices

- **Use `-fdump`/`opt -print` to verify, don't guess.** When you expect an optimization, confirm it fired by reading the post-pass IR. Intuition about what the analysis can prove is often wrong.
- **Give the analyzer information.** `const`, `restrict`, `[[gnu::pure]]`/`__attribute__((const))`, `final`, and avoiding global mutable state all *widen* what dataflow can prove.
- **Don't pre-lower to SSA in your head.** Write clear, possibly-mutating source; the compiler builds SSA far better than manual single-assignment contortions, which can hurt readability without helping.
- **Respect the conservatism.** If the compiler won't hoist something, ask "what fact can't it prove?" rather than assuming a compiler bug. The usual culprits: a pointer that might alias, a call that might have side effects, a value that might escape.

---

## Edge Cases & Pitfalls

- **Aliasing kills available-expressions facts.** `*p = ...; x = a + b; *q = ...; y = a + b;` — if `q` might alias the memory holding `a` or `b`, the second `a+b` is *not* provably available and CSE is blocked. Pointer analysis precision directly limits optimization.
- **Opaque function calls are analysis barriers.** A call to a function the compiler can't see (no body, not pure) is assumed to read and write *all* reachable memory. It clobbers available-expression and reaching-definition facts across the call. This is a major reason inlining (which removes the barrier) is so powerful.
- **Phi nodes are not real instructions.** They have no machine encoding; they're lowered to moves during out-of-SSA. Naively lowering parallel phis can introduce bugs (the "lost copy" and "swap" problems) — getting this right is subtle compiler engineering.
- **`volatile` is a hard fence for dataflow.** A `volatile` access can't be eliminated, duplicated, or reordered relative to other volatiles. Dataflow analyses must treat it as both a definition and a use of "the outside world."
- **Loops need fixpoint iteration, not one pass.** Because a loop's back-edge feeds facts from the bottom back to the top, you can't compute facts in a single forward sweep — you iterate until the loop's facts stabilize. Forgetting this is the classic dataflow-implementation bug.
- **Precision has diminishing returns.** A more precise (and expensive) analysis might unlock one extra optimization. Production compilers deliberately stop at a "good enough" precision because the compile-time cost isn't worth it — which is why some hand-obvious optimizations never fire.

---

## Apply it

1. Find a real component where **Optimization** affects an interface or dependency.
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

- Which boundary is most affected by Optimization?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
