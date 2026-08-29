# Higher-Kinded Types — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Higher-Kinded Types** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Kinds form a typed lambda calculus, one level up

The clean way to see kinds: they are the *types* of the simply-typed lambda calculus whose *terms* are type constructors. Concretely:

```text
VALUE level:  terms  3, \x -> x       have   types   Int, a -> a
TYPE  level:  types  Int, Maybe, []   have   kinds   *, * -> *, * -> *
KIND  level:  kinds  *, * -> *        have   sorts   (just one: BOX/□)
```

Everything you know about function types transfers:

- **Application:** `Maybe Int` is `Maybe` applied to `Int`; kind `*`. Just like `f 3` applies `f : Int -> a`.
- **Currying / partial application:** `Either :: * -> * -> *`; `Either String :: * -> *`. Mirrors `(+) :: Int -> Int -> Int`, `(+) 3 :: Int -> Int`.
- **Higher-order:** `Functor :: (* -> *) -> Constraint` *takes a constructor as an argument*. This is a **higher-order kind** — the type-level analogue of a higher-order function. `Constraint` is GHC's kind for "a thing you can put left of `=>`".
- **Kind variables and polymorphism:** with `PolyKinds`, a definition can quantify over a kind variable `k`, giving type-level generics over kinds (e.g. `Proxy :: forall k. k -> *`).

So "higher-kinded" is precisely "uses a type variable whose kind is itself an arrow (`* -> *` or richer)". The whole edifice is one typed calculus stacked on another.

### 2. `Traversable`: doubly higher-kinded, the crown jewel

`traverse` is the abstraction that most convincingly *needs* HKTs, because it is generic in **two** constructors simultaneously:

```haskell
class (Functor t, Foldable t) => Traversable t where
  traverse :: Applicative f => (a -> f b) -> t a -> f (t b)
--                                            ^t :: * -> * (the structure)
--                              ^f :: * -> *  (the effect)
```

Read it: "for a structure `t` (list, tree, `Maybe`) and an effectful function `a -> f b`, visit every `a` in the structure, run the effect, and turn `t (f b)` *inside-out* into `f (t b)`." A single function gives you:

```haskell
traverse validate   [x, y, z]   :: Either Err [Validated]   -- validate a list, collect/short-circuit
traverse httpGet    urls        :: IO [Response]            -- fire N requests, gather results
traverse lookup     keys        :: Maybe [Value]            -- all-or-nothing lookups
sequence  [Just 1, Just 2]      :: Maybe [Int]   == Just [1,2]
sequence  [Just 1, Nothing]     :: Maybe [Int]   == Nothing
```

You cannot type `traverse` in Java, Go, or Rust: there is no way to write a function parameterized by *two arbitrary `* -> *` constructors*. This is the concrete capability HKTs buy that nothing else replicates.

### 3. The three "highers", disambiguated precisely

These collide constantly. Pin them down:

```text
HIGHER-ORDER (value level, about functions):
    map :: (a -> b) -> [a] -> [b]
    A function whose ARGUMENT is a function. Ordinary. Every language has it.

HIGHER-KINDED (type level, about type constructors):
    class Functor f where fmap :: (a -> b) -> f a -> f b
    A type abstracts over a TYPE CONSTRUCTOR f :: * -> *.
    Java/Go/Rust cannot do this.

HIGHER-RANK (type level, about WHERE forall sits):
    applyToBoth :: (forall a. a -> a) -> (Int, Bool) -> (Int, Bool)
    An argument that is ITSELF polymorphic — the caller cannot choose `a`;
    the function gets to use it at multiple types internally.
    (Rank-1 = all foralls at the outside, the usual case. Rank-2+ nests them.)
```

Diagnostic questions:
- Does it take a *function value*? → higher-**order**.
- Does it abstract over a *container/constructor* (`F<_>`)? → higher-**kinded**.
- Does an *argument* carry its *own* `forall` (must stay polymorphic inside)? → higher-**rank**.

They're orthogonal: `traverse` is higher-kinded *and* higher-order; ST-monad's `runST :: (forall s. ST s a) -> a` is higher-rank but not higher-kinded.

### 4. Tagless-final and MTL: whole programs polymorphic in the effect

The ultimate payoff of HKTs is writing an *entire program* against an abstract effect `F[_]`, then choosing `F` at the edge.

**Tagless-final** encodes capabilities as typeclasses:

