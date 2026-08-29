# Type Inference — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Type Inference** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Why Subtyping Breaks HM

HM's engine is *unification* — making two types **equal** by substitution. Subtyping replaces equality with a *relation*: `Int <: Number`, `Dog <: Animal`. Now when a function expects `Animal` and you pass a `Dog`, you don't want `Dog = Animal` (false) — you want `Dog <: Animal` (true). Inference must solve *subtyping constraints*, which form a lattice, not a simple substitution. The general problem (inferring with subtyping plus polymorphism) is intractable or undecidable in the forms programmers want. This is the deep reason **object-oriented languages have weaker inference than ML**: subtyping is baked into their core, and it poisons the clean unification HM relies on. Languages cope by inferring *locally* and propagating *expected* types, not by globally solving subtype constraints.

### 2. Why Overloading and Typeclasses Need Annotations

`(+)` in Haskell is `Num a => a -> a -> a`. The `Num a =>` is a **constraint**: "for some type `a` that is a number." Inference now does two jobs — solve the types *and* **resolve which instance** satisfies each constraint. Two failure modes appear:

- **Ambiguity.** `show (read s)` — `read :: Read a => String -> a`, `show :: Show a => a -> String`. The intermediate `a` is constrained (`Read`, `Show`) but **never appears in the result**. Inference can't choose the instance. GHC reports *"ambiguous type variable `a`"* and you must annotate: `show (read s :: Int)`.
- **Defaulting.** To stay usable, Haskell *defaults* some ambiguous numeric constraints (`Num` → `Integer`, `Fractional` → `Double`). Convenient, occasionally surprising.

The cost of overloading is that inference stops being purely structural; `::` annotations become a *required* tool, not a nicety.

### 3. The Monomorphism Restriction — The Classic Trap

Haskell has a rule that bites nearly every beginner. A binding like

```haskell
let f = read     -- NO arguments on the left, has a constraint (Read a)
```

is **not** generalized by default — instead of `f :: Read a => String -> a`, the monomorphism restriction forces `f` to a *single* monomorphic type, which inference then can't determine, yielding either an error or a defaulted type frozen at first use. The rationale: generalizing a *value* (not a syntactic function) could silently turn one shared computation into many re-evaluations, and could leave ambiguous constraints. The fix is exactly what the rule pushes you toward: **write a type signature**, or enable `NoMonomorphismRestriction`. It's a textbook case of inference *intentionally* refusing to infer to protect you, and the lesson is the annotation.

### 4. Higher-Rank and Polymorphic Recursion: Inference Gives Up

Two features where inference is provably out of reach:

- **Higher-rank.** `applyTwice :: (forall a. a -> a) -> (Int, Bool)`. The `forall` is in *argument* position (rank-2). Inferring where to place `forall`s is undecidable; GHC requires the signature (with `RankNTypes`).
- **Polymorphic recursion.** A function that calls *itself* at a different type (common with nested datatypes like `data Nested a = Nil | Cons a (Nested [a])`). Type inference for polymorphic recursion is undecidable (Henglein, 1993). You must annotate the recursive function's type; then *checking* it is easy.

The pattern repeats: **inference of these is undecidable, but *checking* them against a written type is decidable.** That asymmetry is the entire justification for bidirectional typing.

### 5. Bidirectional Type Checking — The Modern Engine

Bidirectional typing splits the judgment into two arrows:

- **Synthesis** (`e ⇒ T`): "I can read a type *out* of `e`." Literals, variables, function applications synthesize.
- **Checking** (`e ⇐ T`): "Given expected type `T`, does `e` fit?" Lambdas, `if`-branches, and anything ambiguous are *checked*.

The rule of thumb: **introduction forms are checked, elimination forms synthesize.** A lambda `\x -> body` can't synthesize (what's `x`'s type?) — but if we're *checking* it against `A -> B`, we know `x : A` and check `body ⇐ B`. An *annotation* `(e : T)` is the bridge: it lets you *switch* from checking to synthesis. Information flows down from annotations (checking) and up from leaves (synthesis), and they meet. This:

- **Composes with subtyping** — checking mode just verifies `synthesized <: expected`.
- **Handles higher-rank** — push the `forall` down via the annotation in checking mode.
- **Localizes errors** — a mismatch is reported exactly where synthesized and expected types fail to meet, near your code, not three files away. This is *the* practical win over HM's global solve.

Rust, Scala, Swift, Kotlin, TypeScript, and Haskell's higher-rank extensions are all bidirectional under the hood.

### 6. How TypeScript Actually Infers

TypeScript is the most widely used inferencing type system on Earth, and it is unapologetically *local* and bidirectional:

