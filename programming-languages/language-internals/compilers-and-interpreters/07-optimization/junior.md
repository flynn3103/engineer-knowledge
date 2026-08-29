# Optimization — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Optimization** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The As-If Rule: Optimize Anything, Change Nothing Visible

The compiler's freedom and its constraint are the same sentence: **rewrite the program any way you want, as long as its observable behavior is unchanged.** This is the "as-if" rule (it's literally spelled that way in the C and C++ standards).

What is **observable**, and must be preserved exactly:

- Data written to files, the console, the network — your `printf`, your `write()`.
- Reads and writes to `volatile` objects (think hardware registers, memory-mapped I/O).
- Whether the program terminates, and with what exit code.

What is **not observable**, and the compiler may freely change:

- The order in which internal arithmetic happens (as long as the result is the same).
- Whether a local variable physically exists in memory, a register, or nowhere at all.
- How many machine instructions run, in what order, on which registers.
- Whether a function call happened at all (it might get inlined or deleted).

So when you write:

```c
int x = 2 + 3;
int y = x * 4;
printf("%d\n", y);
```

The compiler is allowed to emit code equivalent to `printf("%d\n", 20);` — it never computes `2+3`, never multiplies, never stores `x` or `y` anywhere. You cannot tell, because the *only* observable thing (the printed `20`) is identical. That's the as-if rule in action.

### 2. The Classic Local Optimizations

These are the rewrites you'll recognize first in disassembly. They're "local" because they look at small windows of code.

**Constant folding.** Compute constant expressions at compile time. `60 * 60 * 24` becomes `86400` in the binary — the multiplications never run.

**Constant propagation.** If `x = 5` and `x` isn't changed afterward, replace later uses of `x` with `5`. This often *enables* more folding: `int x = 5; int y = x + 3;` → `y = 8`.

**Copy propagation.** If `b = a` and neither changes, replace later uses of `b` with `a`, so the copy may become dead and get deleted.

**Algebraic simplification.** Apply math identities: `x + 0` → `x`, `x * 1` → `x`, `x * 0` → `0`, `x - x` → `0`, `!!b` → `b`.

**Strength reduction.** Replace expensive ops with cheap ones. `x * 2` → `x << 1`. `x * 8` → `x << 3`. `x / 4` (for unsigned) → `x >> 2`. Even `x * 5` becomes `(x << 2) + x` — a shift and an add, faster than a general multiply on many CPUs. (The compiler does this; *you* should usually just write `x * 5` and let it.)

**Common subexpression elimination (CSE).** If you compute the same thing twice and nothing in between changed the inputs, compute it once:

```c
int p = (a + b) * c;
int q = (a + b) * d;   // (a + b) is computed twice in source...
```

becomes, internally, `t = a + b; p = t * c; q = t * d;` — one addition.

