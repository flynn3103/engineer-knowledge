# Higher-Kinded Types — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Higher-Kinded Types** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. A typeclass can be parameterized by a `* -> *` type

An ordinary interface abstracts over a *type* of kind `*`. A higher-kinded typeclass abstracts over a *type constructor* of kind `* -> *`. In Haskell the kind is visible:

```haskell
class Functor f where
  fmap :: (a -> b) -> f a -> f b
--          ^a,b are kind *      ^f is applied to a type, so f :: * -> *
```

The compiler **infers** that `f` must have kind `* -> *` because you write `f a` (you apply `f` to a type). You cannot make `f` be `Int` here — `Int a` is nonsense (`Int` takes no arguments). This is the type-level analogue of an arity check.

In Scala the kind is written explicitly with `F[_]`:

```scala
trait Functor[F[_]]:
  def mapA, B(f: A => B): F[B]
//      F[_] declares F :: * -> *
```

`F[_]` means "F is a unary type constructor". Without the underscore, `Functor[F]` would demand `F :: *` and you couldn't write `F[A]`.

### 2. Functor: the laws are the contract

`map`/`fmap` must satisfy:

```text
1. Identity:     fmap id == id
                 fmap (\x -> x) fa  ==  fa
2. Composition:  fmap (g . f) == fmap g . fmap f
                 fmap (\x -> g (f x)) fa  ==  fmap g (fmap f fa)
```

These say "`map` only touches the contents, never the structure". A `map` for a list that reversed the list would *type-check* but **break the laws**, and any generic code assuming lawful Functors could then be wrong. The laws are not optional decoration — they are the part the compiler *can't* check and you must.

### 3. Applicative: combine independent effects

`Functor` can lift `A -> B` into `F<A> -> F<B>`. But what about a two-argument function `A -> B -> C` and two independent effects `F<A>`, `F<B>`? You can't get there with `map` alone. **Applicative** adds exactly that:

```haskell
class Functor f => Applicative f where
  pure  :: a -> f a
  (<*>) :: f (a -> b) -> f a -> f b
```

`pure` injects a value; `<*>` ("ap") applies a wrapped function to a wrapped argument. With them you can lift any n-ary function:

```haskell
-- combine two independent Maybe values with (+)
(+) <$> Just 3 <*> Just 4   == Just 7
(+) <$> Just 3 <*> Nothing  == Nothing      -- any Nothing kills the result
```

The defining trait: the effects are **independent**. `F<B>` does not depend on the *value* inside `F<A>` — only their structures combine. That independence is why Applicative can do things Monad can't always do efficiently (batch, parallelize, accumulate *all* errors).

### 4. Monad: let a later step depend on an earlier result

`Applicative` combines independent effects. **Monad** adds the power for a later effect to *depend on the value produced by an earlier one*:

```haskell
class Applicative m => Monad m where
  (>>=) :: m a -> (a -> m b) -> m b   -- "bind" / flatMap
  -- return = pure
```

The function `a -> m b` receives the *unwrapped* `a` and chooses the next effect based on it. That's the difference: in `<*>` the second effect is fixed up front; in `>>=` it's computed from the first effect's result.

```haskell
lookupUser id      >>= \user ->     -- Maybe User
lookupAddress user >>= \addr ->     -- the address LOOKUP depends on `user`
pure (format addr)
```

### 5. The monad laws

`>>=` and `pure` must obey:

```text
Left identity:   pure a >>= f      ==  f a
Right identity:  m >>= pure        ==  m
Associativity:   (m >>= f) >>= g   ==  m >>= (\x -> f x >>= g)
```

Left identity: wrapping then binding is just calling. Right identity: binding with `pure` changes nothing. Associativity: how you parenthesize a chain doesn't matter — this is what makes `do`-notation / for-comprehensions well-defined.

### 6. Concrete instances (the whole point)

Here is `Maybe` as Functor/Applicative/Monad, end to end:

```haskell
instance Functor Maybe where
  fmap _ Nothing  = Nothing
  fmap f (Just x) = Just (f x)

instance Applicative Maybe where
  pure = Just
  Nothing  <*> _ = Nothing
  Just f   <*> m = fmap f m

instance Monad Maybe where
  Nothing  >>= _ = Nothing          -- short-circuit on absence
  Just x   >>= f = f x              -- feed x into the next step
```

And `Either e` (note: `Either` is `* -> * -> *`, so we fix the error type `e` and the *constructor* `Either e` has kind `* -> *`):

```haskell
instance Monad (Either e) where
  Left  err >>= _ = Left err        -- short-circuit, carry the error
  Right x   >>= f = f x
```

And `[]` (list), where `>>=` is "for each element, run the function, concatenate":

```haskell
instance Monad [] where
  xs >>= f = concat (map f xs)      -- [1,2] >>= \x -> [x,x] == [1,1,2,2]
```

