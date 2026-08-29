# Nominal vs Structural Typing — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Nominal vs Structural Typing** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Two Questions a Compiler Asks

Picture a function `func print(a Animal)`. You call it with some value `x`. The compiler must decide: *is `x` an `Animal`?* The two type systems use different rules:

- **Nominal:** "Was `x`'s type *declared* to be an `Animal` or a subtype of `Animal`? Show me the `extends`/`implements`." If no such declaration exists, **rejected** — even if `x`'s type has every method `Animal` has.
- **Structural:** "Does `x`'s type *have everything* `Animal` requires (the right fields and methods)?" If yes, **accepted** — even if nobody ever mentioned `Animal` when defining `x`'s type.

That is the entire distinction. Everything else is consequences of this one rule.

### 2. Nominal Typing: The Name Is the Identity

In Java, this fails to compile:

```java
class Point2D { int x; int y; }
class Vector2D { int x; int y; }

Point2D p = new Point2D();
Vector2D v = p;   // ❌ COMPILE ERROR: incompatible types
```

`Point2D` and `Vector2D` are structurally identical — same fields, same types. But they have **different names** and no declared relationship, so the compiler refuses the assignment. The name is load-bearing. This is *intentional*: a point and a vector mean different things, and the language won't let you confuse them just because they happen to be laid out the same way.

To make two types compatible in a nominal system, you must **declare** the relationship:

```java
interface Shape { double area(); }
class Circle implements Shape {   // explicit "implements"
    double area() { return 3.14 * r * r; }
}
Shape s = new Circle();   // ✅ allowed because Circle DECLARES it implements Shape
```

The `implements Shape` is the contract. No `implements`, no compatibility — even if `Circle` has an `area()` method.

### 3. Structural Typing: The Shape Is the Identity

In Go, there is **no `implements` keyword**. A type satisfies an interface simply by having the methods:

```go
type Stringer interface {
    String() string
}

type Color struct{ R, G, B int }

func (c Color) String() string {   // just a method; never mentions Stringer
    return fmt.Sprintf("#%02x%02x%02x", c.R, c.G, c.B)
}

var s Stringer = Color{255, 0, 0}   // ✅ Color satisfies Stringer automatically
```

`Color` never says "I implement `Stringer`." It just *has* a `String() string` method, and that's enough. The compiler checks the shape: does `Color` have everything `Stringer` requires? Yes. Done.

The same idea in TypeScript with plain object shapes:

```typescript
interface Named { name: string; }

function greet(n: Named) { console.log("Hi " + n.name); }

greet({ name: "Ada", age: 36 });   // ✅ the object literal HAS a name field
```

The object isn't declared to be `Named`. It just *has* a `name: string`, so it fits.

### 4. The Bug Nominal Typing Catches and Structural Typing Misses

Here is the most practical reason to care. Imagine user IDs and product IDs are both stored as `string`:

```typescript
function getUser(userId: string) { /* ... */ }

const productId: string = "p_4815";
getUser(productId);   // ✅ COMPILES — but it's a bug! Wrong ID passed.
```

Because both are just `string`, the compiler sees nothing wrong. You shipped a bug. **Nominal typing** — or simulating it — fixes this: if `UserId` and `ProductId` are *distinct types* (different names), passing one where the other is expected is a compile error. This is the **newtype pattern**, and the higher tiers show how to get it in every language. For now, just register the idea: *giving the same-shaped data different names is sometimes exactly what you want.*

### 5. Duck Typing: The Dynamic Cousin

In Python (dynamically typed), there's no compile-time check at all. You just call the method and hope it exists:

```python
def make_it_speak(thing):
    return thing.speak()   # works for ANY object with a speak() method
```

If `thing` has `.speak()`, it works; if not, you get a runtime error. This is **duck typing**: compatibility is checked at *runtime* by trying the operation. Structural typing is essentially "duck typing checked at compile time" — same shape-based philosophy, but the compiler verifies it ahead of time so failures are caught before the program runs.

---

## Code Examples

### Nominal — Java (must declare `implements`)

```java
interface Greeter {
    String greet();
}

// This class has a greet() method but does NOT implement Greeter.
class Robot {
    public String greet() { return "BEEP"; }
}

class Person implements Greeter {   // <-- explicit declaration
    public String greet() { return "Hello"; }
}

class Demo {
    public static void main(String[] args) {
        Greeter g1 = new Person();   // ✅ Person declares implements Greeter
        // Greeter g2 = new Robot(); // ❌ COMPILE ERROR even though Robot has greet()
    }
}
```

Robot has the exact method, but without `implements Greeter`, Java rejects it. The shape is irrelevant; the declaration is everything.

### Nominal — C# (same rule)

```csharp
interface IGreeter { string Greet(); }

class Robot { public string Greet() => "BEEP"; }      // not declared
class Person : IGreeter { public string Greet() => "Hello"; }  // declared

IGreeter g = new Person();   // ✅
// IGreeter g2 = new Robot(); // ❌ Robot does not implement IGreeter
```

### Structural — Go (no `implements`, satisfied by shape)

```go
package main

import "fmt"

type Greeter interface {
    Greet() string
}

type Robot struct{}
func (r Robot) Greet() string { return "BEEP" }   // never names Greeter

type Person struct{}
func (p Person) Greet() string { return "Hello" } // never names Greeter

func main() {
    var g Greeter
    g = Robot{}   // ✅ Robot satisfies Greeter just by having Greet()
    fmt.Println(g.Greet())
    g = Person{}  // ✅ same — automatic
    fmt.Println(g.Greet())
}
```

