# Bounded Polymorphism — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Bounded Polymorphism** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Multiple bounds: needing more than one capability

A function may need `T` to do two things. You conjoin the bounds.

```java
static <T extends Comparable<T> & Serializable> T pick(T a, T b) {   // Java: A & B
    return a.compareTo(b) >= 0 ? a : b;   // uses Comparable; Serializable is a separate promise
}
```
```rust
fn pick<T: Ord + Clone>(a: T, b: T) -> T {    // Rust: A + B
    if a >= b { a } else { b }
}
```
```haskell
pick :: (Ord a, Show a) => a -> a -> a        -- Haskell: tuple of constraints
pick a b = if a >= b then a else b
```

`T extends A & B` means "`T` implements **both**." Note an asymmetry in Java: you may name at most **one class** but any number of **interfaces** in a multiple bound, and the class (if present) must come first — because a type can extend only one class.

### 2. `where` clauses: the same bounds, more readable

When bounds pile up, inline syntax gets noisy. `where` clauses move them aside:

```rust
fn process<T, U>(items: Vec<T>, f: U) -> Vec<String>
where
    T: Clone + std::fmt::Display,
    U: Fn(&T) -> bool,
{ /* ... */ }
```
```csharp
static T Pick<T>(T a, T b) where T : IComparable<T>, ISerializable { ... }
```
```swift
func pick<T>(_ a: T, _ b: T) -> T where T: Comparable & Codable { ... }
```

`where` clauses are not a different *kind* of bound — they're the same constraints, relocated. They shine when a bound is long (e.g. `U: Fn(&T) -> bool`) or references multiple parameters.

### 3. F-bounded polymorphism: the self-referential bound

Look hard at the canonical Java signature:

```java
static <T extends Comparable<T>> T max(T a, T b) { ... }
```

