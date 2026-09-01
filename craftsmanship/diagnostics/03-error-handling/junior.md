# Error Handling — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Error Handling** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Error Handling Roadmap](README.md)
> **Focus:** What is an error? Why does it need to be "handled"? The four major language models. Your first instincts.

---

## Core Concepts

### 1. Errors Are Communication

When a function fails, the value it returns is just as much "data" as a successful result. Errors are not a side concern — they are part of the **contract** of every function. The function says: *"On success I give you X; on failure I tell you why."*

Whether your language expresses that with exceptions or returned values doesn't change the underlying truth: every function has a happy path and a sad path, and both need a vocabulary.

### 2. Errors Are Not Bugs

This is the single most important distinction in this whole topic, and the one beginners most often miss.

- A **bug** is a defect — your code is wrong. (You tried to read element `100` from a list of size `5`. You divided by zero because you forgot to check.)
- An **error** is a thing the world did to you. (The disk is full. The user typed `"twenty"` into a number field. The remote server timed out.)

A bug means you must **fix the code**. An error means you must **decide what to do about reality**. These two require completely different responses, and mixing them up is the source of most beginner pain.

### 3. Errors Travel Up

In every error model, the error originates somewhere *deep* in your code (a low-level function near the OS, the network, the database) and has to *travel up* to a higher level that knows what to do about it. A function that reads from a file doesn't know if you wanted to show the user a friendly message or retry — but `main()` or your HTTP handler does. Error handling is the *plumbing* between where failure happens and where it can be answered.

### 4. The Caller Decides

A good function does not decide what an error *means* — it just **reports it accurately**. The caller decides whether to retry, log, swallow, escalate, or crash. A function that "helpfully" prints to stderr and returns `nil` has taken away a decision that wasn't its to make.

### 5. Silence is the Enemy

The single most dangerous thing a program can do with an error is **ignore it**. Silent failures are the reason production data is sometimes wrong for months before anyone notices. We will repeat this in every level of this topic, because it is the single most common mistake.

---

## The Four Error Models

Programming languages don't agree on what an error should *look like*. There are four major schools of thought. As a junior, you don't need to take sides — you need to recognize them.

### Model 1 — Exceptions (Java, Python, C#, JavaScript, Ruby, C++)

A function can `throw` (or `raise`) at any point. The exception then **unwinds the call stack** automatically — every function above is skipped — until some function catches it or the program crashes.

The key property: exceptions are *invisible in the type signature* (in most languages). You can't tell by looking at a function whether it throws. You have to read the docs or the body. This is both the strength (you don't pollute every signature) and the weakness (you can be surprised).

### Model 2 — Return Values (Go, C)

Every function that can fail returns an error alongside its result. The caller is *forced* to look at the error variable — there is no "automatic" propagation.

```go
user, err := getUser(42)
if err != nil {
    return err
}
```

The key property: errors are **completely visible**. The cost: you write `if err != nil` a lot. Go programmers do not see this as boilerplate; they see it as *honesty about how often things fail*.

### Model 3 — `Result<T, E>` (Rust, Swift, Scala/Haskell-style)

The return type itself wraps either success or failure. You cannot use the value without explicitly handling both cases. Rust adds a `?` operator that propagates errors with very little syntax noise.

```rust
fn get_user(id: u64) -> Result<User, DbError> { ... }

let user = get_user(42)?;  // returns Err early if it fails
```

The key property: failure is in the **type system**. The compiler will not let you forget.

### Model 4 — Panic / Abort

For *truly* impossible situations — array index out of bounds, integer division by zero, "invariant X must hold and it doesn't" — most languages provide a way to immediately stop. Go has `panic`, Rust has `panic!`, Python has `assert` and direct interpreter crashes, Java has `Error` (separate from `Exception`).

This is **not** an error model for everyday failures. It is the language's way of saying *"this should be impossible; if it happened, the program is corrupt and must not continue."*

---

## Code Examples

We'll write the same trivial function — *"divide a by b, but b might be zero"* — in all four styles.

### Go (Return Value)

```go
package main

import (
    "errors"
    "fmt"
)

// ErrDivByZero is exported so callers can check for it.
var ErrDivByZero = errors.New("division by zero")

func divide(a, b float64) (float64, error) {
    if b == 0 {
        return 0, ErrDivByZero
    }
    return a / b, nil
}

func main() {
    result, err := divide(10, 0)
    if err != nil {
        fmt.Println("could not divide:", err)
        return
    }
    fmt.Println("result:", result)
}
```

Two return values. The caller is *physically prevented* from forgetting to look at `err` — well, almost: they can use `_` to discard it, but doing so is conspicuous.

### Python (Exception)

```python
class DivisionByZeroError(ValueError):
    """Raised when divide() is called with b == 0."""
    pass

def divide(a: float, b: float) -> float:
    if b == 0:
        raise DivisionByZeroError("b must not be zero")
    return a / b

if __name__ == "__main__":
    try:
        result = divide(10, 0)
        print("result:", result)
    except DivisionByZeroError as e:
        print("could not divide:", e)
```

Only one return value. The error path is in a *separate channel* — `try` / `except`.

