# What Is a Type — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **What Is a Type** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. A Type Is a Set of Values + Operations

Take `bool`. Its **set of values** is exactly `{true, false}` — nothing else is a `bool`. Its **operations** are `&&`, `||`, `!`, equality. Take `byte` (unsigned). Its set is `{0, 1, 2, ..., 255}`. Its operations are arithmetic and comparison. The pattern repeats for every type:

| Type | The set of values | Some valid operations |
|------|-------------------|----------------------|
| `bool` | `{true, false}` | `&&`, `||`, `!`, `==` |
| `byte` | `{0 ... 255}` | `+`, `-`, `&`, `<` |
| `int` | machine integers | `+`, `-`, `*`, `/`, `<`, `==` |
| `string` | all finite text | concat, `length`, slice, `==` |
| `Point{x,y}` | all `(x, y)` pairs | `.x`, `.y`, distance, `==` |

When you ask "what is the type of this value?", you're really asking "**which set does it belong to, and what am I allowed to do with it?**" The two halves matter equally. A type that listed values but not operations would be useless — you'd know what you have but not what you can do. A type that listed operations but not values would be incoherent — operations need something to operate on.

### 2. Types Classify Values

Another way to see it: a type is a **label that sorts values into bins**. Every value carries (or can be assigned) a label that says which bin it lives in. The number `42` is in the `int` bin. `"42"` is in the `string` bin. They *look* alike on paper but live in different bins, and the operations differ: `42 + 1` is `43`, but `"42" + 1` is either an error or `"421"` depending on the language. The type — the bin — is what decides.

Classification is the foundation of everything else. Once values are sorted into bins, the type system can enforce a single, simple rule: **only apply an operation to values in a bin that supports it.** That one rule prevents an enormous range of bugs.

### 3. A Type Is a Contract / a Promise

This is the framing that will serve you best in real code. When you write:

```
func sendEmail(to EmailAddress, subject string) error
```

every type here is a **contract**:

- `to EmailAddress` promises: *this is a valid email address* — not just any string, but one that passed whatever check makes an `EmailAddress`. The function doesn't have to re-validate.
- `subject string` promises: *this is text*.
- returns `error` promises: *the caller will get back something that says whether it worked*.

The types document the function's expectations and guarantees **in a way the compiler enforces**. Comments lie; types don't. If you try to call `sendEmail("not-an-email", 5)`, the type system stops you. A type is a promise that someone (the compiler, or the runtime) actually keeps for you.

### 4. Compile Time vs Run Time (Set-Up)

There are two different moments a type can matter:

- **At compile time**, the *variable or expression* has a **static type** — what the compiler thinks it is. In `int x = 5;`, the static type of `x` is `int`, decided before the program runs.
- **At run time**, the *value* has a **dynamic type** — its actual runtime tag. In a dynamically typed language, `x = 5` makes `x` hold a value whose runtime type is `int`; later `x = "hi"` makes it hold a value whose runtime type is `string`.

Some languages check types at compile time (Java, Go, Rust, TypeScript). Some check at run time (Python, JavaScript, Ruby). The next level (the middle file) is entirely about this static-vs-dynamic distinction. For now, hold onto the idea: **the static type is attached to the name; the dynamic type is attached to the value.**

### 5. Primitive vs Composite Types

- **Primitive types** are the indivisible building blocks: `int`, `float`, `bool`, `char`, `byte`. They come built into the language.
- **Composite (compound) types** are built by combining other types:
  - A **list/array** `[]int` is "many `int`s in order."
  - A **struct/record** `Point{x int, y int}` is "an `int` *and* an `int`, with names."
  - A **map/dictionary** `map[string]int` is "a lookup from `string` to `int`."
  - A **tuple** `(int, string)` is "an `int` *and* a `string`, by position."

You build big types out of small ones. Almost every type you'll define yourself — a `User`, an `Order`, a `Tree` — is composite, assembled from primitives and other composites.

### 6. What a Type System *Does* For You

A type system isn't just bookkeeping. It buys you four concrete things:

1. **It prevents whole classes of errors.** You cannot call a string method on a number, cannot pass two arguments in the wrong order if their types differ, cannot forget a field a struct requires. These bugs become *impossible to write*, not merely caught later.
2. **It documents intent.** Reading `func price(item Product) Money` tells you more than any comment. The signature *is* the documentation, and it can't go stale.
3. **It powers your tools.** Autocomplete, "go to definition," refactoring, inline error squiggles — all of it runs on type information. When your editor knows `user` is a `User`, it can offer you `.name` and `.email`.
4. **It enables fast code.** Knowing a value is an `int` lets the compiler pick the right machine instructions and lay out memory tightly (more on this in deeper levels).

