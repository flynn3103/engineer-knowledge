# Subtyping & Liskov Substitution — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Subtyping & Liskov Substitution** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Subtyping as a Formal Relation

`<:` is defined by inference rules. The structural ones every type system shares:

```text
            S <: T   T <: U                       (reflexivity)
(trans)  ───────────────────         (refl)   ─────────────
                S <: U                              T <: T
```

Then per-constructor rules. The function rule is the canonical one and the home of variance:

```text
        T1 <: S1        S2 <: T2
(→)  ─────────────────────────────────
        S1 → S2   <:   T1 → T2
```

Read the hypotheses: the *argument* type flips (`T1 <: S1` — contravariant), the *result* type stays the same direction (`S2 <: T2` — covariant). This single rule *is* the middle-level "contravariant parameters, covariant returns," now stated as a typing judgment. The whole point of the rule is to guarantee LSP: if `S1 → S2 <: T1 → T2`, then the function can be used wherever a `T1 → T2` is expected.

### 2. The Subsumption Rule Is the Bridge

Subtyping only *does* anything because of one typing rule:

```text
        Γ ⊢ e : S        S <: T
(sub)  ──────────────────────────
              Γ ⊢ e : T
```

This says: if `e` has type `S` and `S <: T`, then `e` *also* has type `T`. This is what lets you pass a `Dog` to a function expecting an `Animal` — the type checker *subsumes* the `Dog`'s type up to `Animal`. Every act of "using a subtype where a supertype is expected" is an application of `(sub)`. LSP is the *semantic* promise that this *syntactic* rule is safe: the program won't go wrong when you do it. A type system is **sound** precisely when subsumption never lets a value be used in a way it can't actually support — which is LSP, formalized.

### 3. Variance Is LSP for Type Constructors

A type constructor `F<·>` (like `List<·>`, `Func<·>`, `Box<·>`) takes a type and produces a type. The question variance answers: *given `S <: T`, what is the relationship between `F<S>` and `F<T>`?*