Same three signatures, three completely different behaviors. *That* is what higher-kinded abstraction buys: generic code over `m` runs against all of them.

### 7. Partial application at the type level (the `Either e` subtlety)

`Functor`/`Monad` demand a `* -> *` argument, but `Either :: * -> * -> *` and `Map :: * -> * -> *` have *two* holes. You make them fit by **fixing all but the last argument**, leaving one hole:

```text
Either        :: * -> * -> *
Either String :: * -> *          ✅ now it fits a Functor/Monad slot
```

Haskell does this with plain partial application: `instance Functor (Either e)`. Scala needs a **type lambda** because you can't write a "partially applied type" inline as easily:

```scala
// Scala 3 type lambda: "fix E, leave one hole X"
type EitherE[E] = [X] =>> Either[E, X]
given [E]: Functor[[X] =>> Either[E, X]] with
  def mapA, B(f: A => B): Either[E, B] = fa.map(f)
```

This is the type-level mirror of currying: `Either` is "curried", and supplying one argument yields a one-hole constructor.

### 8. The encoding problem (languages without native HKTs)

TypeScript and Kotlin cannot write `F<A>` with `F` as a parameter. They fake it via **defunctionalization** (the "lightweight higher-kinded polymorphism" trick, popularized by Yallop & White and used by fp-ts):

- Represent each type constructor by a unique *tag* (a marker type).
- Define one indexed type `Kind<F, A>` ("the type you get by applying constructor `F` to `A`") via a lookup table interface.
- Each real constructor registers itself in that table.

```typescript
// fp-ts-style sketch (simplified)
interface URItoKind<A> {        // the "apply" table, extended by declaration merging
  Option: Option<A>;
  Array:  Array<A>;
}
type URIS = keyof URItoKind<unknown>;        // the set of constructor tags
type Kind<F extends URIS, A> = URItoKind<A>[F];  // "F applied to A"

interface Functor<F extends URIS> {
  map<A, B>(fa: Kind<F, A>, f: (a: A) => B): Kind<F, B>;
}
```

It works, and it's type-safe, but it's verbose, the error messages are rough, and you constantly pass the `F` tag around by hand. We go deeper in `senior.md`. The lesson: **HKTs can be *encoded* almost anywhere, but only native support makes them ergonomic.**

---

## Code Examples

### Generic code over an arbitrary Monad (Haskell)

```haskell
-- Works for Maybe, Either e, [], IO, State s, ... ANY Monad.
twiceThenAdd :: Monad m => m Int -> m Int
twiceThenAdd mx = do
  x <- mx          -- desugars to  mx >>= \x ->
  y <- mx          --              mx >>= \y ->
  pure (x + x + y)

-- main> twiceThenAdd (Just 5)         == Just 15
-- main> twiceThenAdd Nothing          == Nothing
-- main> twiceThenAdd [1,2]            == [3,4,4,5, 4,5,5,6]  (cartesian!)
```

One definition; the behavior changes with the container. `[1,2]` produces a cartesian explosion because list-bind is non-determinism. That single example shows both the power *and* the danger of being generic over `m`.

### The same in Scala with Cats

```scala
import cats.Monad
import cats.syntax.all.*

def twiceThenAdd[F[_]: Monad](fx: F[Int]): F[Int] =
  for {
    x <- fx
    y <- fx
  } yield x + x + y

twiceThenAdd(Option(5))            // Some(15)
twiceThenAdd(List(1, 2))           // List(3,4,4,5, 4,5,5,6)
twiceThenAdd(RightString, Int)// Right(15)
```

`[F[_]: Monad]` reads "for any one-hole constructor `F` that has a `Monad` instance". The for-comprehension is sugar over `flatMap`/`map`, exactly like Haskell `do`.

### Applicative accumulates ALL errors; Monad stops at the first

```scala
import cats.data.Validated      // Applicative that accumulates
import cats.data.Validated.{Valid, Invalid}
import cats.syntax.all.*

def check(name: String, age: Int): Validated[List[String], (String, Int)] = {
  val n = if (name.nonEmpty) name.valid else List("empty name").invalid
  val a = if (age >= 0) age.valid else List("negative age").invalid
  (n, a).mapN((_, _))            // Applicative combine — runs BOTH checks
}

check("", -1)   // Invalid(List("empty name", "negative age"))  -- BOTH errors
```

A `Monad`/`Either` chain would short-circuit and report only `"empty name"`. This is the headline reason Applicative is its own rung: **independent effects can be combined to gather everything, not just the first failure.**

### Writing a Monad instance and checking a law (Haskell)