```scala
trait Console[F[_]]:   def putLine(s: String): F[Unit]; def getLine: F[String]
trait Clock[F[_]]:     def now: F[Long]

def greet[F[_]: Monad](using C: Console[F], K: Clock[F]): F[Unit] =
  for {
    name <- C.getLine
    t    <- K.now
    _    <- C.putLine(s"Hi $name at $t")
  } yield ()

// Production: F = IO. Tests: F = a pure State monad that records output. SAME program.
```

**MTL** stacks capabilities as constraints (`MonadState s`, `MonadError e`, `MonadReader r`). A function `(MonadState Int m, MonadError String m) => m Result` declares "I need state and error", and the concrete monad transformer stack that provides them is chosen elsewhere. Both styles are *only possible* because `m`/`F` is a higher-kinded parameter the whole program quantifies over. This is the architecture behind Cats Effect, ZIO (which goes further with `ZIO[R, E, A]`), and Haskell's `mtl`/`polysemy`/`effectful`.

### 5. Why Rust refuses HKTs — the concrete reasons

Rust *wants* HKTs (RFCs and discussions span a decade) but has not shipped them. The obstacles are real and instructive:

1. **Type inference & coherence interact badly.** Rust's trait resolution must stay decidable and *coherent* (one impl per type globally, the orphan rules). Adding type-constructor variables makes unification and overlap checking dramatically harder; `F<_>` appearing in `where` clauses explodes the search space.
2. **Lifetimes.** Rust types carry lifetimes. A "container" `F<_>` would frequently need to be `F<'a, _>` — abstracting over a constructor that is *itself* lifetime-parameterized — which is a much harder problem than HKTs in a GC'd language. Many natural Rust "functors" (iterators borrowing their source) want exactly this.
3. **Monomorphization & associated-type machinery.** Rust compiles generics by monomorphizing. A truly HKT-generic function would interact with the trait/associated-type system in ways the team judged not yet sound or ergonomic.
4. **No `pure`/return-type polymorphism by default.** `pure :: a -> f a` returns an `f` chosen by *context*; Rust resolves methods by receiver, so "produce the right `F`" is awkward without HKTs.

**The `Functor` you cannot write in Rust:**

```rust
// THIS DOES NOT COMPILE. Rust has no `Self<U>` / higher-kinded `Self`.
trait Functor {
    fn map<A, B>(self: Self<A>, f: impl Fn(A) -> B) -> Self<B>;
    //          ^^^^^^^^ you cannot apply a type parameter `Self` to `A`
}
```

There is no way to say "the same constructor, different element type". You can write `Iterator::map`, `Option::map`, `Result::map` individually, but **not one trait that unifies them**, so no generic `traverse`, no effect-polymorphism.

### 6. GATs: the partial step Rust did take

Generic Associated Types (stable Rust 1.65) let an *associated type* be parameterized by generics or lifetimes:

```rust
trait LendingIterator {
    type Item<'a> where Self: 'a;          // associated type with a LIFETIME parameter
    fn next<'a>(&'a mut self) -> Option<Self::Item<'a>>;
}
```

GATs solve the "lending iterator / streaming iterator" problem (yielding items that borrow from the iterator) — long the poster child for "Rust needs HKTs". But **GATs are not HKTs**:

- A GAT parameterizes an *associated type member* of a trait. An HKT parameterizes the *type implementing the trait* by a constructor.
- You still cannot write `trait Functor` where `Self` is applied to a varying element type. GATs give you `type Item<'a>`, not `Self<A>`.
- They unblock specific patterns (lending iterators, some "type families") that *resemble* HKT use cases, which is why they're called "a step toward". They are not a general substitute, and the Rust community is explicit that full HKTs remain unsolved.

Mentally: **GATs add parameters to the *outputs* of a trait; HKTs would let the *trait itself* range over constructors.** Different axis.

### 7. The defunctionalization encoding, rigorously

