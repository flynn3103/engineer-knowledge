# Effect & Error Execution Models — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Effect & Error Execution Models** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. A Function Is More Than "Inputs → Output"

The simplest mental model of a function is a box: arguments go in, a value comes out. But that model is a lie for most real code. A real function might:

1. **Return a value** (the happy path).
2. **Fail to return a value** (an error).
3. **Do something to the world** while computing (a side effect).
4. **Depend on the world** to compute (read a file, the clock, randomness).

A language's *effect and error execution model* is its answer to: **"When a function does (2), (3), or (4), how does the program behave, and how does the programmer control it?"**

### 2. Two Big Families: "Jump Out" vs "Return a Marker"

There are two fundamentally different ways to handle failure, and almost every language picks one as its default.

**Family A — Exceptions ("jump out"):** When something fails, you `throw`. Normal execution *stops* and the program *jumps* — not to the next line, but out of the current function, then out of *its* caller, then out of *that* caller — until it finds a `catch` that wants to handle this kind of error. Languages: C++, Java, Python, JavaScript, C#.

```python
def read_config():
    f = open("config.json")   # may throw FileNotFoundError
    return f.read()

try:
    data = read_config()
except FileNotFoundError:
    data = "{}"               # control jumped here
```

**Family B — Error values ("return a marker"):** When something fails, you *return* a special value that says "this failed" alongside (or instead of) the result. The caller *checks* it with an ordinary `if`. Nothing jumps; control flows linearly. Languages: Go (the `error` return), Rust (`Result`), C (return codes).

```go
data, err := readConfig()
if err != nil {
    data = "{}"               // we checked and handled it
}
```

The difference feels small in a tiny example but shapes the entire *feel* of a language. Exceptions make the happy path clean and push errors out of sight. Error values make errors visible and impossible to ignore — at the cost of more `if`s.

### 3. The Call Stack and Why "Jumping Out" Is Meaningful

When `main` calls `a`, `a` calls `b`, and `b` calls `c`, the running program holds a **call stack**:

```text
   c        <- currently running
   b        <- waiting for c
   a        <- waiting for b
   main     <- waiting for a
```

If `c` throws an exception and nobody in `c` catches it, the language **unwinds the stack**: it abandons `c`, then checks `b` for a handler, then `a`, then `main`. Each abandoned frame is "popped." If cleanup code was registered (a `finally`, a destructor, a `defer`), it runs as that frame is popped. This is **stack unwinding**, and it's what makes a `throw` deep inside your program able to be caught far away.

The next levels go deep on *how* this unwinding physically happens. For now, the picture is: **an exception travels up the stack, popping frames, until caught.**

### 4. Errors vs Panics: "Expected Failure" vs "Bug"

A crucial distinction, especially in Go and Rust:

- An **error** is an *expected* failure that's part of normal operation: a file might not exist, user input might be malformed, a network might be down. You *handle* these. They are values.
- A **panic** (Go) or **`panic!`** (Rust) is for situations that should *never happen if the program is correct*: an array index out of bounds, a nil-pointer dereference, an invariant violation. The default behavior is to **crash** (after cleanup), because there's no sensible way to continue.

The rule of thumb juniors should internalize: **use errors for things that can go wrong; use panics for things that mean your code is broken.** Reaching for `panic`/exceptions to handle a missing file is poor style in Go and Rust; quietly ignoring a real bug is dangerous everywhere.

### 5. Cleanup on the Way Out: `finally`, `defer`, `ensure`

When control leaves a block — *whether normally or because of an error* — you often need to run cleanup: close the file, release the lock, free the buffer. Every language has a mechanism:

- **Java / JavaScript / Python:** a `finally` block always runs.
- **Go:** a `defer`red call runs when the function returns, even if it panics.
- **Rust:** a value's **`Drop`** runs automatically when it goes out of scope (this is how files close themselves).
- **C++:** a **destructor** runs when an object leaves scope — the basis of RAII ("Resource Acquisition Is Initialization").

The key insight: **cleanup must run on *both* the happy path and the error path.** If your file only closes on success, an error leaks the file handle. This is one of the most common junior bugs, and the language gives you a tool to fix it.

### 6. The Happy Path Should Be Easy to Read

