# Sum, Product & Unit Types — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Sum, Product & Unit Types** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. A type is a set of values — count them

The trick that makes everything else obvious: **think of a type as a set, and count how many values it has.**

- `bool` has **2** values: `true`, `false`.
- A `u8` (unsigned 8-bit integer) has **256** values.
- An enum `enum Color { Red, Green, Blue }` has **3** values.

This count is the type's number of *inhabitants*. We'll use it constantly.

### 2. Product types: AND, and you multiply

A **product type** bundles fields together. A value holds **all** of them at once.

```rust
struct Point { x: bool, y: bool }   // a value has BOTH x AND y
```

How many `Point`s are there? For each of the 2 choices of `x`, there are 2 choices of `y`:

```
(false, false), (false, true), (true, false), (true, true)   →   4 = 2 × 2
```

The number of inhabitants is the **product** of the components' counts. That's literally why it's called a *product* type:

```
|A × B| = |A| × |B|
```

Tuples `(A, B)`, structs, records, and field-bearing classes are all product types. "Has-an `x` and a `y`" → multiply.

### 3. Sum types: OR, and you add

A **sum type** says a value is **one of** several alternatives.

```rust
enum Either { L(bool), R(bool) }   // a value is EITHER an L OR an R
```

How many `Either`s are there? An `L` carries a `bool` (2 options) and an `R` carries a `bool` (2 options). A value is one or the other:

```
L(false), L(true), R(false), R(true)   →   4 = 2 + 2
```

The number of inhabitants is the **sum** of the variants' counts. That's why it's called a *sum* type:

```
|A + B| = |A| + |B|
```

Rust `enum`, Haskell `data`, Swift `enum`, OCaml/F# variants, TypeScript discriminated unions, and Java sealed interfaces are all sum types. "Is an `A` *or* a `B`" → add.

### 4. The tag: how a sum knows what it is

A product is easy to lay out in memory: just put the fields next to each other. A sum is trickier: at any moment the value is *only one* of its variants, so it needs a hidden **tag** (also called a *discriminant*) that says "right now I am a `Circle`," plus enough room for the largest variant's payload.

```
Sum value layout (conceptually):
┌──────┬─────────────────────────────┐
│ tag  │ payload (sized for biggest) │
└──────┴─────────────────────────────┘
   ▲        ▲
   │        └─ the data for whichever variant the tag says
   └─ which variant is this? (0 = Circle, 1 = Rectangle, …)
```

This tag is what makes ADTs **safe**. Old C `union`s have the payload but **no tag** — nothing records which member is active, so you can read it as the wrong type and corrupt everything. ADTs are "tagged unions"; C unions are "untagged." The tag is the whole difference between safe and unsafe.

### 5. Pattern matching: open the box safely

To use a sum value you **pattern match**: you ask "which variant are you?" and, in the same breath, pull out the payload.

```rust
match shape {
    Shape::Circle(r)         => 3.14159 * r * r,
    Shape::Rectangle(w, h)   => w * h,
}
```

Each arm handles one variant and binds its data (`r`, or `w` and `h`). You cannot accidentally read a `Circle`'s radius when the value is actually a `Rectangle` — the match makes that impossible.

### 6. Exhaustiveness: the compiler has your back

Here is the feature that changes how you write programs. A good compiler checks that your match handles **every** variant. If you add a fourth `Shape::Triangle` variant later and forget to handle it somewhere, the compiler **refuses to compile** and points at every match that's now incomplete.

```
error: non-exhaustive patterns: `Triangle { .. }` not covered
```

Think about what just happened: you changed a data definition, and the compiler handed you a to-do list of every place in the entire codebase that needs updating. That's not an annoyance — that's the most valuable refactoring tool you'll ever use. In a language without sum types, that same change would slip through and crash at runtime, on a Friday, in production.

### 7. The Unit type: exactly one value

The **Unit type** has exactly **one** inhabitant. In Rust it's written `()` (and its single value is also written `()`). In Haskell and OCaml it's `()` of type `unit`.

```
|Unit| = 1
```

Why would you want a type with only one value? Because "one value" means "no information to carry." When a function does something for its *effect* (print, save) and has nothing meaningful to return, it returns Unit: "I'm done; here's the one and only value I could possibly give you." It is the **identity of product**: `A × Unit` has the same number of values as `A`, because multiplying by 1 changes nothing. Adding a Unit field to a struct adds no information.

### 8. The Void type: zero values

The **Void type** (also called *Never*, *bottom*, or *Nothing* depending on the language) has **zero** inhabitants. You can never produce one.

```
|Void| = 0
```

What use is a type you can't construct? It's a *promise*: a function returning `Never` is promising it will **never return normally** — it loops forever, or always panics, or always exits. It's the **identity of sum**: `A + Void` has the same number of values as `A`, because the `Void` branch can never actually happen (adding 0 changes nothing). This is why `Result<T, Never>` means "an error case that can never occur."