The Yallop–White trick (TypeScript fp-ts, OCaml, Kotlin Arrow's earlier versions) turns "apply type constructor `F` to `A`" into a *defunctionalized* operation. The essence:

- Each constructor gets a unique **brand/tag** (a phantom marker type).
- A single open type-level function `Apply<F, A>` (called `Kind`/`URItoKind` in fp-ts, `Kind<F, A>` in Arrow) maps `(tag, A)` to the real applied type via a registry.
- Typeclasses are parameterized by the *tag*, and operations use `Apply<F, A>` in their signatures.

```typescript
interface URItoKind<A> {}                    // open registry (declaration merging)
type URIS = keyof URItoKind<unknown>;
type Kind<F extends URIS, A> = URItoKind<A>[F];

// register Option
declare module './hkt' { interface URItoKind<A> { Option: Option<A> } }

interface Monad<F extends URIS> {
  of<A>(a: A): Kind<F, A>;
  flatMap<A, B>(fa: Kind<F, A>, f: (a: A) => Kind<F, B>): Kind<F, B>;
}
```

It is **sound and type-safe** — but it is *first-order emulation* of a higher-order kind feature. The costs: instances are threaded explicitly (no `given` resolution unless you build it), error messages reference `Kind<...>` noise, and partial application of multi-arg constructors needs extra tags (`URIS2`, `URIS3` in older fp-ts) or HKT-with-fixed-params encodings. Kotlin's Arrow used this for years and ultimately leaned away from heavy HKT emulation toward more direct, less generic APIs — a telling signal about the ergonomics ceiling.

---

## Code Examples

### `traverse` unifying validation, IO, and optionality (Haskell)

```haskell
-- ONE function; three radically different effects via the Applicative f.
parseRow :: String -> Either Error Int
loadRows :: [String] -> Either Error [Int]
loadRows = traverse parseRow          -- short-circuits on first parse error

fetch :: Url -> IO Response
fetchAll :: [Url] -> IO [Response]
fetchAll = traverse fetch             -- sequences N IO actions, collects results

-- And sequence is traverse id:
sequence' :: Applicative f => [f a] -> f [a]
sequence' = traverse id
```

### Effect-polymorphic program, two interpreters (Scala / Cats)

```scala
import cats.Monad
import cats.syntax.all.*

trait KVStore[F[_]]:
  def get(k: String): F[Option[String]]
  def put(k: String, v: String): F[Unit]

// Business logic: pure, generic, testable. Mentions no concrete effect.
def upsertUpper[F[_]: Monad](k: String)(using kv: KVStore[F]): F[Unit] =
  for {
    cur <- kv.get(k)
    _   <- kv.put(k, cur.getOrElse("").toUpperCase)
  } yield ()

// At the edge: instantiate F = IO in prod, F = State[Map[...], *] in tests.
```

### The Rust wall, made explicit

```rust
// What we WANT (does not compile in stable Rust):
//   trait Functor { fn map<A, B>(self: Self<A>, f: impl Fn(A)->B) -> Self<B>; }
//
// What we can do instead: a trait with an ASSOCIATED OUTPUT type, but it must
// name the target constructor concretely — no general `Self<B>`.
trait MapOption<A> {
    type Output<B>;                  // a GAT-ish slot, still not Self<B> in general
    fn fmap<B>(self, f: impl Fn(A) -> B) -> Self::Output<B>;
}
// You end up writing one impl per concrete container; nothing unifies them,
// so there is still NO generic `traverse`. This is the HKT gap.
```

### GAT: the lending iterator HKTs can't be conflated with

```rust
trait LendingIterator {
    type Item<'a> where Self: 'a;
    fn next(&mut self) -> Option<Self::Item<'_>>;
}

struct Windows<'s> { data: &'s [u8], i: usize, n: usize }
impl<'s> LendingIterator for Windows<'s> {
    type Item<'a> = &'a [u8] where Self: 'a;   // each item BORROWS from self
    fn next(&mut self) -> Option<&[u8]> {
        if self.i + self.n > self.data.len() { return None; }
        let w = &self.data[self.i..self.i + self.n];
        self.i += 1;
        Some(w)
    }
}
```

This is the GAT success story — yielding borrowed items, impossible before 1.65. Note it parameterizes the *associated type* `Item<'a>`, not the *implementing type* by a constructor. It does not give you `Functor`.

### fp-ts defunctionalized `traverse` consumer (TypeScript)

```typescript
import { array } from 'fp-ts/Array';
import * as O from 'fp-ts/Option';
import * as E from 'fp-ts/Either';

// array.traverse is generic over the target Applicative, encoded via Kind tags.
const parse = (s: string): O.Option<number> => {
  const n = Number(s);
  return Number.isNaN(n) ? O.none : O.some(n);
};

array.traverse(O.Applicative)(['1', '2', '3'], parse); // Option<number[]> = Some([1,2,3])
array.traverse(O.Applicative)(['1', 'x'], parse);       // None
```

Functionally identical to Haskell's `traverse parse`, but the Applicative instance (`O.Applicative`) is passed explicitly and the higher-kinded plumbing lives in `Kind`/`URItoKind` behind the scenes.

---

## Coding Patterns

### Pattern 1: Program to the weakest abstraction (Functor < Applicative < Traversable < Monad)

Constrain to the least powerful typeclass that compiles. `Applicative` instead of `Monad` keeps doors open (parallelism, error accumulation, more instances). This is the single highest-leverage habit in HKT code.

### Pattern 2: Effect at the last hole; structure abstracted separately

In `traverse`, `t` is the structure and `f` the effect. Keep them distinct in your signatures; don't conflate "what shape am I walking" with "what effect am I producing".

### Pattern 3: Tagless-final for swappable interpreters

Express capabilities as `Capability[F[_]]` traits/typeclasses, write logic against `F[_]: Monad`, and choose `F` (IO, test, mock) at the boundary. Keeps the core pure and the effect a deployment decision.

### Pattern 4: In Rust, prefer GATs / concrete impls; don't fake HKTs

When you hit "I want a Functor" in Rust, step back: usually a concrete trait with an associated `Output<B>` GAT, or a hand-written per-type impl, is clearer than a heroic HKT emulation. Reserve emulation for libraries with a strong reason.

### Pattern 5: Quarantine encoding machinery (TS/Kotlin)

If you must encode HKTs, isolate `Kind`/tag/registry plumbing in one module and expose clean `F`-generic APIs. Don't let `URItoKind` leak into application code or error messages users see daily.

---

## Best Practices

- **Default to native HKTs only in languages that have them.** In Rust/Go/native-TS, treat HKT emulation as a last resort with explicit justification.
- **Make the effect a parameter, not a hardcode, in core logic — but interpret it at one well-defined edge.** That's the whole architectural value; don't sprinkle concrete `IO` through the core.
- **Choose Applicative over Monad whenever steps are independent** to preserve parallelism and full-error accumulation.
- **Budget the abstraction tax explicitly.** Write down what reuse you gain vs the comprehension/onboarding/compile cost. Revisit when team or scope changes.
- **Lean on law-tested library instances** (Cats `Discipline`, Haskell QuickCheck laws) rather than bespoke ones; one unlawful instance corrupts every generic caller.
- **Disambiguate "higher" precisely in design docs and reviews.** Confusing higher-kinded with higher-rank/higher-order derails discussions; name the exact axis.
- **For Rust, frame GATs accurately:** they solve lending-iterator/type-family problems, *not* general container-genericity. Don't promise a `Functor` you can't deliver.

---

## Edge Cases & Pitfalls

- **Monad transformer stacks have hidden cost.** `StateT (ExceptT IO)` allocates and indirects per bind; deep stacks can dominate runtime. Cats-Effect/ZIO/`effectful` exist partly to flatten this. Profile effect-heavy code.
- **`pure`'s return-type polymorphism trips inference.** `pure(3)` with no expected `F` is ambiguous; annotate (`3.pure[Option]`, `pure @Maybe 3`). Rust's lack of this is one of its HKT blockers.
- **Coherence assumptions differ across languages.** Haskell/Rust enforce global coherence (one instance per type); Scala's implicits do *not*, so two conflicting `Monad[F]` can be in scope. Generic HKT code can behave differently depending on which instance resolves.
- **`Set`/constrained containers still aren't lawful Functors.** Anything needing `Ord`/`Eq` on elements can't satisfy the unconstrained `* -> *` signature; you need *constrained* Functor classes (e.g. `CFunctor`) — a sign you're at the edge of the abstraction.
- **Conflating GATs with HKTs in design.** They live on different axes (output-parameterization vs constructor-genericity). Claiming GATs "give Rust HKTs" leads to designs that hit a wall.
- **Higher-rank vs higher-kinded mix-ups in type errors.** `runST :: (forall s. ST s a) -> a` is higher-rank; its `forall`-under-arrow errors look alien if you assume it's an HKT issue. Identify the axis before debugging.
- **Encoded HKTs leak in error messages.** `Kind<'Option', A>` noise and `URIS` constraints make TS/Kotlin HKT errors hard for non-experts — a real onboarding hazard that argues against using them in shared code.
- **Over-generalization upfront.** Writing `program[F[_]: Monad]` before a second concrete `F` exists is speculative generality; you pay the tax with no current benefit. Generalize on the second use.

---

## Apply it

1. State the system invariant that **Higher-Kinded Types** must protect.
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

- Which invariant must remain true when Higher-Kinded Types fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
