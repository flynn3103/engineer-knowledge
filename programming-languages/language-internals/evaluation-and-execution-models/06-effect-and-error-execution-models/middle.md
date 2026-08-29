# Effect & Error Execution Models — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Effect & Error Execution Models** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. A `throw` Is a Search, Not a Jump

The single most important correction to the junior mental model: **a `throw` does not jump to a known location.** The throw site has no idea where the catch is. So the runtime performs a **search up the stack**:

```text
   throw here  ──►  does THIS frame catch this type? no → unwind it (run cleanup)
                    does the NEXT frame catch it?    no → unwind it (run cleanup)
                    does the NEXT frame catch it?    YES → stop, run the handler
```

To do this search, the runtime needs to know, for every frame currently on the stack: *what cleanup must run, and is there a catch clause that matches this exception type?* That information is what the compiler precomputes and stashes in tables.

### 2. The Landing Pad: Where Unwinding "Lands" in a Function

When the unwinder decides a particular frame has work to do (cleanup or a catch), it doesn't resume the function at the throw point. It jumps to a special compiler-generated block called a **landing pad**. The landing pad:

1. Runs the cleanups for that frame (call destructors / mark `finally` to run).
2. If this frame has a matching catch, **dispatches** to the catch body.
3. If not, it re-enters the unwinder to continue up to the next frame.

A function with three local objects and a `try/catch` has landing-pad code generated for it — but on the happy path, **none of it runs.** It sits in a cold section of the binary, reached only via the unwinder.

### 3. Two-Phase Unwinding: Search First, Destroy Second

The Itanium C++ ABI (used on Linux/macOS) and Windows SEH both use **two-phase unwinding**:

- **Phase 1 — Search.** Walk *up* the stack asking each frame's **personality routine**, "do you have a handler for this exception?" *Without modifying the stack* — no cleanup runs yet. This phase just *finds* the catching frame (or discovers there is none).
- **Phase 2 — Cleanup/Unwind.** Walk up *again*, this time actually popping frames and running each frame's cleanups, until reaching the frame Phase 1 identified, then transfer into its handler.