`T` appears **inside its own bound**: `Comparable<T>`. This is **F-bounded polymorphism** (the "F" is historical, from the original paper's use of a type operator `F`). Read it as: *"`T` is a type that can be compared **to itself**."*

Why is it written this way rather than `T extends Comparable`? Because `Comparable<X>` means "comparable *to* `X`". You want `T` comparable to *the same type*, so the type argument has to be `T` again. Plain `Comparable` (the raw type) would let you compare a `T` to *anything*, losing the precision — you could accidentally compare a `Banana` to a `Wrench`.

The recursive bound shows up across the ecosystem:

```java
public abstract class Enum<E extends Enum<E>> implements Comparable<E> { ... }
```

`java.lang.Enum` is F-bounded so that `compareTo`, `getDeclaringClass`, etc. are typed in terms of *the specific enum subclass*, not `Enum` in general. Every `enum Color {...}` desugars to `class Color extends Enum<Color>`. The bound enforces "an enum's natural ordering is only with enums of its own kind."

In dictionary-passing languages you usually *don't* write this by hand — you use a **`Self` type** instead:

```rust
trait Ord {
    fn cmp(&self, other: &Self) -> Ordering;   // Self = the implementing type
}
```
```swift
protocol Comparable {
    static func < (lhs: Self, rhs: Self) -> Bool   // Self does the self-reference for you
}
```

`Self` *is* the F-bound, baked into the language so you don't hand-write `Comparable<T>` everywhere. That's a real ergonomic advantage of the dictionary-passing model.

### 4. CRTP — the C++ structural cousin

C++ before concepts achieved a similar self-reference with the **Curiously Recurring Template Pattern**:

```cpp
template <typename Derived>
struct Comparable {
    bool operator>(const Derived& other) const {
        return static_cast<const Derived&>(*this).compare(other) > 0;
    }
};

struct Money : Comparable<Money> {   // <-- passes itself as the template argument
    int cents;
    int compare(const Money& o) const { return cents - o.cents; }
};
```

`Money : Comparable<Money>` mirrors `Color extends Enum<Color>`. The base class is parameterized on the derived class, letting the base call derived methods with the *exact* derived type and no virtual dispatch. It's the static-polymorphism dual of an F-bound. (C++20 concepts give a cleaner alternative for many uses; see `senior.md`.)

### 5. The big split: subtype bounds vs dictionary passing

Here is the conceptual heart of this page. Two languages can write nearly identical generic code, yet satisfy the bound by completely different machinery.

**Subtype bounds (Java, C#, Swift class/protocol-as-type).** `T extends Comparable<T>` is satisfied because the *object itself* is a `Comparable` — its methods live on the object (in its class's method table). The generic call `a.compareTo(b)` is an ordinary (often virtual) dispatch through `a`. Consequence: to make a type satisfy the bound, the type's *own definition* must declare it implements the interface. You cannot, in general, retrofit `Comparable` onto a class you don't own.

**Dictionary passing (Haskell typeclasses, Rust traits, Scala givens/implicits).** `T: Ord` is satisfied because somewhere there's an `instance Ord T` / `impl Ord for T` declaration — a **separate** table of the operations for `T`. The type `T` itself doesn't subtype anything. The compiler finds the right dictionary and either passes it as a hidden argument (Haskell, `dyn Trait` in Rust) or specializes the function and inlines the operations (Rust monomorphization). Consequence: you can write `impl MyTrait for SomeoneElsesType` — adding a capability to a type *after the fact*, without touching its definition.

A picture of one bounded call, both ways:

```text
SUBTYPE BOUND (Java)                  DICTIONARY PASSING (Haskell/Rust)

 a : Comparable<T>                     a : T          dict : Ord-for-T
   │   (methods on the object)           │              │ {compare, lt, ...}
   ▼                                      ▼              ▼
 a.compareTo(b)  ── virtual call      cmp(a, b)  uses ── dict.compare(a, b)
   into a's class vtable                                 (passed in / inlined)
```

Same source intent. Different answer to "where do the operations come from."

### 6. What the split buys you

| Question | Subtype bound (Java/C#/Swift) | Dictionary passing (Haskell/Rust/Scala) |
|---|---|---|
| Add a capability to a type you don't own? | No (must edit the type) | **Yes** (`impl Trait for Foreign`) |
| Type can satisfy bound two different ways? | No (one set of methods on the object) | Yes in principle (one *instance* each, but you can pick via newtype/wrapper) |
| Values boxed / carry a vtable pointer? | Often yes (object header) | Often **no** — monomorphized to plain values (Rust/C++) |
| Dispatch | Usually virtual | Static (monomorphized) or dynamic (`dyn`) by choice |
| Self-reference (`compareTo` to own type) | F-bound by hand (`Comparable<T>`) | `Self` type, built in |

These differences aren't cosmetic — they drive whole design philosophies (Rust's "implement traits for any type," Haskell's `instance`-based extensibility) explored in `senior.md`.

### 7. Default methods on the bound

Both worlds let the bound's interface ship **default implementations**, so satisfying a bound can require implementing only a *core* operation and inheriting the rest:

```rust
trait Comparable {
    fn cmp(&self, other: &Self) -> Ordering;        // you must provide this
    fn max(self, other: Self) -> Self where Self: Sized {  // default, free
        if self.cmp(&other) == Ordering::Less { other } else { self }
    }
}
```

Java interfaces (`default` methods), Swift protocol extensions, and Haskell typeclass default methods all do this. Practical upshot: a well-designed bound has a *minimal* required surface and a *rich* derived surface, so implementing it is cheap but using it is powerful.

---

## Code Examples

### Multiple bounds, four languages

```java
// Java: at most one class, then any interfaces, joined with &
static <T extends Number & Comparable<T>> T clampToMin(T x, T min) {
    return x.compareTo(min) < 0 ? min : x;
}
```
```rust
fn summarize<T: std::fmt::Display + Clone + PartialOrd>(items: &[T]) -> String {
    let mut out = String::new();
    for it in items { out.push_str(&format!("{} ", it.clone())); }
    out
}
```
```csharp
static bool Between<T>(T x, T lo, T hi) where T : IComparable<T>
    => x.CompareTo(lo) >= 0 && x.CompareTo(hi) <= 0;
```
```haskell
describe :: (Show a, Ord a) => a -> a -> String
describe a b = show (if a >= b then a else b)
```

### F-bounded by hand (Java) vs Self type (Rust)

```java
// Java: the F-bound is explicit. Note T appears inside Comparable<T>.
static <T extends Comparable<T>> T maxOf(java.util.List<T> xs) {
    T best = xs.get(0);
    for (T x : xs) if (x.compareTo(best) > 0) best = x;
    return best;
}
```
```rust
// Rust: no hand-written self-reference. `Ord` already uses Self internally.
fn max_of<T: Ord + Copy>(xs: &[T]) -> T {
    let mut best = xs[0];
    for &x in xs { if x > best { best = x; } }
    best
}
```

The Java version *must* spell `Comparable<T>`. The Rust version doesn't, because `Ord::cmp(&self, other: &Self)` carries the self-reference inside the trait.

### Retrofitting a bound: dictionary passing wins

```rust
// Add a capability to a type you don't own — legal because the dictionary
// (the impl) is separate from the type's definition.
trait Summary { fn summary(&self) -> String; }

impl Summary for i32 {                 // i32 is not yours; you extend it anyway
    fn summary(&self) -> String { format!("the integer {}", self) }
}

fn announce<T: Summary>(x: T) { println!("{}", x.summary()); }
// announce(42);  ->  "the integer 42"
```

In Java/C#/Swift you generally cannot make a pre-existing third-party class implement a new interface; the type's *own* declaration would have to change. (Swift extensions and C# extension methods soften this, but they don't make the type a true *subtype* of a new protocol/interface in all cases.) This single example captures the practical difference between the two mechanisms.

### Default methods reduce what an impl must provide

```rust
trait Greet {
    fn name(&self) -> String;                      // required
    fn hello(&self) -> String {                    // default: derived from name()
        format!("Hello, {}!", self.name())
    }
}
struct Dog;
impl Greet for Dog { fn name(&self) -> String { "Rex".into() } }  // hello() comes free
// Dog.hello()  ->  "Hello, Rex!"
```
```java
interface Greet {
    String name();
    default String hello() { return "Hello, " + name() + "!"; }  // Java default method
}
```

### CRTP self-bound in C++ (pre-concepts static polymorphism)

```cpp
template <typename D>
struct Ordered {
    bool operator<=(const D& o) const {
        const D& self = static_cast<const D&>(*this);
        return self.cmp(o) <= 0;            // calls into Derived, no virtual
    }
};
struct Version : Ordered<Version> {
    int n;
    int cmp(const Version& o) const { return n - o.n; }
};
// Version{2} <= Version{5}  ->  true
```

---

## Coding Patterns

### Pattern 1: Self-typed builder via F-bound

```java
abstract class Builder<B extends Builder<B>> {
    @SuppressWarnings("unchecked")
    protected B self() { return (B) this; }
    B name(String n) { /* set */ return self(); }   // returns the *subtype*
}
class UserBuilder extends Builder<UserBuilder> {
    UserBuilder email(String e) { /* set */ return self(); }
}
// new UserBuilder().name("a").email("b")  -- email() is visible after name()
```

The F-bound makes `name()` return `UserBuilder`, so subtype-specific methods stay chainable. Without it, `name()` returns `Builder` and you lose `email()`.

### Pattern 2: Prefer `Self`/dictionary self-reference when the language offers it

```rust
trait Builder: Sized {
    fn name(self, n: &str) -> Self;   // Self handles the self-typing for free
}
```

No hand-written F-bound; `Self` is the cleaner idiom in Rust/Swift.

### Pattern 3: Split many bounds into a `where` clause

```rust
fn run<T, F, E>(input: T, f: F) -> Result<String, E>
where
    T: Clone + std::fmt::Debug,
    F: Fn(T) -> Result<String, E>,
    E: std::error::Error,
{ f(input.clone()) }
```

### Pattern 4: Give the bound a rich default surface

Design your interface/trait so impls provide one or two *core* methods and inherit the rest via defaults — cheaper to implement, easier to use, and easier to evolve without breaking existing impls.

### Pattern 5: Retrofit with a newtype when you can't `impl` directly

In dictionary-passing languages, if you can't add an impl for a foreign type (coherence forbids it — see `senior.md`), wrap it: `struct MyInt(i32)` and `impl MyTrait for MyInt`. The newtype is *yours*, so the impl is allowed.

---

## Best Practices

- **Use `where` clauses once you have more than one or two bounds.** Inline `<T extends A & B & C>` becomes unreadable fast.
- **Reach for `Self`/associated self-reference before hand-rolling an F-bound.** If the language has `Self` (Rust/Swift), prefer it; F-bounds are a workaround for languages without it.
- **Know which mechanism your language uses** before reasoning about retrofitting, boxing, or dispatch. Stand in the right column.
- **In Java multiple bounds, put the (single) class first, interfaces after.** The compiler enforces it; remember it to avoid confusing errors.
- **Keep F-bounds shallow.** They compose poorly: a *list* of F-bounded things, or an F-bound nested in another generic, gets ugly fast. If it's getting deep, reconsider the design.
- **Design bounds with minimal required methods + generous defaults.** It lowers the cost of conforming and lets you extend the interface later without breaking impls.
- **Don't fake retrofitting with casts.** If a language can't retrofit a bound, use a wrapper/newtype or an adapter — never a runtime cast that throws.

---

## Edge Cases & Pitfalls

- **`Comparable<T>` vs `Comparable<? super T>`.** `<T extends Comparable<T>>` rejects a subclass `D` whose comparison is defined on a *parent* type (because `D` implements `Comparable<Parent>`, not `Comparable<D>`). The robust idiom is `<T extends Comparable<? super T>>`. Beginners hit this when an enum or a subclass "should" be comparable but the tight bound refuses it. (Full treatment in `senior.md`.)
- **F-bound doesn't actually stop you passing a *different* type.** `class A implements Comparable<B>` can sneak past loosely written bounds; the recursive bound narrows but doesn't make the API foolproof.
- **Java's raw-type escape hatch.** Using `Comparable` raw (no type argument) silences the F-bound and reintroduces unsafe comparisons. Don't.
- **One class only in a multiple bound (Java).** `<T extends ClassA & ClassB>` is illegal — a type can extend only one class. Multiple *interfaces* are fine.
- **Conflicting default methods (diamond).** When two bounds both supply a default with the same signature, the type must override to disambiguate. Java forces an explicit override; be ready for it.
- **Monomorphization bloat.** In Rust/C++, every distinct `T` you instantiate a bounded generic with creates a fresh code copy. Great for speed, but binary size and compile time can balloon for widely-instantiated generics.
- **Subtype-bound boxing surprise.** In Java, `<T extends Comparable<T>>` with `int` boxes to `Integer`; the autoboxing cost in hot loops is real and invisible in the source.
- **CRTP `static_cast` is unchecked.** `static_cast<const D&>(*this)` trusts that the derived type passed itself correctly. Pass the wrong type and you get undefined behavior, silently.
- **`dyn`/virtual loses monomorphization wins.** Choosing dynamic dispatch (`dyn Trait`, an interface-typed field) over a bounded generic re-introduces a vtable hop and boxing. Sometimes worth it (smaller code), but know the trade.

---

## Apply it

1. Find a real component where **Bounded Polymorphism** affects an interface or dependency.
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

- Which boundary is most affected by Bounded Polymorphism?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