```haskell
newtype Identity a = Identity { runIdentity :: a }

instance Functor Identity where
  fmap f (Identity a) = Identity (f a)
instance Applicative Identity where
  pure = Identity
  Identity f <*> Identity a = Identity (f a)
instance Monad Identity where
  Identity a >>= f = f a

-- Left identity check:  pure 5 >>= f  ==  f 5
--   pure 5 >>= f  =  Identity 5 >>= f  =  f 5   ✅
```

`Identity` is the "no effect" monad — useful as a base case and for testing generic code.

### The TypeScript encoding, used

```typescript
// Given the Kind/URItoKind machinery from Core Concept 8:
const functorArray: Functor<'Array'> = {
  map: (fa, f) => fa.map(f),
};
const functorOption: Functor<'Option'> = {
  map: (fa, f) => (fa._tag === 'None' ? fa : some(f(fa.value))),
};

// Generic consumer — note we pass the instance explicitly (no implicit resolution)
function bump<F extends URIS>(F: Functor<F>, fa: Kind<F, number>): Kind<F, number> {
  return F.map(fa, (x) => x + 1);
}
bump(functorArray, [1, 2, 3]);   // [2, 3, 4]
```

Compare with Scala's `[F[_]: Monad]`: in TypeScript you thread the instance and the tag by hand. It works, it's sound, it's just heavier — which is exactly why HKTs feel native in Haskell/Scala and bolted-on elsewhere.

---

## Coding Patterns

### Pattern 1: Constrain to the weakest typeclass that compiles

Start a generic function with `Functor`. If you need to combine independent effects, widen to `Applicative`. Only widen to `Monad` when a step genuinely depends on a previous result. This maximizes the set of types your function accepts.

### Pattern 2: Fix extra type arguments to reach `* -> *`

To give a Functor/Monad instance for `Either`, `Map`, or `Validated`, fix all but the last type parameter (`Either E`, type lambda `[X] =>> Either[E, X]`). The "effect" is always the *last* hole.

### Pattern 3: Use `do`/for-comprehension for readable bind chains

`do` (Haskell) and `for { ... } yield` (Scala) desugar to `>>=`/`flatMap`. Prefer them over hand-written bind ladders for sequential, dependent steps; they read like imperative code while staying generic over `m`.

### Pattern 4: Reach for Applicative when you want all errors / parallelism

If sub-computations are independent, model them with Applicative so you can accumulate failures or run them concurrently — capabilities a Monadic chain forfeits by sequencing.

---

## Best Practices

- **Verify instances against the laws** — by hand for small types, with property-based tests (`Discipline` in Cats, QuickCheck in Haskell) otherwise. An unlawful instance is a landmine for every generic caller.
- **Prefer existing instances** from Cats/Haskell `base`/fp-ts over rolling your own; they're law-tested.
- **Document the kind** when you introduce a new type constructor: is it `* -> *`? Two holes fixed to one? Make it obvious.
- **Don't over-abstract.** If a function is only ever called with `Option`, don't make it `[F[_]: Monad]`. Generalize when a *second* concrete use appears, not before.
- **Teach `flatMap` concretely.** When onboarding, explain what bind *does* for `Option`/`Either`/`List` before invoking the word "monad".
- **In encoded HKT (TS/Kotlin), isolate the machinery.** Keep the `Kind`/tag plumbing in one module so application code sees clean `F`-generic signatures.

---

## Edge Cases & Pitfalls

- **Unlawful instances type-check.** The compiler verifies the *signatures*, never the *laws*. A Functor whose `map` drops elements compiles fine and silently corrupts generic code. Test the laws.
- **List monad's combinatorial blow-up.** `>>=` for lists is a cartesian product; an innocent generic function can explode from `O(n)` to `O(n^k)` when instantiated at `[]`. Generic-over-`m` code hides its runtime cost.
- **`pure`/`return` ambiguity.** Haskell `return` is `pure`, not control flow. Scala's `pure` needs the target `F` known (`3.pure[Option]`) or inference fails.
- **`Set` is not a lawful Functor (in general).** `Set` requires `Ord`/`Eq` on its elements, so it can't satisfy `Functor`'s "works for *any* element type" signature without constraints — a classic "looks like a Functor but isn't" trap.
- **Two-hole confusion.** Forgetting to fix the extra argument (`Functor Either` instead of `Functor (Either e)`) is a kind error: you'd be feeding a `* -> * -> *` where `* -> *` is required.
- **Applicative vs Monad for errors.** Using a Monad where you wanted *all* errors gets you only the first. Reach for Applicative/`Validated` deliberately.
- **Scala implicit/`given` resolution failures** produce intimidating "could not find implicit Monad[F]" errors — usually a missing import (`cats.syntax.all.*`) or a `F[_]` that has no instance, not a logic bug.

---

## Apply it

1. Find a real component where **Higher-Kinded Types** affects an interface or dependency.
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

- Which boundary is most affected by Higher-Kinded Types?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
