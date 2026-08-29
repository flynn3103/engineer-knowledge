# Evaluation Strategies (call-by-x) — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Evaluation Strategies (call-by-x)** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Two Orthogonal Axes: *What* vs *When*

The junior page's axis was **what** the parameter aliases (value / reference / shared reference). This page's axis is **when** the argument is evaluated:

- **Strict:** evaluate the argument *now*, before entering the body. Call-by-value and call-by-reference are both strict.
- **Non-strict:** *defer* the argument; evaluate it later (or never). Call-by-name and call-by-need are non-strict.

These axes are independent. You can have call-by-value (strict, copies) or call-by-name (non-strict, re-evaluates). The full picture is a grid, not a line.

### 2. Strictness and Termination

This is the headline consequence. Consider:

```text
def const(x, y):  return x      # ignores y

const(42, loop_forever())
```

- **Under call-by-value (strict):** `loop_forever()` is evaluated *before* `const` runs. The program **hangs**, even though `const` never looks at `y`.
- **Under call-by-name/need (non-strict):** `y` is never referenced, so `loop_forever()` is **never evaluated**. The call returns `42`.

So **call-by-name can terminate where call-by-value loops forever.** This is not a curiosity — it is the formal reason normal-order reduction is "more terminating" than applicative-order, and the reason Haskell can write `take 5 [1..]` over an infinite list.

### 3. Call-by-Name: Bind the Expression, Re-Evaluate Each Use

Under call-by-name, the parameter is essentially a macro for the argument *expression*. Every time the body mentions the parameter, the original expression is evaluated again, **in the caller's context**.

```text
// pseudo call-by-name
def twice(x):
    return x + x          // 'x' here means "the argument expression", evaluated TWICE

twice(roll_dice())        // roll_dice() is called TWICE — you may get 3 + 5 = 8
```

