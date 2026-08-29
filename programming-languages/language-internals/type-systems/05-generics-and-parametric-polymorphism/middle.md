# Generics & Parametric Polymorphism — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Generics & Parametric Polymorphism** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Four Kinds of Polymorphism

"Polymorphism" is overloaded; pinning down the four classic kinds (Strachey/Cardelli taxonomy) makes parametric polymorphism precise by contrast:

| Kind | One sentence | Behavior across types | Examples |
|------|--------------|----------------------|----------|
| **Parametric** | One implementation, parameterized by a type, working uniformly for all types. | **Identical** | `List<T>`, `identity<T>`, `map` |
| **Ad-hoc** | Different implementations selected by type — overloading and typeclasses. | **Varies** | `print(int)` vs `print(String)`; `Show`/`Ord` typeclasses; trait methods |
| **Subtype (inclusion)** | One interface, runtime picks the implementation by the object's dynamic type. | **Varies (via override)** | `Shape.area()` overridden by `Circle`, `Square` |
| **Coercion** | Implicit type conversion lets one operation accept several types. | n/a (conversion) | `3 + 4.0` promoting `int` to `double` |

The crucial axis is **does behavior vary by type?** Parametric says *no — same behavior, always*. The other three say *yes — different behavior per type*. This is why parametric polymorphism is uniquely "honest": the type signature alone tells you the function can't be doing anything type-specific. (Bounded generics like `<T: Comparable>` are *parametric polymorphism that calls into ad-hoc polymorphism* for the bounded operation — the structure is uniform, but the comparison is type-specific. That blend is exactly how typeclass/trait dictionaries work.)

### 2. The Central Fork: How Do You Compile `Stack<T>`?

The source is one definition. The machine code is the open question. Two extremes:

**Monomorphization (specialize per type).** For every concrete `Stack<X>` your program uses, the compiler emits a *complete, separate* `Stack<X>` — `Stack<int>`, `Stack<String>`, `Stack<User>` are three independent types in the binary, each with its own machine code. Inside `Stack<int>`, the element really is an `int` stored inline; `push` is `int`-specific code that the optimizer can inline and vectorize.

- ✅ **Zero-cost:** as fast as hand-written specialized code. No boxing. Full inlining and optimization per type.
- ❌ **Code bloat:** N type arguments → up to N copies of the code. Binary grows.
- ❌ **Slow compiles:** the compiler does the work N times, and the optimizer runs on each copy.
- ❌ **No code sharing across instantiations:** `Stack<int>` and `Stack<long>` don't share a single byte of generated code, even though the source is identical.

**Type erasure (share one implementation).** The compiler type-checks using the parameters, then *erases* them, leaving one implementation that operates on a uniform representation — in Java, every `T` becomes `Object` (a reference). There's exactly one `Stack` class; `Stack<String>` and `Stack<Integer>` are the *same* class at runtime, differing only in compile-time-checked source.

- ✅ **Small code:** one implementation regardless of how many type arguments.
- ✅ **Fast compiles:** compile the generic once.
- ❌ **Boxing & indirection:** value types must be boxed to be referenced uniformly (`List<Integer>` holds heap `Integer`s, not `int`s). Pointer chasing, cache misses, GC pressure.
- ❌ **Runtime can't see `T`:** the type argument is gone. `new T()`, `T.class`, `instanceof List<String>` are impossible or meaningless. You need *type tokens* to recover what was erased.

Neither is "better" in the abstract — they trade compile time and binary size against runtime speed and runtime type information. The rest is detail.

### 3. Monomorphization in Practice: C++ and Rust

When you write `Vec<i32>` and `Vec<String>` in Rust, the compiler generates two distinct, fully-specialized types. `vec.push(x)` for `Vec<i32>` compiles to code that moves 4 bytes inline; for `Vec<String>` it moves a 24-byte string struct. There is no `Object`, no boxing, no dynamic dispatch — `T` is *known* at compile time for each copy, so the optimizer treats the generic code exactly as if you'd written the concrete version. This is what "**generics are a zero-cost abstraction**" means in Rust and C++.

Consequences you can observe:

- **`std::mem::size_of::<Vec<i32>>()` and `size_of::<Vec<String>>()` differ** — they're genuinely different types.
- **Inlining and specialization fire fully.** A generic `min<T: Ord>` over `i32` compiles to the same instructions as a hand-written `i32` min.
- **Binary size grows with the number of instantiations.** A heavily generic codebase (or a heavy generic dependency like `serde`) can produce large binaries and long compile times — the well-known cost.
- **C++ templates are *lazily* instantiated:** a member function of a class template is only compiled if actually called, which is both a feature (don't pay for what you don't use) and a source of "errors only when you instantiate" surprises.

### 4. Type Erasure in Practice: Java (and Haskell, TypeScript)