> ⚠️ **Important name clash:** C/Java/JS `void` is **not** the Void type — it's closer to Unit ("a function that returns nothing useful but does return"). The true zero-value type is Rust's `!`, Haskell's `Void`/`Data.Void`, TypeScript's `never`, Kotlin's `Nothing`. Don't let the spelling fool you.

### 9. Why this is called an *algebra*

Put the four facts together:

```
|A × B|  = |A| × |B|     (product → multiply)
|A + B|  = |A| + |B|     (sum     → add)
|Unit|   = 1             (identity of ×)
|Void|   = 0             (identity of +)
```

These obey the same rules as ordinary arithmetic. `A × Unit` ≅ `A` (multiply by 1). `A + Void` ≅ `A` (add 0). `A × Void` has 0 values (multiply by 0 — a struct with an uninhabitable field can never be built). This is why they're called **algebraic** data types: the *counts* of your types literally do arithmetic. You don't need this to use ADTs, but it's a beautiful sanity-check, and `middle.md` shows it explains `Option`, generics, and even function types.

---

## Code Examples

We model the same thing — a **shape** (sum) and a **point** (product) — across several languages, then show `Option` replacing `null`.

### Rust — sum (`enum`), product (`struct`), and a match

```rust
// PRODUCT: a Point has an x AND a y.
struct Point { x: f64, y: f64 }

// SUM: a Shape is a Circle OR a Rectangle OR a Triangle.
enum Shape {
    Circle { radius: f64 },
    Rectangle { width: f64, height: f64 },
    Triangle { base: f64, height: f64 },
}

fn area(s: &Shape) -> f64 {
    match s {
        Shape::Circle { radius }            => std::f64::consts::PI * radius * radius,
        Shape::Rectangle { width, height }  => width * height,
        Shape::Triangle { base, height }    => 0.5 * base * height,
        // Delete one arm and this WON'T COMPILE: non-exhaustive patterns.
    }
}

fn main() {
    let s = Shape::Circle { radius: 2.0 };
    println!("area = {}", area(&s));
}
```

### Swift — same idea, `enum` with associated values

```swift
struct Point { let x: Double; let y: Double }   // product

enum Shape {                                     // sum
    case circle(radius: Double)
    case rectangle(width: Double, height: Double)
    case triangle(base: Double, height: Double)
}

func area(_ s: Shape) -> Double {
    switch s {                                   // exhaustive switch
    case .circle(let r):            return .pi * r * r
    case .rectangle(let w, let h):  return w * h
    case .triangle(let b, let h):   return 0.5 * b * h
    }
}
```

### Haskell — `data` declares both at once

```haskell
data Point = Point Double Double          -- product: two fields side by side

data Shape                                -- sum: three alternatives, separated by |
  = Circle    Double
  | Rectangle Double Double
  | Triangle  Double Double

area :: Shape -> Double
area (Circle r)      = pi * r * r
area (Rectangle w h) = w * h
area (Triangle b h)  = 0.5 * b * h
-- drop a line and GHC warns: Pattern match(es) are non-exhaustive
```

### TypeScript — discriminated union (the tag is a literal field)

```typescript
type Point = { x: number; y: number };              // product (object type)

type Shape =                                          // sum: union with a "kind" tag
  | { kind: "circle"; radius: number }
  | { kind: "rectangle"; width: number; height: number }
  | { kind: "triangle"; base: number; height: number };

function area(s: Shape): number {
  switch (s.kind) {                                   // narrows on the tag
    case "circle":    return Math.PI * s.radius ** 2;
    case "rectangle": return s.width * s.height;
    case "triangle":  return 0.5 * s.base * s.height;
  }
}
```

The string field `kind` *is* the tag. TypeScript narrows the type inside each `case`, so `s.radius` is only accessible in the `"circle"` branch.

### Go — there is no native sum; you fake it with an interface + type switch

```go
type Shape interface{ isShape() }

type Circle struct{ Radius float64 }
type Rectangle struct{ Width, Height float64 }

func (Circle) isShape()    {}
func (Rectangle) isShape() {}

func Area(s Shape) float64 {
    switch v := s.(type) {           // type switch stands in for pattern matching
    case Circle:
        return math.Pi * v.Radius * v.Radius
    case Rectangle:
        return v.Width * v.Height
    default:
        panic("unknown shape")       // no compile-time exhaustiveness — runtime only
    }
}
```

Go has product types (structs) but no built-in sum types. The interface trick works, but note the painful difference: there is **no exhaustiveness check**. Add a new shape, forget a case, and you find out at runtime via the `panic`, not at compile time.