That re-evaluation is the surprising part and the source of both the power (Jensen's device) and the danger (side effects happen N times).

### 4. The Thunk: How Non-Strictness Is Implemented

A language that lacks built-in call-by-name still gets you 90% of the way there with **thunks** — wrapping the argument in a `() -> T` so *nothing runs until you call it*:

```text
// simulate call-by-name with a thunk (lambda)
def twice(thunk):
    return thunk() + thunk()    // forces the thunk each time

twice(lambda: roll_dice())      // explicit deferral
```

A thunk is just a zero-arg closure. It captures the expression and its environment; calling it forces evaluation. Every non-strict mechanism — Scala's `=> T`, Haskell's lazy bindings, your hand-rolled `Supplier<T>` in Java — is a thunk underneath.

### 5. Call-by-Need = Call-by-Name + Memoization (Laziness)

Call-by-name re-evaluates *every* use, which is wasteful and (with side effects) dangerous. **Call-by-need** fixes the waste: force the thunk **once**, cache the result, and every later use reads the cache.

```text
// call-by-need: the thunk memoizes
def twice(lazy_x):
    return lazy_x.force() + lazy_x.force()   // computed ONCE, reused

twice(make_lazy(roll_dice))   // roll_dice() runs exactly once
```

This is exactly Haskell's evaluation model. A binding like `let x = expensive()` does **not** run `expensive()` until `x` is forced, and runs it **at most once** thereafter. That's why laziness is "computed at most once, only if needed."

### 6. Call-by-Copy-Restore (Value-Result)

A fourth strategy, distinct from all the above. At call time, **copy** the argument into the parameter (like call-by-value). The function works on its local copy. On **return**, copy the parameter's final value **back out** into the caller's variable. Ada's `in out` parameters, Fortran's argument convention, and some older systems use this.

It usually *looks* identical to call-by-reference — but it differs precisely under aliasing (when the same variable is passed twice, or a global is also touched), because copy-restore only writes back at the *end*. That subtlety is a famous interview trap, expanded in Tricky Points.

---

## Code Examples

### Example 1: Scala By-Name Parameters (Real Call-by-Name)

Scala has first-class call-by-name via `=> T`:

```scala
// 'cond' is evaluated each time it's used; 'body' too
def myWhile(cond: => Boolean)(body: => Unit): Unit =
  if (cond) { body; myWhile(cond)(body) }

var i = 0
myWhile(i < 3) { println(i); i += 1 }   // works: cond re-evaluated each loop
```

If `cond` were a normal (by-value) `Boolean`, it would be evaluated once at the call and the loop would never re-check it. By-name makes `i < 3` a thunk re-forced every iteration.

### Example 2: Lazy = By-Name + Memo, Also in Scala

```scala
def expensive(): Int = { println("computing"); 42 }

def byName(x: => Int)  = x + x   // prints "computing" TWICE
def byNeed(x: => Int)  = { lazy val v = x; v + v }  // prints "computing" ONCE

byName(expensive())   // computing / computing
byNeed(expensive())   // computing
```

`lazy val` is the memoizing wrapper that turns call-by-name into call-by-need.

### Example 3: Haskell — Non-Strictness Lets a Function Ignore ⊥

```haskell
ghci> const 42 undefined      -- 'undefined' is ⊥
42                            -- never forced, so no crash

ghci> take 3 [1..]            -- infinite list, lazily produced
[1,2,3]

ghci> let xs = 1 : xs in take 5 xs   -- self-referential infinite list
[1,1,1,1,1]
```

The same expressions in a strict language would loop or crash on `undefined`/`[1..]`.

### Example 4: Simulating Call-by-Name in Strict Languages With Thunks

```python
# Python: defer with a lambda (thunk). 'unless' must not eval the body unless needed.
def unless(condition, action):       # WRONG: action already evaluated!
    if not condition:
        action

def unless_lazy(condition, action):  # RIGHT: action is a thunk
    if not condition:
        action()

unless_lazy(user_is_admin, lambda: delete_everything())  # only forced if not admin
```

```java
// Java: Supplier<T> is the thunk type
int orElse(boolean flag, int cheap, Supplier<Integer> expensive) {
    return flag ? cheap : expensive.get();   // expensive computed only if needed
}
```

### Example 5: Jensen's Device (the Classic Call-by-Name Trick)

In Algol 60, you could pass an *expression* and a *loop variable*; mutating the variable in the callee changed what the expression evaluated to:

```text
// Algol-style pseudocode
real procedure SUM(expr, i, lo, hi);
  value lo, hi; integer i;          // i and expr are call-by-name
begin
  real s; s := 0;
  for i := lo step 1 until hi do
    s := s + expr;                  // 'expr' re-evaluated with the new i each pass
  SUM := s
end;

// Caller: sum a[i] for i in 1..n  — pass the EXPRESSION a[i], not a value
total := SUM(a[i], i, 1, n);
```

`expr` is `a[i]`. Each loop iteration mutates `i` (call-by-name), so re-evaluating `a[i]` yields a *different* array element. One generic `SUM` can sum `a[i]`, `a[i]*b[i]`, `1/i`, anything — without higher-order functions. This is the canonical demonstration of call-by-name's expressiveness (and its danger).

---

## Coding Patterns

**Pattern: Thunk a costly default.** Don't compute a fallback you may not use.

```python
def get_or_default(cache, key, default_thunk):
    return cache[key] if key in cache else default_thunk()

get_or_default(c, "k", lambda: expensive_default())   # only runs on miss
```

**Pattern: Lazy logging.** Pass a thunk, not a pre-formatted string.

```java
log.debug(() -> "state=" + dumpExpensiveState());  // string built only if DEBUG on
```

**Pattern: Memoize a thunk to get call-by-need by hand.**

```python
def lazy(thunk):
    box = {}
    def force():
        if "v" not in box:
            box["v"] = thunk()      # compute once
        return box["v"]
    return force
```

**Pattern: Generators for pull-based laziness.**

```python
def naturals():
    n = 0
    while True:
        yield n
        n += 1
# consumer pulls only what it needs — values produced on demand
```

---

## Best Practices

1. **Default to strict; reach for laziness deliberately.** Eager evaluation is predictable; make laziness a conscious tool, not an accident.
2. **Never put observable side effects in a call-by-name / thunk argument** unless you fully control how many times it's forced. By-name may run it 0, 1, or N times.
3. **In lazy languages, watch for space leaks.** Force accumulators (Haskell's `seq`, `$!`, `BangPatterns`, `foldl'`) when building up large thunked values.
4. **Use thunks to avoid wasted work**, but profile — a thunk has allocation and indirection cost; cheap arguments don't deserve deferral.
5. **Prefer call-by-need (memoized) over call-by-name** whenever the argument is referenced more than once, unless re-evaluation is the *point* (as in Jensen's device).
6. **Treat copy-restore as value semantics with a write-back**, and document the aliasing behavior at interop boundaries.

---

## Edge Cases & Pitfalls

**Pitfall 1: Side effects under call-by-name run the wrong number of times.** `twice(print("hi"))` under call-by-name prints `hi` twice; if the parameter is never used, zero times. Predict by counting *uses*, not *calls*.

**Pitfall 2: Space leaks from lazy accumulation.** `foldl (+) 0 [1..1000000]` in Haskell builds a giant chain of unforced `+` thunks before evaluating any — it can blow the stack/heap. Use the strict `foldl'`.

**Pitfall 3: Laziness reorders *when* exceptions fire.** A division by zero hidden in a thunk surfaces only when forced — possibly far from where it was written, possibly never. Debugging "where did this exception come from?" gets harder.

**Pitfall 4: Memoized thunk pins memory.** A call-by-need thunk that captures a large structure keeps it alive until forced (and the cached result keeps living after). Long-lived lazy values are a classic memory-retention bug.

**Pitfall 5: Copy-restore vs reference under aliasing.** If `f(x, x)` is passed the same variable for two copy-restore params, only one write-back survives (order-dependent), whereas true reference would interleave writes live. Same call, different answer.

---

## Common Mistakes

- **Calling thunks "lazy" when they're really call-by-name.** A bare `() -> T` re-evaluates each call; it's lazy *only* if you wrap it in a memoizer.
- **Assuming `&&` evaluates both sides.** It doesn't — it's non-strict in the right operand. People still write `if (p != null & p.ok())` (bitwise `&`, strict) and get NPEs.
- **Expecting Haskell to run top-to-bottom.** Evaluation is demand-driven; "earlier" code may run *after* "later" code, or never.
- **Confusing copy-restore with reference** because they agree in the common (no-aliasing) case.
- **Leaving side effects in lazy bindings**, then being surprised they fire in a confusing order.

---

## Tricky Points

**The aliasing test that separates the four strategies.** Consider a function `f(a, b)` that does `a := 1; b := 2; result := a` and is called as `f(x, x)` with `x` initially `0`:

- **Call-by-value:** `a`, `b` are copies; `x` stays `0`.
- **Call-by-reference:** `a` and `b` are *both* aliases of `x`; `a := 1` then `b := 2` both write `x`, so `x` ends at `2`, and `result` (reading `a`, i.e. `x`) is `2`.
- **Call-by-copy-restore:** `a`, `b` are copies; at return, both copy back into `x`; the last write-back wins, so `x` is `1` or `2` depending on restore order (unspecified in some languages!).
- **Call-by-name:** `a` and `b` are the *expression* `x`; behavior follows reference-like, but with re-evaluation subtleties.

This single example is the cleanest way to *distinguish* the strategies empirically, and a beloved exam/interview question.

**Short-circuit is non-strictness, not laziness.** `a || b` doesn't *memoize* `b`; it just doesn't force it when `a` is true. Don't conflate the two.

**`take 5 [1..]` only works because of WHNF.** Haskell evaluates the list to weak head normal form — enough to see the next cons cell — never the (infinite) whole. Laziness operates at the constructor boundary.

---

## Apply it

1. Find a real component where **Evaluation Strategies (call-by-x)** affects an interface or dependency.
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

- Which boundary is most affected by Evaluation Strategies (call-by-x)?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