### Java (Checked Exception)

```java
public class DivisionByZeroException extends Exception {
    public DivisionByZeroException(String message) {
        super(message);
    }
}

public class Calculator {

    public double divide(double a, double b) throws DivisionByZeroException {
        if (b == 0) {
            throw new DivisionByZeroException("b must not be zero");
        }
        return a / b;
    }

    public static void main(String[] args) {
        Calculator c = new Calculator();
        try {
            double result = c.divide(10, 0);
            System.out.println("result: " + result);
        } catch (DivisionByZeroException e) {
            System.out.println("could not divide: " + e.getMessage());
        }
    }
}
```

Notice `throws DivisionByZeroException` in the signature — Java forces callers to deal with it. We'll revisit checked vs unchecked exceptions in `middle.md`.

### Rust (`Result<T, E>`)

```rust
#[derive(Debug)]
pub enum MathError {
    DivisionByZero,
}

pub fn divide(a: f64, b: f64) -> Result<f64, MathError> {
    if b == 0.0 {
        return Err(MathError::DivisionByZero);
    }
    Ok(a / b)
}

fn main() {
    match divide(10.0, 0.0) {
        Ok(result) => println!("result: {}", result),
        Err(e) => println!("could not divide: {:?}", e),
    }
}
```

The return type *is* the error contract. There is no way to use the value without handling both branches.

### A fifth — Panic (for completeness, NOT recommended for this case)

```go
func divide(a, b float64) float64 {
    if b == 0 {
        panic("division by zero") // BAD: this is a recoverable expected error
    }
    return a / b
}
```

This is *wrong* for `divide`, because division-by-zero is something the caller can sensibly handle. Reserve `panic` for *truly* impossible situations, not "this might happen if my user is sloppy."

---

## Pros & Cons of Each Model

| Model | Pros | Cons |
|-------|------|------|
| **Exceptions** | Clean happy-path code. Easy to centralize error handling at a high level. Stack traces come for free. | Errors are invisible in signatures. Surprising control flow. Performance cost in some languages. Encourages "catch-all" that hides bugs. |
| **Return values (Go-style)** | Total visibility — you can see every error path. Forces the programmer to think about failure on every call. No hidden control flow. | Verbose. Repetitive `if err != nil` boilerplate. Easy to *forget* to wrap an error (lose context). |
| **`Result<T, E>`** | Type-safe — you literally can't ignore an error. Excellent for refactoring (compiler finds every call site). | Requires sum types / pattern matching, which not all languages have ergonomically. Can be verbose without `?`-style sugar. |
| **Panic / Abort** | Honest: when the program is in an impossible state, crashing is *safer* than continuing. | Misused for ordinary errors leads to crash-on-typo bugs. No graceful recovery without `recover()` / signal handling, which complicates the model. |

There is no "right" model — they reflect different cultural beliefs about *what's important*. Exception languages prioritize **clean call sites**; return-value languages prioritize **honest call sites**; Result-based languages prioritize **compile-time guarantees**.

---

## Coding Patterns

Patterns you'll see repeatedly at junior level — recognize them, use them.

### Pattern 1 — Guard at the boundary

Check for failure *first*, get it out of the way, then write the happy path:

```python
def transfer(from_account, to_account, amount):
    if amount <= 0:
        raise ValueError("amount must be positive")
    if from_account.balance < amount:
        raise InsufficientFundsError(from_account.id)
    # ... happy path
```

This is called "early return" or "guard clause" — it keeps the main flow indented at one level.

### Pattern 2 — Return early on error (Go)

```go
func processOrder(id string) error {
    order, err := fetchOrder(id)
    if err != nil {
        return err
    }

    if err := validate(order); err != nil {
        return err
    }

    if err := charge(order); err != nil {
        return err
    }

    return ship(order)
}
```

A staircase down, with the happy result at the bottom.

### Pattern 3 — Try / catch at the top

In exception languages, the typical layout is: *throw freely deep in the code, catch at one well-defined boundary*:

```python
@app.route("/orders/<id>")
def get_order(id):
    try:
        order = order_service.fetch(id)
        return jsonify(order)
    except OrderNotFound:
        return "not found", 404
    except DatabaseError:
        return "internal error", 500
```

The handler in the framework is the *boundary* where errors get translated into HTTP responses.

### Pattern 4 — Match on Result (Rust)

```rust
match get_user(id) {
    Ok(user) => render(user),
    Err(UserError::NotFound) => render_404(),
    Err(UserError::Db(e)) => render_500(e),
}
```

Every branch is visible; the compiler ensures nothing is forgotten.

---

## Clean Code

A junior who follows these will already be ahead of most production code:

1. **Don't swallow errors.** An empty `except: pass` or `catch (Exception e) {}` is a bug.
2. **Be specific.** Catch *only* the errors you actually know how to handle. Re-throw or propagate the rest.
3. **Don't log and re-throw.** Either log it and handle it, or pass it up. Doing both gives you the same error in five log lines.
4. **Error messages are for humans.** "InvalidStateException" is useless. "Cannot ship order: order is in state CANCELED" is debuggable.
5. **Include context.** "File not found" — *which file?* Never produce an error that doesn't name the thing.
6. **One way to fail.** A function should not sometimes return `null` *and* sometimes throw *and* sometimes return `-1`. Pick one.

