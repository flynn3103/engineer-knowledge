# Nominal vs Structural Typing — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Nominal vs Structural Typing** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Subtyping as Inference Rules

Reflexivity and transitivity hold in both systems:

```
———————  (S-Refl)        S <: U   U <: T
T <: T                   ————————————————  (S-Trans)
                             S <: T
```

**Nominal subtyping** adds exactly one source of new edges — declaration:

```
class S extends T   (or S implements T, impl T for S)
———————————————————————————————————————————————  (S-Nom)
                  S <: T
```

There is *no other rule*. If `S <: T` cannot be derived from S-Refl, S-Trans, and the declared S-Nom edges, it does not hold. That's why structurally identical, undeclared types are incompatible.

**Structural subtyping** for records adds width and depth as rules:

```
{ l_i : T_i  (i ∈ 1..n+k) }  <:  { l_i : T_i  (i ∈ 1..n) }     (S-Width)

for each i:  S_i <: T_i
———————————————————————————————————————————  (S-Depth)
{ l_i : S_i }  <:  { l_i : T_i }
```

Width says "more fields is a subtype"; depth says "pointwise-subtype fields is a subtype." A structural system has these rules *instead of* (or in addition to) declaration edges.

### 2. Variance: Where Soundness Lives

Variance governs how subtyping moves through type constructors. Get it wrong and the type system lies.

**Functions are contravariant in parameters, covariant in returns:**

```
T1 <: S1     S2 <: T2
—————————————————————————  (S-Fn)
(S1 -> S2)  <:  (T1 -> T2)
```

Read it carefully: a function is a subtype if it accepts *more* (its parameter type is a *supertype*) and returns *less* (its return type is a *subtype*). A `(Animal) -> Dog` is a subtype of `(Dog) -> Animal`: it handles any `Dog` you pass (since it handles all `Animal`s) and its `Dog` result is a valid `Animal`. This contravariant-parameter rule is *the* place structural function compatibility is subtle.

**Mutable containers must be invariant.** If `Array<Dog> <: Array<Animal>` were allowed, you could write a `Cat` into an `Array<Animal>` alias of an `Array<Dog>` — a heap corruption. Sound languages make mutable generics invariant (Java arrays are a famous unsound exception: covariant arrays throw `ArrayStoreException` at *runtime* to patch the hole). TypeScript deliberately makes arrays covariant and method parameters bivariant for ergonomics, accepting unsoundness.

### 3. Row Polymorphism: Precise Open Records

Plain width subtyping loses information: once you up-cast `{x, y}` to `{x}`, you've forgotten `y`. **Row polymorphism** keeps it with a *row variable* `ρ` standing for "the rest of the fields":

```
{ x : int | ρ }
```

A function `fun r -> r.x` can be typed `{ x : int | ρ } -> int` for *any* `ρ`, so it accepts any record containing an `int x` *and preserves* the other fields in the result type. OCaml objects, PureScript records, and Elm extensible records use this. It's the principled foundation under structural typing: structural subtyping is roughly row polymorphism with the row existentially hidden. Senior insight: row polymorphism is often *more* expressive than subtyping because it never throws away the extra fields.

### 4. Structural Checks Are Coinductive

Consider mutually recursive structural types:

```
type A = { next: B }
type B = { next: A }
```

Checking `A <: A'` for similarly-shaped `A'`/`B'` requires checking `B <: B'`, which requires `A <: A'` again — an infinite regress under naive induction. The correct treatment is **coinductive**: assume `A <: A'` while proving it, and only fail on an actual mismatch. Implementations realize this with a *memo set* of "currently assumed" pairs; revisiting a pair means "assume true." Without this, the checker loops forever on recursive types. Nominal checks don't face this because the answer is a finite ancestry walk on declared edges.

### 5. How Compilers Implement Each Check

**Nominal.** Each type carries a stable identity (a symbol/handle) and a precomputed set or chain of ancestors. `S <: T` is: pointer-equal identities, or `T` ∈ ancestors(`S`). This is O(1) with a precomputed superclass bitset (or a few pointer hops). "Are these the same type?" is a pointer comparison. Subtype tests can be made O(1) with techniques like Cohen's display or interval/relative numbering of the inheritance tree.

**Structural.** `S <: T` recursively compares members, recursing into field/param/return types, with the coinductive memo set above. Cost is proportional to the size of the types compared, and pathological generic instantiations can blow up — which is why TypeScript caches relation results aggressively and has instantiation-depth limits to keep the checker from hanging. There is no O(1) "same type" — identity itself is structural.

**Consequence:** nominal systems get cheap identity and cheap subtype tests; structural systems pay with recursive comparison and need memoization/caching to stay tractable and even to terminate.

### 6. Nominal Opacity vs Structural Transparency

A nominal type can be **opaque**: `newtype UserId = UserId Int` hides that it's an `Int`; clients can't rely on the representation, so you can change it later. A structural type is **transparent**: its shape *is* its interface, so the representation is part of the public contract and harder to evolve. This is a deep API-design lever — nominal opacity buys you representation independence; structural transparency buys you instant interoperability. Branded types in TS are an attempt to buy opacity back inside a transparent system.

---

## Code Examples

### Variance you can feel (Scala, declared variance)

```scala
class Box+A          // +A: covariant (read-only ⇒ safe)
val dogBox: Box[Dog]    = new Box(new Dog)
val animalBox: Box[Animal] = dogBox  // ✅ covariance: Box[Dog] <: Box[Animal]

// A mutable cell must be invariant:
class CellA          // invariant
val dc: Cell[Dog] = new Cell(new Dog)
// val ac: Cell[Animal] = dc         // ❌ rejected — would allow writing a Cat
```

