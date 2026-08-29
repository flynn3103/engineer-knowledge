# Higher-Kinded Types — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Higher-Kinded Types** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Types classify values; kinds classify types

Think of three levels:

```text
LEVEL 0  values:   3        "hi"        true        [1, 2, 3]
                    │          │           │            │
LEVEL 1  types:    Int      String      Bool        List<Int>
                    │          │           │            │
LEVEL 2  kinds:    *          *           *            *
```

A **type** answers "what values can this be?". `3` has type `Int`. A **kind** answers "what types can this be?" — it classifies the *types themselves*. A finished type like `Int` or `List<Int>` has kind `*`.

The key realization: **`List` by itself is not at level 1 next to `Int`.** `List` is incomplete. You can't store a "`List`" the way you store an `Int`. You can only store a `List<Int>` or a `List<String>`. So `List` lives one notch higher — it is a *function at the type level*.

### 2. Type constructors are functions that build types

Read `List` as a little machine:

```text
List : give me a type  -->  I return a finished type
       List(Int)   = List<Int>      ✅ a finished type, kind *
       List(String)= List<String>   ✅ a finished type, kind *
       List        =                ❌ not finished — still hungry for an argument
```

That "type-level function" has a kind that mirrors a normal function signature:

```text
List   :: * -> *          one type in, one type out
Maybe  :: * -> *          one type in, one type out
Set    :: * -> *
Either :: * -> * -> *     two types in (the error type and the value type)
Map    :: * -> * -> *     two types in (key and value)
Int    :: *               needs nothing — already a finished type
```

**Counting the arrows tells you how many type arguments are still missing.** `*` means "done". Each `* ->` means "still needs one more type".

### 3. "Higher-kinded" means a type parameter that is itself `* -> *`

Ordinary generics let you abstract over a *type* of kind `*`:

```text
function length<A>(xs: List<A>): Int     // A is any FINISHED type — kind *
```

A higher-kinded type lets you abstract over a *type constructor* of kind `* -> *`:

```text
function describe<F>(fa: F<String>): String   // F is any CONTAINER — kind * -> *
//                  ^ F could be List, Option, Future, Either<Err, _>, ...
```

Here `F` is not `Int` or `String`. `F` is *the box itself*, left as a hole. You're saying: "I'll work with `F<String>` for **whatever container `F` happens to be**." That is the whole game. Most mainstream languages (Java, Go, C#, Rust, TypeScript as of today's native syntax) **cannot** write that `F` hole — they only have the kind-`*` hole. Haskell and Scala can.

### 4. Why you'd want this: `map` is the same idea everywhere

Look at how `map` shows up across containers:

```text
List:    [1, 2, 3].map(x => x * 10)        ==>  [10, 20, 30]
Option:  Some(2).map(x => x * 10)          ==>  Some(20)
Option:  None.map(x => x * 10)             ==>  None
Either:  Right(2).map(x => x * 10)         ==>  Right(20)
Either:  Left("boom").map(x => x * 10)     ==>  Left("boom")   (untouched)
Future:  fetchAge().map(age => age + 1)    ==>  a Future of (age + 1)
```

In *every* case the shape is: **take a function `A -> B`, reach inside `F<A>`, apply it, hand back `F<B>`, leave the container's structure alone.** That repeated pattern is begging to be named once and reused. The name is **Functor**, and writing "the `map` that works for every `F`" *requires* a higher-kinded type — because you're abstracting over the container `F`.

### 5. Functor, in plain words

A **Functor** is any container `F` (kind `* -> *`) for which you can implement:

```text
map : (A -> B) -> F<A> -> F<B>
```

with two common-sense rules (the **functor laws**):

1. **Identity:** `xs.map(x => x)` returns `xs` unchanged. Mapping with "do nothing" does nothing.
2. **Composition:** `xs.map(f).map(g)` equals `xs.map(x => g(f(x)))`. Two maps fuse into one.

That's it. `List`, `Option`, `Either`, `Future`, trees — all are Functors. The laws are not bureaucracy; they're what lets you refactor `map` chains safely.

### 6. Monad, demystified: `flatMap` + `pure`

Sometimes the function you want to apply *itself returns a container*. Example: `parseInt : String -> Option<Int>`. If you `map` it over an `Option<String>`, you get `Option<Option<Int>>` — a box inside a box. Annoying.

**`flatMap`** (a.k.a. `bind`, `>>=`, `andThen`, `SelectMany`) is `map` followed by *flattening one layer*:

```text
flatMap : (A -> F<B>) -> F<A> -> F<B>
```

A **Monad** is a container `F` with:

- `flatMap` (chain a container-returning step), and
- `pure` / `of` (wrap a plain value: `pure(3)` is `Some(3)` for Option, `[3]` for List),

obeying a few laws. Concretely, here is what `flatMap` *does* per container — no mysticism:

```text
Option:  Some(2).flatMap(x => half(x))   where half(4)=Some(2), half(odd)=None
         Some(4).flatMap(half) = Some(2)        None.flatMap(half) = None
         "stop the chain the moment something is None"

List:    [1, 2].flatMap(x => [x, x*10]) = [1, 10, 2, 20]
         "run the rest for EVERY element and concatenate"

Either:  Right(2).flatMap(step) runs step; Left(e).flatMap(step) = Left(e)
         "short-circuit on the first error, carry it through"
```

So a monad is not magic. It is **"a container of kind `* -> * ` with a sane `flatMap` and `pure`"**, and `flatMap` is just "do the next step, then flatten". The reason it deserves a shared name — and the reason it needs higher-kinded types — is that `flatMap` has the *exact same signature* for `Option`, `List`, `Either`, `Future`, and dozens more. Write the abstraction once, get it for all of them.

### 7. The hierarchy: Functor → Applicative → Monad

These three stack, each adding power:

```text
Functor      can: map  (A -> B) over F<A>
   │  add the ability to combine independent F's
Applicative  can also: combine F<A> and F<B> into F<(A,B)>; lift pure values
   │  add the ability to let a later step DEPEND on an earlier result
Monad        can also: flatMap — sequence steps where step 2 depends on step 1's value
```

You don't need the details now. The shape to remember: **every Monad is an Applicative, every Applicative is a Functor.** More structure = more operations you're promising to provide.

---

## Code Examples

We stay light. The point is to *see* kinds and the shared shape, not to master Haskell yet.

### Seeing kinds (Haskell, read-only)

In a Haskell REPL you can literally ask for a type's kind with `:kind` (`:k`):

```haskell
ghci> :kind Int
Int :: *

ghci> :kind Maybe
Maybe :: * -> *

ghci> :kind Maybe Int      -- now we've supplied the argument
Maybe Int :: *

ghci> :kind Either
Either :: * -> * -> *

ghci> :kind Either String  -- supplied one of two; one hole remains
Either String :: * -> *
```

Notice `Either String` still has kind `* -> *`. Supplying *one* argument to a two-argument constructor leaves a one-argument constructor. This is exactly like a function: give a 2-argument function one argument and you get a 1-argument function back. Kinds behave the same way at the type level.

### The repeated shape of `map` (TypeScript, the part everyone already knows)

```typescript
// You have written all three of these. Stare at how similar they are.
[1, 2, 3].map(x => x + 1);              // Array<number> -> Array<number>

function mapOption<A, B>(o: A | null, f: (a: A) => B): B | null {
  return o === null ? null : f(o);      // Option-ish -> Option-ish
}

promise.then(x => x + 1);               // Promise<number> -> Promise<number>
```

Each one is `(A -> B) -> F<A> -> F<B>` for a different `F` (`Array`, the nullable, `Promise`). The *signature is identical* up to the container. A higher-kinded language lets you write the single function `map<F, A, B>(fa: F<A>, f: (a: A) => B): F<B>` and have it apply to all of them. TypeScript's native syntax cannot, because you cannot write `F<A>` with `F` left as a parameter — `middle.md` shows the clever encoding fp-ts uses to fake it.

### `flatMap` doing different jobs, same signature (pseudocode)

```text
// Option: short-circuit on absence
findUser(id)            // Option<User>
  .flatMap(u => u.emailVerified ? Some(u.email) : None)   // Option<Email>

// List: cartesian / non-determinism
[1, 2, 3].flatMap(n => [n, -n])         // [1, -1, 2, -2, 3, -3]

// Either: stop on first error, keep the error
parseConfig(text)                       // Either<Error, Config>
  .flatMap(cfg => validate(cfg))        // Either<Error, Config>
```

Three completely different runtime behaviors — short-circuit, cartesian product, error-propagation — yet **one shared signature** `(A -> F<B>) -> F<A> -> F<B>`. That shared signature is what `Monad` abstracts, and abstracting it needs higher-kinded types.

