# What Is a Type — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **What Is a Type** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Static Type: Attached to the Expression

The **static type** is a property of a *piece of program text* — a variable, a literal, a function call, any expression. The compiler computes it without running anything, by following the language's rules:

```java
int n = readInt();        // static type of n is int
String s = "hello";       // static type of s is String
List<User> users = ...;   // static type is List<User>
Animal a = new Dog();     // static type of a is Animal (even though it's a Dog)
```

The static type is the compiler's *conservative knowledge*: it's what the compiler can prove is true about that expression for *every possible run*. That last line is the key example — the compiler only knows `a` is *some* `Animal`. It deliberately forgets that it's a `Dog`, because in general it can't track which subtype flows where.

Crucially, **operations are checked against the static type.** You can call `a.eat()` (every `Animal` can eat), but you cannot call `a.bark()` (not every `Animal` barks) even though `a` happens to be a `Dog` right now. The static type, not the runtime reality, governs what you're allowed to write.

### 2. Dynamic Type: Attached to the Value

The **dynamic type** is a property of an actual *value* at *run time*. The `Dog` object that `a` points to carries — physically, in memory, in dynamically typed and object-oriented languages — a tag saying "I am a Dog." This tag is what makes virtual method dispatch, `instanceof`, `isinstance`, and reflection work.

```java
Animal a = new Dog();
// static type of a:  Animal
// dynamic type of a: Dog
System.out.println(a instanceof Dog); // true — asks the runtime tag
a.makeSound();                         // dispatches on the DYNAMIC type → Dog.makeSound()
```

Note the split in that last line: **what you're allowed to call** is decided by the static type (`Animal` must declare `makeSound`), but **which implementation runs** is decided by the dynamic type (`Dog`'s override). This is the entire mechanism of polymorphism, and it only makes sense once you separate the two notions of type.

### 3. The Static/Dynamic Relationship

In a sound statically typed language with subtyping, there's an invariant:

> The dynamic type of a value is always the static type of its expression **or a subtype of it.**

`Animal a` may hold an `Animal`, `Dog`, or `Cat` — never a `String`. This is exactly *why* static checking is safe: the compiler proves a bound (`a` is at most an `Animal`), and the runtime can only ever do better (a more specific subtype), never worse. When you **downcast** (`Dog d = (Dog) a;`), you're asking the runtime to *verify* a guess the static type couldn't confirm — and it can fail (`ClassCastException`) precisely because the static type was a loose upper bound.

### 4. What "Type Checking" Actually Does

Type checking is the process of walking the program and, for each operation, asking: *do the static types of the operands support this operation?* For `x + y`, it asks "is there a `+` defined for these two static types?" For `f(a, b)`, it asks "do `a` and `b`'s static types match `f`'s declared parameter types?" For `obj.method()`, "does `obj`'s static type declare `method`?"