**Dead code elimination (DCE).** Remove code whose results are never used, and code that can never execute. `if (false) { ... }` — the body is deleted. A variable you compute but never read — the computation is deleted. A **dead store** (writing a value that's overwritten before any read) is removed too.

### 3. Inlining: The One That Unlocks Everything Else

**Inlining** replaces a function *call* with a copy of the function's *body*. Instead of jumping to `square()`, the compiler pastes `x * x` right where the call was.

The direct win is avoiding call overhead (pushing arguments, the jump, the return). But the *real* value is what inlining **enables**: once the body is pasted in, all the other optimizations can see across the old function boundary. Constants flow in, dead branches collapse, common subexpressions merge.

```c
int square(int x) { return x * x; }
int f() { return square(5); }
```

After inlining, `f()` is `return 5 * 5;`, which constant-folds to `return 25;`. The function call *and* the multiplication both vanish. This is why inlining is called the **most important enabling optimization**: it's the door that lets every other pass walk through.

The cost: inlining a function everywhere it's called **duplicates** its code, which makes the binary bigger and can hurt the instruction cache. Compilers use heuristics (small functions, hot call sites) to decide. You'll meet the trade-offs in detail in the higher tiers.

### 4. Loop Optimizations (The Junior Slice)

Loops run their body many times, so optimizing inside a loop pays off proportionally. Two you should recognize:

**Loop-invariant code motion (LICM).** If a computation inside a loop produces the same value every iteration, hoist it *out*:

```c
for (int i = 0; i < n; i++)
    a[i] = b[i] + c * d;   // c*d is the same every iteration
```

becomes:

```c
int t = c * d;
for (int i = 0; i < n; i++)
    a[i] = b[i] + t;       // multiply once, not n times
```

**Loop unrolling.** Do several iterations' worth of work per loop pass to reduce loop overhead (the counter increment and the branch):

```c
for (int i = 0; i < n; i++) sum += a[i];
```

might become a version that adds four elements per iteration. Fewer branches, more instruction-level parallelism — but a bigger body.

### 5. Optimization Levels: What `-O2` Actually Means

You select how hard the compiler tries with a flag:

| Flag | Intent |
|------|--------|
| `-O0` | **No optimization.** Fast compiles, easy debugging — variables stay where you put them, line numbers map cleanly. The default while developing. |
| `-O1` | Basic optimizations, modest cost. |
| `-O2` | **The standard release level.** Almost all optimizations that don't risk large code-size growth. What most production builds use. |
| `-O3` | `-O2` plus aggressive ones (more inlining, vectorization). Sometimes faster, **sometimes slower** because of code bloat. Measure, don't assume. |
| `-Os` | Optimize for **size** — like `-O2` but avoid transformations that grow the binary. |
| `-Oz` | Optimize for size even harder (Clang). |

The key junior takeaway: **`-O0` for debugging, `-O2` for shipping.** `-O3` is not automatically better — it can bloat code and thrash the instruction cache, so it must be measured, not assumed. (You'll see why in `senior.md`.)

---

## Code Examples

### Constant folding and propagation (C, via godbolt)

```c
int seconds_per_day(void) {
    int hours = 24;
    int minutes = hours * 60;
    int seconds = minutes * 60;
    return seconds;
}
```

At `-O2`, the entire function compiles to the equivalent of:

```asm
seconds_per_day:
    mov eax, 86400      ; the whole computation folded to one constant
    ret
```

No multiplications, no `hours`/`minutes`/`seconds` variables. The compiler propagated and folded everything at compile time.

### Strength reduction (C)

```c
unsigned times_eight(unsigned x) { return x * 8; }
```

At `-O2`:

```asm
times_eight:
    lea eax, [0 + rdi*8]   ; or: shl edi, 3 — a shift, not a multiply
    ret
```

The multiply by 8 became a shift-left-by-3 (or a `lea`). You wrote the clear thing (`x * 8`); the compiler chose the cheap thing.

### Common subexpression elimination (C)

```c
int f(int a, int b, int c, int d) {
    int p = (a + b) * c;
    int q = (a + b) * d;
    return p + q;
}
```

At `-O2`, the compiler computes `a + b` **once** into a register and reuses it for both products. The source has two `(a + b)`; the machine code has one addition.

### Dead code elimination (C)

```c
int g(int x) {
    int unused = x * x * x;   // never read
    if (1 == 2) {             // can never be true
        return -1;            // unreachable — deleted
    }
    return x + 1;
}
```

At `-O2`, `g` is just `return x + 1;`. The cube is a dead store and is removed; the `if` body is dead code and is removed.

### Inlining unlocks folding (C)

```c
static int square(int x) { return x * x; }
int demo(void) { return square(5) + 1; }
```

At `-O2`, `demo` returns `26` — `square(5)` is inlined to `5 * 5`, folded to `25`, plus `1` is `26`. The call and the multiply both disappear.

### Loop-invariant code motion (C)

```c
void scale(int *a, int n, int c, int d) {
    for (int i = 0; i < n; i++)
        a[i] = a[i] + c * d;   // c*d does not change across the loop
}
```

At `-O2`, `c * d` is computed once before the loop and the loop body just adds the precomputed value. (At `-O3` the loop may also be *vectorized* to process several elements per instruction — more on that in higher tiers.)

> **How to see all of this yourself:** paste any of these into [godbolt.org](https://godbolt.org), pick a compiler (e.g. `x86-64 gcc` or `clang`), and toggle between `-O0` and `-O2`. Watching the assembly shrink and rearrange is the single best way to build intuition for what optimization does.

---

## Coding Patterns

- **Write for clarity; trust the compiler for speed.** Don't replace `x * 2` with `x << 1` in source "for speed" — the compiler already does it, and the shift is harder to read and can be *wrong* for signed division. Write the obvious thing.
- **Keep hot helpers small and in the same translation unit.** Small functions get inlined; a small `static` helper in the same `.c` file is the easiest thing for the compiler to inline. (Cross-file inlining needs LTO — a higher-tier topic.)
- **Make constants visible.** Use `const`/`constexpr`/`final` so the compiler *knows* a value won't change and can propagate and fold it. Hiding a constant behind a non-const global blocks the optimization.
- **Don't compute the same thing in a loop.** Even though LICM exists, it can only hoist what it can *prove* is invariant. If a function call or a pointer write might change things, the compiler conservatively keeps the work inside. Hoist obvious invariants yourself when in doubt.
- **Build release with `-O2`, debug with `-O0 -g`.** Two build configurations, used deliberately.

---

## Best Practices

- **Always benchmark optimized builds.** Never measure performance at `-O0` — the numbers are meaningless. And when comparing `-O2` vs `-O3`, *measure the actual program*, don't assume the higher number wins.
- **Look at the assembly when it matters.** For a genuinely hot path, godbolt is faster than guessing. You'll learn what the compiler does and doesn't do.
- **Don't fight the optimizer with micro-tricks.** Hand-rolled bit twiddling, manual loop unrolling, and clever arithmetic are usually things `-O2` already does — and your version may block a *better* optimization the compiler would have found.
- **Fix undefined behavior; don't rely on it.** Code that works at `-O0` but breaks at `-O2` almost always has UB. Turn on sanitizers (`-fsanitize=undefined,address`) and warnings (`-Wall -Wextra`). The optimizer is allowed to assume UB never happens — so don't make it happen.
- **Keep a separate debug build.** When a release-only bug appears, reproduce it at `-O1` first (often still buggy, but easier to step through) before dropping to `-O0`.

---

## Edge Cases & Pitfalls

- **"It works at `-O0` but breaks at `-O2`."** The classic. Nearly always undefined behavior your code got away with at `-O0`. The fix is to find and remove the UB (sanitizers help), *not* to ship at `-O0`. Optimization didn't cause the bug; it revealed it.
- **A deleted null check.** If you dereference a pointer and *then* check it for null, the compiler may reason "you already dereferenced it, so it can't be null" and **delete your null check** — because dereferencing null is UB, so the check is "dead." Check *before* you dereference. (This is a famous real-world security bug class; the senior tier covers it.)
- **`-O3` ran slower than `-O2`.** Not a paradox. `-O3`'s extra inlining and unrolling bloated the code, the instruction cache started missing, and the program slowed down. Measure both.
- **Floating-point math "changed."** `-ffast-math` lets the compiler reorder and simplify floating-point arithmetic in ways that change results (because FP isn't truly associative). It can break code that depends on exact FP behavior. Don't enable it blindly.
- **A `volatile` variable wasn't optimized — on purpose.** `volatile` tells the compiler "this access is observable; don't remove or reorder it." It exists precisely to *opt out* of optimization for hardware registers and memory-mapped I/O. It is **not** a threading tool (a common confusion).
- **A debug "this should print" disappeared.** A variable you computed for inspection but never *use* may be optimized away, and a debugger will show it as "optimized out." That's correct behavior, not a compiler bug. Mark it `volatile` or actually use it if you need it to survive.
- **Empty loop deleted.** An empty `for` loop you wrote as a delay can be deleted entirely (it has no observable effect). Busy-wait delays must use `volatile` or proper timing primitives.

---

## Apply it

1. Choose one small, known input for **Optimization**.
2. Predict the output or observable behavior.
3. Run the smallest example or probe that exercises the concept.
4. Change one input to trigger a failure or boundary case.
5. Explain the evidence using the guide's vocabulary.

## Verify your work

- Record the exact input, command or code path, and output.
- Repeat the probe and confirm the result is consistent.
- Show one expected success and one expected failure.
- Resolve any difference between the prediction and the evidence.

## Review questions

- What problem does Optimization solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
