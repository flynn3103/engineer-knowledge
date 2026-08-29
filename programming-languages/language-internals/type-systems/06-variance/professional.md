# Variance — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Variance** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The array covariance hole, fully dissected

Java arrays were made covariant in 1995 so that pre-generics code could write polymorphic routines like `void sort(Object[] a)` and call it on a `String[]`. Without covariance, you'd have needed a separate sort per element type. The price: covariance + mutation is unsound, so the runtime *must* check every store.

```java
String[] s = new String[1];
Object[] o = s;        // upcast allowed by covariance
o[0] = Integer.valueOf(42);   // type-checks (Integer IS-A Object)
// JVM checks: is the actual array element type (String) assignable from Integer? NO.
// throws java.lang.ArrayStoreException
```

This means **every reference-array store in Java carries a hidden runtime type check** — a real, measurable cost, and a latent crash. C# made the identical choice with the identical consequence (`ArrayTypeMismatchException`). When C# and Java *added generics*, they made them **invariant** — explicitly to *not* repeat this — which is why `List<String>` is not a `List<Object>` but `String[]` is an `Object[]`.

### 2. Why generics fixed it but arrays couldn't be retrofitted

Generics are *erased* (Java) or reified-but-invariant (C#); either way, the language designers controlled the rules from day one and chose invariance plus opt-in wildcards/`out`/`in`. Arrays predate generics and millions of lines rely on their covariance; removing it would break the world. So both languages live with a permanent, well-documented hazard in arrays and a sound model in generics — a split a professional must keep straight.

### 3. TypeScript: bivariant method parameters by design

TypeScript's structural type system checks function assignability. Under the original (and still default for *methods*) rules, parameters are **bivariant** — a `(x: Animal) => void` and a `(x: Cat) => void` are mutually assignable. That's unsound: assigning a `(x: Cat) => void` where `(x: Animal) => void` is expected lets the function receive a `Dog` and call cat-only methods.

`strictFunctionTypes` (TS 2.6+) fixes this for **standalone function-typed** parameters by checking them **contravariantly** — but deliberately leaves **method** parameters bivariant. The rationale: a huge amount of real code (especially around mutable arrays and event handlers) relies on method-parameter bivariance, and making it strict would break the `Array<T>` methods and DOM event types in painful ways. So TypeScript ships a *partial* fix: sound for function properties, unsound for methods, and documents it.

```typescript
interface EventHandler { handle(e: Event): void; }      // method -> bivariant param
type EventHandlerFn = { handle: (e: Event) => void; };  // function property -> contravariant under strict
```

The same signature shape is checked differently depending on whether it's written as a *method* or a *function-typed property*. Professionals exploit this: write callbacks as function-typed properties to get the sound check.

### 4. The engineering signatures that depend on variance

The payoff for all this theory is APIs that compose. The canonical examples:

- **`Collections.copy(List<? super T> dest, List<? extends T> src)`** — PECS made concrete. `src` produces (covariant `? extends`), `dest` consumes (contravariant `? super`). Without the wildcards, you couldn't copy `List<Cat>` into `List<Animal>`.
- **A contravariant comparator: `sort(List<T>, Comparator<? super T>)`** — lets a `Comparator<Animal>` sort a `List<Cat>`. Drop the `? super` and your generic ordering utilities reject base-class comparators.
- **A contravariant callback sink: `forEach(Consumer<? super T>)`** — lets a `Consumer<Object>` (e.g., a logger) consume a stream of `String`.
- **Covariant return in overrides: `Cat reproduce()` overriding `Animal reproduce()`** — callers of the subtype get the precise type without casting.

### 5. The override asymmetry, stated for engineers

The practical rule professionals enforce in code review: **an override may return a subtype but may not accept a supertype *as an override* (most OO languages make that an overload).** You *can* return a subtype (covariant return — useful). You *cannot* safely accept only a subtype (narrowing a param — unsound). And accepting a supertype, while sound, usually isn't an override in Java/C#. So the only override flexibility you actually get in mainstream OO is **covariant returns** — narrow the output, keep the input the same.

### 6. Defensive immutability as the engineering answer to the array bug

The professional's standard mitigation: when you want covariance, make the data immutable so covariance is *sound*. Return `IReadOnlyList<T>` / `ReadonlyArray<T>` / Kotlin `List` (read-only) from APIs; copy on the way in and out so no covariant alias can mutate your internals. This converts "covariance is dangerous" into "covariance is fine because nothing can be written through the covariant view."

### 7. Variance failures wear disguises in production

The same root cause surfaces as different exceptions and bugs: `ArrayStoreException` (Java arrays), `ArrayTypeMismatchException` (.NET arrays), `ClassCastException` from a downcast that "shouldn't" fail, a TypeScript callback silently receiving the wrong runtime shape (no exception — just wrong behavior because TS types are erased). A professional learns to ask, on seeing these, "is something covariant being mutated, or is a contravariant slot being narrowed?"

---

## Code Examples

### Java — `Collections.copy`-style PECS in production

```java
import java.util.*;

final class Pipes {
    // Producer Extends, Consumer Super — the canonical variance-aware signature.
    static <T> void copy(List<? super T> dest, List<? extends T> src) {
        for (int i = 0; i < src.size(); i++) {
            dest.set(i, src.get(i));     // read T from src (covariant), write T to dest (contravariant)
        }
    }

    public static void main(String[] args) {
        List<Animal> dst = new ArrayList<>(Arrays.asList(null, null));
        List<Cat> src = Arrays.asList(new Cat(), new Cat());
        copy(dst, src);   // copy List<Cat> into List<Animal> — only possible with the wildcards
    }
}
class Animal {}
class Cat extends Animal {}
```

### Java — the array hole that a code reviewer must catch

```java
static void appendNumber(Object[] arr, int idx) {
    arr[idx] = 42;   // looks innocent; throws ArrayStoreException if arr is really a String[]
}

public static void demo() {
    String[] names = {"a", "b"};
    appendNumber(names, 0);   // compiles; ArrayStoreException at runtime
}
```

The fix in review: take a `List<Object>` (invariant, compile-time safe) instead of `Object[]`, or make the parameter `String[]` if that's what it really is.

### TypeScript — `strictFunctionTypes` catching an unsound override

```typescript
// tsconfig: "strictFunctionTypes": true
class Animal {}
class Cat extends Animal { meow() {} }

// Standalone function-typed property: checked CONTRAVARIANTLY (sound)
interface Registry {
    onEvent: (a: Animal) => void;
}

const r: Registry = {
    // ERROR under strictFunctionTypes:
    //   Type '(c: Cat) => void' is not assignable to '(a: Animal) => void'
    onEvent: (c: Cat) => c.meow(),   // would receive a Dog and call meow() -> caught!
};
```

### TypeScript — the method-parameter loophole, made visible

```typescript
class Animal {}
class Cat extends Animal { meow() {} }

// METHOD form -> parameters stay BIVARIANT even with strictFunctionTypes
interface RegistryMethod {
    onEvent(a: Animal): void;
}

const r: RegistryMethod = {
    onEvent(c: Cat) { c.meow(); },   // NO error — bivariant method param (UNSOUND)
};
// r.onEvent(new Animal());  // at runtime: meow is not a function — silent type hole
```

Same intent, opposite safety — purely because one is a method and one is a function-typed property. Professionals prefer the function-typed-property form for callbacks.

### C# — variant interface vs unsafe array, side by side

```csharp
class Animal {}
class Cat : Animal {}

class Demo {
    static void Safe() {
        // Declaration-site variance on an interface: SOUND
        IEnumerable<Cat> cats = new List<Cat>();
        IEnumerable<Animal> animals = cats;   // covariant, no runtime risk
    }
    static void Unsafe() {
        Cat[] cats = new Cat[1];
        Animal[] animals = cats;              // covariant array (legacy)
        animals[0] = new Animal();            // ArrayTypeMismatchException at runtime
    }
}
```

### Kotlin — contravariant comparator and read-only covariance together

```kotlin
open class Animal(val weight: Int)
class Cat(weight: Int) : Animal(weight)

// Comparator<in T> is contravariant -> a Comparator<Animal> can sort Cats
fun sortCats(cats: MutableList<Cat>, cmp: Comparator<in Cat>) {
    cats.sortWith(cmp)
}

val byWeight: Comparator<Animal> = compareBy { it.weight }

fun main() {
    val cats = mutableListOf(Cat(5), Cat(2))
    sortCats(cats, byWeight)        // pass a broad Comparator<Animal> for a List<Cat>
    val readOnly: List<Animal> = cats   // Kotlin's read-only List<out T> is covariant: safe
}
```

---

## Coding Patterns

### Pattern 1: Replace covariant arrays with invariant collections at boundaries

```java
// Hazardous: void process(Object[] items)   // covariant, can ArrayStoreException
void process(List<Object> items) { items.add(42); }   // invariant, compile-time safe
```

### Pattern 2: Function-typed properties for sound TS callbacks

```typescript
// Prefer this (contravariant under strictFunctionTypes):
type Handler<T> = { handle: (x: T) => void };
// Over this (bivariant method param):
interface HandlerMethod<T> { handle(x: T): void }
```

### Pattern 3: Read-only covariant view over mutable internals

```csharp
class Shelter {
    private readonly List<Cat> _cats = new();
    public IReadOnlyList<Animal> Animals => _cats;   // covariant, safe — no Add exposed
}
```

### Pattern 4: PECS signature with a written rationale

```java
// src PRODUCES T (read) -> ? extends ; dest CONSUMES T (write) -> ? super
static <T> void drain(List<? extends T> src, List<? super T> dest) {
    for (T x : src) dest.add(x);
}
```

### Pattern 5: Contravariant comparator parameter

```kotlin
fun <T> topK(items: List<T>, k: Int, cmp: Comparator<in T>): List<T> =
    items.sortedWith(cmp).take(k)   // accepts a Comparator of any supertype of T
```

---

## Best Practices

- **Treat reference-type arrays as a known hazard.** Prefer invariant generic collections at API boundaries; reserve arrays for primitives or tight, locally-controlled code.
- **Enable `strictFunctionTypes` in every TypeScript project,** and write callbacks as function-typed properties to get the sound (contravariant) check.
- **Make data immutable when you want covariance.** Return read-only interfaces; covariance over immutable data is always sound.
- **Use PECS / `in`/`out` in public signatures, concrete types internally.** Flexibility belongs at the boundary.
- **In overrides, allow only covariant returns; reject parameter narrowing in review.** It's the only sound, portable override flexibility.
- **Never expose a mutable internal collection through a covariant view.** A `List<Cat>` returned as `List<? extends Animal>`-shaped read view is fine; returning it as something writable is the array bug reborn.
- **When you debug `ArrayStoreException`/`ArrayTypeMismatchException`/a silently-wrong TS callback, name the variance cause.** It's covariance-plus-mutation or a narrowed contravariant slot, every time.

---

## Edge Cases & Pitfalls

- **`Arrays.asList(...)` returns a fixed-size, array-backed list** that can still surface array-covariance surprises on `set`. Wrap in `new ArrayList<>(...)` when you need a true invariant list.
- **Generic varargs are arrays under the hood.** `static <T> List<T> of(T... items)` creates a covariant array — hence the `@SafeVarargs` annotation and the "unchecked generic array creation" warnings. The array hole leaks into generics through varargs.
- **TS structural typing makes the method/function distinction subtle.** A type literal `{ f(x: T): void }` is a method (bivariant); `{ f: (x: T) => void }` is a property (contravariant under strict). One character of syntax flips the safety.
- **`readonly` in TypeScript is shallow and erased.** `ReadonlyArray<T>` prevents writes at compile time but there's no runtime enforcement — a cast or `any` punches through. It buys soundness only if you don't cheat.
- **C# arrays of value types are *not* covariant** (`int[]` is not `object[]`), so the hole is reference-types-only. Don't over-generalize the rule.
- **Covariant return + generics can require explicit bridge handling in reflection/serialization frameworks.** The synthetic bridge method can confuse annotation processors that don't expect duplicate method signatures.
- **Kotlin `Array<out T>` is read-only-projected**, so you can't pass it where a writable array is needed — people hit this porting Java array code and assume `out` should still allow writes. It can't.
- **`List<*>` (star projection) / `IEnumerable` without type args** give you a safe out-projected read view, *not* `List<Any?>`; trying to add anything but `null` fails.

---

## Apply it

1. Define the user or business outcome that **Variance** should improve.
2. Assign one owner for code, contracts, operations, and incidents.
3. Split delivery into reversible increments that produce evidence early.
4. Publish responsibilities, escalation paths, and compatibility windows.
5. Stop or expand only when the agreed measures support that decision.

## Verify your work

- Each increment has an owner, rollback path, and observable exit condition.
- Adoption, reliability, delivery time, and coordination cost are measured.
- Incident and migration exercises prove that responsibility is executable.
- The old path is removed only after telemetry proves it is unused.

## Review questions

- Which measurable outcome justifies investing in Variance?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
