# Bounded Polymorphism — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Bounded Polymorphism** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Unbounded `<T>`: you can only move it

Start with the most generic function imaginable:

```java
static <T> T identity(T x) { return x; }
```

This compiles, works for *every* type, and is correct — but notice it does *nothing* to `x`. It can't. Try to add even one operation:

```java
static <T> T bigger(T a, T b) {
    return a > b ? a : b;   // COMPILE ERROR: operator > undefined for T
}
```

The compiler refuses. From its point of view, `T` could be `String`, `LocalDate`, `Thread`, `JButton`, or your own `class Potato`. Most of those have no `>`. The promise "works for every `T`" forbids any operation that isn't shared by *literally every* type.

A useful way to see it: with unbounded `<T>`, the only things you can do with a `T` value are **store it, pass it, return it, and put it in / take it out of generic containers**. You can shuffle values around. You cannot inspect them.

### 2. The bound adds a capability

Now constrain `T` to types that *can* be compared:

```java
static <T extends Comparable<T>> T bigger(T a, T b) {
    return a.compareTo(b) >= 0 ? a : b;   // OK now
}
```

By writing `extends Comparable<T>`, you told the compiler: *"I will only ever be called with types that implement `Comparable`."* In return, the compiler now lets you call `Comparable`'s methods — `compareTo` — inside the body. You **narrowed** the set of acceptable `T`s (no more `Thread`, no more `Potato`-without-`Comparable`) and in exchange you **gained** the `compareTo` capability.

That's the whole bargain of bounded polymorphism, in one sentence:

> **A bound shrinks *who can call you* so that it can grow *what you can do.***

### 3. Reading a bound in five languages

The syntax differs; the idea is identical. "`T`, but only types that can be ordered":

```java
<T extends Comparable<T>>      // Java   (subtype bound)
```
```csharp
where T : IComparable<T>       // C#     (subtype bound)
```
```swift
<T: Comparable>                // Swift  (protocol bound)
```
```rust
T: Ord                         // Rust   (trait bound)
```
```haskell
Ord a => ...                   // Haskell (typeclass constraint)
```

In Go, the same shape uses a *constraint interface*:

```go
func MaxT cmp.Ordered T { ... }   // Go 1.21+ (cmp.Ordered constraint)
```

Read every one of these as: "*`T` is any type, **as long as** it provides ordering.*" The keyword (`extends`, `where`, `:`, `=>`) is just punctuation around the same contract.

### 3.5 Upper bounds are the common case

When you write `extends Comparable<T>` or `: Ord`, you're stating an **upper bound**: `T` must be *at most* as general as the bound — it must implement it. This is by far the most common kind of bound and the only one you need at the junior level. (Lower bounds and variance — `? super T` — exist but solve a different problem, namely "what can flow *into* a generic container," and belong to a later discussion.)

### 4. Why the constraint propagates

A subtle but important rule: if your function uses a bounded helper, *you* must carry the same bound.

```java
static <T extends Comparable<T>> T maxOf(List<T> xs) {
    T best = xs.get(0);
    for (T x : xs) best = bigger(best, x);   // bigger needs Comparable
    return best;
}
```

`maxOf` calls `bigger`, and `bigger` requires `T extends Comparable<T>`. So `maxOf` must *also* declare `T extends Comparable<T>` — otherwise it couldn't satisfy `bigger`'s requirement. Bounds **flow upward** through the call chain. You can never have *less* constraint than the things you call. (At the junior level just remember: if the compiler complains that a bound is "not satisfied," you usually need to repeat the bound on the *outer* function too.)

### 5. The bound is a contract, checked at the call site

When someone calls `bigger(a, b)`, the compiler checks at the *call site* that the actual type really does satisfy the bound:

```java
bigger("apple", "banana");       // OK: String implements Comparable<String>
bigger(new Thread(), new Thread()); // ERROR: Thread is not Comparable
```

So the safety is two-sided. Inside the function, the compiler *gives* you the capability. At the call site, it *demands* you supply a type that has it. Neither side can cheat. That's why bounded generics are both flexible *and* type-safe — there's no cast, no runtime "does this support `<`?" check, no `ClassCastException`. It's settled at compile time.