Why two phases? Because of `std::terminate` and unhandled-exception semantics: if Phase 1 finds **no** handler at all, the program can `terminate()` **with the stack intact**, so a debugger sees the full original call stack at the throw point. If you destroyed frames eagerly while searching, that context would be gone. (Phase 1's existence is also why a thrown-but-uncaught exception in C++ doesn't run your destructors before aborting — there's no handler, so it terminates after Phase 1.)

### 4. "Zero-Cost" Exceptions vs `setjmp`/`longjmp`

There are two historical ways to implement exceptions, and the trade-off defines the whole topic.

**The old way — `setjmp`/`longjmp` (sjlj).** Entering a `try` calls `setjmp`, which **saves the CPU registers and stack pointer** into a buffer and links it onto a per-thread list of "active try blocks." Throwing calls `longjmp`, restoring the most recent buffer. This **costs on the happy path**: every `try` you enter does real work (save registers, push onto the list) even if nothing ever throws. Cheap to throw, but you pay continuously for the *possibility* of throwing.

**The modern way — table-driven, "zero-cost."** Entering a `try` does **nothing at runtime**. There's no register save, no list push. Instead the compiler emits **side tables** mapping each program-counter range to "what to unwind / which handlers apply." On throw, a runtime unwinder *reads those tables* to figure out how to walk the stack. The happy path executes the *exact same instructions it would without any try block*. The cost is entirely deferred to throw time, where reading and interpreting tables makes a throw **far more expensive** than a `longjmp` would have been.

The name is a slogan: **"zero-cost" = zero cost on the path that doesn't throw.** A thrown exception can cost **hundreds to thousands of nanoseconds** (table walk, personality calls, cleanup) — orders of magnitude more than a normal function return. This is the entire reason "don't use exceptions for control flow" is good advice.

### 5. Cleanup Runs During Unwinding — In Reverse Order

As frames unwind, their cleanup runs **last-acquired-first-released** (LIFO), because that's destruction order:

- **C++:** local objects are destroyed in reverse construction order as each frame unwinds.
- **Go:** `defer`red calls run in **LIFO** order when the function returns or panics.
- **Java/Python:** `finally` blocks run as control leaves their `try`, innermost first.

This LIFO ordering is what makes RAII correct: if you acquire a lock then open a file, unwinding closes the file then releases the lock — the reverse of acquisition, which is exactly what you want.

### 6. Go's `panic`/`recover`: Unwinding via Deferred Functions

Go has no `throw`/`catch`, but `panic` *is* an unwinding mechanism built on `defer`:

1. `panic(v)` stops normal execution of the current function.
2. It runs that function's **deferred** calls, in LIFO order.
3. If none of them `recover()`, the panic propagates to the **caller**, runs *its* deferreds, and so on up the goroutine.
4. If a deferred call invokes `recover()`, the panic **stops**: the panicking value is returned from `recover()`, and the goroutine resumes normally *from the deferred function's return*.
5. If the panic reaches the top of the goroutine uncaught, the program crashes with a stack trace.

So `defer`+`recover` is structurally a try/finally/catch, just spelled with functions. The key difference from exceptions: it's **explicit and value-based**, and idiom restricts it to genuinely exceptional situations.

### 7. Rust's `?` Desugaring and `panic` Strategy

Rust's `?` is pure sugar over `match`. This:

```rust
let x = fallible()?;
```

desugars (roughly) to:

```rust
let x = match fallible() {
    Ok(v)  => v,
    Err(e) => return Err(From::from(e)),  // convert and early-return
};
```

There is **no unwinding** here — `?` is an ordinary early `return`, as cheap as any return. The `From::from` lets a function convert a lower-level error into its own error type automatically.

Separately, Rust's `panic!` *does* unwind by default (running `Drop`s, exactly like C++ destructors), using the same table-driven Itanium machinery. But Rust lets you choose `panic = "abort"` in `Cargo.toml`, which makes `panic!` **immediately terminate** without unwinding — smaller binaries, no unwind tables, and a guarantee that destructors won't run during a panic. Libraries thus can't rely on catching panics for control flow.

---

## Code Examples

### C++ — RAII cleanup runs during unwinding

```cpp
#include <cstdio>
#include <stdexcept>

struct Guard {
    const char* name;
    explicit Guard(const char* n) : name(n) { printf("acquire %s\n", name); }
    ~Guard() { printf("release %s\n", name); }   // runs even during unwinding
};

void inner() {
    Guard a("lock");
    Guard b("file");
    throw std::runtime_error("boom");   // unwinds: ~file then ~lock, then propagates
}

int main() {
    try {
        inner();
    } catch (const std::exception& e) {
        printf("caught: %s\n", e.what());
    }
}
```

Output:

```text
acquire lock
acquire file
release file      <- LIFO: file released before lock
release lock
caught: boom
```

The destructors of `b` then `a` run as `inner`'s frame unwinds — *before* control reaches the catch in `main`. No `finally` needed; the destructor *is* the cleanup. This is RAII.

### C++ — `noexcept` removes the machinery (and the safety net)

```cpp
void fast(int* p) noexcept {
    *p = 42;            // if this somehow throws, std::terminate() is called immediately
}
```

`noexcept` tells the compiler "no exception leaves here," so it can skip emitting unwind tables for the call and may optimize harder (e.g., `std::vector` uses `noexcept` move constructors to move instead of copy on growth). The contract is enforced: if an exception *does* try to escape a `noexcept` function, the program calls `std::terminate` — no unwinding past it.

### Go — `panic`/`recover` unwinds through deferred functions

```go
package main

import "fmt"

func work() {
    defer fmt.Println("work cleanup")          // runs during the panic, LIFO
    defer fmt.Println("work cleanup (earlier)")
    panic("something broke")
}

func guarded() (err error) {
    defer func() {
        if r := recover(); r != nil {           // catches the panic here
            err = fmt.Errorf("recovered: %v", r)
        }
    }()
    work()
    return nil
}

func main() {
    fmt.Println("err =", guarded())
}
```

Output:

```text
work cleanup
work cleanup (earlier)
err = recovered: something broke
```

The `panic` runs `work`'s deferreds (LIFO), then propagates to `guarded`, whose deferred `recover()` stops it. `recover` only works inside a deferred function — that's where the unwinding gives it a chance to run.

### Rust — `?` is just early return (no unwinding)

```rust
use std::num::ParseIntError;

fn sum_two(a: &str, b: &str) -> Result<i32, ParseIntError> {
    let x: i32 = a.parse()?;   // desugars to: match a.parse() { Ok(v)=>v, Err(e)=>return Err(e.into()) }
    let y: i32 = b.parse()?;
    Ok(x + y)
}

fn main() {
    println!("{:?}", sum_two("2", "3"));      // Ok(5)
    println!("{:?}", sum_two("2", "oops"));   // Err(ParseIntError { .. })
}
```

Each `?` is an ordinary conditional return — no stack search, no tables. This is why Rust's recoverable-error path is as fast as a return, and why Rust reserves the *expensive* unwinding machinery for `panic!` alone.

### Rust — `panic!` unwind vs abort

```rust
fn main() {
    // With default `panic = "unwind"`, Drop impls run as the stack unwinds.
    // With `panic = "abort"` in Cargo.toml, this terminates immediately, no Drops.
    let _g = PrintOnDrop("guard");
    panic!("kaboom");
}

struct PrintOnDrop(&'static str);
impl Drop for PrintOnDrop {
    fn drop(&mut self) { println!("dropping {}", self.0); }
}
```

Under `unwind`, you'll see `dropping guard` before the process exits. Under `abort`, you won't — abort skips destructors. The choice is a real engineering decision: smaller/faster binaries and "panics are always fatal" (abort) vs. running cleanup and being catchable at thread boundaries (unwind).

### Java — `finally` ordering and the "swallowed exception" trap

```java
static int tricky() {
    try {
        throw new RuntimeException("original");
    } finally {
        return 7;   // BUG: this `return` SWALLOWS the exception entirely
    }
}
```

A `return` (or another `throw`) inside `finally` *replaces* the in-flight exception. `tricky()` returns `7` and the `RuntimeException` silently vanishes. Knowing that `finally` runs *during* unwinding — and can hijack it — is exactly the mechanical insight this level gives you.

---

## Coding Patterns

### Pattern 1: Recover only at a boundary, then convert to an error

```go
func handle(req Request) (resp Response, err error) {
    defer func() {
        if r := recover(); r != nil {
            err = fmt.Errorf("handler panic: %v", r)  // contain it at the boundary
        }
    }()
    return process(req), nil
}
```

Don't sprinkle `recover` everywhere. Put it at a meaningful boundary (a request, a worker task) and turn the panic back into an error.

### Pattern 2: RAII / scope guards instead of manual cleanup

```cpp
std::lock_guard<std::mutex> lk(m);   // releases on ANY exit, including unwinding
// ... no matter how this scope ends, the lock is released
```

Let destructors do cleanup so it's automatic on the error path. This is strictly better than `try { } finally { unlock(); }`.

### Pattern 3: Keep `finally`/`defer` cleanup non-throwing and side-effect-light

A `finally` that throws, or a `defer` that panics, can mask the original failure. Cleanup should close/release and nothing more. If cleanup *can* fail, log it — don't let it replace the in-flight exception.

### Pattern 4: Use `?` (or `if err != nil { return err }`) to keep propagation cheap

Reserve the expensive unwinding mechanism for the rare and truly exceptional. Route ordinary failures through return-based propagation, which is as cheap as a function return.

### Pattern 5: Don't catch-and-rethrow without adding value

```java
try { risky(); }
catch (IOException e) { throw e; }   // pointless: adds a frame, no information
```

Either add context (`throw new ServiceException("loading X", e)`) or don't catch at all. A bare rethrow just makes the trace noisier.

---

## Best Practices

- **Never throw on the happy path of a hot loop.** "Zero-cost" means zero on the path that doesn't throw — a throw can be 100–1000× a normal return.
- **Use RAII/`defer`/`finally`, not manual cleanup**, so the error path can't leak resources during unwinding.
- **Keep cleanup code simple and non-throwing.** A throwing destructor (C++) during unwinding calls `std::terminate`; a `return`/throw in `finally` swallows the real error.
- **Mark `noexcept` (C++) where true** to enable optimizations — but only when you can actually guarantee it.
- **Pick `unwind` vs `abort` deliberately (Rust).** Abort for size and "panics are fatal"; unwind when you need cleanup or to catch at thread boundaries.
- **Recover/catch at boundaries, not everywhere.** Contain failures at request/task edges; let them propagate within.
- **Prefer return-based errors for frequent, recoverable failures** to avoid the throw cost entirely.
- **Remember unwinding is LIFO.** Acquire in an order whose reverse is the correct release order.

---

## Edge Cases & Pitfalls

- **Throwing during unwinding.** In C++, if a destructor throws *while* the stack is already unwinding from another exception, `std::terminate` is called — you can't have two exceptions in flight. Destructors should be `noexcept`.
- **`return`/`throw` inside `finally`.** It *replaces* the in-flight exception or return value, silently swallowing the original. A notorious bug class in Java/JS.
- **Uncaught C++ exception doesn't run your destructors.** If Phase 1 finds no handler, the program `terminate()`s *with the stack intact* — your local destructors never run. (Tools/tests sometimes assume cleanup happened; it didn't.)
- **`recover` only works in a deferred function.** Calling `recover()` directly in normal code returns `nil` and does nothing — a common Go beginner mistake.
- **`panic = "abort"` skips `Drop`.** Code that relied on a destructor running during `panic!` (e.g., flushing a buffer) silently won't, under abort.
- **Cost of capturing stack traces.** Constructing an exception in Java/Python *fills in the stack trace*, which walks frames and is surprisingly expensive — sometimes the dominant cost of throwing. (More in `senior.md`.) Reusing a preallocated exception or overriding `fillInStackTrace` are tricks for hot throw sites.
- **`setjmp`/`longjmp` and non-`volatile` locals.** After `longjmp`, the values of locals that were modified between `setjmp` and `longjmp` and not declared `volatile` are *indeterminate*. C++ destructors are *not* run by `longjmp` — mixing it with C++ objects is undefined.
- **`longjmp` across a frame with cleanup leaks.** Because `longjmp` doesn't run destructors or `defer`s, jumping over frames that hold resources leaks them. This is precisely why C++/Go/Rust don't use it.
- **Exceptions crossing a language/ABI boundary.** Throwing a C++ exception through a C frame, or across a `extern "C"` boundary, or out of a callback into a C library, is undefined — the C frames have no unwind handlers/personality. Catch before the boundary.
- **`noexcept` lying.** A `noexcept` function that calls something which throws will `terminate` at the boundary, not propagate. Don't mark `noexcept` unless you're sure.

---

## Apply it

1. Find a real component where **Effect & Error Execution Models** affects an interface or dependency.
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

- Which boundary is most affected by Effect & Error Execution Models?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
