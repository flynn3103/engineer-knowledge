# Reading Codegen (Disassembly & Compiler Output) — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Reading Codegen (Disassembly & Compiler Output)** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Codegen as evidence: settling debates

The senior use of disassembly is *adjudication*. Someone claims X about the compiler; you produce the assembly that confirms or refutes it. The method is always the same:

1. **Reduce to a minimal function** that isolates the claim (no `main`, real parameters, your shipping flags).
2. **Read the output** for the specific signal (packed SIMD? a `call`? a panic branch? a single `mov` from folding?).
3. **Vary one thing** (a flag, a rewrite) and read the *difference*.
4. **Present the diff** as the evidence. "Here's the scalar loop; here's the same loop with `restrict`, now vectorized" ends the argument.

This is more reliable than benchmarking for *structural* claims ("did it vectorize / inline / fold"), because benchmarks have noise and the codegen is deterministic. Reserve benchmarking for *quantitative* claims ("how much faster").

### 2. The benchmark-optimized-away trap

This is the single most common way performance numbers lie. Consider:

```cpp
// WRONG: this "benchmark" likely measures an empty loop.
for (auto _ : state) {
    int x = expensive_compute(42);   // result unused -> may be deleted entirely
}
```

If `expensive_compute(42)` has no side effects and its result is unused, the optimizer is *entitled* to delete the call, the loop body, and possibly the loop. You then measure nanoseconds for *nothing*. The fixes are **sinks** that force the compiler to treat the result as observed:

- **Google Benchmark:** `benchmark::DoNotOptimize(expensive_compute(42));` (keeps the value), and `benchmark::ClobberMemory();` (treats memory writes as observed).
- **Rust:** `std::hint::black_box(expensive_compute(42));` — and `black_box` your *inputs* too, so the compiler can't constant-fold across the call.
- **C/C++ by hand:** store into a `volatile` sink, or use an inline-asm clobber.

**Critically:** the sink alone is not proof. You must *read the disassembly* and confirm the work is actually emitted inside the timed loop. If the body is gone, your sink was insufficient. The discipline is: defeat the optimizer with a sink, then *verify in the assembly*, then trust the number.

### 3. Why `-O3` is sometimes slower than `-O2`

"-O3 is faster" is folklore that's often false. `-O3` enables more aggressive inlining, unrolling, and vectorization heuristics that *can* backfire:

- **Code bloat → i-cache pressure.** Aggressive inlining/unrolling grows hot code past L1-i; fetch stalls cost more than the optimization saved.
- **Over-unrolling small loops** wastes the loop-stream buffer and increases register pressure → spills.
- **Speculative vectorization** of a loop that's usually short (the scalar remainder dominates) adds setup overhead.
- **Inlining a cold path** into a hot caller pushes the hot path further apart.

The senior move: when someone proposes `-O3`, *measure the whole program* (not a microbenchmark), and if it regresses, *read the codegen* to find the bloat (look for huge inlined bodies, deep unrolling). Sometimes the right answer is `-O2` plus targeted `__attribute__((hot))`/PGO, not a blanket `-O3`.

### 4. Reading LLVM IR — the explainable middle layer

Assembly is the *final* answer but it's noisy (register allocation, scheduling). **LLVM IR** sits between source and machine code: typed, SSA-form, target-independent, and it's where most optimizations happen. Reading it is often *clearer* than assembly for understanding *what the optimizer decided* before register allocation muddied it.

```bash
clang -O2 -emit-llvm -S file.c -o file.ll   # textual IR
```