### Function contravariance in a structural system (TypeScript)

```typescript
type Handler<T> = (x: T) => void;

let handleAnimal: Handler<Animal> = (a) => {};
let handleDog: Handler<Dog>;

handleDog = handleAnimal;   // ✅ (Animal)->void <: (Dog)->void  (contravariant param)
// handleAnimal = handleDog; // strictFunctionTypes: ❌ a Dog handler can't take any Animal
```

With `strictFunctionTypes`, TS uses proper contravariance for standalone function types — but *method* syntax remains bivariant for legacy reasons (next section).

### The bivariance soundness hole (TypeScript)

```typescript
interface EventSource<T> {
    handle(cb: (e: T) => void): void;   // METHOD syntax → bivariant params
}
declare let animalSrc: EventSource<Animal>;
let dogSrc: EventSource<Dog> = animalSrc;   // ✅ allowed (bivariant) but UNSOUND:
// dogSrc.handle expects (Dog)=>void, but animalSrc may invoke cb with any Animal
```

This is accepted for ergonomic reasons and is genuinely unsound; standalone function-typed properties (not method shorthand) get the sound contravariant check under `strictFunctionTypes`.

### Row polymorphism (OCaml objects)

```ocaml
(* Accepts ANY object with an x:int method, returns it unchanged.
   The '..' is the row variable: "x:int and possibly more". *)
let get_x (o : < x : int; .. >) = o#x

let p = object method x = 3 method y = 4 end
let _ = get_x p   (* ✅ p has x (and y); the row absorbs y *)
```

### Coinductive structural check (illustration)

```typescript
// Mutually recursive structural types — the checker assumes the goal
// while proving it, using a memo set, to avoid infinite recursion.
type Node = { value: number; next: Node | null };
type Link = { value: number; next: Link | null };

declare const n: Node;
const l: Link = n;   // ✅ structurally identical; proven coinductively
```

### Nominal opacity enabling representation change (Haskell)

```haskell
newtype UserId = UserId Int          -- representation hidden behind the constructor
-- Later you can change it to:
-- newtype UserId = UserId Text
-- ...without breaking clients that only use the exported smart constructor/getters.
```

---

## Coding Patterns

**Pattern: declare variance explicitly where the language allows it** (`out T`/`in T` in C#, `+A`/`-A` in Scala) so the compiler enforces safe substitution.

**Pattern: prefer row polymorphism / generics-with-rest over width up-casts** when downstream code must retain unknown fields.

**Pattern: opaque module boundary (nominal).** Export a type and constructors but not its representation, so clients are structurally blind to internals and you keep evolution freedom.

```typescript
// opaque-id.ts
declare const tag: unique symbol;
export type Id = string & { [tag]: "Id" };   // representation hidden from importers
export const Id = (s: string): Id => s as Id;
```

**Pattern: structural assertion at boundaries, nominal core.** Validate/parse untyped input structurally at the edge, then brand into nominal domain types for the interior.

---

## Best Practices

1. **Annotate variance deliberately.** Default to invariance for anything mutable; make pure producers covariant and pure consumers contravariant.
2. **Don't trust a soundness guarantee the language doesn't make.** Know that TS arrays are covariant and method params bivariant; Java arrays are covariant with runtime checks.
3. **Use opacity for evolvability.** If a type's representation might change, hide it behind a nominal/opaque boundary now.
4. **Prefer row polymorphism for pass-through.** It preserves precision that width subtyping discards.
5. **Structure types to keep structural checking cheap.** Avoid gratuitously deep/recursive generic instantiations that stress the relation cache; name and reuse types so the checker memoizes them.
6. **Make conformance explicit even in structural Go** (`var _ Iface = (*T)(nil)`) so API evolution breaks loudly.
7. **Treat representation changes of a structural public type as breaking.** Its shape is its contract.

---

## Edge Cases & Pitfalls

**1. Covariant-array unsoundness.** `Animal[] a = dogArray; a[0] = new Cat();` compiles in Java/TS. Java throws `ArrayStoreException` at runtime; TS silently corrupts. The variance hole is patched (Java) or unpatched (TS).

**2. Method-bivariance hole in TS.** Method-shorthand parameters are compared bivariantly even under `strict`, so a `EventSource<Dog>` can alias a `EventSource<Animal>` unsoundly. Use function-property syntax to get the sound contravariant check.

**3. Infinite structural recursion without memoization.** A naive structural checker on mutually recursive types loops forever. Real compilers memoize "assumed" pairs; if you write your own type comparison, you must too.

**4. Width subtyping discards information.** Up-casting `{a, b}` to `{a}` forgets `b`; a later down-cast can't recover it soundly. Where pass-through matters, you needed a row variable, not a subtype.

**5. Structural equality of generics is by instantiation, not declaration.** `Box<string>` and an identical structural `Container<string>` may be interchangeable structurally even though they're "different" generics — surprising if you expected nominal separation.

**6. Coherence vs. structural multiplicity.** Nominal trait systems can enforce a single canonical conformance (coherence); structural systems can't easily say "there's one true way `T` is a `Monoid`," which matters for typeclass-style abstractions (expanded in `professional.md`).

**7. Opacity leaks through inference.** A branded/opaque type can leak its base representation through type inference or `typeof` in subtle ways; verify the boundary actually hides what you think it does.

---

## Apply it

1. State the system invariant that **Nominal vs Structural Typing** must protect.
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

- Which invariant must remain true when Nominal vs Structural Typing fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
