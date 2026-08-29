# Type Inference — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Type Inference** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Inference Is Static Typing Without the Typing

The single most important idea: **inference does not make your language dynamic.** When you write `var x = 5;`, the compiler decides *right then* that `x` is an `int`, bakes that into the program, and enforces it forever. This:

```java
var x = 5;
x = "hello";   // COMPILE ERROR — x is an int, always
```

is just as illegal as if you had written `int x = 5;`. The only thing inference removed is the word `int`. Everything else — the safety, the speed, the IDE autocomplete — is identical.

### 2. The Simple Rule: Look at the Initializer

For everyday local inference, the compiler follows a rule you could follow yourself: **look at the value on the right-hand side, take its type, give it to the variable.**

```go
count := 0          // 0 is an int   → count is int
name  := "Ada"      // "Ada" is a string → name is string
ok    := true       // true is a bool → ok is bool
ratio := 3.14       // 3.14 is a float64 → ratio is float64
```

There is nothing mysterious here. You can predict every one of these by asking, "What type is the thing on the right?"

### 3. Why a Literal Is Easy and an Empty List Is Hard

The compiler can only infer when there are **clues**. A literal is a perfect clue: `42` can only be a number, `"x"` can only be a string. But some initializers carry no clue:

```java
var list = new ArrayList<>();  // ArrayList of WHAT? No element to look at.
```

An *empty* list contains nothing, so there's nothing for the compiler to read. This is the recurring junior surprise: **inference fails not because the compiler is dumb, but because you genuinely didn't give it enough information.** The fix is to supply the missing clue — an annotation:

```java
var list = new ArrayList<String>();   // now the element type is explicit
```

### 4. Local Inference Has a Range Limit

The inference in `var`, `auto`, `:=`, and `<>` is **local**: it works *inside* a small scope but stops at boundaries you must annotate yourself. The classic boundary is a **function signature**:

```go
// You MUST write the parameter and return types — Go will not infer them.
func add(a int, b int) int {
    sum := a + b      // but INSIDE the body, := infers freely
    return sum
}
```

