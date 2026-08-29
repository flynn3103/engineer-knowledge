# Optimization — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Optimization** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Catalog, Organized by Scope

It helps to file optimizations by the *scope* of program they examine.

**Peephole / local (within a basic block).** Pattern-match short instruction sequences and rewrite to cheaper equivalents: `mov`+`add` → `lea`, redundant `mov` elimination, `cmp 0` → `test`, multiply-by-power-of-two → shift. Cheap, run repeatedly (LLVM's `instcombine`, GCC's combine pass).

**Global / SSA (within a function).** The dataflow/SSA optimizations: **SCCP**, **GVN/CSE**, copy/constant propagation, aggressive **DCE**, **LICM**, **jump threading**, **tail duplication**. These dominate intra-procedural performance.

**Loop (within loop nests).** LICM, induction-variable simplification and strength reduction, **unrolling**, **fusion/fission**, **interchange**, **vectorization**, **software pipelining** (covered below).

**Interprocedural (across functions).** **Inlining** (the keystone), **devirtualization**, interprocedural constant propagation, **escape analysis**, dead-function/argument elimination, and — at link time — whole-program versions of all of these via **LTO**.

The keystone across scopes is still **inlining**: it converts an interprocedural problem into an intraprocedural one, after which every global and loop optimization can fire. Most of a modern compiler's wins trace back to "inline, then optimize the merged body."

### 2. Loop Optimizations in Depth

Loops are where time is spent, so they get the richest transforms.

**LICM** hoists invariant computations out (from `middle.md`). **Induction-variable strength reduction** turns `i*stride` (a multiply each iteration) into a running pointer incremented by `stride` — converting multiplies to adds. **Induction-variable simplification** canonicalizes and eliminates redundant induction variables.

**Loop unrolling** duplicates the body K times, cutting loop-overhead branches by K and exposing instruction-level parallelism — at the cost of i-cache pressure. **Loop fusion** merges two adjacent loops over the same range into one (better cache reuse, less loop overhead). **Loop fission** splits one loop into two (to isolate a vectorizable part, or relieve register pressure). **Loop interchange** swaps the nesting order of nested loops so the innermost stride matches memory layout — turning a cache-hostile column traversal into a cache-friendly row traversal, often a multiple-x win.

**Vectorization (auto-SIMD)** is the highest-leverage loop transform. The compiler proves successive iterations are independent (no loop-carried dependency, no aliasing) and rewrites the loop to process 4/8/16 elements per instruction using SIMD registers (SSE/AVX/AVX-512 on x86, NEON/SVE on ARM). The wins are large but the preconditions are strict: no data dependencies across iterations, provable non-aliasing (`restrict` helps enormously), trip counts the compiler can reason about, and no side-effecting calls inside. A single un-provable alias or an `if` with a side effect can silently disable it.

**Software pipelining** overlaps the start of iteration *i+1* with the finish of iteration *i*, scheduling instructions so the CPU's pipeline never stalls waiting for a dependency. It's vectorization's scheduling cousin — heavily used on in-order and VLIW targets.

### 3. Register Allocation as Optimization

