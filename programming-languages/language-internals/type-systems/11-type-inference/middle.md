# Type Inference — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Type Inference** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Step 1 — Fresh Type Variables for Every Unknown

When HM sees something whose type it doesn't yet know — a function parameter, an empty list, the result of a call — it **mints a fresh type variable**:

```haskell
\x -> ...    -- x has type t0 (fresh). We'll find out what t0 is from usage.
```

These are not "any type" in a vague sense; they are *specific unknowns* that the next steps will pin down. Think `t0`, `t1`, `t2`, generated like an auto-incrementing counter.

### 2. Step 2 — Generate Constraints From Usage

Every place a value is *used* tells the inferencer something. Usage produces **constraints** (equations):

```haskell
\x -> x + 1
```

- `x` has fresh type `t0`.
- `1` has type `Int`.
- `(+)` has type `Int -> Int -> Int` (in a monomorphic-`Int` world for simplicity).
- We *apply* `(+)` to `x`, so `x` must be `Int`. Constraint: **`t0 = Int`**.
- The result of `x + 1` is `Int`, so the whole lambda has type `t0 -> Int`.

The inferencer is not guessing — it's reading what each operator and call *demands* of its arguments, and writing those demands down as equations.

### 3. Step 3 — Unification Solves the Equations

**Unification** takes the pile of equations and finds a substitution making both sides of each equal. The rules are simple and mechanical:

- A variable unifies with anything: `t0 = Int` → substitution `{t0 ↦ Int}`.
- Two constructors unify if they match and their parts unify: `t0 -> t1 = Bool -> t2` → unify `t0 = Bool` *and* `t1 = t2`.
- Two *different* constructors clash: `Int = Bool` → **type error** (the famous "couldn't match `Int` with `Bool`").

Applying `{t0 ↦ Int}` to the lambda's type `t0 -> Int` gives `Int -> Int`. Done. Unification is the engine; everything else feeds it equations.

### 4. The Occurs-Check — No Infinite Types

What if usage demands `a = a -> b`? That would mean `a` is a function whose argument type is itself, forever: `((... -> b) -> b) -> b`. An **infinite type**. HM forbids this with the **occurs-check**: before binding a variable `a` to a type `T`, check that `a` does **not occur inside** `T`. If it does, reject.

```haskell
\x -> x x     -- apply x to itself
-- x : t0, and applying it: t0 = t0 -> t1
-- occurs-check FAILS: t0 occurs in (t0 -> t1).  REJECTED.
```

This is why `\x -> x x` (self-application) does not typecheck in ML/Haskell. The occurs-check is the guard that keeps unification terminating and types finite.

### 5. Step 4 — Generalization and Let-Polymorphism

Here is HM's signature move. Consider:

```haskell
let id = \x -> x in (id True, id 0)
```

After inferring `id : t0 -> t0`, HM **generalizes**: the free variable `t0` becomes universally quantified — `id : forall a. a -> a`. Now each *use* of `id` **instantiates** that `forall` with a fresh variable: `id True` uses `id : Bool -> Bool`, `id 0` uses `id : Int -> Int`. One definition, many types. That's **let-polymorphism**.

The critical contrast — generalization happens at `let`, **not** at lambda parameters:

```haskell
-- This FAILS:
\id -> (id True, id 0)
-- id is a lambda PARAMETER → monomorphic → one fixed type t0.
-- id True forces t0 = Bool -> _; id 0 forces t0 = Int -> _.
-- Bool clashes with Int.  TYPE ERROR.
```

A `let`-bound name is generalized and reusable at many types; a lambda parameter is **monomorphic** and locked to one type. This distinction *is* Hindley-Milner. (Why the restriction? Generalizing lambda parameters would require guessing a polymorphic type before seeing the body — undecidable in general. `let` lets HM infer the type *first*, then generalize.)

### 6. Principal Types — Always the Most General