---

## Code Examples

The running example everywhere: a generic **`max`** of two values. First the unbounded version that *won't compile*, then the bounded version that does.

### Java

```java
// WON'T COMPILE — unbounded T has no ordering
static <T> T maxBroken(T a, T b) {
    return a.compareTo(b) >= 0 ? a : b;   // error: cannot find symbol compareTo
}

// WORKS — bounded by Comparable
static <T extends Comparable<T>> T max(T a, T b) {
    return a.compareTo(b) >= 0 ? a : b;
}

public static void main(String[] args) {
    System.out.println(max(3, 7));            // 7  (Integer is Comparable)
    System.out.println(max("pear", "apple")); // "pear" (String is Comparable)
    // max(new Object(), new Object());       // would not compile: Object isn't Comparable
}
```

The bound `T extends Comparable<T>` is what unlocks `a.compareTo(b)`. Without it, the *exact same body* is rejected.

### Rust

```rust
// WON'T COMPILE — no ordering on an unbounded T
// fn max_broken<T>(a: T, b: T) -> T { if a >= b { a } else { b } }
//                                         ^^^^^^ error: binary operation `>=` not supported

// WORKS — trait bound T: Ord (or PartialOrd) provides comparison
fn max<T: Ord>(a: T, b: T) -> T {
    if a >= b { a } else { b }
}

fn main() {
    println!("{}", max(3, 7));               // 7
    println!("{}", max("pear", "apple"));    // "pear"
}
```