In IR you can see: inlining (the callee's IR appears in the caller), constant folding (a `ret i32 42`), `noalias`/`nonnull` attributes on parameters, vectorized loops (`<8 x float>` vector types), and `fast` math flags on FP ops. When assembly is too low-level to reason about, drop to IR. Godbolt has an "LLVM IR output" view that color-maps source↔IR just like it does for assembly.

### 5. When the compiler refuses to optimize — and why

Equally important to spotting optimizations is diagnosing *missing* ones. Common, nameable causes:

- **Possible aliasing.** Two `int*` parameters might overlap, so the compiler can't reorder or vectorize across them. `restrict` (C) / non-overlapping slices (Rust) / `__restrict` removes the doubt. In IR, look for `noalias` on the parameters — present = the compiler knows they don't alias.
- **A hidden function call** in the loop (an un-inlined helper, an operator overload, a destructor, a `malloc`) that the compiler must treat as opaque, killing vectorization and motion.
- **`volatile`.** Every access must happen, exactly as written — no folding, no hoisting, no elimination. Great for hardware, ruinous if accidental.
- **UB constraints cutting the other way.** Signed-overflow and strict-aliasing assumptions let the compiler optimize *more*; but `-fno-strict-aliasing` (common in kernels) or `-fwrapv` *removes* assumptions and you'll see less aggressive code. Reading the codegen with and without these flags shows their cost.
- **Floating-point strictness.** Without `-ffast-math`, the compiler can't reassociate or contract FP ops, so reductions stay scalar. The IR shows `fast`/`reassoc` flags when they're permitted.

The senior skill: see the missed optimization in the assembly, form a hypothesis (aliasing? hidden call? volatile? FP strictness?), test it by changing exactly that one thing, and read the new output.

### 6. Surprising codegen, in both directions

Two categories of surprise are worth internalizing:

- **The compiler was cleverer than you.** It replaced your loop with a closed-form formula, turned a `popcount` loop into a single `popcnt`, recognized a `memcpy` pattern and called `memcpy`, or vectorized something you assumed it couldn't. Reading codegen keeps you humble: *check before hand-optimizing*, because you may be "fixing" something already optimal.
- **The compiler did nothing, for a reason you can name.** A division that "should" be a shift wasn't, because the value is signed and could be negative (signed division by a power of two needs a correction). A loop that "should" vectorize didn't, because of aliasing. Each non-optimization has a cause; finding it is the job.

---

## Code Examples

### Example 1: The optimized-away benchmark, exposed and fixed

```cpp
#include <benchmark/benchmark.h>
static int hot(int x) { return x * x + x; }

// BROKEN: result unused -> body may vanish.
static void BM_Broken(benchmark::State& s) {
    for (auto _ : s) hot(42);              // 'hot(42)' is dead code
}
// FIXED: force the result to be observed, and hide the input.
static void BM_Fixed(benchmark::State& s) {
    int in = 42;
    for (auto _ : s) {
        benchmark::DoNotOptimize(in);      // compiler can't fold '42'
        int r = hot(in);
        benchmark::DoNotOptimize(r);       // compiler must keep 'r'
    }
}
```

Compile and *read the loop body* (Godbolt or `objdump`). In `BM_Broken` you'll find the loop contains no `imul`/`add` at all — the work is gone. In `BM_Fixed` you'll see `imul`/`add` survive inside the timed loop. **Only the second is a real benchmark, and only the disassembly proves it.**

### Example 2: Rust `black_box` — both ends matter

```rust
use std::hint::black_box;

fn work(x: u64) -> u64 { x.wrapping_mul(0x9E3779B97F4A7C15) }

fn bench() {
    // Without black_box on the INPUT, the compiler constant-folds work(42).
    let r = work(black_box(42));
    black_box(r);   // and without this, the result is dead -> deleted
}
```

If you `black_box` only the result but pass a literal `42`, the optimizer may still constant-fold `work(42)` to a single constant and you measure a `mov`. Read the codegen: the multiply must be present. `black_box` the *input* to defeat folding and the *output* to defeat elimination.

### Example 3: `restrict` unlocking vectorization, seen in IR and asm

```c
void axpy(float *x, float *y, float a, int n) {        // may NOT vectorize
    for (int i = 0; i < n; i++) y[i] = a * x[i] + y[i];
}
void axpy_r(float * restrict x, float * restrict y, float a, int n) {  // vectorizes
    for (int i = 0; i < n; i++) y[i] = a * x[i] + y[i];
}
```

Read the LLVM IR (`clang -O2 -emit-llvm -S`): the `restrict` version shows `noalias` on the `x`/`y` parameters; without it, the compiler must assume `x` and `y` might overlap and inserts a runtime overlap check or stays scalar. In the assembly, `axpy_r` shows packed `vfmadd...ps`; `axpy` may show scalar `vfmadd...ss` or a guarded slow path. This *is* the evidence that aliasing was the blocker.

### Example 4: Signed division that surprises you

```c
int half(int x) { return x / 2; }       // signed: NOT just a shift
unsigned uhalf(unsigned x) { return x / 2; }  // unsigned: a clean shift
```

```asm
half:                          ; signed needs a correction for negatives
        mov     eax, edi
        shr     eax, 31        ; grab the sign bit
        add     eax, edi       ; bias so truncation rounds toward zero
        sar     eax, 1
        ret
uhalf:                         ; unsigned is trivial
        mov     eax, edi
        shr     eax, 1
        ret
```

If you ever wondered "why isn't `x/2` just `shr`?" — the disassembly answers: signed division by a power of two must correct for negative operands. This is a non-optimization *with a nameable cause* (signedness), not a compiler bug.

### Example 5: The compiler beats your loop (closed form)

```c
unsigned sum_n(unsigned n) {
    unsigned s = 0;
    for (unsigned i = 0; i <= n; i++) s += i;
    return s;
}
```

At `-O2`, gcc often emits a handful of instructions computing `n*(n+1)/2` directly — *no loop at all*. If you were about to "optimize" this loop by hand, the codegen tells you not to bother. Read first.

### Example 6: Reading LLVM IR to see inlining and folding

```bash
clang -O2 -emit-llvm -S demo.c -o demo.ll
```

```llvm
; A folded constant return:
define i32 @answer() {
  ret i32 42                ; '6 * 7' folded to 42 in IR, before asm
}
; A vectorized loop shows vector types:
%wide = load <8 x float>, ptr %p   ; 8-wide vector load -> vectorized
```

Vector types like `<8 x float>` in the IR confirm vectorization at a level above register allocation. `noalias`/`nonnull` attributes on parameters explain *why* optimizations were legal. IR is frequently the clearest place to read the optimizer's decisions.

### Example 7: `-O3` regression, found in the codegen

```bash
# Whole-program timing, not a microbenchmark:
clang -O2 app.c -o app_o2 && clang -O3 app.c -o app_o3
hyperfine ./app_o2 ./app_o3        # suppose -O3 is 8% SLOWER
size app_o2 app_o3                 # -O3 .text is much larger -> bloat
objdump -d app_o3 | less           # the hot function is massively inlined/unrolled
```

The combination — slower whole-program time, larger `.text`, and a visibly bloated hot function in the disassembly — diagnoses an i-cache/bloat regression. The fix might be `-O2` with `[[gnu::hot]]` on the truly-hot function, or PGO, rather than blanket `-O3`.

### Example 8: A `volatile` accidentally killing optimization

```c
int sum(const volatile int *a, int n) {   // 'volatile' here is a mistake
    int s = 0;
    for (int i = 0; i < n; i++) s += a[i];
    return s;
}
```

Because `a` is `volatile`, every `a[i]` read *must* happen, in order — the compiler cannot vectorize, hoist, or coalesce. The assembly shows a scalar load per element with no SIMD, even at `-O3`. Spotting the scalar loop and tracing it back to a stray `volatile` is a classic senior diagnosis. (`volatile` is for hardware/`sig_atomic_t`, not for "make sure the read happens in my benchmark" — use a proper sink instead.)

---

## Coding Patterns

### Pattern 1: Sink-and-verify for every microbenchmark

```cpp
benchmark::DoNotOptimize(input);
auto r = under_test(input);
benchmark::DoNotOptimize(r);
benchmark::ClobberMemory();   // if the work writes memory
```

Then open the disassembly and confirm the timed loop contains the real work. Never trust a number you haven't verified at the instruction level.

### Pattern 2: Minimal-function reduction for adjudication

Strip the claim to one parameterized function, compile with the *shipping* flags, read the one signal you care about (packed SIMD / `call` / panic branch / single `mov`). Keep the snippet in your notes to re-run later.

### Pattern 3: Change exactly one thing, read the diff

To prove a cause, vary a single variable — add `restrict`, add `-ffast-math`, remove `volatile`, switch `-O2`↔`-O3` — and read the difference. One change, one conclusion.

### Pattern 4: Drop to IR when assembly is too noisy

```bash
clang -O2 -emit-llvm -S file.c -o file.ll
```

Read `noalias`/`nonnull` attributes, `<N x T>` vector types, and `fast` FP flags to understand *why* the optimizer did what it did, above the register-allocation noise.

### Pattern 5: Whole-program A/B for optimization-level decisions

Time the *real program* (`hyperfine`, production-like input) for `-O2` vs `-O3`, not a microbenchmark. If `-O3` regresses, `size` + `objdump` to find the bloat. Decide per-program, even per-function (`[[gnu::hot]]`, `__attribute__((optimize(...)))`).

### Pattern 6: Check-before-optimizing

Before writing intrinsics or hand-unrolling, read the compiler's current output. If it's already optimal (closed-form, already vectorized, already a single intrinsic), don't waste the effort — and document the codegen that proves it.

---

## Best Practices

- **Always verify a microbenchmark in the disassembly.** Sinks are necessary but not sufficient; read the timed loop and confirm the work is there.
- **Reserve disassembly for structural claims and benchmarking for quantitative ones** — and require both before a performance decision.
- **Treat `-O3` as a hypothesis.** Measure whole-program, and if it regresses, explain it from the codegen before reverting blindly.
- **Read LLVM IR when assembly obscures the decision.** Attributes and vector types make the optimizer's reasoning legible.
- **Name the blocker for every missed optimization.** "It didn't vectorize" is incomplete; "it didn't vectorize because the pointers might alias — here's the IR without `noalias`" is senior.
- **Check the compiler hasn't already done it** before hand-optimizing.
- **Reproduce in the real build config.** Flags, `-march`, LTO, and PGO all change the codegen; conclusions don't transfer across configs.
- **Keep your reduced examples.** They become a regression suite for "is this still vectorized?" after future changes.

---

## Edge Cases & Pitfalls

- **The sink that doesn't sink.** `DoNotOptimize` on the *result* but a constant *input* still lets folding happen. Hide both ends. Verify in the asm.
- **`volatile` as a benchmark sink.** It works but pessimizes more than intended (forces every access, blocks coalescing) and can give misleadingly slow numbers. Prefer `DoNotOptimize`/`black_box`.
- **Trusting `-O3` because it's a bigger number.** It frequently regresses via bloat/i-cache. Measure the whole program.
- **Reading a structural conclusion off `-O0`.** No optimizations run at `-O0`, so "it didn't vectorize" there is meaningless.
- **Confusing "legal" with "profitable."** The compiler may *be allowed* to vectorize but decline because its cost model says it's not worth it (short trip counts). The IR/remarks distinguish "couldn't" from "chose not to."
- **`-ffast-math`'s correctness cost.** It unlocks FP vectorization but changes results (NaN handling, associativity, denormals). Reading the faster codegen is only half the story — confirm the numerics are acceptable.
- **Strict-aliasing surprises.** Type-punning through incompatible pointers is UB; the compiler may optimize based on the assumption it doesn't happen, producing codegen that "drops" your write. The fix (`memcpy`, `-fno-strict-aliasing`) is visible in the diff.
- **Signed-overflow assumptions.** The compiler assumes signed overflow never happens and optimizes accordingly; `-fwrapv` removes that and you'll see different (often less optimized) code. Don't mistake the difference for a bug.
- **Inlining hiding samples.** When you profile after confirming inlining, the inlined work shows up in the *caller*. Don't conclude "the function is free."
- **IR is not the final word.** The optimizer keeps working after the IR you printed (and the backend does its own thing). For the *final* truth, read the assembly; use IR to understand *intent*.
- **Reduced example diverges from production.** A tiny snippet may vectorize while the real (bigger, aliased, call-laden) loop doesn't. Confirm conclusions on code shaped like the real thing.

---

## Apply it

1. State the system invariant that **Reading Codegen (Disassembly & Compiler Output)** must protect.
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

- Which invariant must remain true when Reading Codegen (Disassembly & Compiler Output) fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
