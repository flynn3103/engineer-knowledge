# Variance — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Variance** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Subtyping: the foundation

Start with the one rule everything rests on. `Cat <: Animal` means: **a `Cat` is a valid `Animal`.** If a function takes an `Animal`, you can pass it a `Cat`. If a variable is declared `Animal x`, you can store a `Cat` in it. This is upcasting and it is always safe — a cat really *is* an animal, it just has extra abilities.

Variance asks the follow-up: subtyping is defined for *plain* types. What about *composed* types built out of them?

### 2. Covariance: the relationship is preserved

A type `F<T>` is **covariant in `T`** when:

```text
Cat <: Animal   implies   F<Cat> <: F<Animal>
```

The subtype relationship flows straight through, in the same direction. This is the intuitive case. It is safe **as long as `F<T>` only ever lets you *read* a `T` out** (a producer). Why? If you have a `Producer<Cat>` and treat it as a `Producer<Animal>`, every value it hands you is a `Cat`, and a `Cat` is a valid `Animal`. No lie is told. Reading is safe.

Examples of naturally covariant things: an immutable read-only list, a function's **return type**, an `Iterator` (you only pull values out), `Optional<T>` (read-only).

### 3. Contravariance: the relationship is reversed

A type `F<T>` is **contravariant in `T`** when:

```text
Cat <: Animal   implies   F<Animal> <: F<Cat>
```

The arrow flips. This feels backwards until you see *why*. Contravariance is the rule for **consumers** — things you only *write into* / *feed values to*.

Consider a `Consumer<T>` that has a method `accept(T value)`. Think about a `Consumer<Animal>` — it can accept *any* animal: a cat, a dog, a hamster. Now, can you use a `Consumer<Animal>` wherever a `Consumer<Cat>` is expected? **Yes!** A thing that can swallow any animal can certainly swallow a cat. So `Consumer<Animal> <: Consumer<Cat>` — the relationship reversed. A consumer of the *more general* type is a subtype of a consumer of the *more specific* type.

Examples of naturally contravariant things: a function's **parameter**, a `Comparator<T>` (it consumes two `T`s), a callback that you hand values to.

### 4. Invariance: no relationship — for safety

A type `F<T>` is **invariant in `T`** when `F<Cat>` and `F<Animal>` have **no subtype relationship at all**, even though `Cat <: Animal`. They are simply different, unrelated types.

This is the correct (and only safe) variance for a **mutable container** — something you can both read from *and* write to. A normal `List<T>` with both `get` and `add` must be invariant, because covariance breaks on the write side and contravariance breaks on the read side. We'll prove this with the array bug below.

### 5. Bivariance: both — and (almost always) wrong

**Bivariant** means `F<Cat>` and `F<Animal>` are mutually substitutable in *both* directions. This is almost always **unsound** — it lets you both read a wrong type out and write a wrong type in. Few languages allow it deliberately; the famous exception is TypeScript's method parameters by default, which is a known unsoundness (covered in `professional.md`).

### 6. The killer example: why mutable containers can't be covariant

Here is the bug that proves invariance is necessary. Java and C# made **arrays covariant** — they let you write `Object[] a = new String[1]`. Watch what that allows:

```java
String[] strings = new String[1];
Object[] objects = strings;     // ALLOWED: arrays are covariant, String[] <: Object[]
objects[0] = 42;                // compiles fine! 42 is an Object.
                                // ...but the array is REALLY a String[]
                                // CRASH: ArrayStoreException at runtime
```

Every line type-checks. The compiler is happy. But at runtime, the JVM has to insert a *check* on every array store, and when you try to put an `Integer` into what is secretly a `String[]`, it throws `ArrayStoreException`. **Covariance plus mutation equals unsoundness.** The only way to make this safe at compile time is to make mutable containers **invariant** — which is exactly what Java did for generics (`List<T>` is invariant) after learning the lesson from arrays.

### 7. The producer/consumer intuition (the shortcut)

You don't have to memorize the four rules. Ask one question about your generic type:

- **Do I only read `T` out of it?** → It's a producer → **covariant** is safe.
- **Do I only write `T` into it?** → It's a consumer → **contravariant** is safe.
- **Do I do both?** → **invariant** — no variance is safe.