In Java, `List<String>` and `List<Integer>` are the **same class** at runtime — `List`. The compiler inserts casts for you and checks them at compile time, but the bytecode operates on `Object`. This design was chosen for **backward compatibility**: generics were added in Java 5, and erasure let new generic code interoperate with the vast body of pre-generics (`Object`-based) code and bytecode. The price:

- **Boxing of primitives.** `List<Integer>` cannot hold `int` (a primitive) — it holds boxed `Integer` objects on the heap. Iterating a `List<Integer>` summing values chases pointers and pressures the GC; an `int[]` is dramatically faster. (Project Valhalla aims to fix this with value classes / specialized generics.)
- **`new T()` is illegal.** At runtime there's no `T` to construct. Workaround: pass a `Class<T>` factory or a `Supplier<T>`.
- **`instanceof List<String>` is illegal**; only `instanceof List` (the raw type) is allowed, because the `<String>` doesn't exist at runtime.
- **You can't overload on erased generic parameters.** `void f(List<String>)` and `void f(List<Integer>)` have the *same* erased signature `f(List)` — a compile error ("same erasure").
- **Unchecked warnings & heap pollution.** Casts the compiler can't verify (e.g. `(List<String>) someRawList`) produce "unchecked" warnings and can let the wrong type sneak in, deferring a `ClassCastException` to a surprising later line.

Haskell and other typeclass languages also erase types but recover per-type behavior differently — see the dictionary section below.

### 5. Reified Generics: C#

C# took the harder, more expensive path and it shows. The CLR (the .NET runtime) **knows the type arguments at runtime**. Practical effects:

- **No boxing for value types.** `List<int>` stores real `int`s inline. The JIT generates a specialized version for each *value-type* instantiation (like monomorphization), while *reference-type* instantiations share one code body (the references are all the same size). This is "specialize value types, share reference types" — a pragmatic hybrid baked into the runtime.
- **`typeof(T)` works.** Inside `Foo<T>` you can ask for `T`'s actual type at runtime and reflect on it.
- **`new T()` works** (with the `where T : new()` constraint), because the runtime can find `T`'s constructor.
- **`x is List<string>` works** — runtime type checks on generic instantiations succeed because the runtime carries the type arguments.

The cost is a heavier runtime that must carry and use this metadata, and JIT-time specialization for each value-type instantiation. C# decided the runtime-type-information and no-boxing benefits were worth it.

### 6. Go's Hybrid: GC-Shape Stenciling + Dictionaries

Go (1.18+) deliberately picked neither extreme. Full monomorphization risked binary bloat and slow builds (Go prizes fast compilation); full boxing (the old `interface{}` style) was the very thing generics were meant to escape. The compromise:

- **Stencil per GC shape, not per type.** Go groups types by their **GC shape** — essentially their memory layout from the garbage collector's view. All pointer-shaped types (any `*T`, any interface, any string-ish pointer) often share one generated copy; distinct value layouts get their own. So `f[*int]`, `f[*User]`, `f[*Foo]` may all share a single stencil, while `f[int]` and `f[float64]` might each get one.
- **Pass a dictionary.** Because one stencil serves many types, the shared code needs type-specific information (the actual type, method implementations, how to make a new one). Go passes a hidden **dictionary** argument carrying this. The shared body looks up what it needs in the dictionary at runtime.

The result sits between the extremes: less code than full monomorphization, less boxing/indirection than full erasure, but *some* runtime indirection through the dictionary (so not always as fast as Rust/C++, and the subject of ongoing optimization). It's a pragmatic engineering choice tuned to Go's priorities (fast builds, simple runtime, good-enough performance).

### 7. Dictionaries Are the Deep Idea Behind Bounded Generics

Notice a pattern: Haskell typeclasses, Go's hybrid, and (conceptually) bounded generics everywhere are implemented by **passing a dictionary of operations**. When you write `max<T: Comparable>(a, b)`, the bound `Comparable` means "there exists a comparison operation for `T`." The compiler must get that operation *to* the generic body. Two ways:

- **Monomorphizing languages** bake the right `compare` *into each specialized copy* — `max<i32>` directly calls `i32`'s compare, inlined, zero-cost.
- **Erasing/dictionary languages** pass a `compare` function (in a dictionary) as a hidden argument — one shared `max` body, called with different dictionaries.

This is *exactly* where parametric polymorphism (uniform structure) meets ad-hoc polymorphism (per-type operation). The bound is the bridge; the dictionary is the runtime mechanism. Keeping this in mind demystifies traits, typeclasses, interfaces-with-methods, and bounded generics — they're all "uniform code + a per-type operations table."

---

## Code Examples

### Java erasure: same-erasure overload is a compile error

```java
import java.util.List;

class ErasureClash {
    // void process(List<String> xs) { }   // <-- if both present...
    // void process(List<Integer> xs) { }  //     COMPILE ERROR: "name clash:
    //                                      //     both have the same erasure process(List)"
}
```

