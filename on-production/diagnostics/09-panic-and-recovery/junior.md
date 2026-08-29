# Panic & Recovery — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Panic & Recovery** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Panic & Recovery Roadmap](README.md)
> **Focus:** The two layers of failure. Panic vs error vs exception. What stack unwinding is. Go `defer`/`panic`/`recover` basics. And the most important judgment a junior can learn early — **when a program *should* crash.**

---

## Core Concepts

### 1. There Are Two Layers of Failure, Not One

Every mature language has split error handling into two layers — even if nobody told you. Layer one is for failures you expect and handle. Layer two is for failures that mean *the program itself is broken*. Mixing them up is the root of most bad error handling. A network timeout is **not** a panic. A nil-pointer dereference **is**.

### 2. A Panic Is a Bug Report From Your Program to You

When you see `panic: runtime error: index out of range [3] with length 3`, the program is not being dramatic. It found that *you* assumed a slice had at least 4 elements and it didn't. The panic is a free, precise, machine-generated bug report. Suppressing it deletes the report and keeps the bug.

### 3. Crashing Is Often the *Safe* Choice

Beginners think a crash is the worst outcome. It usually isn't. The worst outcome is **continuing with corrupt state**: charging a card twice, writing garbage to the database, returning the wrong user's data. A crash is loud, contained, and recoverable (the process restarts). Silent corruption is none of those things. **A clean crash beats a quiet lie.**

### 4. Unwinding Runs Your Cleanup On the Way Out

When a panic or exception travels up the stack, the language runs your cleanup hooks at each level — Go's `defer`, Java/Python's `finally`, Rust/C++ destructors. This is *why* you can still close files and release locks even when things go wrong. Understanding unwinding is understanding *what runs after the bad thing happens*.

### 5. `recover` Is a Scalpel, Not a Blanket

Go's `recover` (and `try/catch` of broad types) is sometimes correct — at a *boundary*, to stop one bad request from killing a whole server. But used everywhere, it becomes the panic equivalent of `except: pass`: it hides bugs forever. The rule for now: **don't recover unless you can name exactly why.** (The middle level teaches the one pattern where you should.)

### 6. The Default Should Be to Let It Crash

When in doubt, do nothing — let the panic propagate, let the exception bubble up, let the process die with a stack trace. This is not laziness; it is the [fail-fast](../03-error-handling/middle.md) principle. You add recovery deliberately, at one place, for one reason. You don't sprinkle it defensively.

---

## The Two-Layer Model

This is the single most important idea on this page. Memorize the table.

| | **Layer 1: Recoverable Error** | **Layer 2: Panic / Unrecoverable** |
|---|---|---|
| **Cause** | The world: bad input, missing file, network down | Your code: nil deref, bad index, broken invariant |
| **Examples** | `ENOENT`, timeout, validation failure, 404 | index out of range, nil pointer, divide by zero, OOM |
| **Right response** | Handle it: return error, retry, show message | Usually: crash with a stack trace |
| **Go** | `return err` | `panic(...)` / runtime panic |
| **Rust** | `Result<T, E>` / `?` | `panic!` / `.unwrap()` on `None` |
| **Java** | checked / runtime `Exception` you catch | `Error` (e.g. `OutOfMemoryError`), unchecked bugs |
| **Python** | `except ValueError:` you handle | uncaught exception, `AssertionError`, `SystemExit` |
| **Node** | rejected promise you `.catch()` | uncaught exception, `throw` of a programmer bug |
| **Frequency** | Common; part of normal operation | Should be *rare*; each one is a bug to fix |

The trap: treating a Layer-2 failure like a Layer-1 one. When you wrap a nil-deref in `try/except: pass`, you've taken a bug your program detected for free and **hidden it**. The bug is still there; you just blinded yourself to it.

The opposite trap exists too — treating a Layer-1 failure like a Layer-2 one. If you `panic()` every time a network call fails, your server dies on the first flaky connection. Network failures are *expected*; they belong in Layer 1.

---

## What Stack Unwinding Is

When a function calls a function calls a function, the runtime keeps a **call stack** — one frame per active call, with each frame holding that call's local variables.