### 7. "Make Illegal States Unrepresentable"

The most powerful idea you'll take from thinking in types: **design your types so that bad states can't even be expressed.** If an order can be `Pending`, `Shipped`, or `Cancelled`, don't model it as three booleans (`isPending`, `isShipped`, `isCancelled`) — that allows nonsense like "pending *and* shipped at once." Model it as a single type with exactly three possibilities. Now the impossible state literally cannot be constructed. The type does the work that validation code, tests, and code review would otherwise have to do — and it does it for free, forever.

---

## Code Examples

We'll show the same handful of ideas across languages: that values have types, that operations are type-restricted, and that mismatches get caught (some at compile time, some at run time).

### Python — types exist even without annotations

```python
x = 42          # value 42 has dynamic type int
y = "42"        # value "42" has dynamic type str

print(type(x))  # <class 'int'>
print(type(y))  # <class 'str'>

print(x + 1)    # 43   — '+' on int means addition
print(y + "!")  # 42!  — '+' on str means concatenation

print(x + y)    # TypeError: unsupported operand type(s) for +: 'int' and 'str'
```

Python doesn't make you *write* the types, but every value still *has* one (its dynamic type), and `+` does completely different things depending on it. The last line is a **type error** — caught at run time, the moment the bad operation executes. The type `int` is a set (whole numbers) with operations (`+` = addition); the type `str` is a set (text) with operations (`+` = concatenation). Same symbol, different operation, because different type.

### Python with type hints — writing the promise down

```python
def average(numbers: list[float]) -> float:
    return sum(numbers) / len(numbers)
```

`numbers: list[float]` is an **annotation**: the promise "this is a list of floats." `-> float` promises a float comes back. Python itself doesn't enforce these at run time, but a type checker like `mypy` reads them and flags mistakes *before* you run — turning a runtime crash into a compile-time warning.

### Java — types checked before the program runs

```java
int x = 42;
String y = "42";

System.out.println(x + 1);   // 43
System.out.println(y + "!"); // 42!

// int z = x + y;            // COMPILE ERROR: bad operand types
String w = x + y;            // "42" + 42 -> "4242" (Java converts here)
```

In Java the type is **part of the variable**. `int x` means *x is forever an int*. The commented line doesn't even compile — the type checker rejects it before any code runs. (Note Java's `+` quietly converts `x` to a string in the last line; that's a language choice, not a universal rule.)

### TypeScript — types layered on top of JavaScript

```typescript
function greet(name: string): string {
  return "Hello, " + name;
}

greet("Ada");   // ok
greet(42);      // COMPILE ERROR: Argument of type 'number'
                //                is not assignable to parameter of type 'string'
```

TypeScript adds a static type layer over dynamically typed JavaScript. The `: string` annotation is a contract the TypeScript compiler enforces. After compilation the types are **erased** — the JavaScript that runs has no types left. The checking happened entirely before run time.

### Go — types as documented contracts

```go
type EmailAddress string

func send(to EmailAddress, subject string) {
    // ...
}

func main() {
    var addr EmailAddress = "ada@example.com"
    send(addr, "Hi")        // ok
    // send("plain", "Hi")  // ok-ish: untyped string literal converts
    // send(5, "Hi")        // COMPILE ERROR: cannot use 5 as EmailAddress
}
```

Here `EmailAddress` is a *distinct type* even though it's "just a string" underneath. Giving it its own name turns a bag of characters into a contract: a function taking `EmailAddress` documents that it expects an address, and the compiler tracks the distinction.

### Rust — types you can't lie about

```rust
fn main() {
    let x: i32 = 42;
    let y: &str = "42";

    println!("{}", x + 1);   // 43

    // let z = x + y;        // COMPILE ERROR: cannot add `&str` to `i32`
    let n: i32 = y.parse().unwrap(); // explicit conversion str -> i32
    println!("{}", x + n);   // 84
}
```

Rust never silently converts between types. To turn the string `"42"` into the number `42`, you must *explicitly* `parse()` it. The type system forces every conversion to be deliberate, which removes a whole category of "I didn't realize that was a string" bugs.

### Modeling a state — making illegal states unrepresentable

```typescript
// BAD: three booleans allow impossible combinations
type OrderBad = {
  isPending: boolean;
  isShipped: boolean;
  isCancelled: boolean;
}; // pending AND shipped AND cancelled all true? nonsense, but allowed

// GOOD: one type, exactly three legal states
type Order =
  | { status: "pending" }
  | { status: "shipped"; trackingId: string }
  | { status: "cancelled"; reason: string };
```