A **static type checker** does all of this at compile time and rejects the program if any check fails — the error appears before the program ever runs. A **dynamic type checker** (a dynamically typed language's runtime) does the same checks but *lazily*, at the moment each operation executes — so `x + y` is checked only when that line actually runs, and only for the values that actually reach it.

The trade-off is stark and worth internalizing: static checking proves the *absence* of type errors across *all* runs but requires the program to satisfy the checker; dynamic checking catches type errors only on the paths and inputs you actually exercise, but never blocks you from running.

### 5. Type Inference: Types You Didn't Write

A statically typed language does not require you to *write* every type. **Type inference** lets the compiler reconstruct them:

```go
x := 42            // Go infers x is int
y := "hello"       // y is string
m := map[string]int{}  // m is map[string]int
```

```rust
let v = vec![1, 2, 3];   // Rust infers Vec<i32>
let n = v.len();          // n is usize
```

Inference ranges from local (Go, C++ `auto`, Java `var` — infer from the right-hand side) to whole-program (Haskell, ML — infer a function's types from how it's used, via the Hindley–Milner algorithm). The important point: **inferred and annotated types are equally static.** Inference is about *who wrote the type down*, not about *when it's known*. The type still exists at compile time; the compiler just figured it out instead of you typing it.

### 6. Type Erasure: Types Gone at Run Time

After checking, some languages **erase** types — the running program has no record of them:

- **Java generics** are erased: `List<String>` and `List<Integer>` are *both* just `List` at run time. The `<String>` exists only to check your code; the JVM never sees it. That's why you can't write `new T[]` or `x instanceof List<String>`.
- **TypeScript** erases *everything*: the compiler checks types, then emits plain JavaScript with all annotations stripped. At run time there is no type information from TypeScript at all.

Erasure is a deliberate trade: you get static checking with zero runtime cost and full backward compatibility, but you lose the ability to *inspect* the erased types at run time. Contrast with languages that keep types around (C# reified generics, Python's runtime types) where `typeof`/`isinstance` can see the full type.

### 7. Type Soundness: "Well-Typed Programs Don't Go Wrong"

This Milner slogan is the *reason type systems exist*. A type system is **sound** if a program that passes the type checker is guaranteed never to hit a certain class of runtime type errors — calling a method that doesn't exist, adding a function to an integer, treating bytes as a pointer. "Don't go wrong" has a precise meaning: the program will never reach a *stuck* state where an operation is applied to an operand of the wrong type with no defined behavior.

Soundness is what makes static types worth the trouble. If the checker accepts your program, an entire category of failures is *provably impossible*, not merely tested-against. Crucially, soundness says nothing about *logic* bugs — a well-typed program can still compute the wrong answer, loop forever, or violate business rules. Types rule out a specific class of failure (type errors), and that class is large and valuable, but it is not "all bugs."

Real-world languages make pragmatic holes in soundness: Java's `null` (a `String` variable can be `null`), unchecked casts, `unsafe` blocks in Rust, `any` in TypeScript, reflection. Each hole is a place where the language traded a soundness guarantee for flexibility — and each is a place runtime type errors can creep back in.

### 8. Strong vs Weak Typing — Why the Terms Are Vague

People say "Python is strongly typed, C is weakly typed," but the terms have no agreed definition. Roughly, a "strong" type system rarely lets you violate type rules implicitly; a "weak" one allows lots of implicit coercion or reinterpretation of bytes. But the line is blurry:

- Python won't add `1 + "1"` (feels strong) but has no compile-time checking (feels weak).
- C will happily reinterpret an `int*` as a `char*` (feels weak) but won't silently turn a struct into a function.
- JavaScript coerces aggressively (`[] + {}` → `"[object Object]"`) — usually called weak.

Better, more precise axes to talk about instead of "strong/weak":

- **Static vs dynamic** — *when* checking happens.
- **Sound vs unsound** — whether well-typed programs are *guaranteed* free of type errors.
- **Implicit vs explicit conversions** — how much the language coerces for you.
- **Memory-safe vs memory-unsafe** — whether you can reinterpret raw bytes.

Use these. "Strong/weak" creates more arguments than it resolves.

### 9. A Type Tells the Compiler the Memory Layout

A type isn't only a logical set of values — for a compiled language it's also a **physical layout decision**. The type tells the compiler exactly how many bytes to allocate and how to interpret them:

| Type | Size (typical) | What the bytes mean |
|------|----------------|---------------------|
| `bool` | 1 byte | 0 = false, nonzero = true |
| `int32` | 4 bytes | two's-complement integer |
| `float64` | 8 bytes | IEEE-754 double |
| `*T` (pointer) | 8 bytes | a memory address |
| `struct{a int32; b int32}` | 8 bytes | two ints side by side |

The *same bytes* mean different things under different types: the 4 bytes `0x40490FDB` are the integer `1078530011` as `int32` but the value `3.1415927` as `float32`. The type is the lens that tells the hardware how to read the bits. This is also why **type safety and memory safety are related but distinct**: type safety says "you won't apply the wrong operation to a value"; memory safety says "you won't read or write memory you shouldn't." A language can have one without the other — but losing type safety often opens the door to losing memory safety too.

---

## Code Examples

### Java — static vs dynamic, and a downcast that fails

```java
class Animal { void eat() {} }
class Dog extends Animal { void bark() {} }
class Cat extends Animal {}

Animal a = new Dog();   // static: Animal, dynamic: Dog
a.eat();                // OK: Animal supports eat()
// a.bark();            // COMPILE ERROR: Animal has no bark() — static type governs

Dog d = (Dog) a;        // downcast: runtime VERIFIES the dynamic type. OK here.
d.bark();               // now legal: d's static type is Dog

Animal b = new Cat();
Dog d2 = (Dog) b;       // compiles fine, but throws ClassCastException at run time
```

The compiler accepts `(Dog) b` because, statically, `b` *could* be a `Dog` (it's an `Animal`). Only the runtime, checking the actual tag (`Cat`), can reject it. This is the static/dynamic gap made concrete.

### Java generics — type erasure

```java
List<String> ss = new ArrayList<>();
List<Integer> is = new ArrayList<>();
System.out.println(ss.getClass() == is.getClass()); // true!  both are ArrayList at run time

// is instanceof List<Integer>  // COMPILE ERROR: cannot check erased type
```

`<String>` and `<Integer>` are erased after checking — the JVM sees only `ArrayList`. The generic types existed solely to let the compiler verify your code.

### Python — checking happens at run time

```python
def process(x):
    return x.upper()      # no static type; nothing checked until this runs

process("hello")          # works: str has .upper()
process(42)               # AttributeError at run time: 'int' has no 'upper'
```

Nothing rejects `process(42)` ahead of time. The "type check" is the runtime attribute lookup, performed lazily, only when the line executes with that value. The dynamic type *is* the type system here.

### TypeScript — types checked then fully erased

```typescript
function double(n: number): number {
  return n * 2;
}
// Compiles to plain JS with NO types:
//   function double(n) { return n * 2; }

const x: unknown = "hi";
// const y: number = x;        // COMPILE ERROR: unknown not assignable to number
const y = x as number;          // assertion: compiler trusts you; NO runtime check
console.log(y * 2);             // runs, produces "hihi"... or NaN — types are gone
```

TypeScript checks at compile time, then emits type-free JavaScript. The `as number` assertion is *not* verified at run time (unlike a Java cast) — TypeScript has nothing to verify with, because the types are erased.

### Go — static type plus a runtime type assertion

```go
var i interface{} = "hello"   // static type: interface{}, dynamic type: string

s := i.(string)               // type assertion: checked at run time
fmt.Println(s)                // hello

n, ok := i.(int)              // comma-ok form: ok == false, no panic
fmt.Println(ok)               // false
// n2 := i.(int)              // would PANIC: interface holds string, not int
```

`interface{}` is Go's "any" — a static type that erases the specifics. To recover the dynamic type you *assert* it, and the runtime verifies against the stored tag.

### Rust — inference, and the type as memory layout

```rust
let x = 3.1415_f32;            // inferred f32: 4 bytes, IEEE-754 single
let bits = x.to_bits();        // the same 4 bytes read as a u32
println!("{:#010x}", bits);    // 0x40490fdb

// reinterpreting the bits under a different type:
let y = f32::from_bits(0x40490fdb);
println!("{}", y);             // 3.1415927

assert_eq!(std::mem::size_of::<f32>(), 4);
assert_eq!(std::mem::size_of::<(i32, i32)>(), 8); // type dictates layout/size
```

`size_of` shows the type *is* a layout decision. `to_bits`/`from_bits` show the same bytes meaning different things under different types — the "lens over bits" model in action.

### Type inference is still static — Go and Rust

```go
x := compute()   // x's type is fixed at compile time by compute()'s return type
```

```rust
let v: Vec<_> = (0..5).collect();  // element type inferred from context; fully static
```

You didn't write the type, but it's known and checked at compile time. Inference ≠ dynamic typing.

---

## Coding Patterns

### Pattern 1: Prefer the comma-ok / checked downcast over the panicking one

```go
if s, ok := i.(string); ok {
    use(s)
} // never panics; you handle the "wrong type" case explicitly
```

Whenever you cross from a loose static type to a specific one, use the form that lets you *handle* a mismatch rather than the one that crashes.

### Pattern 2: Annotate boundaries, infer internals

```rust
fn parse_config(raw: &str) -> Config { /* ... */ }  // annotate the public contract
// inside:
let parts: Vec<_> = raw.split(',').collect();        // let inference handle locals
```

Write types where they're contracts (function signatures); let inference remove noise where the type is obvious from context.

### Pattern 3: Push runtime-type branching to the edge

Convert from `interface{}`/`any`/`Object` to a concrete type *once*, at the boundary (deserialization, plugin loading), then work with concrete static types everywhere inside. Don't sprinkle type assertions through your core logic.

### Pattern 4: Use the type system's own escape hatch honestly

When you must reinterpret (a `union`, `unsafe`, `as`), isolate it in a small, well-named, well-tested function with a comment stating the invariant you're asserting that the compiler can't. The escape hatch is a debt; localize it.

---

## Best Practices

- **Keep the static/dynamic distinction explicit in your head** when debugging "but it compiled!" errors — a runtime cast failure is the static type being looser than reality.
- **Don't reach for casts to silence the checker.** A cast moves a compile error to run time; it rarely *solves* anything. Restructure so the types line up.
- **Treat `null` as a type hole.** In languages where any reference can be `null`, defend at boundaries or adopt optional/nullable types that make the possibility explicit.
- **Annotate public APIs; infer private locals.** Maximize signal (contracts) and minimize noise (obvious locals).
- **Remember erasure when you reach for reflection.** If you're on Java generics or TypeScript, the type you want to inspect at run time may simply not exist anymore.
- **Stop using "strong/weak."** Say "statically/dynamically typed," "sound/unsound," "memory-safe/unsafe," "implicit/explicit conversions" — you'll be understood precisely.
- **Respect the layout meaning of a type.** Picking `int32` vs `int64`, `float32` vs `float64`, or a struct ordering is a real memory and performance decision, not just a label.

---

## Edge Cases & Pitfalls

- **"It compiled, so it's correct" is false.** Static typing rules out *type* errors, not logic errors, infinite loops, or business-rule violations. A well-typed program can still be wrong.
- **A successful cast proves nothing about *future* runs.** `(Dog) a` working once means *this* value was a `Dog`; another run with a `Cat` still throws.
- **Erased generics defeat runtime checks.** `if (x instanceof List<String>)` doesn't compile; at run time you can only see `List`. Don't design around inspecting erased types.
- **Inference can surprise you.** `let x = 5;` might infer `i32` when you wanted `i64`, or Go's `:=` may pick a type you didn't intend. Annotate when the inferred type matters.
- **`any`/`interface{}`/`Object` is a static-typing off switch.** Every value fits, so the checker stops helping. Each one is a place runtime type errors can return.
- **Implicit conversions can silently lose information.** `int` → `float` may lose precision; `long` → `int` may truncate. The type system may allow conversions that quietly corrupt data.
- **Nominal vs structural surprises.** In nominal languages, two identical-looking structs are *different* types; in structural ones (TypeScript), two differently-named types with the same shape are *compatible*. Know which discipline your language uses.

---

## Common Mistakes

1. **Believing the dynamic type is what the compiler checks.** It checks the *static* type; the dynamic type only governs which implementation runs and whether casts succeed.
2. **Thinking type inference means dynamic typing.** Inferred types are fully static — known and checked at compile time. Only *who wrote them* differs.
3. **Treating a TypeScript `as` assertion like a Java cast.** TS assertions are *not* checked at run time (types are erased); they only silence the compiler.
4. **Assuming static typing makes a program correct.** It rules out one class of bug. The rest are still yours.
5. **Using "strongly typed" as if it had a precise meaning.** It doesn't; it confuses static-ness, soundness, and coercion behavior into one fuzzy word.
6. **Forgetting that a type fixes memory layout.** Choosing `float32` over `float64` or reordering struct fields has real size/performance consequences.
7. **Reaching for reflection on erased types** and being puzzled when the type information isn't there.

---

## Tricky Points

- **The static type is deliberately *forgetful*.** Even when the compiler could in principle track that `a` is a `Dog`, it generally treats it as the declared `Animal`, because tracking the precise flow of every subtype is undecidable in general. Flow-sensitive typing (TypeScript's narrowing, Kotlin smart casts) recovers *some* of this locally.
- **Soundness is a property of the *type system*, not your program.** A sound system guarantees *all* well-typed programs avoid type errors. Adding one unsound feature (an unchecked cast) breaks the guarantee for the whole language, which is why these holes are designed carefully.
- **Erasure vs reification is a spectrum.** Java erases generics; C# reifies them (the type is available at run time); Go's interfaces carry the dynamic type but generics (since 1.18) are partly erased. The choice shapes what reflection can do.
- **"Goes wrong" has a technical meaning.** In Milner's formulation, a program "goes wrong" when evaluation gets *stuck* — an operation with no rule for its operand types. Soundness = well-typed programs never get stuck. It does *not* mean "never crashes" (a sound program can still `panic`, throw, or diverge).
- **Memory safety and type safety can be decoupled.** Assembly is memory-unsafe and type-unsafe. A garbage-collected dynamic language is memory-safe but does runtime type checks. Rust is both type-safe and memory-safe *without* GC. They're related dials, not one dial.

---

## Apply it

1. Find a real component where **What Is a Type** affects an interface or dependency.
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

- Which boundary is most affected by What Is a Type?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
