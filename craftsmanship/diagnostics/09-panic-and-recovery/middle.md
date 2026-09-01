# Panic & Recovery — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Panic & Recovery** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Panic & Recovery Roadmap](README.md)
> **Focus:** The one pattern you *should* recover with — **recover-at-the-boundary**. Per-request and per-worker isolation. Logging and reporting a panic instead of swallowing it. Rust's `catch_unwind`. And the discipline of never letting a recovered panic vanish silently.

---

## Core Concepts

### 1. Recover Only Where Work Is Isolated

The recover-at-boundary pattern is safe *only* because each unit of work is independent. One HTTP request doesn't share mutable state with another; one queue job is independent of the next. That independence is what lets you discard a failed unit without poisoning the rest. If your "units" secretly share mutable state (a global cache mid-mutation, a held lock), recovery is *not* safe — you'll keep running on corruption.

### 2. The Boundary Is Infrastructure, Not Business Logic

The recover lives in the *framework layer* — the middleware, the worker loop, the dispatcher — not scattered through your handlers. Business code stays fail-fast. There is **one** recover per boundary, written once, reused everywhere. If you find a `recover()` inside business logic, it's almost certainly wrong.

### 3. A Recovered Panic Must Be Logged AND Reported

Recovering is only half the job. The other half is making sure the bug gets *fixed*. That means: log the panic with its stack at `error` level, increment a metric, and send it to your crash reporter. A boundary that recovers silently is *worse* than no boundary, because now the server survives and nobody ever learns the handler is broken.

### 4. Recovery Is Not Forgiveness

Catching a panic doesn't make the underlying bug go away. The handler still has a nil-deref. Tomorrow's identical request panics again. Recovery buys you **availability** (the server lives) at the cost of **one failed request** — it does not buy you correctness. You still owe a fix.

### 5. Goroutine/Thread Panics Escape Your Boundary

This is the trap that catches everyone. Your HTTP middleware recover protects the request goroutine. But if your handler *spawns a new goroutine* and *that* panics, your middleware can't see it — the new goroutine has its own stack. It crashes the whole process. **Every** goroutine/thread you spawn needs its *own* recover, or it's an unguarded blast radius.

### 6. Sometimes the Right Move After Recover Is to Re-Panic

Recovery gives you a *decision point*, not an obligation to continue. You can recover, inspect the damage, decide the process is in an unsafe state (a lock was held, shared state half-mutated), log it, and then `panic` again — crashing deliberately and cleanly rather than limping on corrupted. Recovering and re-panicking is a legitimate, sometimes-correct pattern.

---

## The Recover-at-Boundary Pattern

The pattern has four obligations. Skip any one and you've done it wrong.

```text
   ┌──────────────────────── THE BOUNDARY ────────────────────────┐
   │                                                              │
   │   1. CATCH    recover() / catch / catch_unwind the panic     │
   │   2. LOG      error-level log WITH the stack trace           │
   │   3. REPORT   metric++ and send to crash reporter            │
   │   4. CONTAIN  fail THIS unit only:                           │
   │                 • HTTP  → return 500                          │
   │                 • worker→ NACK/dead-letter the job, keep loop │
   │                 • task  → mark task failed, continue          │
   │                                                              │
   └──────────────────────────────────────────────────────────────┘
            inside this boundary: STILL fail-fast, NO recover
```

1. **Catch** — stop the unwind at the boundary.
2. **Log** — at `error` level, *with the stack trace*. A panic logged without its stack is nearly useless.
3. **Report** — bump a counter (so you can alert on panic rate) and forward to a crash reporter (so the bug gets a ticket).
4. **Contain** — fail *only* this unit. Return an error to this request; dead-letter this job; mark this task failed. The pool, the server, the loop survive.

If you do 1 and 4 but not 2 and 3, you've built a **silent swallower** — the worst outcome, because the bug now hides behind a surviving server forever.

---

## HTTP Middleware Recovery — Per Language

### Go — `net/http` recovery middleware