The `Order` type makes the impossible *unrepresentable*: there's no way to construct an order that is both shipped and cancelled, and "shipped" *requires* a `trackingId` while "cancelled" *requires* a `reason`. The type encodes the rules, so no validation code or test is needed to enforce them.

---

## Coding Patterns

### Pattern 1: Name your domain types instead of using primitives

```go
type UserID string     // not just "string"
type Cents int         // money in cents, not a bare int
```

This "type alias for meaning" pattern (sometimes called *making the implicit explicit*) prevents mixing up a `UserID` with a `ProductID` even though both are strings underneath. The compiler now treats them as different.

### Pattern 2: Let the type narrow the valid set

```python
from enum import Enum

class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"
```

Instead of accepting any `str` for a color (where typos like `"gren"` slip through), an enum restricts the set of legal values to exactly three. The type *is* the validation.

### Pattern 3: Use composite types to group related data

```go
type Point struct {
    X int
    Y int
}
```

Rather than passing `x` and `y` as two separate ints everywhere (and risking swapping them), bundle them into one type. The struct is the unit you pass around.

### Pattern 4: Push checks into the type, not into runtime guards

Prefer `func setAge(a PositiveInt)` over `func setAge(a int)` with a runtime `if a < 0 { panic }`. If you can express the constraint as a type, the check happens everywhere automatically, and the impossible case never reaches your function.

---

## Best Practices

- **Give meaningful things their own types.** A `UserID` is not "just a string." Naming the type prevents whole categories of mix-ups.
- **Write annotations on public boundaries.** Even in dynamically typed languages, annotate function signatures — they're documentation that tools can check.
- **Prefer the narrowest type that works.** If a function only needs to *read* a list, take a read-only type. If a value can only be one of three things, use an enum, not a string.
- **Let inference handle the obvious; annotate the meaningful.** `x := 5` doesn't need `x int` — it's obvious. A function's return type usually *should* be written, because it's a contract.
- **Make illegal states unrepresentable.** Design types so bad combinations can't be constructed. This is the single highest-value habit in this whole topic.
- **Treat type errors as a gift.** A compile error is the type system catching a bug for free. Don't paper over it with a cast — understand why it fired.
- **Don't fight the type system with escape hatches.** `any`, `Object`, unchecked casts, and `# type: ignore` throw away the very protection you wanted.

---

## Edge Cases & Pitfalls

- **`"5"` is not `5`.** The string `"5"` and the integer `5` are different types in different bins. Mixing them is the single most common beginner bug. Always know whether you're holding text or a number.
- **`null`/`None`/`nil` sneaks past types in many languages.** A variable typed `User` can secretly be `null` in Java, Go, and others — and then `user.name` crashes. Languages like Rust and Kotlin make nullability part of the type so this can't happen silently.
- **Silent conversions hide bugs.** JavaScript's `[] + {}`, Java's `int + String`, and similar implicit conversions can produce surprising results. Know your language's conversion rules.
- **A type annotation in Python is not enforced at run time.** `def f(x: int)` will happily run with a string unless you use a checker like `mypy`. The annotation is a promise *you* must verify with tooling.
- **Two types with the same underlying representation are still different.** A `UserID` and a `ProductID` that are both strings are *not* interchangeable if you declared them as distinct types — and that's the point.
- **Casting lies to the type system.** When you force a value to a type with a cast, you're overriding the checker's judgment. If you're wrong, the bug just moves to run time.

---

## Common Mistakes

1. **Treating types as a formality to satisfy the compiler** instead of a design tool. The point isn't to make errors go away; it's to model your data correctly.
2. **Using `string` for everything.** Dates, money, IDs, and enums all become indistinguishable bags of characters — and bugs slip through. Give them real types.
3. **Reaching for `any`/`Object`/`interface{}` to silence an error.** This discards the type information and pushes the bug to run time.
4. **Confusing the variable's static type with the value's runtime type.** A variable declared `Animal` may hold a `Dog` at run time; the two are different questions.
5. **Assuming a Python annotation prevents bad input.** It doesn't run anything — you need `mypy` or runtime validation.
6. **Casting to make an error disappear** without checking whether the cast is actually valid.
7. **Modeling states with multiple booleans** instead of one type with the legal states, allowing impossible combinations.

---

## Apply it

1. Choose one small, known input for **What Is a Type**.
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

- What problem does What Is a Type solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
