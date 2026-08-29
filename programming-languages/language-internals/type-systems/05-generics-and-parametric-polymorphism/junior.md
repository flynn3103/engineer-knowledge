# Generics & Parametric Polymorphism — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Generics & Parametric Polymorphism** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Problem Generics Solve: Three Bad Options

Before generics, if you wanted a "stack of things," you had three choices, all bad:

**Option A — One stack per type (copy-paste).**

```text
IntStack    { push(int),    pop() -> int    }
StringStack { push(String), pop() -> String }
UserStack   { push(User),   pop() -> User   }
```

Identical code, duplicated N times. A bug fixed in one is still present in the others. Adding a type means copy-pasting again.

**Option B — One stack of `Object` (the "top type").**

```text
ObjectStack { push(Object), pop() -> Object }
```

One implementation — but now every `pop()` returns `Object`, and *you* must cast it back:

```text
String s = (String) stack.pop();   // and if it was actually a User? → crash at runtime
```

You lost type safety. The compiler can no longer stop you from pushing a `User` and popping it as a `String`. The mistake surfaces as a runtime `ClassCastException`, often far from where you made it.

**Option C — Generics.**

```text
Stack<T> { push(T), pop() -> T }
```

One implementation, *and* full type safety. `Stack<String>` only accepts `String`s and `pop()` returns a `String` — checked by the compiler, no cast, no runtime surprise. **This is the whole point.** Generics give you the reuse of Option B with the safety of Option A.

### 2. `<T>` Is Just a Parameter — for Types

You already understand value parameters. In `add(x, y)`, `x` and `y` are placeholders filled in at call time. A type parameter is the *exact same idea*, one level up:

```text
function add(x, y)        ← x, y are VALUE parameters, filled with values
function first<T>(...)     ← T is a TYPE parameter, filled with a type
```

When you call `first<String>(list)` (or just `first(list)` and let inference figure out `T = String`), you are passing `String` as the type argument, exactly as you pass `5` as a value argument. The naming convention `T` is just convention — it stands for "Type." You'll also see `E` (Element), `K`/`V` (Key/Value), `R` (Return). They're all type parameters.

### 3. Uniform Behavior: The Defining Property

Here is the rule that makes parametric polymorphism *parametric*:

> A fully parametric function **does the same thing for every type**. It cannot inspect, branch on, or special-case the type it was given.

Consider `first<T>(items: List<T>) -> T`. Inside the body, `T` is unknown. The function can:

- hold a `T` (store it in a variable),
- move a `T` around (return it, pass it on),
- put `T`s in a `List<T>`.

It *cannot*:

- call `.toUpperCase()` on a `T` (maybe `T` is `int` — no such method),
- compare two `T`s with `<` (maybe `T` is `User` — no ordering),
- create a `new T()` (it doesn't know `T`'s constructor),
- ask "is `T` an `int`?" and behave differently.

This is not a bug. It's the *guarantee*. Because `first<T>` can't touch the contents, you *know* it returns one of the elements unchanged — it can't have transformed your `User` into something else. The type signature alone tells you a lot about what the code does. (At the senior level this becomes "theorems for free": a function of type `T -> T` with no constraints *must* be the identity function — there's literally nothing else it can do.)

### 4. Generic Type vs. Generic Function

Two related but distinct things:

- A **generic type** is parameterized: `List<T>`, `Map<K,V>`, `Optional<T>`. You instantiate it (`List<String>`) and it becomes a concrete type you can make values of.
- A **generic function/method** is parameterized: `first<T>`, `swap<T>`, `map<A,B>`. You call it (often with inference) and the type parameter is resolved per call.

A generic *method* can live inside a non-generic class, and a generic *type* can have non-generic methods. They're orthogonal:

```text
class Box<T> {            // generic TYPE, parameter T
    value: T
    get(): T { ... }      // non-generic method (uses the class's T)
    <U> map(f): Box<U>    // generic METHOD, its own parameter U
}
```

### 5. Type Inference: You Rarely Write `<T>` Explicitly

Modern languages infer the type argument from the values you pass. You write:

```text
let xs = listOf(1, 2, 3)     // compiler infers List<int>
let x  = first(xs)            // compiler infers T = int, x has type int
```

You *can* write it explicitly (`first<int>(xs)`) when inference fails or you want to be clear, but usually you don't. This is why generics feel lightweight in practice — the `<T>` is mostly invisible at the call site.

### 6. A First Taste of Bounds (Constraints)

Sometimes "any type at all" is *too* free. If you want `max<T>(a, b)`, you need to *compare* `a` and `b` — but an unbounded `T` can't be compared. So you **bound** the type parameter: "T must be a type that supports comparison."

```text
max<T: Comparable>(a: T, b: T) -> T { return a > b ? a : b }
```

Now `T` can be any *comparable* type, and inside the body you're allowed to use `>`. This is **bounded polymorphism**, and it sits on the boundary between parametric polymorphism (uniform) and ad-hoc polymorphism (per-type behavior, via the comparison operation). Bounds get a full treatment in the dedicated bounded-polymorphism topic; here, just know that an *unbounded* `T` can do almost nothing, and a *bounded* `T` can do exactly what the bound permits.