In Java this intuition has a name: **PECS — "Producer Extends, Consumer Super."** When you read/produce, use `? extends T`. When you write/consume, use `? super T`. We'll see this in the examples and go deep on it in `middle.md`.

---

## Code Examples

We'll use the same cast — `Animal`, `Cat`, `Dog` — across languages.

### Java — arrays are covariant (and that's the bug)

```java
class Animal {}
class Cat extends Animal {}
class Dog extends Animal {}

public class ArrayCovariance {
    public static void main(String[] args) {
        Cat[] cats = new Cat[1];
        Animal[] animals = cats;   // legal: arrays ARE covariant in Java
        animals[0] = new Dog();    // compiles! Dog is an Animal.
        // At runtime: java.lang.ArrayStoreException — the array is really Cat[]
    }
}
```

The compiler accepts every line. The crash happens at runtime because the JVM checks every array store against the array's *actual* element type.

### Java — generics are invariant (the fix)

```java
import java.util.*;

public class ListInvariance {
    public static void main(String[] args) {
        List<Cat> cats = new ArrayList<>();
        // List<Animal> animals = cats;  // COMPILE ERROR: incompatible types
        // The compiler stops you BEFORE any crash can happen.
    }
}
```

`List<Cat>` is **not** a `List<Animal>` in Java. That rejection is the compiler protecting you from the exact array bug above. Generics learned the lesson arrays didn't.

### Java — covariance and contravariance on demand (wildcards / PECS)

```java
import java.util.*;

public class Pecs {
    // PRODUCER: we only READ animals out of src -> use ? extends (covariant)
    // CONSUMER: we only WRITE animals into dest -> use ? super (contravariant)
    static void copy(List<? super Animal> dest, List<? extends Animal> src) {
        for (Animal a : src) {   // reading: each is at least an Animal
            dest.add(a);         // writing: dest accepts Animal or any supertype
        }
    }

    public static void main(String[] args) {
        List<Cat> cats = new ArrayList<>(List.of(new Cat(), new Cat()));
        List<Object> sink = new ArrayList<>();
        copy(sink, cats);   // src is List<Cat> (a producer of Animals — fits ? extends Animal)
                            // dest is List<Object> (a consumer of Animals — fits ? super Animal)
    }
}
```

This is the real signature shape used by `java.util.Collections.copy`. **Producer Extends, Consumer Super.**

### C# — `out` and `in` declare variance on interfaces

```csharp
// Covariant: T appears only in OUTPUT position -> 'out'
interface IProducer<out T> { T Get(); }

// Contravariant: T appears only in INPUT position -> 'in'
interface IConsumer<in T> { void Accept(T item); }

class Animal {}
class Cat : Animal {}

class Program {
    static void Main() {
        IProducer<Cat> catSource = null;
        IProducer<Animal> animalSource = catSource;   // OK: covariant (out)

        IConsumer<Animal> animalSink = null;
        IConsumer<Cat> catSink = animalSink;           // OK: contravariant (in)
    }
}
```

C# bakes the producer/consumer rule into syntax: `out` = covariant (output only), `in` = contravariant (input only). The compiler *enforces* that a `T` marked `out` never appears as a parameter, and vice versa.

### Kotlin — `out` and `in`, same idea

```kotlin
interface Producer<out T> { fun get(): T }       // covariant
interface Consumer<in T> { fun accept(item: T) } // contravariant

open class Animal
class Cat : Animal()

fun main() {
    val catSource: Producer<Cat> = TODO()
    val animalSource: Producer<Animal> = catSource    // OK (out)

    val animalSink: Consumer<Animal> = TODO()
    val catSink: Consumer<Cat> = animalSink           // OK (in)
}
```

Kotlin's mnemonic is the same words as C# — `out` for "produces/outputs", `in` for "consumes/inputs".

### TypeScript — read-only arrays are safely covariant; mutable ones are the trap

```typescript
class Animal {}
class Cat extends Animal { meow() {} }

// ReadonlyArray is a producer -> covariant is safe
const cats: ReadonlyArray<Cat> = [new Cat()];
const animals: ReadonlyArray<Animal> = cats;  // OK and SOUND: you can only read

// Mutable array covariance is the unsafe analog of the Java array bug
let mutCats: Cat[] = [new Cat()];
let mutAnimals: Animal[] = mutCats;  // TS allows this (arrays are covariant)
mutAnimals.push(new Animal());        // now mutCats[1] is NOT a Cat — unsound
mutCats[1].meow();                    // runtime error: meow is not a function
```

