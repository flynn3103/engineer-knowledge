# Variance — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Variance** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The subtyping rule for a generic, given its variances

For a unary generic `F<T>` with declared variance `v`:

```text
v = covariant     (out, +):   S <: T   ⟹   F<S> <: F<T>
v = contravariant (in,  -):   S <: T   ⟹   F<T> <: F<S>
v = invariant     (0):        F<S> <: F<T>   only if   S = T
```

For a multi-parameter generic, apply this per parameter and require *all* of them simultaneously. So `Function<in A, out B>`: `Function<A1,B1> <: Function<A2,B2>` iff `A2 <: A1` (contravariant) **and** `B1 <: B2` (covariant) — exactly the function rule.

### 2. The positional check: how declaration-site variance stays sound

When you write `class Producer<out T>`, the compiler scans every position where `T` appears in the class body and demands each is a **covariant position**. Concretely:

- A method **return type** is covariant → `out T` allowed there.
- A method **parameter type** is contravariant → `out T` *forbidden* there.
- An *immutable* (`val`/`readonly`/`final`) field of type `T` is covariant (read-only) → allowed.
- A *mutable* (`var`) field of type `T` is both read (covariant) and written (contravariant) → **invariant position** → `out T` forbidden, `in T` forbidden — only an invariant parameter may sit there.

This is *the* mechanism. It is the formalization of the producer/consumer test. The compiler doesn't trust your intent; it proves the parameter only flows in the declared direction.

### 3. Why mutable containers are forced invariant — the proof

Take a mutable `Box<T>` with `fun get(): T` and `fun set(x: T)`.

- `get(): T` puts `T` in a **covariant** position. To declare `out T`, you'd need *only* covariant positions.
- `set(x: T)` puts `T` in a **contravariant** position. To declare `in T`, you'd need *only* contravariant positions.

`T` appears in both. By sign analysis it is in an **invariant** position. Therefore neither `out` nor `in` passes the positional check, and `Box<T>` is forced invariant. This is the rigorous version of "covariance + mutation = unsound." The array bug from `junior.md` is exactly the case of a language (Java arrays) that *skipped* this check and pushed the cost to a runtime `ArrayStoreException`.

### 4. Use-site variance: shift the choice to the caller

Java made generics invariant by default and gave callers wildcards to opt into variance per use:

- `List<? extends Animal>` — a covariant *view*. You may read `Animal`s; you may **not** call `add(x)` for any non-null `x`, because the compiler captured `?` as some unknown subtype of `Animal` and can't prove `x` matches it.
- `List<? super Cat>` — a contravariant *view*. You may `add(Cat)`; reads come out as `Object`, because all the compiler knows is "some supertype of `Cat`."

The brilliance is flexibility: one invariant `List<T>` serves both producer and consumer roles depending on the wildcard at the call site. The cost is verbosity and **wildcard capture** complexity — every `?` is a fresh, anonymous type variable the compiler juggles, which produces those infamous `capture#1 of ? extends Animal` error messages.

### 5. Declaration-site vs use-site — the engineering trade

| | Declaration-site | Use-site |
|---|---|---|
| **Where annotated** | Once, at definition | At every use |
| **Reader burden** | Low at call sites; variance is implicit and uniform | High; every signature repeats `? extends`/`? super` |
| **Author burden** | Must design the type to satisfy the position check | None up front; flexibility deferred |
| **Flexibility** | Fixed per type | Per use — same type, different variance at different sites |
| **Examples** | Scala, Kotlin, C# interfaces | Java generics, C# arrays |