---

## Code Examples

We solve the same tiny problems in each language: a generic `Box<T>` container and a generic `first` function. Watch how similar they look — the concept transfers everywhere even though the syntax differs.

### Java

```java
// Generic class
class Box<T> {
    private final T value;
    Box(T value) { this.value = value; }
    T get() { return value; }
}

// Generic method (the <T> before the return type declares the parameter)
static <T> T first(java.util.List<T> items) {
    return items.get(0);
}

public class Demo {
    public static void main(String[] args) {
        Box<String> b = new Box<>("hello");   // T = String, inferred via <>
        String s = b.get();                     // no cast needed — returns String

        var nums = java.util.List.of(10, 20, 30);
        int n = first(nums);                    // T inferred as Integer
        System.out.println(s + " " + n);
    }
}
```

The `<T>` on `class Box<T>` and on `static <T> T first(...)` declares the parameter. `Box<String>` instantiates it. No casts anywhere — that's the win over an `Object`-based box.

### C#

```csharp
class Box<T> {
    private readonly T value;
    public Box(T value) { this.value = value; }
    public T Get() => value;
}

static T First<T>(System.Collections.Generic.List<T> items) => items[0];

class Demo {
    static void Main() {
        var b = new Box<string>("hello");
        string s = b.Get();
        var nums = new System.Collections.Generic.List<int> { 10, 20, 30 };
        int n = First(nums);     // T inferred as int — and note: int is NOT boxed in C#
        System.Console.WriteLine($"{s} {n}");
    }
}
```

C# looks like Java but has one deep difference we'll meet later: `List<int>` stores real `int`s with no boxing, because C# generics are *reified* (the runtime actually knows `T = int`). Hold that thought.

### Go (generics, Go 1.18+)

```go
package main

import "fmt"

// Generic type
type Box[T any] struct {
	value T
}

func (b Box[T]) Get() T { return b.value }

// Generic function. `any` means "no constraint" (unbounded T).
func FirstT any T {
	return items[0]
}

func main() {
	b := Box[string]{value: "hello"}
	s := b.Get()
	nums := []int{10, 20, 30}
	n := First(nums) // T inferred as int
	fmt.Println(s, n)
}
```

Go uses square brackets `[T any]`. Before Go 1.18, you'd have written `First(items []interface{}) interface{}` and cast the result — exactly Option B above, with all its dangers. Generics removed that pain.

### TypeScript

```typescript
class Box<T> {
  constructor(private readonly value: T) {}
  get(): T { return this.value; }
}

function first<T>(items: T[]): T {
  return items[0];
}

const b = new Box<string>("hello");
const s: string = b.get();
const nums = [10, 20, 30];
const n: number = first(nums); // T inferred as number
console.log(s, n);
```

TypeScript's generics are *compile-time only* — they vanish entirely when compiled to JavaScript (full erasure). They exist purely to help the type checker; at runtime there is no `T` at all.

### Rust

```rust
struct Box2<T> {
    value: T,
}

impl<T> Box2<T> {
    fn get(self) -> T { self.value }
}

fn first<T: Clone>(items: &[T]) -> T {
    items[0].clone()
}

fn main() {
    let b = Box2 { value: String::from("hello") };
    let s = b.get();
    let nums = vec![10, 20, 30];
    let n = first(&nums);  // T inferred as i32
    println!("{} {}", s, n);
}
```

Rust generates a *specialized copy* of `Box2` and `first` for each concrete type (monomorphization) — so `first::<i32>` and `first::<String>` are separate compiled functions, each as fast as if you'd hand-written it. (`Clone` is a bound; an unbounded `T` couldn't be copied out of the slice.)

### C++ (templates)

```cpp
#include <iostream>
#include <vector>

template <typename T>
struct Box {
    T value;
    T get() const { return value; }
};

template <typename T>
T first(const std::vector<T>& items) {
    return items[0];
}

int main() {
    Box<std::string> b{"hello"};
    auto s = b.get();
    std::vector<int> nums{10, 20, 30};
    int n = first(nums);          // T deduced as int
    std::cout << s << " " << n << "\n";
}
```

C++ templates also stamp out a specialized copy per type (like Rust). The compiler generates `Box<int>`, `Box<std::string>`, `first<int>`, etc. — each fully specialized and inlinable.

> **Takeaway:** Six languages, six syntaxes (`<T>`, `[T any]`, `template<typename T>`), but **one idea**: write the code once, leave the type as a parameter, let the compiler fill it in. Whether the compiler stamps out copies (Rust, C++) or shares one implementation (Java, TS, early Go) is an implementation detail you'll study next — but the *programming model* is the same everywhere.

---

## Coding Patterns

### Pattern 1: The Generic Container

The bread-and-butter pattern. Hold the type parameter as a field; expose typed operations.