---

## Best Practices

1. **Think about failure when you design the function, not after.** If you find yourself thinking *"can I just add a try/except later?"* — no, you can't, not well.
2. **Distinguish bugs from expected errors.** Expected errors get error-handling. Bugs get fixed (and possibly a panic/assert/raise to make them loud).
3. **Fail fast for impossible states.** If something *cannot* happen — assert. The earlier a corrupt state is detected, the cheaper the fix.
4. **Fail soft for expected errors.** A user typed `"twenty"` into an age field — your job is to ask again, not to crash.
5. **Make errors actionable.** What can the caller actually *do* with this error? If the answer is "nothing", you've named it wrong.
6. **Keep the boundaries thin.** Errors should be translated only at the system boundary (HTTP, user, log). Internal code passes them along.
7. **Test the error paths.** Most bugs hide in the error paths because no one tested them.

---

## Edge Cases & Pitfalls

### Pitfall 1 — `null` as "error" (and friends)

In old C and old PHP, the convention was: "on failure, return `null` / `-1` / `false` / empty string." This produces calls like:

```php
$result = doThing();
if ($result === false) { /* error... but which one? */ }
```

There is no information about *what* went wrong, only *that* something did. This style is dead for good reasons.

### Pitfall 2 — Throwing inside destructors / `finally`

In many languages, an exception thrown inside a cleanup block can either be swallowed or mask the original exception, depending on the language. Be very careful in `finally`, `__exit__`, `Drop`, and destructor code — they should be *bulletproof* and re-raise nothing.

### Pitfall 3 — Async/await error swallowing

In async code (JS Promises, Python `asyncio`), an unhandled rejection used to silently disappear. Modern runtimes now warn loudly, but a junior writing `someAsync().then(...)` without a `.catch()` can still produce code that fails invisibly.

### Pitfall 4 — Catching `Exception` (or `Throwable`, or `BaseException`)

```python
try:
    do_thing()
except Exception:
    pass  # NEVER
```

You just swallowed `KeyError`, `MemoryError`, `KeyboardInterrupt` (well, almost), and every future error someone adds. Be specific.

### Pitfall 5 — Mixing error styles in one codebase

Some functions return `(value, err)`; some throw; some return `null`. The caller doesn't know what to expect. Pick a style and apply it consistently within a layer.

### Pitfall 6 — Errors crossing thread boundaries

In a `Thread`, `goroutine`, or `Worker`, exceptions thrown in the child often don't reach the parent automatically. You must explicitly catch and report them — otherwise the failure happens silently.

---

## Common Mistakes

1. **`except: pass`** — swallows all errors, including bugs. The fastest way to hide a critical defect.
2. **Generic catch-all at the wrong level** — converting every error into "internal server error" hides distinguishable cases.
3. **`if err != nil { panic(err) }`** in Go — turning expected errors into crashes is hostile to the caller.
4. **Returning an empty result instead of an error** — `getUser(id)` returning an empty `User{}` instead of an error is silent corruption.
5. **Re-throwing without context** — `throw e` at every layer leaves you a stack trace that points to where the error was caught but not what was happening (we'll fix this in `middle.md` with *wrapping*).
6. **Catching for "robustness"** — wrapping `try/except` around things "just in case" hides real bugs.
7. **Validating already-validated data** — instead of trusting the layer above, every layer re-validates and produces conflicting error messages.
8. **Using exceptions for control flow** — `try/except` as a substitute for `if/else` is slow and confusing.
9. **Discarding the original exception** — `raise NewError("oops")` instead of `raise NewError("oops") from e`. We'll see *chaining* in `middle.md`.
10. **Letting `null` mean two things** — "no result found" vs "an error occurred" — should never be the same value.

---

## Tricky Points

- **A `return error` is not "less safe" than `throw`** — it just makes the error path visible. Go programmers consider this a *feature*, not boilerplate.
- **Stack traces aren't free** — in Java and Python they cost a bit of CPU to capture. In hot loops, throwing thousands of exceptions can be a real performance problem. (More on this in `optimize.md` if you ever go that deep.)
- **Some errors aren't errors** — `EOF` (end of file) is the *normal* way most file reads terminate. Don't treat it as a failure. `database returned 0 rows` is often not an error either.
- **"Recoverable" is not a property of the error — it's a property of the caller.** "File not found" can be a recoverable error (try another path) or a fatal one (no config = die), depending on who's asking.
- **Exception hierarchies do matter** — catching `IOException` will also catch `FileNotFoundException` if it inherits from it. Knowing the hierarchy is half of using exceptions well.
- **`finally` runs even when you `return`** — but **not** when the process is killed. Don't rely on it for permanent cleanup.
- **`panic` in Go can be recovered with `recover()` in a deferred function** — but most idiomatic Go code does not do this. Save it for the very top of a goroutine.

---

## Apply it

1. Choose one small, known input for **Error Handling**.
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

- What problem does Error Handling solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