- **Contextual typing (checking mode).** `arr.map(x => x.length)` — the expected type of the callback comes from `map`'s signature and `arr`'s element type, so `x` is inferred without annotation. Remove the context (`const f = x => x.length;`) and `x` becomes an error (`noImplicitAny`) — there's nothing to check against.
- **Best common type.** `[1, 2, null]` infers `(number | null)[]` by finding a type compatible with all elements (or a union).
- **Generic inference from arguments.** `function id<T>(x: T): T` called as `id(42)` infers `T = number` from the argument. Inference of `T` flows from call arguments and the expected return type.
- **`as const`.** `{ kind: "a" } ` infers `{ kind: string }`; `{ kind: "a" } as const` infers the *literal* `{ readonly kind: "a" }`. A deliberate knob to make inference *narrower*.
- **Limits.** TS can't always infer generics from return position, struggles with higher-order generic flow, and will happily infer a type *wider* than you wanted (widening literals, inferring `string` where you meant a literal union). The fix is the same as everywhere: annotate to anchor.

### 7. Inference Failures and Their Cryptic Errors

The senior skill is reading inference failures:

- **HM/unification:** "couldn't match `Int` with `Bool`" reported at a *use* site, far from the wrong definition. The bug is upstream; the error is downstream.
- **Ambiguity:** "ambiguous type variable `a` arising from a use of `show`" — a constrained variable that never reaches the result. Cure: a type annotation that pins `a`.
- **TypeScript widening:** the dreaded "Type `string` is not assignable to type `"red" | "blue"`" — inference widened your literal. Cure: `as const` or an explicit annotation.
- **Too-wide / too-narrow:** TS infers `string` when you wanted a literal union (too wide), or narrows a `let` to a literal you meant to stay general (rare). Annotate to set the intended width.

The unifying lesson: **annotations are not just documentation; they are error-localization anchors and inference seeds.** A signature on the *right* boundary turns a cascade of confusing errors into one precise one.

---

## Code Examples

### Ambiguous type variable (Haskell)

```haskell
-- read  :: Read a => String -> a
-- show  :: Show a => a -> String

bad s = show (read s)
-- error: Ambiguous type variable 'a0' arising from a use of 'show'
--   the intermediate 'a0' is Read AND Show, but appears in NO result.

good s = show (read s :: Int)   -- annotation pins a0 = Int. Resolved.
```

### The monomorphism restriction biting a beginner (Haskell)

```haskell
-- Beginner writes:
average = \xs -> sum xs / fromIntegral (length xs)
-- Surprise: the MR + defaulting can freeze the numeric type, or:
let g = read in (g "1" :: Int, g "2.0" :: Double)
-- error: g is monomorphic; can't be both Int-reader and Double-reader.

-- Fix 1: a signature.
average :: [Double] -> Double
average xs = sum xs / fromIntegral (length xs)
-- Fix 2 (file-level): {-# LANGUAGE NoMonomorphismRestriction #-}
```

### Higher-rank: inference can't, checking can (Haskell)

```haskell
{-# LANGUAGE RankNTypes #-}

-- Cannot be inferred — the forall in argument position is rank-2.
runBoth :: (forall a. [a] -> Int) -> ([Int], [Bool]) -> (Int, Int)
runBoth f (xs, ys) = (f xs, f ys)
-- With the signature, CHECKING f xs and f ys is trivial.
```

### Bidirectional flow in Scala / Rust (synthesis up, checking down)

```scala
// Scala: the expected return type (checking) flows INTO the lambda;
// the literals (synthesis) flow OUT.
val f: Int => Int = x => x + 1   // x : Int inferred from the annotated type
List(1,2,3).map(x => x * 2)      // x : Int from List[Int].map's signature
```

```rust
// Rust: return type annotation (checking) lets the body's `?`/collect infer.
fn parse_all(ss: &[&str]) -> Result<Vec<i32>, std::num::ParseIntError> {
    ss.iter().map(|s| s.parse()).collect()
    // collect's target type is inferred FROM the function's return type.
    // Remove the return annotation and `collect` can't pick a container.
}
```

### TypeScript: contextual typing, best common type, `as const`, generic inference

```typescript
// Contextual typing (checking): x inferred from Array<number>.map signature
[1, 2, 3].map(x => x.toFixed(2));   // x: number, no annotation needed

// No context → noImplicitAny error:
// const f = x => x * 2;            // x implicitly 'any' (error under strict)

// Best common type:
const xs = [1, 2, null];            // inferred: (number | null)[]

// Generic inference from arguments:
function first<T>(arr: T[]): T | undefined { return arr[0]; }
const n = first([1, 2, 3]);         // T = number  →  n: number | undefined

// Widening vs. as const:
const a = { kind: "circle" };       // { kind: string }   (widened)
const b = { kind: "circle" } as const; // { readonly kind: "circle" } (literal)
```

