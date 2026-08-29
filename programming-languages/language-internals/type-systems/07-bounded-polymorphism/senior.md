# Bounded Polymorphism — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Bounded Polymorphism** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Dictionary translation: the compilation story

A typeclass-constrained function is *desugared* into an ordinary function that takes the class's operations as an explicit argument — the **dictionary**. Conceptually, this Haskell:

```haskell
class Eq a where (==) :: a -> a -> Bool

elem :: Eq a => a -> [a] -> Bool
elem x [] = False
elem x (y:ys) = x == y || elem x ys
```

is compiled roughly to (pseudo-code, dictionary made explicit):

```haskell
data EqDict a = EqDict { eq :: a -> a -> Bool }   -- the dictionary type

elem' :: EqDict a -> a -> [a] -> Bool             -- constraint becomes a parameter
elem' d x []     = False
elem' d x (y:ys) = (eq d) x y || elem' d x ys     -- == becomes a field access
```

The `Eq a =>` constraint **becomes a value parameter** of type `EqDict a`; every use of `==` becomes a lookup into that dictionary. At a call site `elem 3 [1,2,3]`, the compiler finds the `Eq Int` instance, materializes its dictionary, and passes it. Rust does the same conceptually; with monomorphization it then *specializes* `elem'` per type and inlines the dictionary away, but the *meaning* is dictionary passing. (Dynamic dispatch — `dyn Trait`, `&dyn Eq` — keeps the dictionary as a runtime vtable instead of erasing it.)

This is why typeclasses are "principled overloading": the desugaring is a *mechanical, type-directed translation* into plain parametric code. Nothing magic, nothing syntactic — the constraint is real data.

### 2. Superclasses: dictionaries that contain dictionaries

`class Eq a => Ord a` says "every `Ord` type is also `Eq`." Under dictionary translation, the `Ord` dictionary *contains* (a pointer to) the `Eq` dictionary:

```text
OrdDict a = { eqDict :: EqDict a, compare :: a -> a -> Ordering, ... }
```

So an `Ord a` constraint also supplies `Eq a` for free. Rust's `trait Ord: PartialOrd + Eq` is the same: the supertrait bound means an `Ord` implementer must also implement its supertraits, and the dictionaries nest. This is how capability *hierarchies* (`Eq` → `Ord`, `PartialOrd` → `Ord`, `Num` → `Fractional`) are encoded.

### 3. Coherence: one instance per type, everywhere

The critical correctness property of typeclasses is **coherence**: for a given type `T` and class `C`, the *whole program* uses the **same** instance. Why it matters: consider `Set T`, which orders elements via `Ord T`. If module A inserted elements using one `Ord T` and module B looked them up using a *different* `Ord T`, the set's invariant ("sorted, no duplicates") would silently break — you'd get duplicate entries, failed lookups, corruption. Coherence guarantees this can't happen: there is one canonical `Ord T`, period.

Coherence is a *global* property, which is what makes it subtle. It's not enough to check one module; the compiler (and the language's rules) must guarantee that no two modules can introduce *conflicting* instances that later meet.

### 4. The orphan rule: protecting coherence

To make coherence enforceable without whole-program analysis, languages restrict *where* instances may be declared. The **orphan rule** (Rust; Haskell warns/`-XOrphanInstances`):

> An `instance C for T` may only be defined in the crate/module that defines **`C`** or the one that defines **`T`** (or, for parameterized `T`, where a local type appears in a covered position).

If neither the class nor the type is yours, the instance is an **orphan** and is rejected. Rationale: if orphans were allowed, two independent crates could *both* write `impl Display for VendorType` differently, and a program depending on both would have two conflicting instances meeting at link time — incoherence. By tying each instance to a crate that owns one of its components, the rule guarantees at most one such crate can exist for any (class, type) pair.

The practical pain: you frequently *want* to implement someone else's trait for someone else's type (e.g. `impl Serialize for ThirdPartyStruct`) and the orphan rule forbids it. The standard escape is the **newtype**: wrap the foreign type in a local one (`struct W(ThirdPartyStruct)`), which you own, and impl on the wrapper. This is the most common friction senior Rust/Haskell engineers hit.

### 5. Associated types vs extra type parameters