Both `Robot` and `Person` satisfy `Greeter` with **zero** declaration. They simply have a `Greet() string` method. This is the canonical example of structural, implicit interface satisfaction.

### Structural — TypeScript (object literal fits by shape)

```typescript
interface Greeter {
    greet(): string;
}

const robot = { greet: () => "BEEP", batteryLevel: 80 };
const person = { greet: () => "Hello" };

function announce(g: Greeter) {
    console.log(g.greet());
}

announce(person);   // ✅ has greet()
announce(robot);    // ✅ has greet() (extra batteryLevel is fine for a variable)
```

Neither object is declared to be a `Greeter`. They just have a `greet(): string`, so they fit. (Passing an *object literal directly* triggers an extra check — covered in pitfalls.)

### The ID-mixup bug — and a first taste of the fix (Rust newtype)

```rust
// WITHOUT newtypes: both are just u64 — easy to swap by accident.
fn ban_user(user_id: u64, _moderator_id: u64) { /* ... */ }

// WITH newtypes: distinct names => the compiler stops the mix-up.
struct UserId(u64);
struct ModeratorId(u64);

fn ban_user2(user: UserId, _mod: ModeratorId) { /* ... */ }

fn main() {
    let u = UserId(10);
    let m = ModeratorId(99);
    ban_user2(u, m);          // ✅ correct order
    // ban_user2(m, u);       // ❌ COMPILE ERROR: ModeratorId is not UserId
}
```

Rust is nominal, so `UserId` and `ModeratorId` are different types even though both wrap a `u64`. Swapping them won't compile. That's the newtype pattern preventing a real bug.

---

## Coding Patterns

**Pattern: small interfaces (structural).** In Go, define interfaces with one or two methods (`Reader`, `Stringer`). Small shapes are easy to satisfy and maximize the benefit of implicit conformance.

```go
type Closer interface { Close() error }   // anything closeable fits
```

**Pattern: the newtype wrapper (nominal).** Wrap a primitive to get a distinct type and stop mix-ups.

```rust
struct Celsius(f64);
struct Fahrenheit(f64);   // can't accidentally add a Celsius to a Fahrenheit
```

**Pattern: accept interfaces, return concrete types (Go idiom).** Functions take structural interfaces (flexible inputs) but return concrete structs (clear outputs).

**Pattern: declare conformance explicitly even when not required (Java/C#/Rust).** In nominal languages you must, but the *benefit* is that the declaration documents intent and the error message points at the right contract.

---

## Best Practices

1. **Know which model your language uses.** Go interfaces and TypeScript = structural. Java/C#/Rust/Swift = nominal. This changes what mistakes are possible.
2. **In structural languages, don't rely on names for safety.** Two same-shaped types are interchangeable — if you need them distinct, build a newtype/branded type.
3. **Give semantically different values distinct types.** A `UserId` and `OrderId` should never both be a bare `string`/`int`, even though it's "more typing."
4. **In Go, keep interfaces small.** Big interfaces are hard to satisfy and undercut the flexibility structural typing is meant to provide.
5. **Let the compiler help.** When a Go type "mysteriously" satisfies an interface you didn't expect, that's structural typing working as designed — but double-check it's intended.
6. **Don't fight your language.** Faking nominal typing in TypeScript (branding) or structural in Java (reflection) is sometimes right, but it's advanced — reach for it deliberately, not by default.

---

## Edge Cases & Pitfalls

**1. Accidentally satisfying a Go interface.** You add a `Close() error` method to a struct for unrelated reasons, and suddenly it satisfies some `io.Closer`-based code path you never intended. The compiler won't warn you — there's no declaration to check. Be aware that *any* matching method set conforms.

**2. The "extra property" surprise in TypeScript.** A variable with extra fields can be passed to a smaller interface, but an **object literal** passed directly is checked more strictly (excess property check) and rejected:

```typescript
interface Point { x: number; y: number; }
function plot(p: Point) {}

const obj = { x: 1, y: 2, z: 3 };
plot(obj);              // ✅ via variable
plot({ x: 1, y: 2, z: 3 });  // ❌ excess property 'z' — literal is checked strictly
```

This trips up beginners constantly. The literal-vs-variable distinction is real.

**3. Same shape, different meaning.** In a structural language, `type Meters = number` and `type Seconds = number` are the *same type* — the alias is just a nickname. Adding meters to seconds compiles fine. You need a branded/newtype to separate them.

**4. Empty interfaces match everything.** Go's `interface{}` (or `any`) and TypeScript's `{}` are satisfied by almost anything because they require *no* members. An empty shape is the loosest possible structural requirement.

**5. Forgetting `implements` in a nominal language doesn't always error where you expect.** In Java, a class with the right method but no `implements` compiles fine on its own — the error only appears at the *assignment* to the interface type. The mismatch surfaces later than you'd think.

**6. Duck typing failures are runtime, not compile time.** In Python, calling `.speak()` on something without it crashes *when that line runs*, possibly only on a rare code path. Structural typing's whole point is to move that failure to compile time.

---

## Apply it

1. Choose one small, known input for **Nominal vs Structural Typing**.
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

- What problem does Nominal vs Structural Typing solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