After the IR is optimized, it still uses *unbounded virtual registers*. **Register allocation** maps them onto the finite physical register set (16 GP registers on x86-64). This is itself an optimization: values that live in registers are far cheaper than values spilled to the stack. The classic formulation is **graph coloring** — build an interference graph (two values that are simultaneously live interfere and can't share a register), then color it with K colors (K = physical registers); uncolorable nodes are **spilled** to memory. **Linear-scan** allocation is a faster, lower-quality alternative used in JITs where compile time matters. (Register allocation belongs to code generation; the cross-link is that allocation quality directly determines whether all the upstream optimization survives to fast machine code — spilling a hot value can erase the benefit of every preceding pass.)

### 4. Escape Analysis, Devirtualization, Bounds-Check Elimination, TCO

**Escape analysis** proves an allocated object does not "escape" the function (no reference to it is stored anywhere outlasting the call, returned, or passed to an opaque callee). If it doesn't escape, the compiler can **stack-allocate** it (no GC/heap pressure) or, via **scalar replacement of aggregates**, split it into individual registers and skip allocation entirely. This is central in Go (heap-vs-stack decided by escape analysis), Java/HotSpot (scalar replacement of non-escaping objects), and C++ (RVO-adjacent reasoning).

**Devirtualization** replaces a virtual or indirect call with a direct call (then often inlines it) when the dynamic type is provable — from `final`, from a single loaded implementation, or from class-hierarchy analysis. JITs do **speculative devirtualization** (assume the monomorphic type seen so far, guard it, deoptimize if wrong — a runtime-systems topic). Direct calls are faster *and* inlinable; virtual calls are neither, so devirtualization is a big enabling win in OO code.

**Bounds-check elimination** removes array-bounds checks the compiler proves can't fail — e.g. inside `for (i = 0; i < a.len; i++) a[i]`, the index is provably in range, so the per-iteration check is deleted. Critical for the performance of safe languages (Java, Go, Rust, C#); the optimizer recovers most of the cost of memory safety.

**Tail-call optimization** reuses the caller's stack frame when a call is the last action before returning, turning tail recursion into a loop (constant stack space). Mandatory in functional languages (Scheme guarantees it); opportunistic in C/C++ (`-O2` often does it); explicit in some (`[[clang::musttail]]`).

### 5. The Phase-Ordering Problem and the `-O` Pipelines

Passes enable and disable each other, so **the order matters and no optimal order exists** — phase ordering is provably hard (the search space is enormous and pass interactions are non-monotone). Compilers respond with a **fixed, hand-tuned pipeline**, and they *iterate* some clusters (run inlining → simplification → inlining again) to chase the cascade. LLVM's pipeline, for instance, runs early simplification to make functions inlinable, an inliner inside a "CGSCC" pass manager that re-simplifies after inlining, then loop and vectorization passes late.

The `-O` levels are *presets* of this pipeline:

- **`-O0`** — essentially no passes; fast compile, faithful debugging.
- **`-O1`** — a conservative subset; quick wins, low code growth.
- **`-O2`** — the full standard pipeline minus the most code-bloating transforms; the production default.
- **`-O3`** — `-O2` plus aggressive inlining, unrolling, and vectorization. **Not reliably faster** — the extra code can blow the i-cache, hurt branch prediction, and increase memory traffic. Always measure; on many real workloads `-O2` ties or beats `-O3`.
- **`-Os` / `-Oz`** — optimize for size; skip transforms that grow the binary (`-Oz` even more aggressively). Often a *good speed choice* on i-cache-bound code precisely because smaller code fits in cache.

The takeaway: optimization level is a *trade-off knob*, not a "more is better" dial.

### 6. LTO and PGO (Outline)

**Link-time optimization (LTO)** defers optimization to link time, when the linker sees *all* translation units (and with full LTO, all of them at once). This enables **cross-module inlining**, whole-program devirtualization, and interprocedural constant propagation across file boundaries — wins ordinary per-file compilation can't reach. **ThinLTO** is a scalable, parallel variant that summarizes each module and imports only the functions worth inlining, getting most of full-LTO's benefit at a fraction of the link cost.

**Profile-guided optimization (PGO)** compiles twice: an instrumented (or sampled) first build collects a *real* execution profile, and the second build uses it to guide decisions optimizers otherwise guess at — which calls to inline (hot ones), how to lay out basic blocks (hot path falls through, cold code is split out to keep the i-cache hot), and which branches to predict. PGO routinely yields 5–20% on large applications because it replaces static heuristics with measured truth. (Both are detailed in `professional.md` as build-engineering concerns.)

JITs take this further with **speculative, profile-driven, deopt-guarded** optimization: they assume the common case observed at runtime, compile aggressively for it, and bail out (deoptimize) if an assumption breaks — covered fully in runtime-systems.

### 7. The Undefined-Behavior Contract — Latitude and Liability

The as-if rule only constrains the optimizer for **well-defined** executions. When a program has **undefined behavior**, the standard imposes *no* requirements at all, so the optimizer is licensed to **assume UB cannot occur** and optimize accordingly. This is not malice — it's the source of huge wins:

- **Signed-overflow is UB**, so the compiler assumes `i + 1 > i` always holds for `int i` — which lets it prove loops terminate, promote `int` induction variables to wider types, and vectorize. (`-fwrapv` makes signed overflow defined two's-complement, *disabling* these.)
- **Strict aliasing** (pointers of incompatible types don't alias) lets the compiler keep a value in a register across a write through an unrelated pointer type — enabling CSE/LICM it otherwise couldn't prove. (`-fno-strict-aliasing` turns this off.)
- **Dereferencing null is UB**, so if you dereference `p` and *then* check `if (p)`, the compiler concludes `p` can't be null at the check and **deletes the branch** — the value couldn't have been read otherwise.

The liability is that the *same* inferences turn latent bugs into miscompiles and security holes. The infamous pattern: a "harmless" null check deleted because of a prior dereference (a real Linux kernel CVE class), an overflow-based bounds check optimized away (signed overflow UB), an infinite loop deleted because loops without side effects are assumed to terminate. Code that "worked at `-O0`" breaks at `-O2` because `-O0` doesn't run the passes that *act on* the UB assumption.

Two engineering responses: (1) **eliminate UB** — sanitizers (`-fsanitize=undefined,address`), warnings, and discipline; and (2) **constrain the optimizer** when porting UB-laden legacy code — `-fwrapv`, `-fno-strict-aliasing`, `-fno-delete-null-pointer-checks`. And because the optimizer itself can have bugs (**miscompiles**), serious toolchains lean on **translation validation** like **Alive2**, which proves (or refutes) that a specific LLVM transformation preserves semantics — catching optimizer bugs that fuzzing alone misses.

A related foot-gun: **`-ffast-math`** lets the optimizer treat floating-point as associative and assume no NaNs/infinities, enabling vectorized reductions and reassociation — but *changing results*, breaking Kahan summation, `x != x` NaN checks, and anything depending on IEEE semantics. It's UB-adjacent latitude you opt into, and it bites silently.

---

## Code Examples

### Loop interchange for cache locality (C)

```c
// Column-major traversal of a row-major array: cache-hostile (stride = N).
for (int j = 0; j < N; j++)
    for (int i = 0; i < N; i++)
        sum += a[i][j];

// After loop interchange: row-major traversal, stride = 1, cache-friendly.
for (int i = 0; i < N; i++)
    for (int j = 0; j < N; j++)
        sum += a[i][j];
```

The compiler (with the right analysis, or you by hand) swaps the loops so the inner index strides by 1 through contiguous memory. On large `N` this is often a several-fold speedup purely from cache behavior — no fewer arithmetic ops, just better access order.

### Aliasing blocks vectorization; `restrict` unblocks it (C)

```c
void add(float *a, float *b, float *c, int n) {
    for (int i = 0; i < n; i++)
        a[i] = b[i] + c[i];     // can a alias b or c? Compiler must assume yes.
}

void add_r(float *restrict a, float *restrict b, float *restrict c, int n) {
    for (int i = 0; i < n; i++)
        a[i] = b[i] + c[i];     // restrict promises no aliasing → clean vectorization
}
```

Without `restrict`, the compiler emits a runtime alias check plus a scalar fallback (in case `a` overlaps `b`/`c`). With `restrict`, it vectorizes directly. Inspect on godbolt at `-O3 -march=native` — the second function uses AVX (`vaddps`); the first guards itself first.

### Undefined behavior: the deleted null check (C)

```c
int deref(int *p) {
    int x = *p;          // dereference — UB if p is null, so compiler assumes p != null
    if (p == NULL)       // ... therefore this check is provably false ...
        return -1;       // ... and this branch is DELETED.
    return x;
}
```

At `-O2`, the `if (p == NULL)` branch is removed entirely: because `*p` already executed (UB if null), the optimizer concludes `p` cannot be null at the check. If `p` *is* null, you get a crash on the deref with no graceful `-1` — the safety net was optimized away. This exact pattern caused a real Linux kernel privilege-escalation bug. The fix is to check *before* dereferencing (or compile with `-fno-delete-null-pointer-checks` on kernel-style code).

### Signed overflow UB enabling (and `-fwrapv` disabling) a transform (C)

```c
// Compiler assumes signed i never overflows, so (i + 1 > i) is always true,
// the loop provably terminates, and i can be promoted/vectorized.
int sum(int *a, int n) {
    int s = 0;
    for (int i = 0; i < n; i++) s += a[i];   // 'i' as int: overflow is UB
    return s;
}
```

At `-O2`, the compiler may widen `i` to 64-bit and vectorize freely. Compile with `-fwrapv` (signed overflow defined as wraparound) and some of these inferences are *disabled* — slower but UB-safe-by-definition. This is the trade legacy codebases make.

### Escape analysis → stack allocation (Go)

```go
func sum(n int) int {
    p := new(int)   // does *p escape? No — only used locally.
    for i := 0; i < n; i++ { *p += i }
    return *p
}
```

```bash
go build -gcflags='-m' escape.go
# ./escape.go: new(int) does not escape   ← stack-allocated, zero heap/GC pressure
```

Go's escape analysis proves `p` doesn't escape `sum`, so the allocation is placed on the stack — no heap allocation, no garbage to collect. Make `p` escape (return it, store it in a global) and the same line reports "escapes to heap."

### Seeing the pipeline and confirming a transform (LLVM)

```bash
# Print the IR after every pass to find exactly where vectorization fires:
clang -O3 -mllvm -print-after-all -S add.c 2>&1 | grep -A2 'loop-vectorize'

# Ask why a loop did NOT vectorize:
clang -O3 -Rpass-missed=loop-vectorize -Rpass-analysis=loop-vectorize -c add.c
# -> "loop not vectorized: cannot prove pointers do not alias" etc.
```

The `-Rpass-missed`/`-Rpass-analysis` remarks are the senior engineer's best tool: the compiler *tells you* which precondition it couldn't prove, turning "why didn't it vectorize?" from guesswork into a specific, fixable fact.

---

## Coding Patterns

- **Feed the vectorizer.** Eliminate aliasing the compiler can't disprove (`restrict`, local copies, separate buffers), keep loop bodies branch-light and call-free, and use simple integer induction variables. Then *verify* with vectorization remarks.
- **Inline-enable hot paths.** Keep hot helpers small; mark genuine hot leaf calls for inlining where the language allows; use LTO to inline across translation units. Most perf tuning is inlining tuning.
- **Make types tell the truth so escape analysis/devirtualization fire.** `final`/`sealed` classes and concrete types enable devirtualization; not leaking references enables stack allocation. Don't gratuitously box, capture, or store references.
- **Prefer defined operations on hot paths.** Use unsigned or explicit wider types where overflow is intended; don't *rely* on UB for speed — write code that's both defined *and* lets the optimizer prove what it needs.
- **Treat `-ffast-math` as a per-translation-unit decision, never a global default**, and isolate fast-math code so it can't silently change unrelated FP results.

---

## Best Practices

- **Measure on the real workload; never trust the `-O` number.** Benchmark `-O2`/`-O3`/`-Os` and pick by data. On i-cache-bound services `-Os` frequently wins.
- **Use the compiler's optimization remarks.** `-Rpass`, `-Rpass-missed`, `-Rpass-analysis` (Clang) and `-fopt-info` (GCC) tell you exactly what fired and what didn't, and *why*. This is the difference between guessing and engineering.
- **Run sanitizers in CI, not just locally.** UBSan + ASan catch the bugs the optimizer would otherwise weaponize. A clean sanitizer run is the precondition for trusting `-O2`/`-O3`.
- **Adopt LTO/PGO deliberately, with build infrastructure to support it.** ThinLTO for scalable cross-module inlining; PGO with a representative profile (a stale profile can *hurt*).
- **Don't paper over miscompiles by lowering `-O`.** If `-O2` "breaks" your code, prove whether it's UB (almost always) or a genuine optimizer bug before reaching for `-O0`. Report real miscompiles upstream with a reduced test case (`creduce`).

---

## Edge Cases & Pitfalls

- **The deleted null/overflow check.** Covered above — the single most dangerous UB-exploitation pattern. Always validate *before* the operation that makes the value's validity an assumption.
- **`-O3` slower than `-O2`.** Aggressive inlining/unrolling bloated the binary past the i-cache. Real and common; measure both.
- **Vectorization silently disabled.** One un-provable alias, one side-effecting call, or one loop-carried dependency turns a vectorized loop back into a scalar one with *no error* — only a missed-optimization remark. Check the remarks; don't assume.
- **`-ffast-math` breaking summation/NaN logic.** Reassociation changes results; `x != x` (a NaN test) folds to `false`. Devastating in numerical code and easy to enable accidentally via a build preset.
- **Register pressure erasing upstream wins.** Excessive inlining or unrolling can spill hot values to the stack, and the spill cost can exceed the benefit of every prior optimization. More inlining is not monotonically better.
- **PGO with a stale or unrepresentative profile.** The optimizer trusts the profile; if it's from a different workload, it lays out *cold* code as hot and *pessimizes* the real path. Refresh profiles with releases.
- **LTO exposing latent ODR/UB bugs.** Cross-module inlining can surface one-definition-rule violations and UB that per-file builds hid — a "LTO broke my build" that's really "LTO revealed my bug."
- **Tail-call optimization that *doesn't* happen.** C/C++ TCO is opportunistic — a destructor, a `volatile`, or a non-tail position quietly prevents it, and deep recursion overflows the stack. Use `[[clang::musttail]]` (or restructure) when you *need* the guarantee.

---

## Apply it

1. State the system invariant that **Optimization** must protect.
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

- Which invariant must remain true when Optimization fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
