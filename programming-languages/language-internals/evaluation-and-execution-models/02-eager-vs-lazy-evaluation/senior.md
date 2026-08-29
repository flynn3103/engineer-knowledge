# Eager vs. Lazy Evaluation — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Eager vs. Lazy Evaluation** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Everything Is a Thunk Until Forced

In Haskell, evaluation is **demand-driven**. Nothing computes until something needs it. A binding allocates a thunk:

```haskell
let x = expensive 42      -- allocates a thunk; 'expensive' does NOT run
    y = x + x             -- another thunk, referring to x's thunk
in  print y               -- forcing y forces x ONCE (call-by-need memoizes), then adds
```

When `print y` demands `y`, the runtime forces the `+` thunk, which forces `x`'s thunk — *once*. Because of call-by-need, `x` is evaluated a single time even though `y` mentions it twice; the result is written back into `x`'s thunk. That memoization is the difference between call-by-need (Haskell) and call-by-name (re-evaluate each use).

The practical consequence: **the order your code is written has almost nothing to do with the order things execute.** Execution order is whatever the demand for the final result dictates. This is liberating and disorienting in equal measure.

### 2. Infinite Data Is Idiomatic, Not Exotic

```haskell
nats   = [0..]                       -- infinite: 0,1,2,...
ones   = repeat 1                    -- infinite: 1,1,1,...
naturalsBy2 = iterate (+2) 0         -- 0,2,4,...
fibs   = 0 : 1 : zipWith (+) fibs (tail fibs)   -- self-referential Fib stream

main = do
  print (take 10 fibs)               -- [0,1,1,2,3,5,8,13,21,34]
  print (takeWhile (< 100) (map (^2) nats))   -- squares under 100
```

`fibs` defines itself in terms of itself — well-founded *only* because `:` (cons) is lazy in its tail, so `fibs` is a thunk that unfolds exactly as far as `take`/`takeWhile` demands. This is the cleanest possible version of the lazy-stream patterns from earlier levels, and it's just *how you write Haskell*.

### 3. WHNF vs. NF: How Far Does Forcing Go?

Crucial and frequently misunderstood: forcing a value does **not** mean evaluating it completely. It means evaluating to **Weak Head Normal Form (WHNF)** — just enough to expose the *outermost constructor*.

```haskell
seq (1 + 2 : undefined) ()   -- OK! WHNF only needs the outermost (:),
                             -- not the head (1+2) nor the tail (undefined).
```

`seq` forces to WHNF. The list above has outermost constructor `(:)`, so `seq` is satisfied — it never touches the head thunk `1+2` or the bottom tail. To force *everything*, you need `deepseq` / `force`, which drives to **Normal Form (NF)**: no thunks anywhere inside.

This distinction is the source of countless "I added `seq` and still leaked" bugs. `seq` on a tuple forces the tuple's outer constructor but leaves both *components* as thunks. You wanted NF; you got WHNF.

### 4. The Space Leak: `foldl` and the Thunk Tower

Here is the canonical disaster. Sum a billion numbers:

```haskell
import Data.List (foldl)

main = print (foldl (+) 0 [1..1000000000])    -- DON'T: space leak
```

`foldl` is **lazy in its accumulator**. It does *not* compute the running sum. Instead it builds:

```text
(((...((0 + 1) + 2) + 3) + ...) + 1000000000)
```