### A taste of writing the abstraction (Scala, just read it)

```scala
// "Functor" for ANY container F that has one hole. F[_] is the HKT part.
trait Functor[F[_]] {
  def mapA, B(f: A => B): F[B]
}

// One instance for Option, one for List. The CALLER's code below never
// mentions Option or List — only "some Functor F".
given Functor[Option] with
  def mapA, B(f: A => B): Option[B] = fa.map(f)

given Functor[List] with
  def mapA, B(f: A => B): List[B] = fa.map(f)

// Generic over the container: works for Option, List, or anything with a Functor.
def bump[F[_]](fa: F[Int])(using F: Functor[F]): F[Int] =
  F.map(fa)(_ + 1)

bump(Some(41))      // Some(42)
bump(List(1, 2, 3)) // List(2, 3, 4)
```

`F[_]` in `Functor[F[_]]` is Scala's way of writing "F is a one-hole type constructor, kind `* -> *`". That underscore-in-brackets is a higher-kinded type. You'll learn to write these in `middle.md`/`senior.md`; for now, just notice that `bump` is **one function that runs for every container**.

---

## Coding Patterns

### Pattern 1: Reach for `map` before `flatMap`

If your transformation is a plain `A -> B`, use `map`. Use `flatMap` *only* when your step returns a container (`A -> F<B>`). Over-reaching for `flatMap` produces awkward code and demands more structure (Monad) than you need (Functor).

### Pattern 2: Read `F<_>` / `F[_]` / `f a` as "some container, unspecified"

When you see a one-hole type parameter, mentally substitute "any of List, Option, Either, Future…". The code is promising to behave for *all* of them.

### Pattern 3: Pick the lowest rung (Functor < Applicative < Monad)

Ask for the least powerful abstraction that does the job. If you only transform inside the box, require `Functor`. Asking for `Monad` everywhere needlessly narrows what types your function accepts.

### Pattern 4: Let the container handle absence/error, not `if`-ladders

`Option`/`Either` plus `map`/`flatMap` replace nested null checks and try/catch ladders with a flat chain that short-circuits automatically. That chaining is exactly what the Monad structure provides.

---

## Best Practices

- **Learn kinds before learning monads.** "Monad" is confusing until you've internalized that `F` is a `* -> *` thing. Count the holes first.
- **Don't say "monad" mystically.** It's a container with `flatMap` and `pure` obeying laws. If you can explain what `flatMap` does for `Option` and `List`, you understand monads.
- **Trust the laws when refactoring.** `map(f).map(g)` becomes `map(g ∘ f)`; a `flatMap` chain can be reordered per the monad laws. These rewrites are safe *because* the laws hold.
- **Prefer the standard `map`/`flatMap` on your language's built-in `Optional`/`Result`/`Stream`** to get comfortable, even before touching HKT libraries. You're already using Functors and Monads informally.
- **Don't introduce an HKT library into a team that isn't ready.** The abstraction tax is real. Make sure the reuse payoff is worth the onboarding cost.

---

## Edge Cases & Pitfalls

- **"`List` is a type" — no.** `List` is a *type constructor* (kind `* -> *`). `List<Int>` is the type. Saying "a value of type `List`" is a category error, like saying "a value of type `+`".
- **`map` returning nested containers.** Mapping an `F`-returning function gives `F<F<B>>`. That's the signal you wanted `flatMap`, which flattens one layer.
- **Confusing the three "highers".** *Higher-kinded* (abstract over type constructors), *higher-rank* (abstract over polymorphic functions), and *higher-order* (functions that take functions) are three different things. They share the word "higher" and nothing else. Senior pages disambiguate carefully; just don't assume they're the same.
- **Assuming every language can do this.** Java's `<T>` and Go's `[T any]` are kind-`*` only. You *cannot* write a general `Functor` in them; the type parameter can't itself be a one-hole constructor. This is a real, hard limitation, not an oversight you can work around with more generics.
- **Thinking monads are about side effects.** `Option` and `List` are monads with zero side effects. The monad structure is about *sequencing and flattening*, not I/O — though it's famously *used* to sequence I/O in Haskell.
- **Forgetting the laws.** A type with a `map` that secretly reorders or drops elements is *not* a lawful Functor, and generic code built on Functor will misbehave. Laws are part of the contract.

---

## Apply it

1. Choose one small, known input for **Higher-Kinded Types**.
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

- What problem does Higher-Kinded Types solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