When a class operation involves a *second* type that's determined by the implementing type, you have two encodings.

**Extra type parameter on the class (multi-param):**

```rust
trait Collection<Item> {                  // Item is an input parameter
    fn first(&self) -> Option<Item>;
}
```

**Associated type (output type, a member of the trait):**

```rust
trait Collection {
    type Item;                            // Item is determined BY the implementer
    fn first(&self) -> Option<Self::Item>;
}
```

The difference is *functional dependency*: with an associated type, the implementing type **determines** `Item` — a `Vec<i32>` has exactly one `Item` (`i32`), so you write `Collection`, not `Collection<i32>`, everywhere. With a type parameter, a type could in principle implement `Collection<i32>` *and* `Collection<String>`, so callers must always specify which, and inference suffers. Rust uses an associated type `Item` on `Iterator` precisely because an iterator yields exactly one item type; making it a parameter would force `Iterator<u8>` annotations everywhere and break inference. Haskell encodes the same with **type families** / functional dependencies; Swift uses `associatedtype`.

Rule of thumb: **if the implementing type determines the other type, use an associated type. If a single type genuinely needs multiple implementations differing in that type, use a parameter.** `Add<Rhs>` in Rust is a parameter (you can add `Vec` to `Vec` *and* a scalar to a `Vec`), but its *output* is an associated type (`type Output;`) because, given the inputs, the result type is determined.

### 6. Constraint propagation, formally

A bounded function's constraints must be *discharged*: every use of a class operation must be justified by a constraint in scope, and that constraint propagates to callers.

```haskell
sortUnique :: Ord a => [a] -> [a]      -- Ord a in scope: nub/sort allowed
sortUnique = sort . nub                 -- nub needs Eq (from Ord's superclass), sort needs Ord
```

`sortUnique` calls `sort` (`Ord a =>`) and `nub` (`Eq a =>`). Because `Ord a` *implies* `Eq a` via the superclass, a single `Ord a` constraint discharges both. The compiler's constraint solver assembles the right dictionaries by chaining superclass edges. A caller of `sortUnique` must, in turn, supply `Ord a` — constraints flow outward exactly as at the junior level, but now the *solver* is doing real work: searching instances, following superclass and instance-implication edges, building nested dictionaries.

### 7. The expression problem, and how typeclasses crack it

Wadler's **expression problem**: you have a datatype (say, arithmetic expressions: `Lit`, `Add`) and operations (`eval`, `pretty`). You want to add **new datatype cases** (e.g. `Mul`) *and* **new operations** (e.g. `optimize`) — each independently, without modifying or recompiling existing code, and with full static type safety.

- **Object-oriented (subtype) style** makes adding new *types* (cases) easy — write a new class implementing the interface — but adding a new *operation* hard: you must edit *every* existing class to add the method. Types are open; operations are closed.
- **Functional `case`/pattern-matching style** makes adding new *operations* easy — write a new function with a `case` over the constructors — but adding a new *type* hard: every existing function's `case` must gain a branch. Operations are open; types are closed.

Typeclasses dissolve the dilemma. Model each *operation* as a typeclass:

```haskell
class Eval a where eval :: a -> Int
class Pretty a where pretty :: a -> String

data Lit = Lit Int
data Add a b = Add a b

instance Eval Lit       where eval (Lit n) = n
instance (Eval a, Eval b) => Eval (Add a b) where eval (Add x y) = eval x + eval y
```

Now:

- **Add a new type** `Mul`: define `data Mul a b` and `instance Eval (Mul a b)`, `instance Pretty (Mul a b)`. No existing code recompiles.
- **Add a new operation** `Optimize`: define `class Optimize a` and write instances for `Lit`, `Add`, `Mul`. No existing type code recompiles.

Both axes are open. That is the precise sense in which **typeclass-style bounded polymorphism is strictly more extensible than subtype interfaces** — it's open to new *types* and new *operations* simultaneously, which the expression problem proves the naive OO and naive FP styles each cannot do.

### 8. Negative reasoning and specialization (a note)