After erasure, both methods are `process(List)`. The JVM can't tell them apart, so the compiler forbids it. This is a direct, observable consequence of erasure that monomorphizing languages don't have.

### Java erasure: `new T()` is illegal; use a factory or `Class<T>`

```java
import java.util.function.Supplier;

class Factory<T> {
    // T make() { return new T(); }   // <-- ILLEGAL: T is erased, no constructor known

    private final Supplier<T> ctor;
    Factory(Supplier<T> ctor) { this.ctor = ctor; }
    T make() { return ctor.get(); }    // workaround: caller supplies the constructor
}

// Usage: new Factory<>(StringBuilder::new).make();
```

### Java erasure: `instanceof` on a parameterized type is illegal

```java
import java.util.List;

class InstanceOfDemo {
    static boolean test(Object o) {
        // return o instanceof List<String>;  // <-- ILLEGAL: <String> not at runtime
        return o instanceof List;              // only the raw check is allowed
    }
}
```

### Java erasure: the super-type-token trick to *recover* type info

```java
// Because erasure throws away T, a generic CLASS can't see its own T at runtime.
// But the type argument of a SUPERCLASS is retained in class metadata (it's part
// of the .class file's signature). Subclassing an abstract generic captures it:
import java.lang.reflect.ParameterizedType;
import java.lang.reflect.Type;

abstract class TypeRef<T> {
    final Type type;
    TypeRef() {
        ParameterizedType pt =
            (ParameterizedType) getClass().getGenericSuperclass();
        this.type = pt.getActualTypeArguments()[0];   // recovers T
    }
}

// Usage captures String via an anonymous subclass:
//   TypeRef<String> ref = new TypeRef<String>() {};
//   ref.type  ->  class java.lang.String
```

This is how Jackson's `TypeReference` and Guice's `TypeLiteral` work — a clever workaround for what erasure removed. The fact that this trick is *needed at all* is the clearest signal that Java erases.

### C# reified: `typeof(T)` and `new T()` just work

```csharp
class Reified<T> where T : new() {
    public string Name() => typeof(T).Name;   // runtime knows T
    public T Make() => new T();                // runtime can construct T
}

// Usage:
//   var r = new Reified<System.Text.StringBuilder>();
//   r.Name();  // "StringBuilder"  -- impossible in Java without a token
```

The same operations that are *illegal in Java* are *trivial in C#* — because C# reifies and Java erases. This contrast is the single best way to feel the difference.

### Boxing, made visible (Java vs. C#/Rust intuition)

```java
import java.util.ArrayList;
import java.util.List;

class BoxingCost {
    static long sumBoxed(List<Integer> xs) {   // each element is a heap Integer
        long total = 0;
        for (Integer x : xs) total += x;        // unboxing on every iteration
        return total;
    }
    static long sumPrimitive(int[] xs) {        // contiguous ints, no boxing
        long total = 0;
        for (int x : xs) total += x;
        return total;
    }
    // For large N, sumPrimitive is several times faster: no heap Integers,
    // no pointer chasing, better cache behavior. The List<Integer> pays the
    // erasure-boxing tax; C#'s List<int> and Rust's Vec<i32> do not.
}
```

### Go hybrid: one source, shape-based stencils + a dictionary (conceptual)

```go
package main

import "fmt"

// One generic source.
func MaxT int | float64 | string T {
	if a > b {
		return a
	}
	return b
}

func main() {
	// The compiler may emit a stencil per GC shape and thread a hidden
	// dictionary carrying the concrete type's operations into the shared body.
	// You don't see the dictionary; it's how one body serves multiple types
	// without full per-type monomorphization.
	fmt.Println(Max(3, 7))         // int
	fmt.Println(Max(2.5, 1.5))     // float64
	fmt.Println(Max("a", "b"))     // string
}
```

### Before/after Go generics: the whole reason they exist

```go
// BEFORE generics (Go < 1.18): interface{} + type assertion = manual, unsafe erasure.
func FirstAny(items []interface{}) interface{} {
	return items[0]
}
// Caller must assert and risk a runtime panic:
//   s := FirstAny(xs).(string)   // panics if it wasn't a string

// AFTER generics: type-safe, no assertion, no panic.
func FirstT any T {
	return items[0]
}
// Caller gets the right type, checked at compile time:
//   s := First(strs)   // s is string, guaranteed
```

This is *exactly* the junior-level "stop casting `Object`" lesson, realized at the language level: `interface{}` + assertion was hand-rolled erasure with all its dangers; `[T any]` is the safe parametric version.

---

## Coding Patterns

### Pattern 1: Pass a Type Token Under Erasure

When an erased language needs `T`'s identity at runtime, thread it explicitly:

```java
<T> T parse(String json, Class<T> type) { /* uses type.getName(), etc. */ }
// or the super-type-token for parameterized targets: new TypeReference<List<User>>(){}
```

Design the API to take the token; don't fight erasure.

### Pattern 2: Box at the Boundary, Specialize in the Hot Path (erased langs)

Keep the friendly generic API (`List<Integer>`) at module edges, but drop to primitives (`int[]`, `IntStream`) inside performance-critical inner loops. Convert once, compute fast.

### Pattern 3: Erase a Monomorphized Generic to Cap Bloat

In Rust/C++, when a generic is instantiated for *many* types but the body is large and not performance-critical, route through a *single* dynamically-dispatched copy to share code:

```rust
// Monomorphized: one copy per T -> bloat if many Ts and big body.
fn log_all<T: std::fmt::Display>(xs: &[T]) { for x in xs { println!("{}", x); } }

// Erased via trait objects: ONE copy, dynamic dispatch -> smaller binary.
fn log_all_dyn(xs: &[&dyn std::fmt::Display]) { for x in xs { println!("{}", x); } }
```

This is *deliberately choosing erasure* for code-size where the runtime cost is acceptable — a key senior/professional lever.

### Pattern 4: Prefer Constraints/Concepts Over Naked Templates (C++)

Use C++20 `concepts` (or older SFINAE) to constrain template parameters so errors are reported at the call site with a readable message, not as a 200-line instantiation backtrace.

```cpp
template <typename T>
concept Addable = requires(T a, T b) { a + b; };

template <Addable T>          // clear constraint at the signature
T add(T a, T b) { return a + b; }
```

---

## Best Practices

- **Know which strategy your language uses** before reasoning about generics performance or runtime-type capabilities. It's the master fact.
- **In erased languages, treat value-type generics as a performance smell in hot paths.** `List<Integer>` is fine for cold code, costly in tight loops.
- **Don't rely on runtime type info that erasure removed.** No `new T()`, no `instanceof List<String>` in Java. Thread tokens explicitly instead, and centralize them.
- **In monomorphizing languages, watch instantiation count.** A generic used with dozens of types and a large body multiplies binary size and compile time. Measure; erase behind a `dyn`/virtual boundary when it pays.
- **Use named constraints (C++ concepts, Rust trait bounds, C# `where`)** to get clear errors and self-documenting signatures, instead of unconstrained templates that fail deep inside instantiation.
- **Never silence unchecked-cast warnings without proof** (Java). They mark exactly the spots where erasure could let a wrong type through and surface a delayed `ClassCastException`.
- **When you need both no-boxing and runtime type info, recognize you want C#-style reification** — and that other languages make you pick one or work around the other.

---

## Edge Cases & Pitfalls

- **Same-erasure overloading (Java).** Two methods differing only in generic type arguments share an erased signature → compile error. Rename or redesign.
- **`List<String>[]` arrays (Java).** Generic array creation is forbidden (`new List<String>[10]` won't compile) because arrays are *reified and covariant* while generics are *erased and invariant* — combining them would let a stored wrong type escape detection. Use `List<List<String>>` instead.
- **Unchecked warnings = future `ClassCastException`.** An erased cast the compiler can't verify can pollute a collection with the wrong type; the crash appears later, at the *read* site, far from the cause. Treat these warnings as real.
- **Raw types re-open the hole.** Passing a `List` (raw) where `List<String>` is wanted disables checks and is the classic path to a runtime `ClassCastException` through "heap pollution."
- **C++ template error walls.** A constraint violation deep in instantiation can produce pages of errors pointing at library internals, not your bug. Mitigate with `concepts`/`static_assert`. (C++20 concepts dramatically improve this.)
- **Monomorphization bloat is silent.** A small generic used with many types, or pulled in transitively by a dependency, can quietly balloon binary size and compile time. It won't error — you just notice a huge artifact and slow builds.
- **Go's dictionary indirection isn't free.** Go generics can be *slower* than you'd expect from a "zero-cost" mental model imported from Rust; the shared-stencil-plus-dictionary design trades some speed for code size and build time. Benchmark; don't assume.
- **Boxing hides in `Object`-bounded or interface-bounded Java generics.** A `<T>` that gets autoboxed (`Integer`) or routed through an interface can allocate where you didn't expect. Profilers reveal it; reasoning about erasure predicts it.
- **Reflection sees erased types as raw (Java).** At runtime, `someList.getClass()` is just `ArrayList`, not `ArrayList<String>` — generic type arguments of *instances* are gone (only certain *declaration sites*, like superclass parameters or field/method signatures, retain them in metadata).

---

## Apply it

1. Find a real component where **Generics & Parametric Polymorphism** affects an interface or dependency.
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

- Which boundary is most affected by Generics & Parametric Polymorphism?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