### `Option` / `Maybe` — the canonical sum, replacing `null`

```rust
// Rust: Option<T> is literally `enum Option<T> { None, Some(T) }`
fn find_user(id: u32) -> Option<String> {
    if id == 1 { Some("alice".to_string()) } else { None }
}

fn main() {
    match find_user(7) {
        Some(name) => println!("found {name}"),
        None       => println!("no such user"),  // you CANNOT forget this branch
    }
}
```

In a language with `null`, `find_user` would return a `String` that might secretly be null, and nothing forces you to check — until it crashes. With `Option`, the *type* says "this might be absent," and the compiler makes you handle the absent case. That's the same bug, made impossible.

> **Counting check:** `Option<bool>` has `1 + 2 = 3` values: `None`, `Some(false)`, `Some(true)`. It's `1 + A` where the `1` is `None` (a Unit-like variant) and `A` is the wrapped type. The algebra predicts the count exactly.

---

## Coding Patterns

### Pattern 1: Replace flags-and-nullables with a sum

Before (a product that allows illegal states):

```rust
struct Connection {
    connected: bool,
    socket: Option<Socket>,   // null when disconnected... but nothing enforces that
    retry_count: u32,
}
```

After (a sum where every state carries exactly what it needs):

```rust
enum Connection {
    Disconnected,
    Connecting { attempts: u32 },
    Connected  { socket: Socket },
}
```

Now `Connected` *always* has a socket; `Disconnected` *can't* have one.

### Pattern 2: `Option` instead of `null` for "might be missing"

```rust
fn first_even(v: &[i32]) -> Option<i32> {
    v.iter().copied().find(|n| n % 2 == 0)
}
```

The caller *must* handle `None`. There is no null to forget to check.

### Pattern 3: `Result` instead of exceptions for "might fail"

```rust
fn parse_port(s: &str) -> Result<u16, String> {
    s.parse::<u16>().map_err(|_| format!("not a port: {s}"))
}
```

Success and failure are both in the return type, both visible, both handled.

### Pattern 4: Make the tag explicit in languages without native sums

In TypeScript and Go, keep a `kind`/type-marker field and always switch on it. Treat the type switch as your pattern match, and add a `default` that loudly fails so a forgotten case is at least *noisy*.

---

## Best Practices

- **Prefer a sum to a struct-with-flags whenever the word "or" shows up in the spec.** "A user is *either* a guest *or* a member" → sum, not booleans.
- **Make every variant carry exactly the data that variant needs — no more, no less.** That's how you kill illegal states.
- **Always pattern match exhaustively.** In languages that check it, lean on the compiler. In ones that don't, add a failing default and a test.
- **Avoid catch-all wildcards (`_ =>`) in matches over your own sums** when you can. A wildcard silences the exhaustiveness check, so adding a variant won't flag this match. Spell out the cases.
- **Use the standard `Option`/`Result` (or `Maybe`/`Either`) instead of inventing your own** "maybe missing" or "maybe failed" types.
- **Name variants for the domain, not for the data.** `Disconnected`, not `StateZero`.
- **Return Unit (`()` / `void`) honestly** when a function is called for its effect; don't return a meaningless `bool` or `0`.

---

## Edge Cases & Pitfalls

- **`void` is not Void.** C/Java/JS `void` means "returns nothing useful" (Unit-like). The true zero-value type is Rust `!`, TS `never`, Kotlin `Nothing`, Haskell `Void`. Mixing them up confuses a lot of conversations.
- **Untagged C unions are a foot-gun.** `union { int i; float f; }` has no tag. Read the wrong member and you reinterpret raw bytes. ADTs add the tag; C unions don't. Never treat a C union like a safe sum type.
- **The wildcard arm defeats exhaustiveness.** `match s { Circle(_) => …, _ => … }` compiles forever, even after you add ten new variants, silently routing them to the catch-all. Use it sparingly.
- **A struct with a nullable field is a *weak* sum.** `socket: Option<Socket>` plus `connected: bool` technically encodes states, but it also encodes the *illegal* ones. Promote to a real sum.
- **Order/position can be a tag by accident.** A tuple `(bool, bool)` has no field names; it's easy to swap. Prefer named fields for products with same-typed components.
- **Empty sum vs empty product.** A sum with zero variants is Void (0 values, can't construct). A product with zero fields is Unit (1 value — the empty tuple). Beginners mix these up; remember: no-choice OR = impossible, no-fields AND = trivially one value.
- **Recursive sums need indirection in some languages.** A linked list `Cons(head, tail)` or a tree references *itself*. Languages like Rust require a `Box`/pointer so the size is finite. The idea is the same; the mechanics differ.

---

## Apply it

1. Choose one small, known input for **Sum, Product & Unit Types**.
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

- What problem does Sum, Product & Unit Types solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