A useful mental split: **annotate the edges, infer the insides.** Function parameters and return types are edges; local variables are insides. (Languages like Haskell and OCaml lift even this restriction with whole-program inference — that's the next levels.)

### 5. The Compiler Reads More Than the Initializer (a Little)

Sometimes there's no initializer but there *is* a target. Java's diamond is the example: `List<String> xs = new ArrayList<>();`. Here the compiler reads the *declared* type on the left (`List<String>`) and fills the `<>` on the right. So inference can flow from the **expected type**, not just the initializer. You'll meet this idea formally later as "contextual typing" and "bidirectional checking"; for now, just notice the compiler sometimes looks left, not only right.

### 6. Return-Type Inference: Sometimes Yes, Usually Annotate

Languages vary on whether a function's *return* type can be inferred:

- **C++** (`auto` return type): yes — the compiler reads your `return` statements.
- **Rust:** no for top-level functions — you must write `-> Type`. (It infers everything *inside* the body, though.)
- **Go:** no — you always write the return type.
- **Java/C#:** no — methods always declare their return type.

The reason mainstream languages *require* return annotations even when they could infer them is **readability and error quality**: a written return type documents the function and localizes errors to that function instead of letting a mistake ripple out to every caller.

---

## Code Examples

The same idea — declare a local without writing its type — across the mainstream "local inference" languages.

### Go — `:=` short variable declaration

```go
package main

import "fmt"

func main() {
    count := 0          // int
    name := "Bakhodir"  // string
    pi := 3.14159       // float64
    ready := true       // bool

    // count = "x"      // would be: cannot use "x" (string) as int
    fmt.Printf("%T %T %T %T\n", count, name, pi, ready)
    // prints: int string float64 bool
}
```

`:=` is Go's inference operator. It only works for *new* locals inside a function. At package level and for function parameters, you write types.

### Java — `var` (since Java 10) and the diamond `<>`

```java
import java.util.ArrayList;
import java.util.List;

public class Infer {
    public static void main(String[] args) {
        var count = 0;                 // int
        var name = "Bakhodir";         // String
        var nums = new ArrayList<Integer>();  // ArrayList<Integer>

        // The diamond: type args inferred from the LEFT side
        List<String> words = new ArrayList<>();  // <> = <String>
        words.add("hi");

        // var cannot be used without an initializer:
        // var x;        // ERROR — nothing to infer from
        System.out.println(name + " " + count + " " + words);
    }
}
```

`var` only works on locals *with an initializer*. You cannot use it for fields, parameters, or return types.

### C# — `var`

```csharp
var count = 0;                  // int
var name = "Bakhodir";          // string
var list = new List<int>();     // List<int>

// var x;          // ERROR — no initializer, nothing to infer
```

C#'s `var` is identical in spirit to Java's: local, initializer-driven, fully static.

### C++ — `auto`

```cpp
#include <string>
#include <vector>

int main() {
    auto count = 0;              // int
    auto name = std::string{"Bakhodir"};  // std::string
    auto pi = 3.14;              // double
    std::vector<int> v = {1, 2, 3};
    for (auto x : v) {           // x is int, inferred from the vector
        (void)x;
    }
    // auto y;        // ERROR — auto needs an initializer
    return 0;
}
```

A subtle C++ note for later: `auto` strips references and `const` by default (`auto x = ref;` copies). Juniors should just know `auto` reads the initializer; the reference/const rules are a `middle.md` topic.

### Rust — function-body inference

```rust
fn main() {
    let count = 0;          // i32 (Rust's default integer)
    let name = "Bakhodir";  // &str
    let pi = 3.14;          // f64

    let mut nums = Vec::new();  // type not known YET...
    nums.push(1);               // ...now Rust knows it's Vec<i32>

    println!("{name} {count} {pi} {nums:?}");
}
```

Rust shows off something stronger than the others: `Vec::new()` had no type at first, but Rust *waited*, saw `nums.push(1)` later, and inferred `Vec<i32>` from the **usage**. That's a step up from "just read the initializer," and it's a preview of the real inference engine you'll meet in `middle.md`.

### Where inference fails — and the fix

```rust
fn main() {
    // let v = Vec::new();   // ERROR: type annotations needed
                             // (nothing is ever pushed, so no clue)

    let v: Vec<i32> = Vec::new();  // FIX 1: annotate the variable
    let w = Vec::<i32>::new();     // FIX 2: annotate the call
    let _ = (v, w);
}
```

```java
// var list = new ArrayList<>();  // ERROR / infers ArrayList<Object>
var list = new ArrayList<String>();  // FIX: give the element type
```

The pattern is always the same: **inference failed because you withheld the only clue. Supply it.**

---

## Coding Patterns

### Pattern 1: Infer when the right-hand side names the type

```java
var user = userRepository.findById(id);   // type is User — obvious, infer it
var users = new ArrayList<User>();         // type is in the expression — infer it
```

If a human reading the line already sees the type, the `var` keyword costs nothing and saves clutter.

### Pattern 2: Annotate when the right-hand side hides the type

```java
// var x = parse(input);            // x is... ? Reader has to chase parse().
Token x = parse(input);             // now the line is self-documenting.
```

### Pattern 3: Supply the clue when a container is empty

```rust
let scores: Vec<i32> = Vec::new();      // annotate the variable, OR
let scores = Vec::<i32>::new();         // annotate the constructor
```

```go
items := make([]string, 0)              // the make() call carries the type
```

### Pattern 4: Let the diamond mirror the declaration (Java)

```java
Map<String, List<Integer>> m = new HashMap<>();   // <> repeats the left side
```

Write the full type once on the left; let `<>` avoid repeating it on the right.

### Pattern 5: Annotate function edges, infer locals

```rust
fn parse_line(line: &str) -> Option<i32> {   // edges: annotated
    let trimmed = line.trim();               // local: inferred
    let parsed = trimmed.parse();            // local: inferred from context
    parsed.ok()
}
```

---

## Best Practices

- **Treat `var`/`auto`/`:=` as "the type is clear from this line."** If it isn't clear, write the type. This single guideline resolves most `var` style debates.
- **Always annotate public API boundaries.** Method parameters and return types are read far more than they're written; make them explicit even when a language *could* infer them.
- **Never assume inference makes code dynamic.** `var x = 5` is `int x = 5`. The type is fixed.
- **When inference fails, read the error literally.** "type annotations needed" or "cannot infer" means *you* withheld a clue, not that the compiler is broken. Find the empty container or ambiguous literal and label it.
- **Watch the default numeric type.** A bare integer literal becomes `int`/`i32`; a bare float becomes `double`/`f64`. If you need `long`/`i64`, annotate or use a typed literal (`0L`, `0i64`).
- **Use your IDE's "show inferred type" feature** before committing inferred locals — confirm the compiler inferred what you expected.
- **Be stricter in code that's reviewed in diffs.** A reviewer reading a `.diff` in a terminal has no IDE hover; explicit types help them.

---

## Edge Cases & Pitfalls

- **Empty containers infer nothing.** `var list = new ArrayList<>();` and `let v = Vec::new();` have no element to read. Annotate the element type.
- **Numeric literals default surprisingly.** `var x = 0;` is `int`, not `long` or `byte`. `auto x = 0;` is `int`, not `size_t`. If a later `x = someBigValue` overflows, the bug is the inferred narrow type.
- **`var` with no initializer is illegal.** `var x;` has nothing to infer from — every local-inference language rejects it. You must initialize on the same line.
- **The inferred type can be wider or narrower than you wanted.** `var x = condition ? 1 : 2.0;` might infer `double` (the common type), surprising you if you expected `int`.
- **C++ `auto` drops `const` and references.** `const std::string& r = get(); auto x = r;` makes `x` a **copy**, not a reference. Use `auto&` / `const auto&` when you want to bind by reference. (Detail for `middle.md`, but the copy can bite a junior.)
- **`var` hides the type from readers without an IDE.** Code review tools, `git diff`, and printouts don't show hovers. Over-using `var` on non-obvious lines hurts reviewers.
- **Float/int mixing.** `auto avg = sum / count;` where both are `int` does **integer** division — inference faithfully gives you `int`, including the truncation bug. Inference reflects the expression; it doesn't fix your arithmetic.
- **It is *not* dynamic typing.** The most common beginner misconception. You cannot reassign `var x = 5` to a string later. If you came from Python/JavaScript, unlearn this immediately.

---

## Apply it

1. Choose one small, known input for **Type Inference**.
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

- What problem does Type Inference solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