Most modern languages (Scala, Kotlin, C#) favor declaration-site as the default and offer use-site as an escape hatch (Kotlin's `out`/`in` *projections*, C# can't easily). Java is the major use-site-only holdout for generics.

### 6. Variance and the `Comparable`/`Iterator`/`Function` standard library

The standard library is where these rules earn their keep:

- `Iterator<out T>` / `Iterator<? extends T>` — covariant; you only pull values.
- `Comparable<in T>` / `Comparator<? super T>` — contravariant; a comparator that orders `Animal`s can order `Cat`s, so a `Comparator<Animal>` should be accepted where a `Comparator<Cat>` is wanted. Generic bounds in `sort` are written `Comparator<? super T>` precisely for this.
- `Function<in A, out B>` — per-position: contravariant input, covariant output.
- `Supplier<out T>` / `Consumer<in T>` — the textbook producer and consumer.

When you see these `in`/`out`/`? super`/`? extends` decorations on the standard library, they are not decoration — they are the position check made visible.

### 7. Soundness: what variance buys and what it doesn't

The soundness guarantee is: a program that type-checks under the variance rules will never crash with a type error from a well-typed operation. Variance *preserves* the substitution guarantee of subtyping through type constructors. What it does **not** give you: it doesn't make *every* `F<S> <: F<T>` you might *want* legal — only the safe ones. And it says nothing about runtime semantics beyond type safety (no claims about nullability, side effects, etc.).

---

## Code Examples

### Scala — declaration-site `+`/`-` and the position check

```scala
// Covariant: T only in OUTPUT positions
class ImmutableBox+T {
  def get: T = value                       // covariant position: OK
  // def set(x: T): Unit = ???             // would NOT compile:
  //   "covariant type T occurs in contravariant position"
}

// Contravariant: T only in INPUT positions
trait Printer[-T] {
  def print(x: T): Unit                    // contravariant position: OK
  // def produce(): T                      // would NOT compile:
  //   "contravariant type T occurs in covariant position"
}

class Animal; class Cat extends Animal
val cats: ImmutableBox[Cat] = new ImmutableBox(new Cat)
val animals: ImmutableBox[Animal] = cats   // covariance: OK, sound (read-only)
```

The commented-out lines are *exactly* the compiler's position check firing.

### Scala — `@uncheckedVariance` escape hatch

```scala
import scala.annotation.unchecked.uncheckedVariance

// Asserts to the compiler: "I know T appears in a contravariant position here,
// but I've reasoned about soundness myself." Used in the stdlib for buffers.
trait Builder[+T] {
  def add(x: T @uncheckedVariance): Unit   // suppress the position error
}
```

This is the manual-override sticker. It is occasionally necessary (the Scala collections library uses it) but it shifts the soundness burden onto you.

### Kotlin — declaration-site plus use-site projections

```kotlin
// Declaration-site: Source is covariant, Sink is contravariant
interface Source<out T> { fun next(): T }
interface Sink<in T> { fun put(x: T) }

open class Animal; class Cat : Animal()

// USE-SITE projection: make an otherwise-invariant Array covariant for this parameter
fun copyOut(from: Array<out Animal>) {       // 'out' projection: read-only view
    for (a in from) println(a)
    // from[0] = Animal()  // ERROR: out-projected array can't be written
}

fun main() {
    val src: Source<Cat> = TODO()
    val animalSrc: Source<Animal> = src       // covariance from declaration-site

    val sink: Sink<Animal> = TODO()
    val catSink: Sink<Cat> = sink             // contravariance from declaration-site
}
```

Kotlin shows both designs in one language: `out`/`in` at the declaration, plus `out`/`in` *projections* at the use site for types (like `Array`) that are declared invariant.

### Java — use-site wildcards and capture

```java
import java.util.*;

// One invariant List<T>, two roles chosen at the use site:
static double sum(List<? extends Number> producers) {   // covariant view: read
    double total = 0;
    for (Number n : producers) total += n.doubleValue();
    // producers.add(1);  // ERROR: capture of ? extends Number — can't prove the element type
    return total;
}

static void fillWithZeros(List<? super Integer> consumers, int n) {  // contravariant view: write
    for (int i = 0; i < n; i++) consumers.add(0);
    // Integer x = consumers.get(0);  // ERROR: reads come out as Object
}
```

### C# — declaration-site on interfaces; arrays are use-site (and unsafe)

```csharp
interface IEnumerable<out T> { /* T only in output positions */ }
interface IComparer<in T> { int Compare(T a, T b); /* T only in input positions */ }

class Animal {}
class Cat : Animal {}

class Demo {
    static void M() {
        IEnumerable<Cat> cats = null;
        IEnumerable<Animal> animals = cats;   // covariant interface — sound

        // Arrays remain covariant (legacy, pre-generics) and UNSOUND:
        Cat[] catArray = new Cat[1];
        Animal[] animalArray = catArray;       // allowed
        // animalArray[0] = new Animal();       // throws ArrayTypeMismatchException at runtime
    }
}
```

C# is the cleanest illustration of the split: **interfaces** got sound declaration-site variance in 4.0, while **arrays** kept the old unsound use-site covariance for backward compatibility — and pay for it with a runtime `ArrayTypeMismatchException`.

---

## Coding Patterns

### Pattern 1: Split a read/write type into producer + consumer interfaces

```kotlin
interface ReadOnly<out T> { fun get(i: Int): T }     // covariant
interface WriteOnly<in T> { fun set(i: Int, v: T) }  // contravariant
interface ReadWrite<T> : ReadOnly<T>, WriteOnly<T>   // invariant where you need both
```

The pair gives callers a covariant view, a contravariant view, and an invariant union — the most flexible design the position check allows.

### Pattern 2: Use-site projection to borrow variance from an invariant type

```kotlin
fun render(items: List<out Drawable>) { for (d in items) d.draw() }
// Caller may pass List<Button>, List<Label>, etc., without List being declared covariant.
```

### Pattern 3: PECS as the use-site form of producer/consumer

```java
static <T> void pipe(List<? extends T> src, List<? super T> dst) {
    for (T x : src) dst.add(x);
}
```

### Pattern 4: Reach for the escape hatch only with a written-down argument

When you must use `@uncheckedVariance`/`@UnsafeVariance`, write a comment proving the position is safe (e.g., "T only ever escapes after a defensive copy"). The compiler stops checking; your comment is the new proof.

---

## Best Practices

- **Default to declaration-site variance where your language offers it.** Annotate `out`/`in` on interfaces with a single clear role.
- **Design types so the position check passes naturally — split read and write.** If a type wants covariance but has a setter, that setter belongs on a separate invariant interface.
- **Treat a position-check error as a soundness warning, not a nuisance.** It is telling you the variance you asked for would let a wrong value through.
- **Use wildcards (`? extends`/`? super`) in *public* Java signatures, not internal ones.** Flexibility belongs at the API boundary; internal code can stay concrete.
- **Avoid the escape hatch unless you can write the soundness argument.** `@uncheckedVariance`/`@UnsafeVariance` moves the proof obligation to you.
- **Prefer `IReadOnlyList<out T>`/`List` over arrays at boundaries.** Arrays' legacy covariance is a runtime hazard; the generic alternatives are sound.
- **Document the variance intent of each type parameter.** Future maintainers shouldn't have to re-derive whether `T` is produced or consumed.

---

## Edge Cases & Pitfalls

- **A single mutating method collapses the type to invariant.** Add one `set(T)` to a covariant type and the position check fails. Move it to a separate interface or accept invariance.
- **Wildcard capture errors are about an *unknown but fixed* type.** `List<? extends Animal>.add(cat)` fails not because cats aren't animals but because the compiler captured `?` as "some specific unknown subtype of Animal" and can't prove `cat` matches it.
- **`@uncheckedVariance`/`@UnsafeVariance` silences the check, not the danger.** Scala's mutable collections use it correctly; misuse reintroduces the array bug under a different name.
- **C# generic *delegates* and *interfaces* support declaration-site variance; classes do not.** You can't write `class Box<out T>` in C#. Use an interface.
- **Java has no declaration-site variance at all.** Every `List<T>` is invariant; you *must* use wildcards. Code ported from Kotlin/Scala loses its declaration-site annotations.
- **Variance interacts with nullability and bounds.** `out T` with a lower-bounded use, or `T : Comparable<T>` f-bounds, can produce surprising "out-projected type ... cannot be used" errors. Read the capture in the message.
- **Out-projection makes a parameter read-only even for `var`.** Kotlin's `Array<out T>` forbids writes; people expect `out` to mean "covariant and still writable" — it can't, by the position check.
- **Star projection (`List<*>`) is not the same as `List<Any?>`.** `*` means "some unknown type argument," producing an out-projected read view, not the top type.

---

## Apply it

1. State the system invariant that **Variance** must protect.
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

- Which invariant must remain true when Variance fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