A landmark property: every well-typed HM expression has a **principal type** — a single most-general type from which all its other valid types follow by instantiation. HM's algorithm always *finds* it, with no annotations.

```haskell
\x -> x          -- principal type: forall a. a -> a
const = \x y -> x  -- principal type: forall a b. a -> b -> a
map              -- principal type: forall a b. (a -> b) -> [a] -> [b]
```

You never get a needlessly specific type by accident. If your code permits `forall a. a -> a`, that's exactly what HM gives you. This is why ML/Haskell code is so reusable "for free."

### 7. Why HM Is Decidable, Fast, and Rank-1

HM hits a sweet spot: inference is **decidable** (always terminates with yes/no) and, in practice, near-linear. The price is **rank-1 polymorphism**: every `forall` lives at the *outermost* level of a type. You can have `forall a. a -> a`, but **not** `(forall a. a -> a) -> Int` — a function that takes a polymorphic function as an argument (rank-2). HM cannot infer rank-2 and higher; once you need them, you must annotate. Full type inference for rank-2+ polymorphism is undecidable, which is exactly why Haskell requires a signature for higher-rank functions. The next level (`senior.md`) covers what else breaks HM: subtyping, overloading/typeclasses, and polymorphic recursion.

---

## Code Examples

### Tracing `\x -> x + 1` by hand

```text
Expression:  \x -> x + 1

1. FRESH:    x : t0
2. CONSTRAINTS from usage of (+):
             (+) : Int -> Int -> Int     (Int-specialized for clarity)
             x used as left arg of (+)   ⇒  t0 = Int
             1 : Int                     ⇒  consistent
             result of (+) : Int
3. UNIFY:    {t0 ↦ Int}
4. RESULT:   \x -> x + 1  :  Int -> Int
```

### Tracing `compose` (`\f g x -> f (g x)`)

```text
Expression:  \f g x -> f (g x)

1. FRESH:    f : t0,  g : t1,  x : t2
2. CONSTRAINTS:
   (g x):   g applied to x  ⇒  t1 = t2 -> t3      (g : t2 -> t3)
   (f _):   f applied to (g x)'s result (t3)
                              ⇒  t0 = t3 -> t4     (f : t3 -> t4)
   whole:   \f g x -> ...   :  t0 -> t1 -> t2 -> t4
3. SUBSTITUTE:  t1 ↦ (t2 -> t3),  t0 ↦ (t3 -> t4)
4. RESULT (rename t2→a, t3→b, t4→c):
   compose : (b -> c) -> (a -> b) -> a -> c
```

No annotations, and HM derived the fully general type. This is the heart of why ML-family code is so concise.

### Let-polymorphism in action (OCaml)

```ocaml
let id = fun x -> x in   (* id : 'a -> 'a  (generalized) *)
let a = id true in        (* instantiate 'a = bool *)
let b = id 0 in           (* instantiate 'a = int  *)
(a, b)                    (* : bool * int  — totally fine *)
```

```ocaml
(* The lambda version FAILS — id is a parameter, monomorphic: *)
let bad = fun id -> (id true, id 0)
(* Error: this expression has type bool but an expression
   was expected of type int — id's single type 'a was fixed
   to (bool -> _) by the first use, clashing with int. *)
```

### The occurs-check, demonstrated (Haskell, in GHCi)

```haskell
> let f = \x -> x x
<interactive>: Occurs check: cannot construct the infinite type:
               t ~ t -> t1
```

GHC literally names the rule. `x x` demands `x`'s type contain itself; the occurs-check rejects it.

### Where HM stops: higher-rank needs an annotation (Haskell)

```haskell
{-# LANGUAGE RankNTypes #-}

-- HM cannot INFER this; you must WRITE the rank-2 type.
applyToBoth :: (forall a. a -> a) -> (Int, Bool)
applyToBoth f = (f 1, f True)

-- Without the signature, GHC would force f to ONE monomorphic
-- type and reject (f 1, f True), exactly like the lambda-id case.
```