Coherence interacts with two advanced features. **Specialization** (Rust, unstable; Haskell `OVERLAPPING`) lets a more specific instance override a generic one — powerful but it strains coherence (which instance "wins" must be principled, hence the long stabilization saga). **Negative reasoning** ("`T` does *not* implement `C`") is mostly disallowed because it's non-monotonic: adding an instance later would silently change which code path is selected, breaking the open-world assumption that makes coherence composable. Seniors should know these exist and why they're handled cautiously; you rarely need them, and reaching for them is a design smell.

---

## Code Examples

### Dictionary translation, made explicit

```haskell
-- Source
class Show a where show :: a -> String
shout :: Show a => a -> String
shout x = show x ++ "!"
```
```haskell
-- Desugared (constraint -> explicit dictionary parameter)
data ShowDict a = ShowDict { showImpl :: a -> String }
shout' :: ShowDict a -> a -> String
shout' d x = showImpl d x ++ "!"
-- call site:  shout' showDictInt 42
```

### Coherence saving a `Set`

```rust
use std::collections::BTreeSet;
// BTreeSet<T> relies on T: Ord. Coherence guarantees the SAME Ord<T>
// is used for inserts and lookups — otherwise the tree invariant breaks.
let mut s = BTreeSet::new();
s.insert(3); s.insert(1); s.insert(3);
assert_eq!(s.len(), 2);   // sound precisely because Ord<i32> is canonical everywhere
```

### Orphan rule + newtype escape (Rust)

```rust
// trait Display and type Vec<T> are BOTH foreign to this crate:
//   impl std::fmt::Display for Vec<i32> { ... }   // ERROR: orphan rule

// Fix: wrap in a local newtype you own.
struct Csv(Vec<i32>);
impl std::fmt::Display for Csv {                  // legal: Csv is local
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        let parts: Vec<String> = self.0.iter().map(|n| n.to_string()).collect();
        write!(f, "{}", parts.join(","))
    }
}
// println!("{}", Csv(vec![1,2,3]));  ->  "1,2,3"
```

### Associated type vs type parameter (Rust)

```rust
// Associated type: the implementer DETERMINES Item; callers don't annotate.
trait Stream {
    type Item;
    fn next(&mut self) -> Option<Self::Item>;
}
struct Counter(u32);
impl Stream for Counter {
    type Item = u32;
    fn next(&mut self) -> Option<u32> { self.0 += 1; Some(self.0) }
}

// Generic code uses Self::Item without ever naming u32:
fn first<S: Stream>(s: &mut S) -> Option<S::Item> { s.next() }
```
```rust
// Parameter version would force annotations and permit multiple impls:
// trait Stream<Item> { fn next(&mut self) -> Option<Item>; }
// fn first<S: Stream<???>>  -- caller must pin Item; inference degrades.
```

### Expression problem solved with typeclasses (Haskell sketch)

```haskell
class Eval a    where eval    :: a -> Int
class Optimize a where optimize :: a -> a   -- a NEW operation added later

data Lit   = Lit Int
data Add a b = Add a b
data Mul a b = Mul a b                       -- a NEW type added later

instance Eval Lit where eval (Lit n) = n
instance (Eval a, Eval b) => Eval (Add a b) where eval (Add x y) = eval x + eval y
instance (Eval a, Eval b) => Eval (Mul a b) where eval (Mul x y) = eval x * eval y
-- Adding Mul required NO change to Eval/Add. Adding Optimize requires NO change to types.
```

### Superclass / supertrait nesting

```rust
trait Shape: std::fmt::Debug {           // supertrait: every Shape is Debug
    fn area(&self) -> f64;
}
fn describe<T: Shape>(s: &T) {
    println!("{:?} has area {}", s, s.area());   // Debug available via supertrait
}
```

---

## Coding Patterns

### Pattern 1: Newtype to escape the orphan rule (or to pick a non-default instance)

```rust
// Two valid orderings for the same data → wrap to choose one per context.
struct ByLength(String);
impl PartialEq for ByLength { fn eq(&self, o: &Self) -> bool { self.0.len() == o.0.len() } }
// ... Eq, PartialOrd, Ord by length ...
```

Newtypes both dodge orphans *and* let you supply an alternative instance without violating coherence.

### Pattern 2: Prefer associated types for "one companion type" relationships