```text
   main()              ← frame 0  (bottom of stack)
     process()         ← frame 1
       loadUser()      ← frame 2
         parseRow()    ← frame 3  ← PANIC fires here
```

When `parseRow` panics, the program doesn't just vanish. It **unwinds**: it walks back up — frame 3, then 2, then 1, then 0 — and at *each* frame it runs that frame's cleanup code (`defer` in Go, `finally` in Python/Java, destructors in Rust/C++). This is how files get closed and locks get released even during a failure.

```text
   PANIC at parseRow (frame 3)
        │  run parseRow's deferred cleanup
        ▼
   unwind to loadUser (frame 2)
        │  run loadUser's deferred cleanup
        ▼
   unwind to process (frame 1)
        │  run process's deferred cleanup
        ▼
   unwind to main (frame 0)
        │  no recover anywhere → process dies, prints stack trace
        ▼
   PROCESS EXITS (non-zero status)
```

If somewhere along the way a frame has a `recover()` (Go) or a `catch`/`except` (others), the unwinding **stops there** and normal execution resumes from that point. That's the difference between a panic that kills the process and one that's contained.

> Two flavors worth naming now: **unwinding** (walk up, run cleanup) vs **aborting** (stop instantly, run *nothing*). Go and Java unwind. Rust can do either depending on config. A raw `SIGABRT`/`SIGSEGV` typically aborts. You'll go deep on this at the senior and professional levels; for now, just know cleanup runs during *unwinding* but not during an *abort*.

---

## Code Examples

### Example 1 — A panic vs a returned error in Go

```go
package main

import (
	"errors"
	"fmt"
)

// LAYER 1: the world might not have this user. Return an error — caller decides.
func findUser(id int, users map[int]string) (string, error) {
	name, ok := users[id]
	if !ok {
		return "", fmt.Errorf("user %d not found", id) // expected, recoverable
	}
	return name, nil
}

// LAYER 2: this index access PANICS if the slice is too short.
// That's a *bug* (someone built the slice wrong), not a recoverable error.
func thirdElement(s []int) int {
	return s[2] // panics with "index out of range" if len(s) < 3
}

func main() {
	users := map[int]string{1: "Ada"}

	// Layer 1: handled gracefully.
	if name, err := findUser(99, users); err != nil {
		fmt.Println("handled:", err) // handled: user 99 not found
	} else {
		fmt.Println("found:", name)
	}

	// Layer 2: this will crash the program with a stack trace — and that's correct.
	fmt.Println(thirdElement([]int{10, 20})) // panic: runtime error: index out of range [2] with length 2
	_ = errors.New                            // (silence unused import in this trimmed example)
}
```

The lesson: `findUser` returns an `error` because "no such user" is a normal fact about the world. `thirdElement` panics because being handed a too-short slice means *the calling code is broken*. Don't try to "handle" the second one — fix the caller.

### Example 2 — Go `defer`, `panic`, and `recover`

```go
package main

import "fmt"

func cleanup() {
	fmt.Println("cleanup ran (defer always runs, even on panic)")
}

func risky() {
	defer cleanup() // runs on normal return AND on panic
	fmt.Println("about to panic")
	panic("something broke")
	// unreachable
}

func main() {
	// recover MUST be inside a deferred function to work.
	defer func() {
		if r := recover(); r != nil {
			fmt.Println("recovered from:", r) // we caught the panic here
		}
	}()

	risky()
	fmt.Println("this line is NOT reached — risky() panicked") // never printed
}
```

Output:

```text
about to panic
cleanup ran (defer always runs, even on panic)
recovered from: something broke
```

Read the order carefully. `panic` fires → unwinding begins → `risky`'s `defer cleanup()` runs → unwinding continues to `main` → `main`'s deferred `recover()` catches it. The line after `risky()` in `main` is *not* reached, because we caught at `main`, not in the middle. **`recover` only works inside a `defer`, and only catches panics from the same goroutine.**

### Example 3 — The same idea in Python, Java, and Node

#### Python