The `(forall a. a -> a)` *inside* a parameter position is rank-2. HM is rank-1, so inference can't reach it — the annotation is mandatory.

### Inference flowing backward through usage (Rust, a local-HM-flavored case)

```rust
let mut v = Vec::new();   // v : Vec<?>  — fresh element type
v.push(3u8);              // constraint: element = u8
// v is inferred as Vec<u8> from the LATER push, not the declaration.
```

Rust isn't full HM, but its local inference uses the same "collect constraints from all uses, then unify" idea within a function body.

---

## Coding Patterns

### Pattern 1: Write top-level signatures even though inference doesn't need them

```haskell
-- Idiomatic Haskell: annotate every top-level binding.
average :: [Double] -> Double
average xs = sum xs / fromIntegral (length xs)
```

The body is fully inferable; the signature is there for *humans* and for *pinning errors* to this function instead of its callers.

### Pattern 2: Use `let` (not lambda) when you need polymorphic reuse

```ocaml
let twice f x = f (f x)   (* polymorphic; reusable at many types *)
```

If you find yourself wanting one helper used at several types, bind it with `let` so generalization applies.

### Pattern 3: Annotate to *narrow* an over-general inferred type

```haskell
-- read :: Read a => String -> a   — too general; which `a`?
n :: Int
n = read "42"        -- annotation chooses the instance and resolves it
```

### Pattern 4: Add a signature to *move* a confusing error

When an error points deep inside a helper, add a type signature to the *boundary* function. Inference then checks against your signature locally, and the error surfaces at the real mismatch instead of cascading.

---

## Best Practices

- **In HM languages, annotate top-level definitions by convention.** It's not required for the compiler; it's required for the next human and for sane error messages.
- **Reach for `let`/`where` bindings when you need polymorphism;** remember lambda parameters are monomorphic.
- **When an error is cryptic, bisect with annotations.** Add a signature to a sub-expression or helper to force the checker to localize the clash. The error usually jumps to the real culprit.
- **Don't fight the principal type.** If HM infers something more general than you expected, your code genuinely *is* that general — usually a good thing.
- **Know your rank-1 boundary.** The moment you pass a polymorphic function as an argument, expect to write a `forall` annotation; inference can't reach there.
- **Treat a unification "cannot match X with Y" as: two usages disagree.** Find the two places that each demand a type of the same value, and reconcile them.

---

## Edge Cases & Pitfalls

- **The error is reported far from the bug.** Unification finds a contradiction at *some* point in the equation set; that point is often not where you made the mistake. A wrong type in one function can surface as an error in a caller three files away. This is HM's defining frustration.
- **Self-application is rejected (occurs-check).** `\x -> x x` and similar fail with "infinite type." Not a compiler bug — a deliberate guard.
- **Lambda parameters are not polymorphic.** `\f -> (f 1, f True)` fails. People coming from dynamic languages expect `f` to adapt; HM locks it to one type. Use a `let` or a higher-rank annotation.
- **Over-general types defer errors.** A function inferred as `forall a. a -> a` when you *meant* `Int -> Int` will compile, then fail confusingly at a distant call site where the wrong type is finally forced.
- **Numeric literals are themselves polymorphic in Haskell.** `42 :: Num a => a`. This is great until ambiguity strikes (see the monomorphism restriction in `senior.md`) and you must annotate `:: Int`.
- **A small edit can cascade.** Because types flow globally, changing one definition's type can break inference in many places at once — sometimes a flood of errors from one root cause.
- **"It compiled but the type is wrong."** HM guarantees *type safety*, not that the inferred type is the one you *intended*. An overly general inferred type is the usual sign you should have annotated to constrain it.

---

## Apply it

1. Find a real component where **Type Inference** affects an interface or dependency.
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

- Which boundary is most affected by Type Inference?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