If a type determines its element/output/error type, model it as an associated type, not a parameter. Reserve parameters for genuinely multi-instance relationships (`Add<Rhs>`).

### Pattern 3: Encode capability hierarchies with superclasses/supertraits

`trait Ord: PartialOrd + Eq` / `class Eq a => Ord a`. Require the *strongest* needed and get the weaker for free; don't re-list `Eq` when you already demand `Ord`.

### Pattern 4: Model an operation axis as a typeclass to keep it open

When you anticipate adding new operations over a fixed set of types (or vice versa), make each operation a class/trait. You buy two-axis extensibility — the expression-problem win.

### Pattern 5: Pass an explicit dictionary/comparator when coherence fights you

When you genuinely need *two* behaviors for one type (e.g. sort by name vs by age), don't fight coherence — pass the operation explicitly (`sort_by`, an explicit `Comparator`, a manually-constructed dictionary). Coherence is for the *canonical* instance; ad-hoc per-call behavior should be an ordinary argument.

---

## Best Practices

- **Treat constraints as data.** When designing, ask "what dictionary does this constraint pass, and is it the canonical one?" It clarifies coherence and retrofitting decisions.
- **Respect coherence; route exceptions through newtypes or explicit arguments.** Never try to register two instances for one type — wrap, or pass the behavior in.
- **Default to associated types; reach for class type parameters only for true multi-instance needs.** It keeps inference healthy and signatures clean.
- **Demand the strongest bound you need and let superclasses supply the rest.** Avoid redundant `Eq + Ord` — `Ord` already implies `Eq`.
- **Package instances with the type or the class you own.** Design libraries so downstream users don't *need* orphans; if a popular foreign type needs your trait, provide a feature-gated impl from *your* crate (you own the trait).
- **Keep instances total and lawful.** `Ord` instances must be transitive and antisymmetric; an unlawful instance silently corrupts every collection built on it. Test instance laws (often via property tests).
- **Avoid overlapping/specialized instances and negative reasoning** unless you can articulate exactly why coherence still holds. They're advanced for a reason.

---

## Edge Cases & Pitfalls

- **Orphan rule blocks the obvious.** `impl ThirdPartyTrait for ThirdPartyType` is rejected. Newtype-wrap, or get one of the two crates to provide the impl behind a feature flag.
- **Unlawful instances corrupt collections silently.** A non-transitive `Ord`, an `Eq`/`Hash` mismatch (`a == b` but `hash(a) != hash(b)`) breaks `HashMap` with no error — just wrong answers and lost entries.
- **`Comparable<T>` vs `Comparable<? super T>` (subtype world).** The tight self-bound rejects a subclass that inherits comparability from a parent. In the typeclass world the analog is "is the instance head `C T` or `C (f a)`?" — instance resolution can surprise you with overlapping or unreachable instances.
- **Associated type vs parameter chosen wrongly.** Picking a parameter where an associated type belonged forces callers to annotate everywhere and wrecks inference; picking associated where you truly need multiple instances boxes you in. The "does the type *determine* it?" test is the deciding question.
- **Coherence vs "I want two orderings."** Coherence intentionally forbids two `Ord` instances for one type. Beginners try to declare both and get a conflict; the fix is a newtype or an explicit comparator, not fighting the compiler.
- **Superclass cycles / over-constrained hierarchies.** Deep `class A => B`, `class B => C` chains make instances tedious; derive where possible.
- **Specialization soundness.** A more specific overlapping instance that disagrees with the generic one can make the same expression mean different things depending on inferred types — a notorious source of subtle bugs; this is why specialization stayed unstable in Rust for years.
- **Open-world assumption breaks negative reasoning.** Code that branches on "`T` is *not* `Foo`" is fragile: someone adding `impl Foo for T` downstream changes behavior at a distance. Most languages forbid it for exactly this reason.
- **Monomorphization vs `dyn` is a semantic-adjacent choice.** Erasing dictionaries (mono) and keeping them (`dyn`) are both "dictionary passing," but `dyn` requires object-safe traits (no generic methods, no `Self`-returning methods) — a senior must know which traits can be `dyn` at all.

---

## Apply it

1. State the system invariant that **Bounded Polymorphism** must protect.
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

- Which invariant must remain true when Bounded Polymorphism fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