- **Covariant** (`F<+T>`): `S <: T ⟹ F<S> <: F<T>`. Safe when `T` appears only in **output** positions — return types, read-only fields. A `Producer<Dog>` is safely a `Producer<Animal>`: every dog it produces is an animal.
- **Contravariant** (`F<-T>`): `S <: T ⟹ F<T> <: F<S>`. Safe when `T` appears only in **input** positions — parameters, write-only sinks. A `Consumer<Animal>` is safely a `Consumer<Dog>`: something that eats any animal will eat a dog.
- **Invariant**: `T` appears in **both** input and output positions (a mutable container's `get` and `set`). Then *neither* direction is safe, so `F<S>` and `F<T>` are unrelated.

This is the deepest statement of LSP available: **variance is the rule that decides when a parameterized subtype is substitutable for a parameterized supertype.** The behavioral four-rules of the middle level are this rule specialized to method contracts (a method's parameters are input positions ⇒ contravariant ⇒ "don't strengthen preconditions"; a method's return is an output position ⇒ covariant ⇒ "don't weaken postconditions").

### 4. Why Mutable Containers Must Be Invariant (and Arrays Lie)

Consider why `List<Dog>` is *not* a subtype of `List<Animal>` in a sound system. Suppose it were. Then:

```text
List<Dog> dogs = ...;
List<Animal> animals = dogs;     // if List were covariant
animals.add(new Cat());          // type-checks: Cat is an Animal
Dog d = dogs.get(0);             // 💥 might be the Cat — type hole!
```

The `add` (input position) wants contravariance; the `get` (output position) wants covariance. A mutable list uses `T` in both, so it must be **invariant**. This is exactly why Java generics are invariant by default and why Scala's `class List[+T]` is *immutable*.

Now the famous lie: **Java and C# arrays are covariant** — `Dog[] <: Animal[]` holds. This is **unsound**, and the languages "patch" the hole with a *runtime* check:

```java
Dog[] dogs = new Dog[3];
Object[] objs = dogs;          // covariant — compiles
objs[0] = new Cat();           // compiles (Cat is Object)... 💥 ArrayStoreException at runtime
```

The static type system permits the unsafe assignment; the JVM inserts a runtime store check to catch it. This was a deliberate 1995 decision (Java had no generics, and covariant arrays let `sort(Object[])` work on any array). It is the canonical example of a language *knowingly violating LSP in its own type system* and paying for it with a runtime check on every array store.

### 5. Declaration-Site vs Use-Site Variance

Two designs for letting programmers express variance:

**Declaration-site** (Scala, C#, Kotlin): variance is fixed where the type is *defined*. `interface IEnumerable<out T>` in C# is covariant *everywhere it's used*. Cleaner for users; requires the designer to commit, and the compiler verifies that `T` only appears in legal positions for that variance.

```scala
trait Producer[+T] { def get(): T }            // covariant — T only in output
trait Consumer[-T] { def put(t: T): Unit }      // contravariant — T only in input
```

**Use-site** (Java wildcards): the *user* picks variance per use:

```java
List<? extends Number> producers;   // covariant view: can read Number, cannot add
List<? super Integer>  consumers;   // contravariant view: can add Integer, read only Object
```

Java's mnemonic is **PECS — Producer Extends, Consumer Super**. If you only *read* from a structure, it's a producer ⇒ `? extends`. If you only *write* to it, it's a consumer ⇒ `? super`. The wildcard is literally LSP applied at the call site: `? extends T` gives you a covariant (read-safe) view; `? super T` a contravariant (write-safe) view.

### 6. Nominal vs Structural, Formally

- **Nominal**: `S <: T` iff there's a declared chain `S extends/implements ... T`. The relation is a fixed DAG given by declarations. Java, C#, C++, Scala. Advantages: intentional (you can't be a subtype by accident), supports sealed hierarchies, names carry semantic intent. Disadvantage: can't retrofit a subtype relationship onto types you don't own.
- **Structural**: `S <: T` iff `S`'s members include `T`'s members with compatible (variance-respecting) types. TypeScript, Go interfaces, OCaml object types. Advantages: duck typing, retroactive conformance, fits gradual typing. Disadvantage: *accidental* conformance — a type can satisfy an interface by coincidence and then violate the unwritten behavioral contract (structural typing checks shape, never semantics — the behavioral LSP gap is *wider* here).

Both are *type-level* subtyping. Neither checks the *behavioral* contract — that's still LSP's domain and still has no compiler. (The nominal-vs-structural distinction has its own dedicated topic in this section; the link to it is in prose only by request.)

### 7. Bounded and Recursive Subtyping (Briefly)

**Bounded quantification** lets a generic constrain its parameter via subtyping: `<T extends Comparable<T>>`. **F-bounded polymorphism** is the recursive case where the bound mentions `T` itself — common for self-referential APIs (`Enum<E extends Enum<E>>`, fluent builders `Builder<B extends Builder<B>>`). These let subtyping and genericity interact: a method `<T extends Animal> void feed(List<T>)` accepts `List<Dog>`, `List<Cat>`, etc., recovering covariance-like flexibility without making `List` itself covariant.

---

## Code Examples

### Example 1: Variance verified at the declaration site (Scala)

```scala
// Covariant: T only appears in output position (return of get) — compiler accepts +T.
trait Source[+T] { def get(): T }
val dogs: Source[Dog]   = ...
val animals: Source[Animal] = dogs        // ✓ Source[Dog] <: Source[Animal]

// Contravariant: T only in input position — compiler accepts -T.
trait Sink[-T] { def put(t: T): Unit }
val animalSink: Sink[Animal] = ...
val dogSink: Sink[Dog] = animalSink        // ✓ Sink[Animal] <: Sink[Dog]

// Invariant by necessity: T in BOTH positions — +T or -T would fail to compile.
trait Cell[T] { def get(): T; def set(t: T): Unit }
```

If you tried `trait Cell[+T]`, the compiler rejects it: `set(t: T)` is a contravariant (input) use of a covariant parameter — a direct LSP soundness check, enforced at definition time.

### Example 2: PECS in Java — use-site variance as LSP at the call site

```java
// Producer: we only READ Numbers out — use ? extends (covariant view).
static double sum(List<? extends Number> src) {
    double total = 0;
    for (Number n : src) total += n.doubleValue();   // read ok
    // src.add(1);  // ✗ compile error: can't write through a producer view
    return total;
}

// Consumer: we only WRITE Integers in — use ? super (contravariant view).
static void fillWithZeros(List<? super Integer> dst, int count) {
    for (int i = 0; i < count; i++) dst.add(0);       // write ok
    // Integer x = dst.get(0);  // ✗ can only read as Object through a consumer view
}

sum(List.of(1, 2, 3));            // List<Integer> as List<? extends Number>  ✓
fillWithZeros(new ArrayList<Number>(), 3);  // List<Number> as List<? super Integer>  ✓
```

`? extends` recovers covariance for reads; `? super` recovers contravariance for writes — both are LSP-preserving views carved out of an otherwise invariant `List`.

### Example 3: The covariant-array unsoundness, demonstrated

```java
Integer[] ints = new Integer[3];
Number[]  nums = ints;            // ✓ compiles: arrays are covariant (Integer[] <: Number[])
nums[0] = 3.14;                   // ✓ compiles: Double is a Number
// 💥 java.lang.ArrayStoreException at runtime
```

The static type system permits an assignment that violates LSP (an `Integer[]` cannot actually hold a `Double`); the JVM inserts a per-store runtime type check to preserve memory safety. Generics fixed this by being invariant — `List<Integer>` is *not* a `List<Number>`, so the same mistake is a compile error.

### Example 4: Declaration-site variance in C#

```csharp
public interface IEnumerable<out T> { IEnumerator<T> GetEnumerator(); }  // covariant
public interface IComparer<in T>    { int Compare(T a, T b); }            // contravariant

IEnumerable<Dog>    dogs    = new List<Dog>();
IEnumerable<Animal> animals = dogs;       // ✓ out T: covariance

IComparer<Animal> byName = ...;
IComparer<Dog>    dogCmp  = byName;        // ✓ in T: contravariance (an animal-comparer compares dogs)
```

The `out`/`in` annotations let the compiler *prove* substitutability once, at the interface, for all consumers.

### Example 5: F-bounded polymorphism recovering flexibility

```java
// Self-referential bound: every Enum subtype compares only to its own kind.
abstract class Enum<E extends Enum<E>> implements Comparable<E> { /* ... */ }

// Generic method gives "covariance for this call" without making List covariant:
static <T extends Shape> double totalArea(List<T> shapes) {
    return shapes.stream().mapToDouble(Shape::area).sum();
}
totalArea(new ArrayList<Circle>());   // ✓ List<Circle> accepted via the bound
```

---

## Coding Patterns

**Pattern 1 — Derive variance from positions, then annotate.** For each type parameter, classify every occurrence as input or output. All-output ⇒ covariant. All-input ⇒ contravariant. Mixed ⇒ invariant (or split the type).

**Pattern 2 — Split mutable types into covariant read + invariant write.** The standard trick to get covariance you couldn't otherwise have:

```kotlin
interface Source<out T> { fun get(): T }            // covariant
interface Sink<in T>    { fun put(t: T) }            // contravariant
interface Cell<T> : Source<T>, Sink<T>              // invariant where both are needed
```

**Pattern 3 — Apply PECS at every generic method boundary.** Parameters you only read from: `? extends`. Parameters you only write to: `? super`. This maximizes the LSP-valid set of arguments callers can pass.

**Pattern 4 — Prefer generic methods over covariant containers.** A bounded type parameter (`<T extends Shape>`) often gives the flexibility you wanted from covariance, soundly, without committing the container itself.

---

## Best Practices

- **Make containers immutable if you want them covariant.** Mutability forces invariance; immutability frees variance. This is the single most useful LSP-and-variance design lever.
- **Annotate variance at declaration when your language supports it.** It documents and *proves* the substitutability contract once, for all users, instead of pushing wildcard noise onto every call site.
- **Use PECS deliberately in Java APIs**, even though it's verbose — it widens what callers can pass and is itself LSP applied per-use.
- **Never rely on array covariance.** Treat `Object[]` parameters as a legacy hazard; prefer `List<? extends T>` which is statically sound.
- **Remember variance is only half of LSP.** The compiler proves the type-constructor relationship; you still owe the *behavioral* contract (the four rules) for the values themselves.
- **In structural-typing languages, write the behavioral contract down explicitly** — there's no declaration site to carry intent, so accidental conformance is a live risk.

---

## Edge Cases & Pitfalls

- **The unsound array trap in disguise.** Generic varargs, reflection, and legacy `Object[]` APIs reintroduce array covariance — and `ArrayStoreException` — into otherwise generic code.
- **Variance position violations the compiler reports cryptically.** "Covariant type parameter T occurs in contravariant position" means you used a `+T` parameter as a method *input*. The fix is usually a lower-bounded method generic (`def putU >: T` in Scala).
- **Wildcard capture confusion.** `List<?>` (unbounded) lets you read `Object` and write nothing but `null`; programmers expect to be able to copy within it and can't without a capture helper method.
- **Site-vs-declaration mismatch when porting.** Code translated from Scala/C# (declaration-site) to Java (use-site) must re-express variance as wildcards at every use, and vice versa — a common porting bug.
- **Top/Bottom edge cases.** `Nothing`/`never` (bottom) is a subtype of everything, so a function returning `never` is a subtype of any return type — handy for throwers, surprising in inference.
- **Structural accidental conformance.** In Go/TS, a type can satisfy an interface because two unrelated methods happen to share a name and signature, then violate the unwritten behavioral contract — a pure-LSP break the type checker is blind to.
- **Self-bounds that leak.** F-bounded `Builder<B extends Builder<B>>` works until a subclass forgets to re-parameterize `B`, at which point fluent chains return the wrong static type — a subtle substitutability defect.

---

## Apply it

1. State the system invariant that **Subtyping & Liskov Substitution** must protect.
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

- Which invariant must remain true when Subtyping & Liskov Substitution fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