Rust spells the bound `T: Ord`. The `>=` operator works because the `Ord` trait provides it. (Rust's standard library already ships `std::cmp::max`, but this shows the mechanism.)

### Go

```go
package main

import (
	"cmp"
	"fmt"
)

// WORKS — T is constrained to ordered types via cmp.Ordered
func MaxT cmp.Ordered T {
	if a > b {
		return a
	}
	return b
}

func main() {
	fmt.Println(Max(3, 7))             // 7
	fmt.Println(Max("pear", "apple"))  // "pear"
}
```

Go expresses the bound as a *constraint interface*, `cmp.Ordered`, listing the types that support `<`/`>`. An unconstrained `[T any]` would reject `a > b` exactly like the others.

### Swift

```swift
// WORKS — protocol bound T: Comparable
func maxOf<T: Comparable>(_ a: T, _ b: T) -> T {
    return a >= b ? a : b
}

print(maxOf(3, 7))            // 7
print(maxOf("pear", "apple")) // "pear"
```

Swift bounds by *protocol*: `T: Comparable`. The `>=` operator is a requirement of the `Comparable` protocol, so the body may use it.

### C#

```csharp
static T Max<T>(T a, T b) where T : IComparable<T>
{
    return a.CompareTo(b) >= 0 ? a : b;
}

// Max(3, 7) -> 7 ;  Max("pear","apple") -> "pear"
```

C# uses a `where T : IComparable<T>` clause — same upper-bound idea, different keyword.

### Haskell

```haskell
-- The constraint `Ord a` before the => means "for any type a that is Ord"
maxOf :: Ord a => a -> a -> a
maxOf a b = if a >= b then a else b

-- maxOf 3 7        => 7
-- maxOf "pear" "apple" => "pear"
```

Haskell writes the constraint as `Ord a =>`. Without `Ord a`, the `>=` would be a type error: `a` would be fully unbounded and ordering wouldn't be in scope.

### Side-by-side: unbounded vs bounded (Java)

```java
static <T> int countNonNull(T a, T b) {       // fine: only moves/compares-to-null
    int n = 0;
    if (a != null) n++;
    if (b != null) n++;
    return n;
}
```

```java
static <T extends Comparable<T>> boolean inOrder(T a, T b) {  // needs the bound
    return a.compareTo(b) <= 0;
}
```

The first is happy unbounded because `!= null` is allowed on any reference. The second *requires* the bound because `compareTo` is not.

---

## Coding Patterns

### Pattern 1: Bound by exactly the interface you call — and no more

```rust
// You only need to *print* it, so bound by Display, not Ord/Clone/etc.
fn announce<T: std::fmt::Display>(x: T) {
    println!("Here is: {}", x);
}
```

Don't over-constrain. If you only print `T`, don't require `Ord`. The minimal bound maximizes reuse.

### Pattern 2: Combine bounds when you need more than one capability

```rust
fn max_and_print<T: Ord + std::fmt::Display>(a: T, b: T) {
    let m = if a >= b { a } else { b };
    println!("max is {}", m);
}
```
```java
static <T extends Comparable<T>> void show(T a, T b) { ... } // single bound here
```

`T: Ord + Display` (Rust) or `<T extends A & B>` (Java) requires *both* capabilities. (Multiple bounds get a fuller treatment in `middle.md`.)

### Pattern 3: Propagate the bound up the call chain

```java
static <T extends Comparable<T>> T maxOf(List<T> xs) {  // must repeat the bound
    T best = xs.get(0);
    for (T x : xs.subList(1, xs.size()))
        if (x.compareTo(best) > 0) best = x;
    return best;
}
```

If the body uses ordering, the signature must promise ordering. The bound isn't optional decoration.

### Pattern 4: Let the standard library's bound do the work

```go
import "slices"
// slices.Max requires cmp.Ordered internally — you just supply an ordered type
m := slices.Max([]int{3, 1, 4, 1, 5})  // 5
```

Most standard libraries already wrap the common bounds (`sort`, `max`, `min`). Use them before writing your own bounded helper.

---

## Best Practices

- **Bound by the smallest interface that compiles.** If `Comparable` is enough, don't require your own bigger interface. Smaller bounds accept more types.
- **Let the use site of the capability drive the bound.** Add a bound *because* the body calls a method, not "just in case."
- **Repeat bounds up the call chain honestly.** When the compiler says a bound isn't satisfied, the fix is usually to add the same bound to the calling function, not to cast or suppress.
- **Prefer standard bounds (`Comparable`, `Ord`, `Eq`, `Hash`, `Number`) over hand-rolled interfaces** when a standard one fits — they're already implemented by built-in types.
- **Name the capability, not the type, in your head:** "this needs *ordering*," "this needs *equality*." That tells you which bound to reach for.
- **Don't bound an identity/move-only function.** If you only store and return `T`, unbounded is correct and maximally reusable.
- **Read the bound aloud as "any type that can …".** `<T extends Comparable<T>>` = "any type that can be compared to itself." It demystifies the syntax.

---

## Edge Cases & Pitfalls

- **"Why can't I call `.toString()` / `<` / `.equals()` on `T`?"** Because `T` is unbounded. The fix is a bound (or, for `equals`/`toString` in Java specifically, note those exist on `Object` so they *are* callable — but a *meaningful, type-specific* comparison still needs `Comparable`).
- **Over-constraining.** Requiring `<T extends Comparable<T>>` on a function that never compares anything needlessly rejects valid types. The compiler won't warn you — your *callers* will, when their type is refused.
- **Forgetting to propagate the bound.** Calling a bounded helper from an unbounded function fails to compile with a "bound not satisfied" error. Add the bound to the outer signature.
- **Confusing the bound with a cast.** A bound is checked at compile time and never throws. If you instead cast `T` to `Comparable` at runtime, you've thrown away the safety and invited a `ClassCastException`.
- **Java's `Comparable<T>` is recursive.** `T extends Comparable<T>` mentions `T` *inside* its own bound. This "self-referential" shape is normal but looks alien at first; it just means "comparable *to its own type*." The full story (F-bounded polymorphism) is in `middle.md`/`senior.md`.
- **`Object` is not `Comparable`.** `max(new Object(), new Object())` won't compile. Many beginners expect "everything is comparable" — it isn't.
- **Operators vs methods.** In Java/C# you call a *method* (`compareTo`), in Rust/Swift/Haskell/Go you use an *operator* (`>=`, `>`). Both are "use the bound's capability"; only the surface syntax differs.
- **A bound on the type ≠ a bound on its elements.** Bounding `T` says nothing about a `List<T>`'s other operations. Each capability you need is its own bound.

---

## Apply it

1. Choose one small, known input for **Bounded Polymorphism**.
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

- What problem does Bounded Polymorphism solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