### TypeScript inferring a too-wide type, and the fix

```typescript
type Shape = "circle" | "square";

// Inference WIDENS the array's element type to string:
const shapes = ["circle", "square"];     // string[]  — too wide!
function draw(s: Shape) {/*...*/}
// shapes.forEach(draw);                 // error: string not assignable to Shape

// Fix: anchor the intended type.
const shapes2: Shape[] = ["circle", "square"];   // Shape[]
const shapes3 = ["circle", "square"] as const;   // readonly ["circle","square"]
```

---

## Coding Patterns

### Pattern 1: Annotate the signature, infer the body

```rust
pub fn group_by_first<K: Eq + Hash, V>(pairs: Vec<(K, V)>) -> HashMap<K, Vec<V>> {
    let mut out = HashMap::new();          // body fully inferred from the return type
    for (k, v) in pairs { out.entry(k).or_default().push(v); }
    out
}
```

### Pattern 2: Pin ambiguity with a targeted annotation

```haskell
-- Don't annotate everything — annotate the ONE ambiguous spot.
result = sum (map read (words input) :: [Int])
```

### Pattern 3: Use `as const` to stop TypeScript widening

```typescript
const ROUTES = ["home", "about", "contact"] as const;
type Route = typeof ROUTES[number];   // "home" | "about" | "contact"
```

### Pattern 4: Provide a return-type annotation to drive `collect`/`into` inference

```rust
let nums: Vec<i32> = lines.iter().map(|l| l.len() as i32).collect();
// The annotation on `nums` is the checking context collect() needs.
```

### Pattern 5: Break a cryptic error by annotating the boundary, not the leaf

When inference errors cascade, add a signature to the *function* that should own the type. Bidirectional checking then traps the mismatch at that boundary instead of letting it ripple to callers.

---

## Best Practices

- **Annotate public boundaries; infer private bodies.** This is the single highest-leverage inference discipline in any partially-inferring language. Boundaries are documentation *and* error anchors.
- **When you see "ambiguous type variable," look for a constrained var that never reaches the result.** The cure is always a pinning annotation.
- **In Haskell, write top-level signatures** — it sidesteps the monomorphism restriction *and* localizes errors. Treat the MR as the compiler telling you to annotate.
- **In TypeScript, reach for `as const` for literal data** (route tables, action types, tuples) and for explicit types at config boundaries. Don't trust widening to preserve literals.
- **Remember: inference of higher-rank and polymorphic recursion is undecidable.** Don't fight the compiler — annotate and move on. *Checking* will be instant.
- **Use the IDE's "expand/quick info" to see what was actually inferred** before trusting it. TypeScript and rust-analyzer both show the real inferred type; confirm it matches intent.
- **Place one seed annotation, not ten.** Find the boundary that the solver pivots on; annotating there fixes the cascade with minimal noise.

---

## Edge Cases & Pitfalls

- **The error is downstream of the bug (HM/unification).** A wrong type in a definition surfaces at a far-away use. Bisect by annotating intermediate boundaries to pull the error toward the cause.
- **Ambiguous type variables from typeclasses.** `read`/`show` chains, `mempty`, numeric literals in polymorphic contexts. The variable is constrained but invisible in the result; annotate to resolve.
- **The monomorphism restriction freezes a binding.** A point-free or argument-free definition with a constraint silently becomes monomorphic. Symptom: "could not deduce... " or a type frozen at first use. Cure: a signature.
- **TypeScript widening literals.** `const x = "a"` in an object widens to `string`; arrays widen element types; this breaks assignment to literal-union types. Use `as const` or annotate.
- **TypeScript losing context → `any`.** Pull a callback out into a standalone `const` and its parameters lose their contextual types, silently becoming `any` (or erroring under `noImplicitAny`). Keep callbacks inline or annotate.
- **Subtyping + inference yields surprising least-upper-bounds.** `cond ? dog : cat` may infer `Animal` (or a union, or `{}` in TS), not what you expected. Annotate the result if a specific type matters.
- **Generic inference from return position is weak.** Many languages can't infer a type parameter that appears only in the return type; you must supply it explicitly (`collect::<Vec<_>>()`, `id<number>(...)`).
- **Defaulting hides intent.** Haskell defaulting (`Num` → `Integer`) and TS's structural widening both "helpfully" pick a type. Convenient until the picked type is wrong; annotate when the default isn't what you mean.

---

## Apply it

1. State the system invariant that **Type Inference** must protect.
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

- Which invariant must remain true when Type Inference fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