— a thunk a billion levels deep, held entirely on the heap, *then* forced all at once at the end, typically overflowing the stack. The program either crashes or consumes gigabytes. The data list `[1..1e9]` is fine (lazy, GC'd as consumed); the **accumulator** is the leak.

The cure is **`foldl'`** (strict left fold, from `Data.List`):

```haskell
import Data.List (foldl')

main = print (foldl' (+) 0 [1..1000000000])   -- DO: constant space
```

`foldl'` forces the accumulator to WHNF on *every step*, so the running total is a real number, not a growing thunk. Constant memory, no overflow. The rule of thumb every Haskeller internalizes: **for a strict accumulation, use `foldl'`, never `foldl`.** (And `foldr` is the right choice when you're building a lazy structure or can short-circuit — different tool.)

### 5. Buying Strictness Back: `seq`, `$!`, BangPatterns, `deepseq`

Because laziness is the default, controlling space means *inserting strictness* at the right spots:

- **`seq a b`** — forces `a` to WHNF, then yields `b`. The primitive.
- **`f $! x`** — strict application: force `x` to WHNF, then call `f`. Sugar over `seq`.
- **`{-# LANGUAGE BangPatterns #-}` + `!x`** — force on bind, the ergonomic everyday tool:

```haskell
{-# LANGUAGE BangPatterns #-}
sumStrict :: [Int] -> Int
sumStrict = go 0
  where
    go !acc []     = acc          -- !acc forces the accumulator each call
    go !acc (x:xs) = go (acc + x) xs
```

- **`deepseq` / `force`** — drive to full Normal Form when WHNF isn't enough (e.g. a tuple/record accumulator whose *fields* would otherwise stay thunked):

```haskell
import Control.DeepSeq (deepseq, force)

-- A leak even with foldl', because the PAIR is WHNF but its components thunk:
meanLeaky = foldl' (\(s, c) x -> (s + x, c + 1)) (0, 0)   -- s and c still thunks!

-- Fix: force the components.
meanStrict = foldl' step (0, 0)
  where step (!s, !c) x = (s + x, c + 1)                  -- BangPatterns on fields
```

The `meanLeaky` case is the classic "I used `foldl'` and *still* leaked" trap: `foldl'` forces the tuple to WHNF, but WHNF for `(s, c)` is just "it's a pair" — `s` and `c` themselves stay thunks and tower up. You need component strictness (`!s`, `!c`) or `deepseq`.

### 6. Laziness and Side Effects Don't Mix Cleanly

Pure laziness reorders and skips computation freely — which is *fine* for pure values but *catastrophic* for side effects (the order and number of effects would be undefined). Haskell resolves this by making effects explicit in the `IO` type, sequenced by `>>=`/`do`-notation, *outside* the lazy-evaluation game. This is the deep version of a lesson from earlier levels: **keep side effects out of lazy values.** The famous `lazy IO` / `readFile`-returns-lazy-string feature is widely considered a misfeature precisely because it smuggles effects (file handles closing) into laziness, producing non-deterministic resource bugs. Senior practice prefers strict/streaming IO libraries.

---

## Code Examples

### The leak and its fix, side by side

```haskell
import Data.List (foldl, foldl')

-- LEAKS: billion-deep thunk tower in the accumulator → stack overflow.
badSum :: Integer
badSum = foldl (+) 0 [1..100000000]

-- CONSTANT SPACE: foldl' forces the accumulator each step.
goodSum :: Integer
goodSum = foldl' (+) 0 [1..100000000]
```

### `seq` forces, but only to WHNF — watch the depth

```haskell
import Control.DeepSeq (force)

pair :: (Int, Int)
pair = (1 + 1, 2 + 2)

whnf = pair `seq` "forced to WHNF"   -- forces the tuple shape; 1+1 and 2+2 STAY thunks
nf   = force pair `seq` "forced to NF" -- forces components too: both are real Ints now
```

### A strict accumulator with BangPatterns (the idiomatic fix)

```haskell
{-# LANGUAGE BangPatterns #-}

mean :: [Double] -> Double
mean xs = s / fromIntegral c
  where
    (s, c) = foldl' step (0, 0) xs
    step (!s, !c) x = (s + x, c + 1)   -- !s, !c force fields → no thunk buildup
```

### Infinite structures + the sieve, Haskell-native

```haskell
primes :: [Int]
primes = sieve [2..]
  where sieve (p:xs) = p : sieve [x | x <- xs, x `mod` p /= 0]

main = print (take 10 primes)   -- [2,3,5,7,11,13,17,19,23,29]
```

`sieve` recurses over an *infinite* list and yet `take 10` makes it terminate — demand-driven evaluation realizes only the prefix asked for. This is the middle-level sieve, but here it's the *natural* expression, not a deliberate trick.

### Laziness enables custom control flow

```haskell
-- Because arguments are thunks, you can write your own short-circuit / control flow:
myIf :: Bool -> a -> a -> a
myIf True  t _ = t      -- 'f' (the else branch) is never forced
myIf False _ f = f      -- 't' is never forced

safeHead :: [a] -> a -> a
safeHead xs def = myIf (null xs) def (head xs)   -- head xs not forced if xs is empty
```

In a strict language `myIf` can't work — both branches would evaluate before the call. Laziness is what makes `&&`, `||`, `if` expressible as *ordinary functions* rather than built-in magic.

### Bottom in an unforced position is harmless

```haskell
-- This is FINE: we never force the second element, so 'undefined' never blows up.
safe = take 1 [1, undefined, 3]    -- [1]

-- This blows up: forcing the spine to length reaches 'undefined'.
boom = length [1, undefined, 3]    -- length forces the SPINE... but not the elements!
                                   -- actually OK: length only forces (:), not heads.
-- THIS blows up: summing forces the elements.
kaboom = sum [1, undefined, 3]     -- *** Exception: Prelude.undefined
```

The subtlety — `length` forces the list *spine* (the `(:)` constructors) but **not** the element thunks, so `length [1, undefined, 3]` is `3`, no crash — is exactly the WHNF/NF distinction in the wild, and a favorite interview trap.

---

## Coding Patterns

**Pattern: strict left fold for accumulation.** Use `foldl'` (and `Data.Map.Strict`, strict `State`, strict fields) whenever you reduce a sequence to a value. `foldl` is almost always wrong here.

**Pattern: bang the accumulator.** With `BangPatterns`, prefix accumulator parameters with `!` in recursive helpers so they force to WHNF each step.

**Pattern: strict data fields.** Declare record/data fields strict with `!` so values stored in them are forced on construction, preventing thunk accumulation inside long-lived structures:

```haskell
data Stats = Stats { total :: !Int, count :: !Int }   -- strict fields, no inner thunks
```

**Pattern: `deepseq` at boundaries.** Force results to NF before storing them in caches, sending across threads, or returning from a worker, so you don't ship a thunk that retains a huge structure.

**Pattern: keep laziness for the producer, add strictness at the reducer.** Lazy generation (`[1..]`, `iterate`) is great; the *consumer that folds it down* is where strictness goes.

**Pattern: quarantine effects in `IO`.** Never bury side effects in lazy pure values; sequence them explicitly.

---

## Best Practices

- **Default to `foldl'` for strict reductions; reserve `foldr` for lazy/short-circuiting builds.** Know which one each problem wants.
- **Make accumulator fields strict** (`!Int`, BangPatterns) — the single highest-leverage anti-leak habit.
- **Understand WHNF vs. NF before reaching for `seq`.** If your accumulator is a tuple/record, WHNF won't save you; force the components.
- **Profile with heap profiling** (`+RTS -h`) when memory climbs — leaks are invisible to the type checker and obvious in a heap profile.
- **Don't sprinkle `seq` blindly.** Place strictness where demand analysis fails: long-lived accumulators and large folds. Over-forcing kills the benefits (infinite data, short-circuiting).
- **Keep effects in `IO`, avoid lazy IO** for resources (file handles, sockets); prefer streaming libraries with deterministic resource handling.
- **Treat `length`/`sum`/`foldl'`/pattern-match as forcing operations**; reason about exactly what depth each forces.

---

## Edge Cases & Pitfalls

**Pitfall 1: `foldl` instead of `foldl'`.** The textbook space leak. `foldl (+) 0 hugeList` towers thunks. Always `foldl'` for strict accumulation.

**Pitfall 2: "`foldl'` and still leaking."** `foldl'` forces only to WHNF. A tuple/record accumulator is WHNF as soon as its *constructor* is known; its *fields* stay thunks. Force the fields (`!s`, `!c`, strict data fields, `deepseq`).

**Pitfall 3: `seq` doesn't deep-force.** `x `seq` y` forces `x` one layer. If you needed the whole structure evaluated, you wanted `deepseq`/`force`.

**Pitfall 4: lazy state in `State`/`Writer` monad.** The lazy variants accumulate thunks in the state/log identically to `foldl`. Use `Control.Monad.State.Strict`, strict `Writer`/`mtl` accumulators, or accumulate into strict structures.

**Pitfall 5: lazy IO resource leaks.** `readFile` returns a lazy `String`; the handle closes when the string is fully consumed — which may be never, or after the `withFile` scope. Non-deterministic. Prefer strict/streaming IO.

**Pitfall 6: over-forcing.** Slapping `deepseq` everywhere destroys laziness's benefits — infinite structures now hang, short-circuiting now evaluates both branches, and you pay to force values you never use. Strictness is a scalpel, not a hammer.

**Pitfall 7: `⊥` hiding in unforced positions.** A bottom value (error/loop) lurking in a structure is *fine* until something forces it — meaning a refactor that adds a force (e.g. switching `foldr` to `foldl'`, or adding `length`) can resurrect a latent crash that "always worked before."

---

## Apply it

1. State the system invariant that **Eager vs. Lazy Evaluation** must protect.
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

- Which invariant must remain true when Eager vs. Lazy Evaluation fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