TypeScript, like Java, lets mutable arrays be covariant for ergonomic reasons — and inherits the same soundness hole. The `ReadonlyArray` version is genuinely safe.

---

## Coding Patterns

### Pattern 1: PECS for flexible method signatures (Java)

```java
// Producer Extends, Consumer Super
static <T> void transfer(List<? extends T> from, List<? super T> to) {
    for (T item : from) to.add(item);
}
```

Read from `? extends`, write to `? super`. Memorize PECS and you'll write correct wildcard signatures without thinking about the soundness proof.

### Pattern 2: Mark interfaces by role (C# / Kotlin)

```csharp
interface IReader<out T> { T Read(); }     // producer -> out -> covariant
interface IWriter<in T> { void Write(T x); } // consumer -> in -> contravariant
```

Split a read/write interface into a producer interface and a consumer interface, each with the right variance. This is cleaner than one invariant interface and unlocks flexibility.

### Pattern 3: Prefer immutable types when you want covariance

If you find yourself wishing `List<Cat>` were a `List<Animal>`, ask whether the list needs to be mutable at all. An *immutable* list can be safely covariant. Reach for `ReadonlyArray<T>` (TS), `List<out T>` (Kotlin's read-only `List` is already covariant!), or `IReadOnlyList<out T>` (C#).

### Pattern 4: A contravariant comparator

```java
// A Comparator<Animal> can compare Cats, so it should be usable as Comparator<Cat>.
static void sortCats(List<Cat> cats, Comparator<? super Cat> cmp) {
    cats.sort(cmp);
}
// Now a general Comparator<Animal> can be passed in to sort cats.
```

`? super Cat` is contravariance in action: a more general comparator is accepted.

---

## Best Practices

- **Default mutable containers to invariant.** Don't fight your compiler when it refuses `List<Animal> a = catList`. It's right.
- **Use the producer/consumer test, not memorized rules.** Ask "do I read or write `T`?" and the variance falls out.
- **In Java, learn PECS and apply it mechanically.** `? extends` to read, `? super` to write.
- **In C#/Kotlin, mark each interface's parameter `out` or `in` when it's purely produced or consumed.** Let the compiler verify you didn't mix positions.
- **Prefer immutable types when you want covariance.** Immutability makes covariance safe for free.
- **Never rely on array covariance.** It compiles but it's a runtime trap. Treat arrays of reference types as a known hazard.
- **Don't fabricate bivariance.** If a language lets you (casts, `any`, unsafe interfaces), you're punching a hole in your type safety.

---

## Edge Cases & Pitfalls

- **The classic array-store crash.** `Object[] a = new String[1]; a[0] = 42;` compiles, throws `ArrayStoreException`. Covariant array + mutation = unsound. The #1 thing to remember from this page.
- **`List<Cat>` is *not* a `List<Animal>` in Java/C#/Kotlin generics.** People expect it to be. It isn't, and that rejection is a *feature*.
- **Contravariance feels backwards.** `Consumer<Animal> <: Consumer<Cat>` (not the other way). If it feels wrong, you're normal — re-read the garbage-chute analogy.
- **A read-only list is covariant; a mutable one is invariant.** Same data, different variance, purely because of mutation. Kotlin's `List` (read-only) is covariant; its `MutableList` is invariant.
- **Wildcards limit you.** A `List<? extends Animal>` lets you read `Animal`s but you *cannot* `add` to it (except `null`) — because the compiler doesn't know the real element type. A `List<? super Cat>` lets you add `Cat`s but reads come out as `Object`. This is the price of variance, and it's correct.
- **`null` is special.** You can usually add `null` to a `? extends` list because `null` is a member of every reference type. Don't read meaning into that.
- **Variance is per-type-parameter.** A `Map<K, V>` can be (and is) invariant in `K` and could be covariant in `V` — each slot has its own variance. A `Function<A, B>` is contravariant in `A` and covariant in `B`. We cover this in `middle.md`.

---

## Apply it

1. Choose one small, known input for **Variance**.
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

- What problem does Variance solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
