# Variance — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Variance** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The function subtyping rule, stated precisely

For two function types:

```text
(A1 -> B1) <: (A2 -> B2)
   iff
A2 <: A1     (parameter: CONTRAVARIANT — the arrow flips)
   and
B1 <: B2     (return:    COVARIANT     — the arrow preserved)
```

Read it as: a function `f : A1 -> B1` can be used wherever `g : A2 -> B2` is expected when `f` accepts at least everything `g` would be given (so `A2 <: A1`, `f`'s parameter is a *supertype*) and `f` returns something that fits where `g`'s result was expected (so `B1 <: B2`, `f`'s result is a *subtype*).

### 2. Why parameters are contravariant — the substitution argument

Suppose code expects a `g : Cat -> Int` and somewhere calls `g(someCat)`. You want to substitute your `f` for `g`. The caller will hand `f` a `Cat`. For `f` to be safe, `f` must be able to accept that `Cat`. If `f : Animal -> Int`, it accepts *any* animal, so it certainly accepts the `Cat`. So `f : Animal -> Int <: Cat -> Int` — the function with the *more general* parameter is the subtype. **More general input = subtype.** That's contravariance.

If instead `f : Persian -> Int` (a subtype of `Cat`), it would choke when handed a plain `Cat`. So narrowing a parameter is *unsafe* — you may not do it.

### 3. Why returns are covariant — the same argument, other end

The caller does `Int x = g(someCat)` expecting an `Int`. If your `f` returns a `PositiveInt <: Int`, the caller still gets something usable as an `Int`. So `f : Cat -> PositiveInt <: Cat -> Int` — the function with the *more specific* return is the subtype. **More specific output = subtype.** That's covariance.

### 4. The slogan: "accept more, return less"

A function is a *better* (sub-) function if it is more **lenient** about what it takes and more **precise** about what it gives. "Accept more" = wider parameter (contravariant). "Return less" = narrower return (covariant). Both make the function *more useful* as a drop-in. This single sentence is the most-tested variance fact in interviews.

### 5. Override rules fall straight out of this

Method overriding is function subtyping with the parameter and return slots:

- **Covariant return**: an override may return a **subtype** of the original return type. `Animal reproduce()` may be overridden by `Cat reproduce()`. Java 5+ allows this; before that you had to return the exact type.
- **Parameter contravariance** *would* allow an override to accept a **supertype** of the original parameter. It's sound — but most OO languages (Java, C#, C++) treat a different parameter type as **overloading**, not overriding, so you rarely see it. Scala and a few others support genuine parameter contravariance in overrides.
- **What you must NOT do**: narrow a parameter (demand a subtype) or widen a return (return a supertype) — both break substitutability.

A clean way to remember override rules: **"a subclass method may promise more (narrower return) and demand less (wider parameter)."** That's LSP for methods, and it's exactly function variance.

### 6. Per-position variance: one generic, multiple slots

`Function<A, B>` has two slots with opposite variances. In C#:

```csharp
interface Func<in A, out B> { B Invoke(A arg); }
```

`A` is `in` (contravariant — it's only consumed as a parameter), `B` is `out` (covariant — it's only produced as a return). Variance is computed *per type parameter*, by looking at every position where that parameter appears:

- Appears only in output positions → covariant (`out`).
- Appears only in input positions → contravariant (`in`).
- Appears in both → invariant.

### 7. Variance composes (positions can flip)

Variance is computed by multiplying signs as you nest. Treat covariant as `+` and contravariant as `-`. A position's overall variance is the product of the variances of every constructor wrapping it.

Consider `(Cat -> Int) -> String`, a function that *takes a function*. The inner `Cat` sits in the parameter position of the inner function (`-`), which itself sits in the parameter position of the outer function (`-`). `(-) × (-) = (+)` — so `Cat` is in a **covariant** position overall. A higher-order function's *callback's parameter* ends up covariant. This "minus times minus is plus" rule is how you reason about deeply nested signatures, and it trips up almost everyone the first time.

---

## Code Examples

### Scala — function variance is built into the standard library

```scala
// Scala's Function1 is DECLARED:  trait Function1[-T1, +R]
//   -T1  contravariant in the argument
//   +R   covariant in the result
class Animal
class Cat extends Animal
class Persian extends Cat

val takesCat:    Cat => Animal    = (c: Cat) => new Animal
val takesAnimal: Animal => Persian = (a: Animal) => new Persian

// Is (Animal => Persian) a subtype of (Cat => Animal)?
// Param:  Cat <: Animal   ✓ (contravariant: wider param OK)
// Return: Persian <: Animal ✓ (covariant: narrower return OK)
val asCatToAnimal: Cat => Animal = takesAnimal   // compiles — accept more, return less
```

`takesAnimal` accepts *more* (any animal, not just cats) and returns *less* (a `Persian`, more specific than `Animal`), so it is a valid `Cat => Animal`.

### Java — covariant return types in overrides

```java
class Animal { Animal reproduce() { return new Animal(); } }

class Cat extends Animal {
    @Override
    Cat reproduce() { return new Cat(); }   // covariant return: Cat <: Animal — legal in Java 5+
}

// Why it's safe: anyone calling animal.reproduce() expects an Animal.
// A Cat IS an Animal, so returning a Cat never disappoints the caller.
```

Before Java 5 this was a compile error; you had to declare the return type as `Animal`. The relaxation is pure covariant-return reasoning.

### Java — why you can't narrow a parameter (it becomes overloading, not overriding)

```java
class Handler { void handle(Animal a) { } }

class CatHandler extends Handler {
    // void handle(Cat c) { }   // This does NOT override — it OVERLOADS.
    // If it DID override and narrowed the param, then:
    //   Handler h = new CatHandler();
    //   h.handle(new Dog());    // caller passes a Dog (legal for Handler.handle)
    //                           // but CatHandler only handles Cats -> unsound!
}
```

Narrowing a parameter via override would be unsound, which is why Java refuses to treat it as an override at all.

### TypeScript — function types, with strictFunctionTypes

```typescript
class Animal {}
class Cat extends Animal { meow() {} }

type CatFn = (c: Cat) => void;
type AnimalFn = (a: Animal) => void;

declare let takesAnimal: AnimalFn;
declare let takesCat: CatFn;

// Sound assignment: a function taking Animal can stand in for one taking Cat
// (contravariant parameters): it accepts MORE.
let asCatFn: CatFn = takesAnimal;   // OK under strictFunctionTypes — sound

// The UNSOUND direction is rejected only when strictFunctionTypes is ON:
let asAnimalFn: AnimalFn = takesCat; // ERROR (strict): takesCat would receive a Dog and call .meow()
```

With `strictFunctionTypes` enabled, TypeScript checks standalone function parameters **contravariantly** (sound). Method parameters remain bivariant — covered in `professional.md`.

### Kotlin — declaration-site variance on a function-like interface

```kotlin
interface Transform<in A, out B> {   // contravariant in A, covariant in B
    fun apply(input: A): B
}

open class Animal
class Cat : Animal()
open class Shape
class Circle : Shape()

fun main() {
    val animalToCircle: Transform<Animal, Circle> = TODO()
    // Usable where Transform<Cat, Shape> is wanted:
    //   in A:  Cat <: Animal  -> accepts more (contravariant)  ✓
    //   out B: Circle <: Shape -> returns less (covariant)     ✓
    val catToShape: Transform<Cat, Shape> = animalToCircle      // compiles
}
```

### C# — nested variance, the sign-multiplication rule

```csharp
// Action<T> is contravariant: Action<in T>
// Action<Action<T>> -> T sits inside contravariant inside contravariant -> COVARIANT overall.
class Animal {}
class Cat : Animal {}

class Demo {
    static void Run() {
        Action<Action<Cat>> outer = null;
        // Because (-)×(-) = (+), this behaves covariantly in the inner T:
        Action<Action<Animal>> wider = outer;   // permitted: minus-times-minus is plus
    }
}
```

---

## Coding Patterns

### Pattern 1: Contravariant callback parameter (Java)

```java
interface Sink<T> { void accept(T value); }

static void feedCats(List<Cat> cats, Sink<? super Cat> sink) {
    for (Cat c : cats) sink.accept(c);
}
// A Sink<Animal> can be passed: it consumes Cats fine. ? super = contravariance.
```

### Pattern 2: Covariant return in a factory hierarchy

```java
abstract class AnimalShelter { abstract Animal adopt(); }
class CatShelter extends AnimalShelter {
    @Override Cat adopt() { return new Cat(); }   // callers get the precise type for free
}
```

### Pattern 3: Split a transform into `in`/`out` slots (Kotlin/C#)

```kotlin
interface Pipe<in I, out O> { fun run(input: I): O }
```

Mark inputs `in`, outputs `out`. The compiler verifies each parameter only appears in its declared role — a free correctness check.

### Pattern 4: Use the sign rule before trusting a nested signature

When a signature nests functions (`(A -> B) -> C`), don't guess. Multiply signs from the outside in for each occurrence of a type parameter, then write the `in`/`out`/invariant annotation that results.

---

## Best Practices

- **Memorize "accept more, return less."** It governs overrides, callbacks, and higher-order signatures in every language.
- **For overrides, narrow returns and (where the language allows) widen parameters — never the reverse.** That's the LSP-safe direction.
- **Annotate function-like interfaces with `in`/`out` (C#/Kotlin) or `-`/`+` (Scala).** It documents intent and lets the compiler catch position mistakes.
- **When a signature nests, compute variance with sign multiplication.** Don't reason by gut feeling about `(A -> B) -> C`.
- **Turn on `strictFunctionTypes` in TypeScript.** It restores sound contravariant checking of standalone function parameters.
- **Prefer `Comparator<? super T>` / `Consumer<? super T>` in public APIs.** Contravariant bounds make your API accept more callers' types.
- **Prefer `? extends T` / `Iterator<? extends T>` for producers you return or read.** Covariant bounds make your API usable in more contexts.

---

## Edge Cases & Pitfalls

- **Method parameters in TypeScript are bivariant by default.** Even with `strictFunctionTypes`, *method* (not standalone function) parameters stay bivariant — a deliberate unsound concession. See `professional.md`.
- **Overriding vs overloading confusion.** Changing a parameter type in a subclass often creates an *overload*, not an override — so `@Override` (Java) or `override` (Kotlin/C#) is your safety net; use it.
- **Covariant return + generics + erasure → bridge methods.** On the JVM, a covariant-return override compiles to a synthetic bridge method. Usually invisible, but it shows up in stack traces and reflection.
- **Contravariance breaks naïve equality/`compareTo`.** `Comparable<T>` is often `Comparable<? super T>` precisely so a base-class `compareTo` works for subclasses. Forgetting the `? super` produces frustrating "cannot be applied" errors.
- **The nested flip surprises everyone.** A callback's parameter inside a higher-order function ends up *covariant*. If you "just feel" the variance you'll get it wrong; multiply signs.
- **Languages disagree on parameter contravariance in overrides.** Java/C#/C++ treat differing parameters as overloads; Scala and Eiffel allow genuine contravariant overriding. Don't assume portability.
- **`void`/`Unit` return is covariant too, trivially.** A function returning `Nothing`/`never` is a subtype of one returning anything — `Nothing` is the bottom type, a subtype of all.

---

## Apply it

1. Find a real component where **Variance** affects an interface or dependency.
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

- Which boundary is most affected by Variance?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