```python
# Layer 1: expected. Handle it.
def load_config(path: str) -> dict:
    try:
        with open(path) as f:
            return json.loads(f.read())
    except FileNotFoundError as e:
        raise RuntimeError(f"config missing at {path}") from e  # turn into a clear error

# Layer 2: a bug. Let it crash with a real traceback.
def average(nums: list[float]) -> float:
    return sum(nums) / len(nums)  # ZeroDivisionError on empty list — that's a bug upstream

# The 'finally' equivalent of Go's defer:
def with_lock(lock):
    lock.acquire()
    try:
        do_work()
    finally:
        lock.release()  # runs whether do_work() returns or raises
```

#### Java

```java
// Exception (Layer 1) — recoverable, you catch it.
try {
    var data = Files.readString(Path.of("config.json"));
} catch (IOException e) {
    log.warn("config unreadable, using defaults", e); // handle
}

// Error (Layer 2) — you do NOT catch OutOfMemoryError to "keep going".
// Letting it propagate and crash the process is the correct behavior.

// finally is Java's cleanup hook (or try-with-resources, which is better):
Lock lock = ...;
lock.lock();
try {
    doWork();
} finally {
    lock.unlock(); // always runs, even if doWork() throws
}
```

#### Node.js

```js
// Layer 1: a rejected promise you handle.
try {
  const data = await fs.readFile("config.json", "utf8");
} catch (err) {
  console.warn("config unreadable, using defaults:", err.message);
}

// Layer 2: a programmer bug thrown synchronously.
function third(arr) {
  if (!Array.isArray(arr)) throw new TypeError("expected an array"); // assertion-style
  return arr[2];
}
// An uncaught throw crashes the Node process — by default, and usually correctly.
```

---

## Panic vs Error vs Exception — Per Language

| Language | "Recoverable" mechanism | "Panic" mechanism | Default if uncaught |
|---|---|---|---|
| **Go** | `return err` (explicit) | `panic(...)`, runtime panics | Process exits, prints stack of the panicking goroutine |
| **Rust** | `Result<T, E>`, `Option<T>`, `?` | `panic!`, `.unwrap()`, `.expect()` | Unwinds (default) or aborts; thread dies, often the process |
| **Java** | `Exception` (checked/unchecked) you catch | `Error` (e.g. `OutOfMemoryError`), uncaught `RuntimeException` | Thread's `UncaughtExceptionHandler`; main thread death → JVM exits |
| **Python** | `except SomeError:` | uncaught exception, `AssertionError` | Prints traceback, exits non-zero |
| **Node/JS** | `try/catch`, `.catch()` on promises | uncaught `throw`, unhandled rejection | `uncaughtException` handler or process exit |

Two subtleties that trip beginners:

1. **In Java, `Error` and `Exception` are siblings under `Throwable`.** You *can* technically `catch (Throwable t)` and catch an `OutOfMemoryError` — but you almost never should. `Error` exists precisely to say "this is the panic layer; don't catch me."
2. **In Python, not everything is an `Exception`.** `SystemExit`, `KeyboardInterrupt`, and `GeneratorExit` inherit from `BaseException`, *not* `Exception`. So a bare `except Exception:` correctly lets Ctrl-C and `sys.exit()` through. A bare `except:` (no type) catches *everything* including those — which is a bug. **Never write `except:` with no type.**

---

## When a Program SHOULD Crash

This is the judgment that separates good engineers from defensive-programming cargo cultists. Crash (or let it crash) when:

- **An invariant your code relies on is violated.** "This map always has this key by now." "This slice is never empty here." If it is, your mental model is wrong, and continuing means operating on false assumptions.
- **Continuing would corrupt data.** A half-applied transaction, a partial write, a double charge. Better to die clean than commit garbage.
- **You cannot construct a sane fallback.** If there's no meaningful "default" or "retry," and the only options are "crash" or "pretend nothing happened," crash.
- **It's startup configuration.** A missing required env var or malformed config at boot should crash *immediately* and loudly. Don't start a server that's misconfigured — fail before you accept a single request.
- **A programmer-error assertion fails.** `assert balance >= 0`. If that's ever false, you have a bug that *must* be found, not hidden.

Do **not** crash when:

- The failure is expected and you have a real response (return an error, show a 404, retry the call).
- You're at a request/worker **boundary** and can contain the blast radius to one request (the middle-level pattern).
- The failure is in optional, non-critical work (a metrics push failing shouldn't kill the request).

> The heuristic: **crash on broken invariants, handle on bad input.** If you can't tell which one you're looking at, that confusion *is* the bug — go find out which it is before writing a single `catch`.

---

## Pros & Cons of Crashing vs Recovering

| Approach | Pros | Cons |
|---|---|---|
| **Let it crash (fail-fast)** | Loud, immediate, debuggable. Clean state on restart. Bug can't spread or corrupt data. Stack trace points right at it. | One bug can take down a whole process. Needs a supervisor/restart to be resilient. Bad UX if it's user-facing and unguarded. |
| **Recover at a boundary** | Contains blast radius to one request/worker. Server survives a bad input. Can log + report the panic cleanly. | Only safe if state really is isolated per request. Easy to get wrong (leaked locks, shared corrupt state). |
| **Recover-and-continue everywhere** | Feels "robust" to beginners. Nothing ever crashes. | Almost always a bug. Hides defects forever. Continues on corrupt state. The classic `except: pass` disease. |
| **Convert to a returned error** | Right answer for Layer-1 failures. Caller decides what to do. | Wrong (and noisy) if applied to genuine bugs — you'd be "handling" something unhandleable. |

The honest rule: **default to crashing; recover only at deliberate boundaries; never recover-and-continue blindly.**

---

## Coding Patterns

### Pattern 1 — The Startup Assertion (Crash Early)

```go
func mustEnv(key string) string {
	v := os.Getenv(key)
	if v == "" {
		// Crash at startup. A misconfigured server should never accept traffic.
		log.Fatalf("required env var %s is not set", key)
	}
	return v
}

dbURL := mustEnv("DATABASE_URL") // if missing, process dies here, before serving
```

The `Must`/`mustX` naming convention (Go) signals "this panics/exits on failure, by design." It's appropriate for *startup* and *programmer-supplied* inputs, not for runtime user input.

### Pattern 2 — `defer` for Guaranteed Cleanup

```go
func process(path string) error {
	f, err := os.Open(path)
	if err != nil {
		return err // Layer 1: file might not exist
	}
	defer f.Close() // runs on normal return AND on panic — file always closes

	return doWork(f)
}
```

### Pattern 3 — Let It Propagate (the "do nothing" pattern)

```python
def parse_order(raw: dict) -> Order:
    # If raw is missing required keys, KeyError propagates. Good.
    # Do NOT wrap this in try/except: pass — a malformed order is a bug to surface.
    return Order(id=raw["id"], total=raw["total"])
```

Sometimes the most correct code is the code you *don't* write. No `try`. No `recover`. Let the failure travel to where someone can actually decide.

### Pattern 4 — The Sanity Assertion

```go
if len(items) == 0 {
	panic("invariant violated: items must be non-empty at this point")
}
```

If your assumption holds, this is invisible. If it's wrong, you get an immediate, loud crash *at the exact line the assumption broke* — a free, precise diagnostic. (See the same idea in [Debugging — Junior](../01-debugging/junior.md#coding-patterns).)

---

## Clean Code

- **Never write `except:` (Python) or `catch (Throwable)` (Java) without a very specific reason.** They swallow Ctrl-C, `SystemExit`, and `OutOfMemoryError` — things you must let through.
- **Never write `recover()` (Go) just to "be safe."** Recover only at a boundary you can name, for a reason you can articulate.
- **Don't convert bugs into errors to make them "go away."** A `nil` deref turned into a returned `nil, nil` is a landmine for the next caller.
- **Name panic-on-failure functions clearly** — `MustParse`, `mustEnv` — so readers know they crash by design.
- **Put cleanup in `defer`/`finally`/`with`, not in the happy path** — so it runs even when things blow up.
- **Crash on startup misconfiguration.** A server that boots with bad config is worse than one that refuses to boot.

---

## Best Practices

1. **Sort every failure into Layer 1 or Layer 2 before reacting.** The category dictates the response.
2. **Default to letting it crash.** Add recovery deliberately, never defensively.
3. **Read the panic message and stack trace.** They tell you exactly which invariant broke and where.
4. **Use `defer`/`finally` for cleanup**, so locks and files release during unwinding.
5. **Fail fast at startup** for any missing or invalid required configuration.
6. **Never use a bare `except:` or catch the panic-layer types** (`Error`, `BaseException`) without a deliberate, documented reason.
7. **Fix the cause of a panic, not the symptom.** Catching it is treating the smoke; fixing the invariant is putting out the fire.
8. **When you must recover, log the panic and the stack** so the bug isn't lost. (Detail at the middle level and in [Crash Reporting](../07-crash-reporting/README.md).)

---

## Edge Cases & Pitfalls

- **A panic in a goroutine/thread can crash the *whole* process**, even though the rest of the program looks fine. In Go, a panic in a goroutine with no `recover` in *that goroutine* takes down everything. You cannot catch it from the parent.
- **`recover()` only works in a deferred function, and only in the same goroutine.** Calling `recover()` directly (not via `defer`) does nothing. Calling it from a different goroutine does nothing.
- **`finally`/`defer` can swallow the original exception** if *they* throw or return. A `finally` that `return`s discards the in-flight exception. Be careful what you do in cleanup.
- **Python's bare `except:` catches `KeyboardInterrupt` and `SystemExit`.** Now Ctrl-C doesn't work and `sys.exit()` is ignored. Always catch a specific type, or at least `except Exception:`.
- **A divide-by-zero is not the same across languages.** Integer `1/0` panics/throws in Go, Java, Python. But *floating-point* `1.0/0.0` gives `+Inf`/`NaN` silently — no crash, just poison data downstream. (See [Debugging — Junior](../01-debugging/junior.md).)
- **Catching too broadly hides new bugs.** A `catch (Exception e)` around a big block will silently catch the `NullPointerException` you introduce next month.

---

## Common Mistakes

1. **`try/except: pass` (or Go's `_ = err`, or empty `catch {}`).** The single most damaging beginner habit. It turns a detected failure into silent wrong behavior.
2. **Treating a bug as an error.** Wrapping a nil-deref in error-handling instead of fixing the nil. The bug stays; you just stopped seeing it.
3. **Treating an error as a bug.** Panicking on a network timeout. Now a flaky connection crashes your server.
4. **Using `recover()` everywhere "to be safe."** Defensive recovery hides every bug in the program.
5. **Catching `Throwable` / using bare `except:`.** Swallows the things you must never swallow (OOM, Ctrl-C, exit).
6. **Assuming a goroutine/thread panic is contained.** It isn't, by default. An unhandled goroutine panic kills the whole process.
7. **Doing meaningful work in `finally`/`defer` that can itself fail**, masking the original failure.
8. **Not reading the stack trace.** The panic told you exactly where and why. Read it before you "fix" anything.
9. **Crashing the request path on optional work** (a failed metrics emit shouldn't 500 the user).
10. **Starting a server with invalid config** instead of crashing at boot.

---

## Tricky Points

1. **`recover()` returns `nil` when there's no panic** — so `if r := recover(); r != nil` is the idiom. A `recover()` that's never reached during a panic does nothing.
2. **`defer` evaluates its arguments immediately, but runs the call at the end.** `defer fmt.Println(x)` captures `x`'s value *now*, not at return time. Subtle source of "wrong value logged" bugs.
3. **The panic-layer types are deliberately separate.** Java's `Error`, Python's `BaseException` (above `Exception`), Go's runtime panics — the language *designers* drew the line so you'd know not to catch them.
4. **An exception thrown inside a `finally` replaces the original.** The first failure is lost; you only see the second. Java even has "suppressed exceptions" to partially address this.
5. **Re-panicking after recover** is sometimes correct: you recover at a boundary, log it, then decide the state is too corrupt and `panic` again to crash. Recovering doesn't *commit* you to continuing.
6. **Floating-point division by zero doesn't panic** — it yields `Inf`/`NaN`. The "safe-looking" math is the dangerous one because there's no crash to alert you.
7. **`os.Exit()` (Go) / `System.exit()` (Java) skip `defer`/`finally` entirely.** They terminate *now*, with no unwinding. Don't expect cleanup to run after them.

---

## Apply it

1. Choose one small, known input for **Panic & Recovery**.
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

- What problem does Panic & Recovery solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