```go
package main

import (
	"log/slog"
	"net/http"
	"runtime/debug"
)

// Recover wraps a handler so a panic in it fails ONE request, not the server.
func Recover(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if rec := recover(); rec != nil {
				// 2. LOG with stack. 3. REPORT (metric + reporter).
				stack := debug.Stack()
				slog.Error("panic recovered in handler",
					"panic", rec,
					"method", r.Method,
					"path", r.URL.Path,
					"stack", string(stack),
				)
				panicsTotal.Inc()                 // metric for alerting
				report.Capture(rec, stack, r)     // send to Sentry/etc.

				// 4. CONTAIN: this request fails, others are unaffected.
				w.WriteHeader(http.StatusInternalServerError)
				_, _ = w.Write([]byte("internal server error\n"))
			}
		}()
		next.ServeHTTP(w, r) // 1. the panic (if any) unwinds into the defer above
	})
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/boom", func(w http.ResponseWriter, r *http.Request) {
		var p *int
		_ = *p // nil dereference → panic, caught by Recover, server keeps running
	})
	// Wrap the whole mux once. Every route gets the boundary.
	http.ListenAndServe(":8080", Recover(mux))
}
```

> The standard library's `net/http` server already recovers panics *per connection* to avoid killing the process — but it does **not** log a stack or return a clean 500, and it aborts the response mid-stream. You still want your own middleware for proper logging, reporting, and a controlled response.

### Java / Spring — a global exception boundary

```java
// Spring MVC: one place that turns any uncaught throwable into a 500 + log + report.
@RestControllerAdvice
public class PanicBoundary {

    private static final Logger log = LoggerFactory.getLogger(PanicBoundary.class);

    @ExceptionHandler(Throwable.class) // catch even RuntimeExceptions/Errors at the edge
    public ResponseEntity<String> handle(Throwable t, HttpServletRequest req) {
        // 2. LOG with stack (SLF4J includes it when you pass the throwable).
        log.error("uncaught throwable on {} {}", req.getMethod(), req.getRequestURI(), t);
        // 3. REPORT
        Sentry.captureException(t);
        panicCounter.increment();
        // 4. CONTAIN: this request → 500. Others unaffected (each runs on its own thread).
        return ResponseEntity.status(500).body("internal server error");
    }
}
```

Spring's servlet model already isolates requests on separate threads, so one request's uncaught exception doesn't end the JVM. The `@RestControllerAdvice` is the boundary where you log, report, and respond.

### Python / Flask — an error handler boundary

```python
import logging, traceback
from flask import Flask, jsonify

app = Flask(__name__)
log = logging.getLogger(__name__)

@app.errorhandler(Exception)  # the boundary: any uncaught Exception in a view
def handle_uncaught(e):
    # 2. LOG with stack.  3. REPORT.
    log.error("uncaught exception in view", exc_info=True)
    sentry_sdk.capture_exception(e)
    panics_total.inc()
    # 4. CONTAIN: this request → 500. Flask isolates requests, so others are fine.
    return jsonify(error="internal server error"), 500

@app.get("/boom")
def boom():
    return {}["missing"]  # KeyError → caught by the boundary, server keeps serving
```

Note: this catches `Exception`, *not* `BaseException` — so `KeyboardInterrupt` and `SystemExit` still propagate correctly, exactly as the junior level warned.

### Node / Express — error-handling middleware

```js
const express = require("express");
const app = express();

app.get("/boom", (req, res) => {
  const obj = null;
  res.json(obj.value); // TypeError → forwarded to the error middleware below
});

// The boundary: Express routes errors (and sync throws) here.
// (For async handlers, wrap them or use express-async-errors so rejections reach this.)
app.use((err, req, res, next) => {
  // 2. LOG with stack.  3. REPORT.
  console.error("uncaught error", { method: req.method, path: req.path, stack: err.stack });
  Sentry.captureException(err);
  panicsTotal.inc();
  // 4. CONTAIN
  res.status(500).json({ error: "internal server error" });
});

app.listen(8080);
```