```java
class Stack<T> {
    private final java.util.List<T> items = new java.util.ArrayList<>();
    void push(T item) { items.add(item); }
    T pop() { return items.remove(items.size() - 1); }
    boolean isEmpty() { return items.isEmpty(); }
}
```

`Stack<String>` and `Stack<Integer>` share this one definition, each fully type-safe.

### Pattern 2: The Identity / Pass-Through Function

When you only move a value, not inspect it, leave `T` unbounded.

```typescript
function identity<T>(x: T): T { return x; }
function pair<A, B>(a: A, b: B): [A, B] { return [a, b]; }
```

These are maximally reusable *because* they do nothing type-specific.

### Pattern 3: Prefer a Type Parameter Over `Object`/`any`

Whenever you're about to write `Object` or `any` as a parameter or return type, ask: "could this be `<T>` instead?" Usually yes, and it's strictly better.

```text
// Before (loses type, needs cast):
Object firstOf(List items)           →  String s = (String) firstOf(list);

// After (keeps type, no cast):
<T> T firstOf(List<T> items)         →  String s = firstOf(list);
```

### Pattern 4: Let Inference Work; Annotate Only When Needed

Write `first(xs)`, not `first<String>(xs)`, unless the compiler can't infer it (e.g. an empty collection where there's nothing to infer from). Over-annotating is noise.

### Pattern 5: Name Parameters Meaningfully Past the Basics

`<T>` is fine for a single all-purpose type. For maps and richer types, prefer `<K, V>`, `<Key, Value>`, `<Element>` — names that say what the parameter *is*.

---

## Best Practices

- **Reach for generics before `Object`/`any`/`interface{}`.** The cast-everywhere style is the problem generics solve. If you're casting, you probably wanted a type parameter.
- **Keep unbounded `T` truly unbounded.** If your function works for *any* type, don't accidentally constrain it. The fewer the requirements on `T`, the more reusable the code.
- **Add a bound only when you actually use a capability.** Need to compare? Bound to `Comparable`. Need to print? Bound to whatever the language requires. Don't add bounds "just in case" — they restrict callers.
- **Lean on type inference.** Specify type arguments explicitly only when inference fails or clarity demands it.
- **Use conventional parameter names.** `T`, `E`, `K`, `V`, `R` — your readers know these. Reserve descriptive names (`<Entity>`) for when it genuinely helps.
- **Don't try to inspect or construct `T` at the junior level.** `new T()`, `T.class`, `instanceof T` either don't compile or have surprising caveats (especially under erasure — see pitfalls). If you need that, you've hit an advanced corner; ask for help or use a different design.
- **Make containers generic, behaviors polymorphic.** "A list *of* X" → generic. "An X that *behaves* like a shape" → interface/subtype. Don't mix them up.

---

## Edge Cases & Pitfalls

- **Casting instead of parameterizing.** The classic anti-pattern: taking `Object` and casting back. It compiles, then throws `ClassCastException` at runtime when the actual type isn't what you assumed. Generics move that error to *compile time*, where it belongs.
- **Mixing raw and generic types (Java).** Using a `List` (raw) where a `List<String>` is expected disables the type checks and produces "unchecked" warnings — and re-opens the door to runtime `ClassCastException`. Never use raw types in new code.
- **Expecting `T` to have methods it might not.** `T.toString()` is usually fine (everything has it in many languages), but `T.compareTo`, `T < T`, `T()` (construction) require a *bound* or won't compile. The compiler is protecting you: an unbounded `T` could be *any* type.
- **`new T()` doesn't work in many languages.** In Java (and others using erasure), the runtime doesn't know what `T` is, so it can't construct one. Workarounds (factories, passing a `Class<T>`) exist but are advanced. In C++/Rust/C# the story differs — another preview of the implementation differences ahead.
- **Boxing surprises in Java/erased systems.** `List<Integer>` stores *boxed* `Integer` objects on the heap, not raw `int`s. For large numeric data this is a real performance and memory cost. C#/Rust/C++ don't pay it for value types. (Detail in `middle.md`/`professional.md`.)
- **Assuming `<T>` exists at runtime.** In Java, TypeScript, and Go's design lineage, the type argument is partly or fully *erased* — at runtime you often *can't* ask "what was `T`?" `instanceof List<String>` is illegal in Java for this reason. In C# you *can* (`typeof(T)`), because its generics are reified. Don't assume one model.
- **Over-genericizing.** Not everything needs `<T>`. If a function only ever takes a `User`, making it `<T>` adds noise and obscures intent. Generics are for code that's genuinely type-agnostic.
- **Confusing "generic" with "inheritance."** `Box<Animal>` is *not* a supertype of `Box<Cat>` in most languages — even though `Animal` is a supertype of `Cat`. This surprises everyone at first. The reason (variance) is its own topic; for now, just know `List<Cat>` is *not* automatically a `List<Animal>`, and trying to treat it as one won't compile.

---

## Apply it

1. Choose one small, known input for **Generics & Parametric Polymorphism**.
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

- What problem does Generics & Parametric Polymorphism solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