A good error model lets you read the *intended* logic without drowning in failure handling. Exceptions do this by hiding the error path entirely (it's "somewhere up there in a catch"). Go does it by convention (`if err != nil { return err }` is so common your eyes learn to skim it). Rust's `?` operator does it by *desugaring* a check into a single character:

```rust
let data = read_config()?;   // if it failed, return the error now; else unwrap the value
```

Each model is trying to solve the same tension: **make failure impossible to forget, but don't make the happy path unreadable.** No model perfectly wins.

---

## Code Examples

We'll solve the same small task across languages: **read an integer from a string, and handle the "it's not a number" failure.** Watch how each language *models* the failure.

### Python — Exceptions

```python
def parse_count(s):
    return int(s)            # raises ValueError if s isn't a number

# Caller handles it by catching:
try:
    n = parse_count("banana")
    print("got", n)
except ValueError:
    print("not a number, using 0")
    n = 0
finally:
    print("done parsing")    # ALWAYS runs, success or failure
```

`int("banana")` *raises* `ValueError`. Control jumps from inside `parse_count` straight to the `except`. The `finally` runs either way. Notice: the function signature gives *no hint* that it can fail — you have to know.

### Java — Exceptions (checked vs unchecked)

```java
import java.io.*;

class Demo {
    // Checked: the compiler FORCES callers to handle or declare IOException.
    static String readFirstLine(String path) throws IOException {
        try (BufferedReader r = new BufferedReader(new FileReader(path))) {
            return r.readLine();   // try-with-resources auto-closes r
        }
    }

    public static void main(String[] args) {
        try {
            System.out.println(readFirstLine("missing.txt"));
        } catch (IOException e) {
            System.out.println("could not read: " + e.getMessage());
        }
    }
}
```

`IOException` is a **checked exception**: Java won't compile `main` unless it catches or declares it. `int x = Integer.parseInt("banana");` throws `NumberFormatException`, which is **unchecked** — the compiler doesn't force you to handle it. The `try (...)` is *try-with-resources*: it closes the reader automatically, the Java version of `defer`.

### Go — Error Values

```go
package main

import (
    "fmt"
    "strconv"
)

func parseCount(s string) (int, error) {
    n, err := strconv.Atoi(s)
    if err != nil {
        return 0, fmt.Errorf("parseCount: %w", err) // wrap with context
    }
    return n, nil
}

func main() {
    n, err := parseCount("banana")
    if err != nil {
        fmt.Println("error:", err)   // we explicitly checked
        n = 0
    }
    fmt.Println("count is", n)
}
```

There is no jumping. `parseCount` *returns* an `error` (which is `nil` on success). The caller checks `if err != nil`. The `%w` verb **wraps** the underlying error so callers can still inspect it. This is the Go way: failure is data, handled in line.

### Go — `panic` and `recover` (for the rare unrecoverable case)

```go
func mustParse(s string) int {
    n, err := strconv.Atoi(s)
    if err != nil {
        panic("mustParse: invalid input " + s) // a bug, not a normal failure
    }
    return n
}

func safeCall() (result int, err error) {
    defer func() {
        if r := recover(); r != nil {
            err = fmt.Errorf("recovered: %v", r) // turn panic back into an error
        }
    }()
    return mustParse("banana"), nil
}
```

`panic` unwinds the goroutine running deferred functions; `recover` (only meaningful inside a `defer`) stops it. Idiomatic Go reserves this for truly exceptional cases, not routine errors.

### Rust — `Result<T, E>` and the `?` Operator

```rust
use std::num::ParseIntError;

fn parse_count(s: &str) -> Result<i32, ParseIntError> {
    let n: i32 = s.parse()?;   // `?`: on Err, return it now; on Ok, unwrap the value
    Ok(n)
}

fn main() {
    match parse_count("banana") {
        Ok(n)  => println!("count is {}", n),
        Err(e) => println!("error: {}", e),
    }
}
```

`s.parse()` returns a `Result`. The `?` operator is shorthand: *"if this is an error, return it from the whole function right now; otherwise give me the success value."* The compiler **forces** you to handle both `Ok` and `Err` in `match` — you cannot accidentally ignore the failure.

### Rust — `panic!` for Bugs

```rust
fn get(v: &[i32], i: usize) -> i32 {
    v[i]   // out-of-bounds index PANICS — this is a bug, not a recoverable error
}
```

Indexing out of bounds doesn't return an error in Rust; it `panic!`s and unwinds (or aborts). Recoverable failures use `Result`; programming bugs use `panic!`. Same split as Go.

### JavaScript — `try/catch` and Promises

```javascript
function parseCount(s) {
  const n = Number(s);
  if (Number.isNaN(n)) throw new Error("not a number: " + s);
  return n;
}

try {
  console.log(parseCount("banana"));
} catch (e) {
  console.log("error:", e.message);
} finally {
  console.log("done");
}

// Async failure travels through a rejected Promise instead of the call stack:
async function load() {
  try {
    const res = await fetch("/data.json"); // a rejected promise throws here
    return await res.json();
  } catch (e) {
    return {};                              // handles the async failure
  }
}
```

Synchronous failures `throw` and are caught with `try/catch`. *Asynchronous* failures (a network error) arrive as a **rejected Promise**; `await` turns that rejection back into a `throw` you can `catch`. Same syntax, different plumbing underneath.

### Haskell — `Maybe` (failure as a value)

```haskell
import Text.Read (readMaybe)

parseCount :: String -> Maybe Int
parseCount s = readMaybe s     -- Just 5  on success, Nothing on failure

main :: IO ()
main =
  case parseCount "banana" of
    Just n  -> putStrLn ("count is " ++ show n)
    Nothing -> putStrLn "not a number"
```

`Maybe Int` is *either* `Just n` *or* `Nothing`. There is no throwing — failure is an ordinary value you pattern-match on. (`Either` is the richer cousin that carries an error message instead of just "nothing.") We'll see in later levels how Haskell chains many such steps without nesting `case`s.

---

## Coding Patterns

### Pattern 1: Always pair acquisition with guaranteed cleanup

```python
with open("data.txt") as f:   # Python: __exit__ always closes f
    process(f)
```

```go
f, err := os.Open("data.txt")
if err != nil {
    return err
}
defer f.Close()               // runs no matter how the function returns
process(f)
```

Open and "schedule the close" right next to each other. Never rely on reaching a manual close at the bottom — an error path will skip it.

### Pattern 2: Check the error *immediately* (Go)

```go
n, err := strconv.Atoi(s)
if err != nil {
    return fmt.Errorf("parsing count: %w", err)
}
// from here on, `n` is known-good
```

Handle or return the error on the very next lines. Don't let a known-bad value flow into later code.

### Pattern 3: Add context as the error travels up

Each layer should say *what it was doing* when it wraps an error: `"reading config: open file: no such file"`. In Go use `fmt.Errorf("...: %w", err)`; in Rust use libraries that attach context; in exceptions, chain causes. A bare `"no such file"` with no context is a debugging nightmare.

### Pattern 4: Don't catch what you can't handle

Catch an exception (or check an error) only at a layer that can *do something* about it — retry, substitute a default, report to the user. If you can't handle it here, let it propagate. Catching and swallowing an error you can't fix hides bugs.

### Pattern 5: Errors for the expected, panics for the impossible

```rust
// Recoverable: caller decides what to do.
fn find_user(id: u64) -> Result<User, NotFound> { /* ... */ }

// Unrecoverable: this means our own logic is broken.
fn assert_sorted(v: &[i32]) {
    for w in v.windows(2) {
        if w[0] > w[1] { panic!("internal bug: slice not sorted"); }
    }
}
```

---

## Best Practices

- **Never silently ignore an error.** `_, _ = doThing()` in Go or an empty `catch {}` in Java is how data gets corrupted. At minimum, log it.
- **Handle errors at the right level.** The lowest level *reports*; a higher level *decides*. Don't try to recover where you lack the context to recover.
- **Always run cleanup on every exit path.** Use `with`/`defer`/`try-with-resources`/RAII so you can't forget on an error path.
- **Add context when propagating.** "Failed to charge customer 42: connection refused" beats "connection refused".
- **Use the right tool for the right severity.** Routine failure → error/`Result`. Programming bug → panic/assert. Don't blur these.
- **Make the happy path readable.** If your code is 80% error handling and 20% logic, consider whether a different model (or a helper) would clarify.
- **Don't use exceptions for ordinary control flow.** Throwing to break out of a loop is slow and confusing; exceptions are for exceptional cases.
- **Read the function's signature/docs to learn what can fail.** In exception languages this is the hardest part — you often can't tell, so check the docs.

---

## Edge Cases & Pitfalls

- **The swallowed error.** An empty `catch` or an ignored Go `err` makes a real failure vanish. The program limps onward with bad data. This is the single most common error-handling bug.
- **Leaked resources on the error path.** You open a file, then an error returns *before* you close it. If you didn't use `defer`/`finally`/RAII, the handle leaks. Multiply by thousands of requests → resource exhaustion.
- **Returning a "zero" value with the error.** In Go, `return 0, err` returns *both* a meaningless `0` and the error. If the caller forgets to check `err`, it uses the `0`. Always check first.
- **`finally` that hides the real error.** If your `try` throws *and* your `finally` also throws (or `return`s), the original exception can be lost. Keep cleanup code simple and non-throwing.
- **Catching too broadly.** `except Exception:` or `catch (Throwable)` catches *everything*, including bugs you wanted to crash on (and even `KeyboardInterrupt` in Python). Catch the specific type you can handle.
- **Panicking for routine failures (Go/Rust).** Using `panic`/`unwrap()` because a file might be missing is bad style — that's a normal, recoverable error. Reserve panic for *bugs*.
- **Assuming async errors behave like sync ones.** A rejected JavaScript Promise that nobody `await`s or `.catch`es becomes an "unhandled rejection" that your `try/catch` never sees. Async failure has its own plumbing.
- **`int("banana")` gives no compiler warning.** In exception languages, nothing in the *type* tells you a call can fail. You can call a throwing function and forget to handle it, and it compiles fine. This is why Go and Rust make failure part of the return.
- **Returning early without cleanup in C.** Classic C has no `finally`. The `goto cleanup;` idiom exists exactly because every error path must jump to a single cleanup block, and forgetting one leaks.

---

## Apply it

1. Choose one small, known input for **Effect & Error Execution Models**.
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

- What problem does Effect & Error Execution Models solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