> Express only routes *synchronous* throws (and `next(err)`) to error middleware. An *async* handler that rejects bypasses it and becomes an `unhandledRejection` — which can crash the process. Use `express-async-errors`, or `try/catch … next(err)` in every async route. This is the Node version of "goroutine panics escape your boundary."

---

## Per-Worker Isolation in a Pool

A worker pool pulls jobs off a queue. One poisoned job must fail *that job* — not kill the worker, and definitely not kill the pool. The recover goes *inside the loop, around each job*.

```go
func (w *Worker) Run(jobs <-chan Job) {
	for job := range jobs {
		w.process(job) // each call recovers internally — a bad job can't kill the loop
	}
}

func (w *Worker) process(job Job) {
	defer func() {
		if rec := recover(); rec != nil {
			slog.Error("panic processing job",
				"job_id", job.ID, "panic", rec, "stack", string(debug.Stack()))
			report.Capture(rec, debug.Stack(), job)
			job.DeadLetter() // 4. CONTAIN: route the poison job aside, keep consuming
		}
	}()
	w.handle(job) // a panic here unwinds into the defer, not into Run's loop
}
```

The critical structural detail: the `recover` must wrap **each job**, *inside* the loop. A common bug is putting `defer recover()` at the top of `Run` — then the *first* panic recovers, but the `for range` loop has already been unwound past, so the worker stops consuming and silently dies. **Recover per job, not per worker lifetime.**

```text
   WRONG                                RIGHT
   ─────                                ─────
   func Run(jobs) {                     func Run(jobs) {
     defer recover()  ← too high          for job := range jobs {
     for job := range jobs {                process(job)  ← recover INSIDE
       handle(job)                        }                  process()
     }                                  }
   }                                    one bad job → that job fails,
   one bad job → loop dies,             loop keeps consuming
   worker stops forever
```

---

## Goroutine and Thread Panics Are Not Auto-Contained

Repeat after the runtime: **a recover only catches panics in its own goroutine/thread.** This is the single most common production-down mistake in this topic.

```go
func badHandler(w http.ResponseWriter, r *http.Request) {
	// The middleware's recover protects THIS goroutine.
	go func() {
		// But this is a NEW goroutine. The middleware can't see it.
		doAsyncWork() // if this panics → WHOLE PROCESS DIES, despite the middleware
	}()
	w.Write([]byte("accepted"))
}
```

The fix: every spawned goroutine gets its own recover. Wrap it in a helper so you can't forget.

```go
// Go runs fn in a goroutine that recovers, logs, and reports its own panics.
func Go(fn func()) {
	go func() {
		defer func() {
			if rec := recover(); rec != nil {
				slog.Error("panic in spawned goroutine",
					"panic", rec, "stack", string(debug.Stack()))
				report.Capture(rec, debug.Stack(), nil)
			}
		}()
		fn()
	}()
}

// usage: Go(doAsyncWork)  — now an async panic is contained, logged, reported.
```

Java has the same trap and the same fix via `Thread.UncaughtExceptionHandler`:

```java
Thread.setDefaultUncaughtExceptionHandler((thread, throwable) -> {
    log.error("uncaught in thread {}", thread.getName(), throwable);
    Sentry.captureException(throwable);
});
// Or per-thread:
var t = new Thread(task);
t.setUncaughtExceptionHandler((th, ex) -> log.error("worker died", ex));
```

Python threads: an uncaught exception in a `threading.Thread` prints a traceback but does *not* propagate to the main thread (and won't crash the process by default). Use `threading.excepthook` (3.8+) to centralize logging/reporting so those failures aren't lost.

---

## Rust `catch_unwind`

Rust's panics, by default, **unwind** — which means you can catch them at a boundary with `std::panic::catch_unwind`. This is the Rust equivalent of the recover-at-boundary pattern, used for exactly the same reason: stop a worker/request panic from tearing down the whole thread/process.

```rust
use std::panic::{self, AssertUnwindSafe};

fn handle_job(job: Job) {
    // The boundary: catch a panic from job processing so one bad job
    // doesn't unwind out and kill the worker thread.
    let result = panic::catch_unwind(AssertUnwindSafe(|| {
        process(job) // may panic! / .unwrap() on None / index OOB
    }));

    match result {
        Ok(()) => {} // normal completion
        Err(payload) => {
            // 2. LOG  3. REPORT  4. CONTAIN
            let msg = payload
                .downcast_ref::<&str>().map(|s| s.to_string())
                .or_else(|| payload.downcast_ref::<String>().cloned())
                .unwrap_or_else(|| "non-string panic".into());
            tracing::error!(panic = %msg, "recovered panic in job");
            dead_letter(job);
        }
    }
}
```

Two Rust-specific things you must know now:

1. **`catch_unwind` requires `UnwindSafe`.** The closure's captures must be `UnwindSafe` — a compile-time signal that a panic crossing the boundary won't leave data half-mutated and observable. When you *know* the boundary is safe (e.g. you discard the closure's state on panic), `AssertUnwindSafe` overrides the check. Reaching for `AssertUnwindSafe` without thinking is how you reintroduce the corruption bug.
2. **`catch_unwind` does NOT work if the program is compiled with `panic = "abort"`.** With abort, a panic terminates the process instantly — there is no unwind to catch. Many production Rust binaries set `panic = "abort"` (smaller binaries, no unwind tables). On those, `catch_unwind` is a no-op safety-wise. You'll go deep on this trade-off at the [senior](senior.md) and [professional](professional.md) levels.

> Rust idiom: `catch_unwind` is for **boundaries** (FFI edges, thread/worker isolation, test harnesses), not for control flow. Recoverable failures still use `Result`/`?`. Don't use `catch_unwind` to "handle" a `None`; use `match`/`?`.

---

## Logging and Reporting a Recovered Panic

The recover is worthless if the panic disappears. Three signals, every time:

| Signal | Why | How |
|---|---|---|
| **Log line (`error` level, with stack)** | So you can read what happened during an incident | `slog.Error(..., "stack", debug.Stack())`, `log.error(..., exc_info=True)`, `log.error(msg, throwable)` |
| **Metric (`panics_total` counter)** | So you can *alert* on a rising panic rate before users complain | Prometheus counter, `panicsTotal.Inc()` |
| **Crash reporter capture** | So each unique panic becomes a *ticket* with a stack, deduplicated by fingerprint | `Sentry.captureException`, `report.Capture(...)` — see [Crash Reporting](../07-crash-reporting/middle.md) |

A subtlety: **capture the stack at the moment of recovery**, not later. By the time control returns from your handler, the stack that panicked has already unwound — `debug.Stack()` called too late shows the recovery site, not the crash site. In Go, call `debug.Stack()` *inside* the deferred recover function. In Java/Python the throwable/traceback object carries the original stack, so you can log it whenever, but still log it immediately.

> Don't log the raw `recover()` value alone — `panic("boom")` recovers as the string `"boom"` with *no* stack unless you grab `debug.Stack()` yourself. A reporter wants both the value and the stack.

---

## Never Swallow a Panic

The anti-pattern, in every language:

```go
defer func() { recover() }()                 // Go: swallows silently
```
```python
try: risky()
except Exception: pass                        # Python: swallows silently
```
```java
try { risky(); } catch (Throwable t) {}       // Java: swallows silently (and catches Error!)
```
```js
try { risky(); } catch (e) {}                 // JS: swallows silently
```

Every one of these recovers and does *nothing*. The bug is now invisible *and* the program keeps running on whatever broken state caused the panic. This is strictly worse than not recovering at all, because:

- Without recovery, the process crashes → you find out immediately → you fix it.
- With silent recovery, the process survives → you never find out → the bug corrupts data quietly for weeks.

The rule has no exceptions at this level: **if you recover, you log and report. If you're not going to log and report, don't recover.**

---

## Code Examples

### A complete, correct Go boundary helper used three ways

```go
package boundary

import (
	"log/slog"
	"runtime/debug"
)

// Guard runs fn, recovering+logging+reporting any panic, and reports whether
// a panic occurred so the caller can CONTAIN appropriately.
func Guard(ctx string, fn func()) (panicked bool) {
	defer func() {
		if rec := recover(); rec != nil {
			panicked = true
			stack := debug.Stack()
			slog.Error("recovered panic", "where", ctx, "panic", rec, "stack", string(stack))
			report.Capture(rec, stack, ctx) // metric + reporter inside Capture
		}
	}()
	fn()
	return false
}
```

```go
// HTTP boundary
func handler(w http.ResponseWriter, r *http.Request) {
	if boundary.Guard("GET /order", func() { serveOrder(w, r) }) {
		w.WriteHeader(http.StatusInternalServerError)
	}
}

// Worker boundary
for job := range jobs {
	job := job
	if boundary.Guard("job:"+job.ID, func() { handle(job) }) {
		job.DeadLetter()
	}
}

// Spawned-goroutine boundary
go func() { boundary.Guard("async:reindex", reindex) }()
```

One helper, three boundaries, all four obligations met (catch, log, report, contain). The business code inside (`serveOrder`, `handle`, `reindex`) stays completely fail-fast — no `recover` anywhere in it.

### Re-panic when the state is unsafe

```go
defer func() {
	if rec := recover(); rec != nil {
		slog.Error("panic while holding the ledger lock", "panic", rec, "stack", string(debug.Stack()))
		report.Capture(rec, debug.Stack(), nil)
		// We panicked mid-mutation while holding a lock. The shared ledger may be
		// half-written. Continuing is unsafe — crash deliberately for a clean restart.
		panic(rec) // re-panic: availability is not worth corrupting the ledger
	}
}()
mutateLedgerUnderLock() // if this panics mid-write, recover-then-re-panic
```

Recovering does not commit you to continuing. When isolation is *not* real — shared state was being mutated, a lock was held — the correct move is to log, report, and re-panic for a clean crash. Better one restart than a corrupted ledger.

---

## Coding Patterns

### Pattern: the four-obligation boundary (catch, log, report, contain)

Never write a recover that does fewer than all four. If you're tempted to skip log+report, don't recover at all.

### Pattern: recover *per job*, not *per worker lifetime*

```go
for job := range jobs {          // loop survives
    func() {
        defer recoverLogReport() // boundary is HERE, around one job
        handle(job)
    }()
}
```

### Pattern: a `SafeGo` wrapper so you can't forget goroutine recovery

```go
func SafeGo(fn func()) { go func() { defer recoverLogReport(); fn() }() }
// Ban raw `go fn()` in code review for anything that can panic. Use SafeGo.
```

### Pattern: convert panic → typed error at the boundary (Go)

```go
func Call(fn func() error) (err error) {
	defer func() {
		if rec := recover(); rec != nil {
			err = fmt.Errorf("panic: %v\n%s", rec, debug.Stack()) // becomes a normal error
		}
	}()
	return fn()
}
```

Useful when the caller's contract is "return an error" — the boundary translates the panic into the error the caller expects, *with* the stack attached.

---

## Clean Code

- **Exactly one recover per boundary**, written in infrastructure code, reused. No `recover()` in business logic.
- **Every recover logs (with stack) and reports.** No silent `recover()`, no `except Exception: pass`, no empty `catch`.
- **Every spawned goroutine/thread is launched through a recovering wrapper** (`SafeGo`, a guarded thread factory). Ban raw `go fn()`/`new Thread(fn)` for panic-prone work in review.
- **Recover catches the request-layer types, not the abort-layer ones** — `Exception` not `BaseException` in Python; don't catch `Error` in Java unless you re-throw.
- **Capture the stack at recovery time**, not later, or you'll log the recovery site instead of the crash site.
- **If isolation is an illusion (shared mutation, held lock), re-panic** rather than continue.

---

## Best Practices

1. **Install the boundary once, at the framework layer.** Wrap the whole mux / the worker loop / the interceptor — don't repeat it per route.
2. **Recover per unit of isolated work** (per request, per job), never per long-lived loop/worker.
3. **Always log+report a recovered panic.** Metric for alerting, reporter for ticketing, log with stack for the incident.
4. **Give every goroutine/thread its own recover.** The request boundary does not reach a goroutine you spawned.
5. **Keep business logic fail-fast.** The boundary is the *only* recover point; inside it, let bugs surface.
6. **Re-panic when the state is unsafe.** Held locks and half-mutations mean a clean crash beats limping on.
7. **In Rust, use `catch_unwind` only at real boundaries**, mind `UnwindSafe`, and remember it's inert under `panic = "abort"`.
8. **Return a generic 500 to the client; keep the detail in logs/reporter.** Never leak a stack trace in an HTTP response.

---

## Edge Cases & Pitfalls

- **`defer recover()` at the top of a worker loop kills the loop on first panic** — the `for range` is already unwound. Recover *inside* the loop body.
- **A panic in a spawned goroutine ignores the parent's recover** and crashes the process. Every goroutine needs its own.
- **Express async handlers bypass error middleware** — a rejected promise becomes an `unhandledRejection`. Wrap async routes.
- **`recover()` called outside a `defer`, or in a different goroutine, returns `nil`** and does nothing. It must be in a deferred function in the panicking goroutine.
- **Capturing the stack too late** logs the recovery site. Grab `debug.Stack()` inside the deferred function.
- **Rust `catch_unwind` under `panic = "abort"`** can't catch anything — the process aborts first. Check your `Cargo.toml` profile.
- **`AssertUnwindSafe` silences a real warning.** If the closure mutates shared state and panics mid-way, you've recovered into corruption.
- **Catching `Throwable`/`BaseException` at the boundary** can swallow `OutOfMemoryError`/`SystemExit`. Catch the request-layer type, and if you must catch broadly, re-throw the abort-layer ones.

---

## Common Mistakes

1. **Silent recover** — recovering with no log and no report. Worse than not recovering; the bug hides behind a living server.
2. **Recover per worker lifetime instead of per job** — the worker silently dies after the first panic.
3. **Forgetting goroutine/thread recovers** — an async panic crashes the whole process despite a perfect request boundary.
4. **Recover sprinkled in business logic** — every bug hidden, the boundary discipline destroyed.
5. **Treating recovery as a fix** — the handler still has the bug; tomorrow's identical request panics again. Recovery buys availability, not correctness.
6. **Continuing after recovering from a panic that held a lock or half-mutated shared state** — now the whole process runs on corruption. Re-panic instead.
7. **Leaking the stack trace to the client** in the 500 response — information disclosure; keep detail server-side.
8. **Using `catch_unwind` for control flow** instead of `Result`/`?` — wrong tool; and it's inert under abort.
9. **Catching `BaseException`/`Throwable`** at the boundary and swallowing exit/OOM signals.

---

## Tricky Points

- **`net/http` already recovers per connection**, but ugly (no clean response, no stack log). Your middleware exists to do it *properly*, not to enable recovery.
- **A recovered panic and a returned error should look identical to the client** — both are a 500. The difference is purely internal (one had a stack trace and a reporter ticket).
- **`recover()` only returns non-nil during an active panic.** Code that calls `recover()` on the happy path always gets `nil` — that's why the `if r := recover(); r != nil` idiom exists.
- **Re-panicking preserves the original panic value** if you `panic(rec)`, but **loses the original stack** — the new panic's stack starts at the re-panic site. Log the original stack *before* re-panicking.
- **Rust's `catch_unwind` returns `Result<T, Box<dyn Any>>`** — the panic payload is type-erased. You `downcast_ref::<&str>()`/`::<String>()` to read the message, and often can't get more than that.
- **Java `@RestControllerAdvice` catching `Throwable`** will also catch `Error` subtypes; that's usually fine for *one request* (return 500), but if the `Error` is `OutOfMemoryError`, the JVM may be doomed regardless — don't pretend a 500 fixed it.
- **Python's `threading.excepthook` vs `sys.excepthook`** — thread exceptions go to the former (3.8+), main-thread to the latter. Wire both if you want all panics reported.

---

## Apply it

1. Find a real component where **Panic & Recovery** affects an interface or dependency.
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

- Which boundary is most affected by Panic & Recovery?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
