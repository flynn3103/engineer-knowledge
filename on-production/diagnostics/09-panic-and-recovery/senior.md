# Panic & Recovery — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Panic & Recovery** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Panic & Recovery Roadmap](README.md)
> **Focus:** The *design* decision behind every panic boundary — **fail-fast vs. recover, abort vs. unwind, crash-only vs. graceful**. Supervision trees, panic propagation across goroutines/threads/async tasks, lock poisoning, and the policy you set once at the architecture level so that ten thousand call sites don't each have to decide.

---

## Core Concepts

### 1. The decision is "crash vs. recover," and it is an *architecture* decision

At this level the question is never "how do I recover this one panic?" It is "for *this class* of failure, in *this* service, is the correct response to crash the process and let it be restarted, or to contain the failure in-process and keep running?" That answer depends on the **cost of a restart** and the **recoverability of the state** — two properties of your architecture, not of the call site. A stateless HTTP pod behind a load balancer: crashing is nearly free, prefer crash-only. A singleton leader holding a 40 GB in-memory index with a 6-minute warm-up: crashing is expensive, you lean toward in-process containment and very careful state management. The senior makes this call deliberately and writes it down.

### 2. Unwind buys you a catch point; abort buys you a guarantee

A runtime that **unwinds** runs destructors and gives you a place to `catch`/`recover` — but it also means a panic can be *caught and ignored*, and that destructors run while the program is in a half-broken state (a destructor touching corrupt data can make things worse). A runtime that **aborts** gives up the catch point entirely in exchange for one guarantee: *a process that hit an impossible state dies immediately and cannot limp on.* For security-sensitive or correctness-critical code, that guarantee is worth more than recoverability. The senior chooses per service, sometimes per build profile.

### 3. "Let it crash" is a *strategy*, not an abdication

Erlang's "let it crash" looks reckless until you see the other half: every process runs under a **supervisor** that restarts it from a known-good initial state. The genius is that *recovery becomes the only stop/start path*, so it is exercised constantly and is therefore reliable — unlike defensive cleanup code that runs once a year and is always buggy. "Let it crash" works *only* with supervision and cheap, stateless-or-checkpointed restart. Copy the philosophy only when you also copy the supervisor.

### 4. A panic's blast radius equals its concurrency unit — know the unit per runtime

The single most expensive senior mistake is misjudging *how far a panic reaches*:

| Runtime | Unit | An uncaught panic/exception in that unit… |
|---|---|---|
| Go | goroutine | …**crashes the whole process.** No per-goroutine isolation. |
| Rust | thread | …(unwind) terminates *that thread*, leaves others running; (abort) kills the process. |
| Java | thread | …terminates *that thread*; the JVM survives (unless it's a non-daemon main or an `Error` like OOM). |
| Python | thread | …terminates *that thread* (prints traceback); main process survives. |
| Node | event loop / Worker | …`uncaughtException` → **process is now undefined**, exit; a `Worker` thread crash is isolated from the main thread. |

Go is the outlier and the trap: it has *no* thread-level isolation, so every goroutine is a process-level liability unless individually guarded. Rust/Java/Python isolate at the thread; Node isolates at the Worker.

### 5. Recovering into corrupt state is the failure mode the whole topic exists to prevent

Containment is only legitimate when the failed unit was *isolated*. The moment a panic happens mid-mutation of shared state — a half-updated map, a lock held over an invariant that's now broken — recovering and *continuing* means running on corruption. Rust encodes this directly with **lock poisoning**: a panic while holding a `Mutex` poisons it, and every later `lock()` returns `Err`, forcing you to acknowledge the data may be inconsistent. Other languages give you no such signal — *you* must reason about it, and the correct move is usually to crash (re-panic / abort), not continue.

### 6. Set the policy once; don't make every call site decide

Ten thousand call sites cannot each correctly decide crash-vs-recover. The senior installs the decision in *infrastructure*: one recover boundary per request, one supervisor per worker class, one process-level last-resort handler, one `panic` strategy in the build profile, and lint/review rules that forbid ad-hoc `recover()`/`catch (Throwable)` in business code. The policy lives in a handful of places, is documented, and is enforced — so the property holds across the codebase by construction.

### 7. Every crash is also a post-mortem artifact — design the death

A process that must die should die *informatively*: dump goroutines/threads, capture the panic value and stack, write a core if it's cheap, increment a `panics_total` metric, and flush the crash reporter *before* exiting. `GOTRACEBACK=crash`, `-XX:+HeapDumpOnOutOfMemoryError`, a `SIGABRT` core — these turn an outage into evidence. The senior designs the moment of death as carefully as the happy path.

---

## Fail-Fast vs. Recover — The Real Decision

The middle page's rule — "default to crash, recover only at boundaries" — is correct but incomplete. The senior decision is a *function of three variables*:

| Variable | Pushes toward **fail-fast (crash)** | Pushes toward **recover (contain)** |
|---|---|---|
| **Cost of restart** | Cheap: stateless pod, k8s reschedules in seconds | Expensive: large in-memory state, slow warm-up, leader election |
| **Recoverability of state** | State may be corrupt / invariant broken | State is provably isolated (per-request, immutable) |
| **Blast radius of continuing** | One process; siblings unaffected | Continuing endangers shared data / other users |

The decision matrix:

```text
                       │ restart is CHEAP        │ restart is EXPENSIVE
   ────────────────────┼─────────────────────────┼──────────────────────────
   state may be CORRUPT │ CRASH (fail-fast).      │ CRASH anyway — corrupt +
                        │ Cheapest + safest.      │ expensive still beats
                        │                         │ serving wrong data.
   ────────────────────┼─────────────────────────┼──────────────────────────
   state is ISOLATED    │ Either works; prefer    │ RECOVER at boundary.
                        │ crash-only for          │ Containment avoids a
                        │ simplicity.             │ pricey restart, and it's
                        │                         │ safe because isolated.
```

The one cell where recovery is the *clear* winner is bottom-right: **isolated state + expensive restart.** That's the request boundary in a server holding warm caches — exactly the middle-level pattern. Everywhere else, fail-fast is at least competitive and usually simpler. The top row — *corrupt state* — is non-negotiable: **never recover-and-continue past corruption,** regardless of restart cost. Serving wrong data is worse than any restart.

> The senior's bias: **when in doubt, crash.** A crash is loud, honest, and bounded. A wrong recovery is quiet, dishonest, and unbounded. You can always *add* a recover boundary later when you've proven isolation; you cannot un-corrupt a ledger.

### The "is this an `Err` or a panic" boundary, revisited at scale

A senior also owns the *upstream* decision: which failures are recoverable Layer-1 errors (`Result`/`error`/exceptions you handle) versus unrecoverable Layer-2 panics. The rule scales: **anything an operator/caller could plausibly respond to is an error; anything that means "a programmer's assumption is false" is a panic.** A 404 is an error. A `nil` where your invariant guaranteed non-nil is a panic. Drawing this line *consistently across a service* is a senior responsibility — see [Error Handling — Senior](../03-error-handling/senior.md) for the error half of this boundary.

---

## Abort vs. Unwind — The Runtime Policy

Unwinding is not free, and it is not always safe. The senior chooses the panic *strategy* deliberately, per language and sometimes per build.

### Rust — `panic = "unwind"` vs `panic = "abort"`

```toml
# Cargo.toml — the policy lives here, set once for the whole binary.
[profile.release]
panic = "abort"   # default is "unwind"
```

| | `panic = "unwind"` (default) | `panic = "abort"` |
|---|---|---|
| Destructors on panic | Run (stack unwinds) | **Not run** — process dies immediately |
| `catch_unwind` | Works | **Inert** — nothing to catch |
| Binary size | Larger (unwind tables) | Smaller (no landing pads) |
| Per-panic cost | Higher (frame-by-frame walk) | Zero (just `abort`) |
| Corruption guarantee | None — a panic can be caught & ignored | **A panicking process dies, period** |
| FFI safety | Risk of unwinding across C (UB unless `C-unwind`) | Safe: never unwinds across FFI |

**When a senior picks `abort`:**

- The binary is a leaf service where a restart is cheap and you want the *smallest, fastest* binary and the strongest "corruption → death" guarantee (much of the embedded and security world, and many CLI tools).
- You link heavily with C and don't want to reason about unwinding across FFI at all.
- You have *no* legitimate `catch_unwind` boundary (no thread-pool isolation, no test-harness catch) — then unwinding only buys you risk.

**When a senior keeps `unwind`:**

- You run a thread pool / worker model that isolates panics per worker via `catch_unwind` (a Rust web server, a `rayon` job runner) — you *need* the catch point.
- You're a library: **libraries should not assume `abort`** because the final binary chooses the strategy. Write code correct under both.

```rust
// A worker that ISOLATES panics — only meaningful under panic = "unwind".
use std::panic::{self, AssertUnwindSafe};

fn run_job(job: Job) -> JobOutcome {
    let result = panic::catch_unwind(AssertUnwindSafe(|| process(job)));
    match result {
        Ok(out) => out,
        Err(payload) => {
            let msg = downcast_panic(&payload);
            tracing::error!(panic = %msg, job_id = %job.id, "worker job panicked");
            metrics::counter!("worker.panics").increment(1);
            JobOutcome::Failed                 // CONTAIN: this job dies, pool lives
        }
    }
    // Under panic = "abort", this catch_unwind never fires and the WHOLE
    // process dies on the first panicking job. If your design depends on
    // per-job isolation, you MUST keep panic = "unwind".
}

fn downcast_panic(p: &Box<dyn std::any::Any + Send>) -> String {
    p.downcast_ref::<&str>().map(|s| s.to_string())
        .or_else(|| p.downcast_ref::<String>().cloned())
        .unwrap_or_else(|| "non-string panic payload".into())
}
```

> The trap: a team sets `panic = "abort"` for a smaller binary, *then* someone adds a `catch_unwind`-based worker pool expecting isolation. It compiles. It "works" in dev (no panics). In production the first panicking job kills the whole process. **The panic strategy and the isolation design must agree, and that agreement must be a written, reviewed decision.**

### Go — always unwinds, but `fatal error` cannot be recovered

Go always unwinds for `panic`, so `recover` always works *for panics*. But Go has a second, non-recoverable class: **fatal runtime errors** — concurrent map writes, stack overflow, out-of-memory, a deadlock detected by the runtime. These print `fatal error:` (not `panic:`) and **cannot be recovered** — they're Go's `abort`. You do not get to choose; the runtime decides which failures are recoverable.

```go
// This is a PANIC — recoverable.
var p *int
_ = *p                      // panic: runtime error: invalid memory address

// This is a FATAL ERROR — NOT recoverable, no recover() will catch it.
m := map[int]int{}
go func() { for { m[1] = 1 } }()
go func() { for { m[2] = 2 } }()   // fatal error: concurrent map writes
```

The senior knob is `GOTRACEBACK`, which governs how a fatal/uncaught panic *dies*:

```bash
GOTRACEBACK=all    ./svc   # dump ALL goroutine stacks (default for most services)
GOTRACEBACK=crash  ./svc   # dump all stacks AND produce a core dump (SIGABRT)
```

Set `GOTRACEBACK=crash` on services where a core dump is worth the disk — it converts a fatal crash into a debuggable artifact. See [Crash Reporting — Senior](../07-crash-reporting/senior.md) for turning these into tickets.

### Java — unwinds, but `Error` is the "abort-ish" tier

The JVM always unwinds (`finally`/try-with-resources run). The senior distinction is `Exception` vs `Error`: `RuntimeException` is a recoverable-at-boundary panic-analogue; `Error` (`OutOfMemoryError`, `StackOverflowError`, `LinkageError`) signals the *JVM itself* may be doomed. Catching `Error` to "keep serving" is the Java version of recovering into corruption — you can catch it for *one request's* 500, but don't pretend the JVM is healthy.

### Node — you don't unwind a corrupt event loop

Node has no "abort vs unwind" knob, but it has the same *principle* baked into its docs: after `uncaughtException`, **the process is in an undefined state** and the only correct action is to log, flush, and exit. There is no safe "resume the event loop." `worker_threads` are Node's isolation primitive — a crashing Worker doesn't kill the main process (covered below).

---

## Crash-Only Software

**Crash-only software** (Candea & Fox, USENIX HotOS 2003) is the design philosophy underneath modern cloud-native services, and it's the senior's default for stateless components. The thesis:

> *Make crashing the only way to stop, and recovery the only way to start. Then recovery is exercised on every start, so it is always correct — and you delete all the buggy "graceful shutdown" code that never ran anyway.*

The implications for how you design panic/recovery:

1. **No graceful-shutdown path to maintain.** If `kill -9` and a clean `SIGTERM` lead to the *same* recovery on next boot, you don't have two code paths to keep correct. Half the "shutdown hook" bugs in the world come from a graceful path that diverges from the crash path.
2. **Every restart is from a known-good state.** State lives in durable stores (DB, queue, object store) or is reconstructable. The process holds only *derived* state it can rebuild. This is what makes "let it crash" safe.
3. **Idempotency everywhere.** Because a crash can happen mid-operation, every operation must be safe to retry after restart. (See Retry Pattern and the `retry-pattern` skill.)
4. **Fast, bounded recovery.** Crash-only is only cheap if recovery is fast. A 6-minute warm-up turns "let it crash" into a 6-minute outage. Crash-only pushes you toward *checkpointing* and *lazy* state loading.

```text
   GRACEFUL-CENTRIC DESIGN              CRASH-ONLY DESIGN
   ───────────────────────             ─────────────────
   start ──► run ──► graceful stop      start = recover ──► run ──► CRASH
                │         │                  ▲                         │
                │      (buggy, rare)         └─────────────────────────┘
                └──► sometimes crash         one path, always tested
   two stop paths, one untested         one stop path, always tested
```

Kubernetes is a crash-only system by construction: liveness probes *kill* unhealthy pods, the scheduler *recreates* them, and there is no "pause and fix in place." When you design for k8s, **lean into crash-only**: prefer `panic`/crash + restart over elaborate in-process recovery, *as long as* your restart is cheap and your state is durable. The famous anti-pattern is `CrashLoopBackOff` — crash-only degrades badly when recovery *isn't* fast or the crash is deterministic (the pod crashes, restarts, crashes again on the same poison input). Crash-only assumes restart eventually succeeds; pair it with poison-input handling and a dead-letter path.

> **Senior judgment:** crash-only is the right default for stateless and checkpoint-able services. It is *wrong* for a stateful singleton where a restart loses 40 GB of irreplaceable in-memory state and takes minutes to rebuild — there, you invest in in-process resilience and very careful corruption detection. Know which kind of service you're holding.

---

## Supervision — Letting a Tree Restart What Crashed

The most important idea this page imports from outside the "recover" mindset: **don't catch the failure in place — let it propagate up to a supervisor whose entire job is to restart the failed unit from a known-good state.** This is the Erlang/OTP model, copied by Akka, Elixir, and (in spirit) by Kubernetes.

### Why supervision beats in-place recovery for stateful units

In-place `recover` says: *"I caught the panic; I'll patch up and continue."* But continuing from a half-failed state is exactly the corruption risk. Supervision says: *"the unit failed; throw it away and start a fresh one from a clean initial state."* The fresh unit has *no* corrupt state because it never touched the bad input. Recovery-by-replacement sidesteps the corruption question entirely.

### Restart strategies (OTP/Akka vocabulary every senior should know)

| Strategy | Behavior | Use when |
|---|---|---|
| **one-for-one** | Restart only the crashed child | Children are independent (typical worker pool) |
| **one-for-all** | Restart *all* children when any crashes | Children share coupled state; one's death invalidates the rest |
| **rest-for-one** | Restart the crashed child + those started after it | Children form a dependency chain |
| **max_restarts / intensity** | If a child crashes more than N times in T seconds, the *supervisor* gives up and escalates upward | Always — this is the circuit breaker that stops a restart storm (`CrashLoopBackOff` analogue) |

The `max_restarts` parameter is the senior's safety valve: it converts "let it crash" from an infinite-retry footgun into a bounded one. If a worker crashes 5 times in 10 seconds, the input is *deterministically* poisoned — restarting again is pointless, so the supervisor escalates (dead-letters the input, alerts, or itself crashes up to *its* supervisor).

### A supervised worker pool in Go (no actor framework needed)

You don't need Akka to apply supervision thinking. Here's a supervisor goroutine that restarts a worker when it panics, with a restart budget that trips:

```go
// Supervise runs `work` in a goroutine, restarting it when it panics,
// up to maxRestarts within window. Past the budget, it gives up and
// escalates (returns an error to ITS caller — the next supervisor up).
func Supervise(ctx context.Context, name string, maxRestarts int, window time.Duration, work func(context.Context)) error {
	var restarts []time.Time
	for {
		if ctx.Err() != nil {
			return ctx.Err()
		}
		crashed := runGuarded(ctx, name, work) // returns true if it panicked
		if !crashed {
			return nil // clean exit, nothing to restart
		}

		now := time.Now()
		restarts = append(restarts, now)
		// Drop restarts outside the window.
		cutoff := now.Add(-window)
		i := 0
		for ; i < len(restarts) && restarts[i].Before(cutoff); i++ {
		}
		restarts = restarts[i:]

		if len(restarts) > maxRestarts {
			// Restart budget exceeded: the failure is persistent, not transient.
			// Escalate instead of looping forever (the CrashLoopBackOff lesson).
			slog.Error("supervisor giving up; restart intensity exceeded",
				"worker", name, "restarts", len(restarts), "window", window)
			metrics.SupervisorGaveUp.WithLabelValues(name).Inc()
			return fmt.Errorf("worker %q exceeded restart budget (%d in %s)", name, maxRestarts, window)
		}

		backoff := time.Duration(len(restarts)) * 200 * time.Millisecond
		slog.Warn("restarting crashed worker", "worker", name, "restart", len(restarts), "backoff", backoff)
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(backoff):
		}
	}
}

// runGuarded runs work, recovering+logging+reporting a panic, returning
// whether it panicked. This is the recover-at-boundary brick from middle.md,
// now used as the supervisor's failure DETECTOR — not as the resilience itself.
func runGuarded(ctx context.Context, name string, work func(context.Context)) (panicked bool) {
	defer func() {
		if rec := recover(); rec != nil {
			panicked = true
			stack := debug.Stack()
			slog.Error("worker panicked", "worker", name, "panic", rec, "stack", string(stack))
			report.Capture(rec, stack, name) // crash reporter — see crash-reporting/
		}
	}()
	work(ctx)
	return false
}
```

The structural insight: the `recover` is *not* the resilience strategy — it's the supervisor's *failure detector*. The resilience comes from **restart-from-clean-state plus a bounded restart budget.** This is "let it crash" implemented in Go.

### Erlang/Elixir — the real thing

```elixir
# A supervisor restarting up to 3 crashes in 5 seconds, one_for_one.
# Past the budget, THIS supervisor itself crashes up to its parent.
children = [
  {Worker, []},
  {Worker, []}
]

Supervisor.init(children,
  strategy: :one_for_one,
  max_restarts: 3,
  max_seconds: 5
)
```

In OTP, the worker code itself is written *without* defensive error handling — it just does the happy path and lets a bad message crash it. The supervisor restarts it. This is only safe because (a) restart is microseconds, (b) state is held in a separate, supervised process or an external store, and (c) `max_restarts` stops a poison-message storm.

> **The portable lesson, even if you never write Erlang:** prefer *restart-from-clean-state* over *recover-and-continue* for any unit whose state might be corrupt — and always bound the restarts. Kubernetes liveness probes + `restartPolicy` + `CrashLoopBackOff` are this exact pattern at the container level.

---

## Panic Propagation Across Concurrency Units

The middle page warned that "a recover only catches its own goroutine." At senior level you need the full propagation matrix and the idiomatic *structured-concurrency* fixes per runtime.

### Go — goroutines do not propagate, they detonate

A panic in a goroutine that isn't recovered **crashes the entire process** — there is no thread-level isolation, and the parent goroutine cannot catch a child's panic. This is Go's sharpest edge.

```go
// WRONG: the request boundary's recover does NOT protect this goroutine.
func handler(w http.ResponseWriter, r *http.Request) {
	go doAsyncWork()       // if this panics → WHOLE PROCESS DIES
	w.Write([]byte("accepted"))
}
```

Structured-concurrency fix with `errgroup` — panics still don't propagate as errors automatically (a panic isn't an `error`), so wrap:

```go
// errgroup gives you cancellation + error collection, but a PANIC in a
// goroutine is not an error — it still crashes the process. Convert it.
g, ctx := errgroup.WithContext(ctx)
for _, job := range jobs {
	job := job
	g.Go(func() (err error) {
		defer func() {
			if rec := recover(); rec != nil {
				err = fmt.Errorf("panic in job %s: %v\n%s", job.ID, rec, debug.Stack())
			}
		}()
		return process(ctx, job)
	})
}
if err := g.Wait(); err != nil {   // panic now arrives as a normal error
	return err
}
```

> Go 1.23's `errgroup` and most libraries still do **not** auto-recover goroutine panics. The senior bans raw `go fn()` for panic-prone work via lint and provides a `SafeGo`/guarded-`errgroup` wrapper. One missed `go fn()` is a process-wide outage waiting for the wrong input.

### Rust — threads isolate, async tasks return the panic as `Err`

A panic in a spawned **thread** terminates only that thread (under unwind); `JoinHandle::join()` returns `Err` carrying the payload:

```rust
let handle = std::thread::spawn(|| {
    panic!("worker exploded");        // terminates THIS thread only (unwind)
});
match handle.join() {
    Ok(_) => {}
    Err(payload) => {
        // The panic propagates to the PARENT here, as an Err — not a crash.
        eprintln!("worker thread panicked: {}", downcast_panic(&payload));
    }
}
```

Tokio **tasks** are even cleaner — a panic in a task is captured and surfaced through the `JoinHandle`:

```rust
let handle = tokio::spawn(async {
    panic!("task exploded");
});
match handle.await {
    Ok(_) => {}
    Err(join_err) if join_err.is_panic() => {
        // The task panicked; the runtime caught it. Other tasks keep running.
        tracing::error!("task panicked: {:?}", join_err);
    }
    Err(_) => { /* task was cancelled */ }
}
```

This is why Rust's concurrency story is safer here than Go's: the runtime *captures* the panic at the task boundary and hands it to you as a `Result`, instead of detonating the process. But note: a detached task whose `JoinHandle` you drop swallows the panic silently — the senior keeps the handle or uses a `JoinSet` so panics aren't lost.

### Java — threads isolate; wire an `UncaughtExceptionHandler` and prefer pools

A panic (uncaught `RuntimeException`) in a `Thread` kills *that* thread; the JVM lives. But the death is silent unless you install a handler:

```java
// Global safety net for raw threads.
Thread.setDefaultUncaughtExceptionHandler((thread, throwable) -> {
    log.error("uncaught in thread {}", thread.getName(), throwable);
    Sentry.captureException(throwable);
    panicCounter.increment();
});
```

The subtle trap: with an `ExecutorService`, a task that throws is handled differently depending on submission:

```java
ExecutorService pool = Executors.newFixedThreadPool(4);

pool.execute(() -> { throw new RuntimeException("boom"); });
//   ^ execute(): the worker thread dies, UncaughtExceptionHandler fires,
//     the pool quietly replaces the thread. You SEE it (if handler installed).

Future<?> f = pool.submit(() -> { throw new RuntimeException("boom"); });
//   ^ submit(): the exception is SWALLOWED into the Future. The worker
//     thread does NOT die, no handler fires. You only learn of it when
//     you call f.get() — which most people forget. SILENT failure.
```

> **Senior gotcha that has caused real incidents:** `ExecutorService.submit()` *eats* the exception into the returned `Future`. If you never call `Future.get()`, the failure vanishes. Always either `get()` the future or override `afterExecute`/use `execute()` for fire-and-forget so the handler fires.

### Python — threads isolate; `threading.excepthook` centralizes; multiprocessing differs

An uncaught exception in a `threading.Thread` prints a traceback and kills *that thread*; the process survives. Centralize reporting:

```python
import threading, sys, logging
log = logging.getLogger(__name__)

def thread_hook(args):
    log.error("uncaught in thread %s", args.thread.name,
              exc_info=(args.exc_type, args.exc_value, args.exc_traceback))
    sentry_sdk.capture_exception(args.exc_value)

threading.excepthook = thread_hook        # 3.8+, for THREAD exceptions
sys.excepthook = lambda *a: log.error("uncaught in main", exc_info=a)  # MAIN thread
```

`concurrent.futures` mirrors Java's `submit` trap: an exception in a `ThreadPoolExecutor`/`ProcessPoolExecutor` task is stored in the `Future` and re-raised only on `future.result()`. With `ProcessPoolExecutor`, a worker that *segfaults* (not a Python exception) brings down the pool with a `BrokenProcessPool` — a true crash, not a catchable exception.

### Node — `uncaughtException` means "exit," and `worker_threads` are the isolation unit

After `uncaughtException`, **the event loop is in an undefined state.** The documented-correct handler logs, flushes, and *exits* — it does **not** resume:

```js
process.on("uncaughtException", (err, origin) => {
  // The process is now in an UNDEFINED state. Do NOT resume the event loop.
  log.fatal({ err, origin }, "uncaughtException — exiting");
  Sentry.captureException(err);
  flushTelemetrySync();
  process.exit(1);            // let the supervisor (pm2/k8s) restart a clean process
});

process.on("unhandledRejection", (reason) => {
  // Modern Node crashes on this by default; handle it the same way.
  log.fatal({ reason }, "unhandledRejection — exiting");
  Sentry.captureException(reason);
  flushTelemetrySync();
  process.exit(1);
});
```

For true isolation, Node's unit is the **Worker thread** — a crash in a Worker does *not* kill the main process:

```js
const { Worker } = require("node:worker_threads");

const worker = new Worker("./risky-task.js");
worker.on("error", (err) => {
  // The Worker threw uncaught — the worker thread is gone, MAIN survives.
  log.error({ err }, "worker crashed; respawning");
  metrics.workerCrashes.inc();
  spawnReplacementWorker();          // supervision at the Worker level
});
worker.on("exit", (code) => {
  if (code !== 0) log.warn({ code }, "worker exited nonzero");
});
```

This is Node's version of the supervision pattern: run risky/CPU-bound work in a `Worker`, treat a Worker crash as a recoverable event in the main thread, respawn from clean state.

### The propagation matrix, consolidated

| Runtime | Spawn primitive | Uncaught panic propagates to parent as… | Process survives? |
|---|---|---|---|
| Go | `go fn()` | **nothing** — process crashes | ❌ No (must self-recover) |
| Go | `errgroup` (with manual recover) | an `error` from `Wait()` | ✅ if you wrap |
| Rust | `thread::spawn` | `Err` from `join()` (unwind) | ✅ Yes |
| Rust | `tokio::spawn` | `JoinError{is_panic}` from `await` | ✅ Yes |
| Java | `new Thread` | `UncaughtExceptionHandler` (after thread dies) | ✅ Yes |
| Java | `executor.submit` | stored in `Future`, re-raised on `get()` (**silent if never get**) | ✅ Yes |
| Python | `threading.Thread` | `threading.excepthook` (after thread dies) | ✅ Yes |
| Python | `ProcessPoolExecutor` (segfault) | `BrokenProcessPool` | ❌ pool broken |
| Node | `uncaughtException` | event — **process must exit** | ❌ exit & restart |
| Node | `worker_threads` | `'error'` event on the Worker | ✅ main survives |

---

## Lock Poisoning and Corrupt-State Detection

The whole topic's nightmare is *recovering into corruption.* Rust is the only mainstream language that detects this for you, via **lock poisoning** — and understanding it teaches the principle every language needs.

### Rust — a panic while holding a lock poisons it

```rust
use std::sync::Mutex;

let data = Mutex::new(Vec::<i32>::new());

// Thread A: panics WHILE holding the lock, mid-mutation.
let result = std::thread::spawn(|| {
    let mut guard = data.lock().unwrap();
    guard.push(1);
    panic!("crashed mid-mutation");   // the Vec may now be in a half-updated state
    // guard dropped during unwind → the Mutex is now POISONED
}).join();

// Thread B (or later code): the lock REMEMBERS that a panic occurred while held.
match data.lock() {
    Ok(guard) => use_data(&guard),
    Err(poisoned) => {
        // The data MAY be inconsistent. Rust forces you to acknowledge it.
        tracing::error!("lock poisoned — data may be corrupt");
        // Option 1: recover the data anyway, accepting the risk:
        let guard = poisoned.into_inner();
        // Option 2 (often correct): propagate / crash — don't trust the data.
    }
}
```

The design lesson is profound: **poisoning makes "did a panic leave this shared state inconsistent?" a question the type system forces you to answer.** Every other language leaves that question implicit, and the default human answer ("eh, probably fine, keep going") is the bug.

> Note: there's an ongoing debate that poisoning is over-eager (most code `.unwrap()`s the poison and ignores it), and some prefer `parking_lot::Mutex` which *doesn't* poison. The senior view: poisoning is a *correctness prompt*. If you `into_inner()` away every poison without thinking, you've reintroduced the exact bug poisoning exists to catch.

### Every other language — *you* are the poison detector

There is no automatic poisoning in Go, Java, Python, or Node. The discipline must be manual:

```go
// Manual "poisoning" — re-panic when a panic happened mid-mutation under a lock.
func (l *Ledger) Apply(tx Transaction) {
	l.mu.Lock()
	defer l.mu.Unlock()
	defer func() {
		if rec := recover(); rec != nil {
			slog.Error("panic mid-ledger-mutation; state may be corrupt",
				"panic", rec, "stack", string(debug.Stack()))
			report.Capture(rec, debug.Stack(), tx)
			// The ledger may be half-written and we hold no signal that it's clean.
			// CRASH rather than serve a corrupt ledger. This is manual poisoning.
			panic(rec)        // re-panic: process dies, supervisor restarts clean
		}
	}()
	l.balance += tx.Amount   // if a panic fires between these two lines,
	l.audit = append(l.audit, tx) //   the ledger is inconsistent
}
```

The senior generalizes: **any shared mutable state guarded by a lock needs a documented answer to "what happens if we panic mid-mutation?"** The default answer should be *crash*, because continuing is unfalsifiable corruption. Reserve recover-and-continue for state you can *prove* is either untouched or transactional (e.g., a copy-on-write swap that's atomic, so a panic before the swap leaves the original intact).

```go
// Corruption-proof by design: build a NEW value, swap atomically at the end.
// A panic before the swap leaves the old value fully intact — nothing to poison.
func (c *Config) Reload(raw []byte) error {
	next, err := parse(raw)   // if this panics, c.current is untouched
	if err != nil {
		return err
	}
	c.current.Store(next)     // single atomic swap — no half-state ever observable
	return nil
}
```

> The deepest senior move isn't detecting corruption after the fact — it's *designing it out*: copy-on-write, atomic swap, transactional updates, immutable data. If a panic can never leave observable half-state, the whole "recover into corruption" question disappears. See the `immutability-patterns` skill.

---

## Process-Level Last-Resort Handlers

Below the boundary recoveries sits one final net: the process-level handler that fires when *everything else* missed. Its job is **not** to keep running — it's to die *informatively and cleanly*.

| Runtime | Last-resort hook | Correct action |
|---|---|---|
| Go | a top-level `defer recover()` in `main`; `GOTRACEBACK`; `debug.SetTraceback` | log + flush reporter + (usually) re-panic/exit; can't truly "continue" |
| Rust | `std::panic::set_hook` | log/report in the hook; the hook runs *before* unwind/abort |
| Java | `Thread.setDefaultUncaughtExceptionHandler` | log + report; thread is already dying |
| Python | `sys.excepthook` + `threading.excepthook` + `faulthandler` | log + report; for segfaults, `faulthandler.enable()` |
| Node | `process.on('uncaughtException' / 'unhandledRejection')` | log + flush + **`process.exit(1)`** |

Rust's `panic::set_hook` is especially useful because it runs *before* the unwind/abort decision — so it works even under `panic = "abort"`:

```rust
use std::panic;

fn install_panic_hook() {
    let default = panic::take_hook();
    panic::set_hook(Box::new(move |info| {
        // Runs on EVERY panic, BEFORE unwinding/aborting — works under abort too.
        let location = info.location().map(|l| format!("{}:{}", l.file(), l.line()))
            .unwrap_or_else(|| "unknown".into());
        let msg = info.payload().downcast_ref::<&str>().copied().unwrap_or("?");
        tracing::error!(%location, panic = %msg, "PANIC");
        crash_reporter::capture_panic(info);    // ship to Sentry BEFORE we die
        default(info);                           // keep the default backtrace print
    }));
}
```

> The senior rule for last-resort handlers: **they report, they don't resuscitate.** A process that reached the last-resort handler hit a state nobody anticipated — the safe assumption is that it's corrupt. Flush telemetry, capture the crash, exit non-zero, let the supervisor restart clean.

---

## Designing the Panic Policy for a Service

Bring it together: the senior deliverable is a **written panic policy** that every engineer on the team inherits. A real one reads like this:

```text
   ┌──────────────────── ORDERS-SERVICE PANIC POLICY ────────────────────┐
   │                                                                     │
   │  1. CLASSIFICATION                                                  │
   │     • Caller-recoverable failure  → return error (Layer 1)          │
   │     • Broken programmer invariant → panic (Layer 2)                 │
   │     • Runtime-fatal (concurrent map write, OOM) → let it die        │
   │                                                                     │
   │  2. RECOVER BOUNDARIES (the ONLY recover sites)                     │
   │     • HTTP middleware  → log+report+500, server lives               │
   │     • Worker, per-job  → log+report+dead-letter, pool lives         │
   │     • Every spawned goroutine via SafeGo (lint-enforced)            │
   │                                                                     │
   │  3. CRASH-vs-CONTAIN MATRIX                                         │
   │     • Stateless path + cheap restart → prefer CRASH (crash-only)    │
   │     • Mid-mutation under a lock      → CRASH (manual poisoning)     │
   │     • Isolated request + warm caches → CONTAIN at boundary          │
   │                                                                     │
   │  4. RUNTIME STRATEGY                                                │
   │     • Go: GOTRACEBACK=crash in prod (core dump)                     │
   │     • Rust libs: correct under unwind AND abort                     │
   │     • Rust bins: panic=abort UNLESS a catch_unwind worker pool      │
   │                                                                     │
   │  5. SUPERVISION                                                     │
   │     • Worker classes run under Supervise(max=5/30s) → escalate      │
   │     • k8s liveness probe kills + reschedules (crash-only)           │
   │     • CrashLoopBackOff alert wired to on-call                       │
   │                                                                     │
   │  6. ON DEATH                                                        │
   │     • flush crash reporter, dump goroutines, panics_total++ THEN exit│
   │                                                                     │
   │  ENFORCEMENT: lint bans raw `go fn()`, empty recover, catch(Throwable)│
   │               in business code; CI greps for silent swallows.        │
   └─────────────────────────────────────────────────────────────────────┘
```

The point of writing it down: the policy becomes a **property of the codebase**, checked in review and lint, instead of a decision re-litigated at every call site by engineers of varying experience.

---

## Code Examples

### Go — a complete supervised, crash-only-friendly worker service

```go
package main

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"os/signal"
	"runtime/debug"
	"syscall"
	"time"
)

// SafeGo: the ONLY sanctioned way to spawn a goroutine. Lint bans raw `go`.
func SafeGo(name string, fn func()) {
	go func() {
		defer func() {
			if rec := recover(); rec != nil {
				slog.Error("goroutine panic", "name", name,
					"panic", rec, "stack", string(debug.Stack()))
				report.Capture(rec, debug.Stack(), name)
				// A bare spawned goroutine has no supervisor; for THIS process
				// we let a leaked panic die loudly rather than silently continue.
			}
		}()
		fn()
	}()
}

// Supervise restarts `work` on panic, bounded by a restart budget.
func Supervise(ctx context.Context, name string, work func(context.Context)) error {
	const maxRestarts, window = 5, 30 * time.Second
	var crashes []time.Time
	for {
		if ctx.Err() != nil {
			return ctx.Err()
		}
		if !runGuarded(ctx, name, work) {
			return nil
		}
		now := time.Now()
		crashes = append(crashes, now)
		cutoff := now.Add(-window)
		for len(crashes) > 0 && crashes[0].Before(cutoff) {
			crashes = crashes[1:]
		}
		if len(crashes) > maxRestarts {
			return fmt.Errorf("worker %q exceeded restart budget", name) // escalate
		}
		slog.Warn("restarting worker", "name", name, "count", len(crashes))
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(time.Duration(len(crashes)) * 200 * time.Millisecond):
		}
	}
}

func runGuarded(ctx context.Context, name string, work func(context.Context)) (panicked bool) {
	defer func() {
		if rec := recover(); rec != nil {
			panicked = true
			slog.Error("worker panic", "name", name, "panic", rec, "stack", string(debug.Stack()))
			report.Capture(rec, debug.Stack(), name)
		}
	}()
	work(ctx)
	return false
}

func main() {
	// GOTRACEBACK=crash should be set in the environment for a core dump.
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGTERM, syscall.SIGINT)
	defer stop()

	// Supervised worker; if it blows its restart budget, the whole process
	// exits non-zero — and k8s restarts it clean (crash-only at the container).
	if err := Supervise(ctx, "order-consumer", consumeOrders); err != nil {
		slog.Error("supervisor escalated; exiting for a clean restart", "err", err)
		os.Exit(1)
	}
}

func consumeOrders(ctx context.Context) { /* pull jobs; a poison job panics → restart */ }
```

### Rust — a thread pool that isolates panics, with poisoning awareness

```rust
use std::panic::{self, AssertUnwindSafe};
use std::sync::{Arc, Mutex};

struct Pool {
    state: Arc<Mutex<Stats>>,   // shared, lock-protected — poisoning matters here
}

impl Pool {
    fn run_job(&self, job: Job) {
        let state = Arc::clone(&self.state);
        // catch_unwind isolates this job's panic to the pool (needs panic="unwind").
        let outcome = panic::catch_unwind(AssertUnwindSafe(|| process(job)));
        match outcome {
            Ok(()) => {
                // Update shared stats; if the lock is poisoned, a PRIOR job panicked
                // mid-mutation — the stats may be inconsistent. Decide explicitly.
                match state.lock() {
                    Ok(mut s) => s.completed += 1,
                    Err(poisoned) => {
                        tracing::error!("stats lock poisoned; refusing to trust counters");
                        // We choose to crash this pool rather than report wrong stats.
                        let _ = poisoned; // not into_inner() — we don't trust it
                        std::process::abort();
                    }
                }
            }
            Err(payload) => {
                tracing::error!("job panicked: {}", downcast_panic(&payload));
                metrics::counter!("pool.job_panics").increment(1);
                // The job is contained; the pool keeps running OTHER jobs.
            }
        }
    }
}

fn downcast_panic(p: &Box<dyn std::any::Any + Send>) -> String {
    p.downcast_ref::<&str>().map(|s| s.to_string())
        .or_else(|| p.downcast_ref::<String>().cloned())
        .unwrap_or_else(|| "non-string panic".into())
}
# struct Job; struct Stats { completed: u64 } fn process(_: Job) {}
```

### Java — supervised executor with visible failures

```java
// A ThreadPoolExecutor that does NOT swallow task failures (the submit() trap).
public class SupervisedPool extends ThreadPoolExecutor {
    private static final Logger log = LoggerFactory.getLogger(SupervisedPool.class);

    public SupervisedPool(int n) {
        super(n, n, 0L, TimeUnit.MILLISECONDS, new LinkedBlockingQueue<>());
    }

    @Override
    protected void afterExecute(Runnable r, Throwable t) {
        super.afterExecute(r, t);
        // For execute(): t carries the throwable.
        // For submit(): the throwable hid inside the Future — dig it out.
        if (t == null && r instanceof Future<?> f && f.isDone()) {
            try {
                f.get();
            } catch (CancellationException ce) {
                t = ce;
            } catch (ExecutionException ee) {
                t = ee.getCause();   // <-- the exception submit() swallowed
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
            }
        }
        if (t != null) {
            log.error("task failed in pool", t);   // now it's VISIBLE
            Sentry.captureException(t);
            taskFailures.increment();
        }
    }
}
```

### Node — supervised worker pool with respawn

```js
const { Worker } = require("node:worker_threads");
const os = require("node:os");

class WorkerPool {
  constructor(script, size = os.cpus().length) {
    this.script = script;
    this.size = size;
    this.workers = [];
    for (let i = 0; i < size; i++) this.#spawn();
  }

  #spawn() {
    const w = new Worker(this.script);
    w.on("error", (err) => {
      // A Worker crashed (uncaught throw). MAIN process is unaffected.
      log.error({ err }, "worker crashed; respawning from clean state");
      metrics.workerCrashes.inc();
      this.#replace(w);                 // supervision: restart the dead worker
    });
    w.on("exit", (code) => {
      if (code !== 0) this.#replace(w);  // nonzero exit = abnormal, respawn
    });
    this.workers.push(w);
  }

  #replace(dead) {
    this.workers = this.workers.filter((x) => x !== dead);
    if (this.workers.length < this.size) this.#spawn();
  }
}
```

---

## Worked Example — A Recover That Hid a Data-Corruption Bug

**The setup.** A payments service has a global recover middleware (the textbook middle-level pattern). One handler updates an in-memory `balanceCache` under a mutex *and* writes to the database. The cache and DB are supposed to stay in sync.

```go
func (h *Handler) Debit(w http.ResponseWriter, r *http.Request) {
	acct, amt := parse(r)
	h.mu.Lock()
	defer h.mu.Unlock()

	h.balanceCache[acct] -= amt           // (1) mutate cache
	if err := h.db.Debit(acct, amt); err != nil { // (2) write DB
		panic(err)                        // a DB error panics here
	}
	w.WriteHeader(200)
}
```

**The incident.** A DB hiccup makes `h.db.Debit` return an error for a burst of requests. Each one `panic`s at line (2) — *after* the cache was already decremented at line (1). The global recover middleware catches every panic, logs it, returns 500, and **keeps the server running.** For six hours, the in-memory `balanceCache` drifts further and further below the real DB balances, because every failed debit still subtracted from the cache. Customers see *lower* balances than they actually have. No alert fires — the server is "healthy," returning 500s at a rate buried in normal noise.

**Why the boundary recovery made it worse.** The recover was *correct at the request level* (one request fails, server lives) but *wrong at the state level*: the panic happened **mid-mutation of shared state under a lock**, and recovering-and-continuing kept serving from a corrupt cache. The bulkhead had a hole in it — the cache is shared across requests, so "request isolation" was an illusion.

**Diagnosis.** On-call notices `balanceCache` and DB diverging via a reconciliation job. A `git log -p` on the handler + the 500-rate graph aligning with the DB hiccup window points at the panic-after-mutation ordering. The recovered panics *were* in the logs and the crash reporter — but nobody connected "recovered 500" with "cache corruption" because the recover made it look benign.

**The three fixes (defense in depth):**

```go
// FIX 1 — order operations so a failure can't leave half-state.
//          Write the DB FIRST; only touch the cache after it succeeds.
func (h *Handler) Debit(w http.ResponseWriter, r *http.Request) {
	acct, amt := parse(r)
	h.mu.Lock()
	defer h.mu.Unlock()

	if err := h.db.Debit(acct, amt); err != nil {
		// Recoverable error → return it, don't panic. Cache untouched.
		http.Error(w, "debit failed", http.StatusInternalServerError)
		return
	}
	h.balanceCache[acct] -= amt   // only after the source of truth is updated
	w.WriteHeader(200)
}

// FIX 2 — manual poisoning: if anything DOES panic mid-mutation, crash,
//          don't let the boundary recover serve a corrupt cache.
defer func() {
	if rec := recover(); rec != nil {
		slog.Error("panic under balance lock; cache may be corrupt", "panic", rec)
		report.Capture(rec, debug.Stack(), nil)
		panic(rec)  // re-panic past the boundary → clean restart, fresh cache
	}
}()

// FIX 3 — the DB error was never a panic to begin with.
//          A DB failure is a Layer-1 error the caller can respond to (retry/500),
//          NOT a broken-invariant panic. Misclassification was the root cause.
```

**The lessons (all senior-level):**

1. **A boundary recover is not a license to recover into corruption.** The recover must sit *outside* the corruptible region; here the corruption was *inside* the lock, past the mutation.
2. **`panic` was the wrong tool for a DB error** — a recoverable failure was promoted to a panic, then caught and hidden. Classification (error vs. panic) is the upstream root cause.
3. **Design out the half-state**: do the irreversible/authoritative write first, the derived update second. A panic between them then can't corrupt.
4. **"Server healthy + returning 500s" can mask data corruption.** Wire a *correctness* alert (cache/DB reconciliation), not just a liveness one.

---

## Failure Stories From the Field

These are the shapes of real incidents this topic exists to prevent.

| Story | Root cause | Senior takeaway |
|---|---|---|
| **The silent goroutine that killed prod** | A handler spawned `go sendMetrics()`; a nil-map write inside panicked. No recover. The *whole Go process* died — every in-flight request dropped — despite a perfect request-level recover middleware. | Go goroutines detonate the process. Ban raw `go fn()`; every spawn through `SafeGo`. |
| **`submit()` ate the exception** | A scheduled cleanup job thrown into `executor.submit()` started throwing. Nobody called `Future.get()`. The cleanup silently stopped for *weeks*; disk filled, then the host died. | `ExecutorService.submit` swallows exceptions into the `Future`. Use `afterExecute` or `execute()` for fire-and-forget. |
| **`panic = "abort"` met `catch_unwind`** | A team set `abort` for a smaller binary. Months later, someone added a `catch_unwind` worker pool expecting per-job isolation. First panicking job killed the whole service in prod. | The panic strategy and the isolation design must be one reviewed decision. |
| **The poisoned cache (above)** | Recover-and-continue past a mid-mutation panic served a corrupt in-memory balance for 6 hours. | Never recover *into* corruption; design out half-state; classify DB errors as errors. |
| **CrashLoopBackOff storm** | A bad config deploy made the process panic on boot. k8s restarted it forever; the restart storm hammered the config service, which then failed *other* services. "Let it crash" with no restart budget. | Bound restarts (`max_restarts`/backoff). A deterministic crash is not a transient one. |
| **The `uncaughtException` that resumed** | A Node service installed an `uncaughtException` handler that *logged and continued* (no `exit`). The event loop ran on undefined state; it served subtly wrong responses until a memory corruption finally crashed it hours later. | After `uncaughtException`, the only safe action is exit. Never resume. |
| **FFI unwind UB** | A Rust panic unwound across an `extern "C"` callback into a C library. Undefined behavior; intermittent corruption that took weeks to trace. | Never unwind across FFI. Use `catch_unwind` at the boundary, or `extern "C-unwind"` with explicit handling, or `abort`. |

---

## Coding Patterns

### Pattern: the recover is the supervisor's *detector*, not the resilience

```go
crashed := runGuarded(ctx, name, work) // recover detects the failure
if crashed { restartFromCleanState() } // restart provides the resilience
```

### Pattern: design out half-state (authoritative write first)

```go
if err := db.Write(x); err != nil { return err } // source of truth first
cache.Set(x)                                      // derived state second
// A failure between them leaves the cache consistent with the DB.
```

### Pattern: copy-on-write atomic swap (no observable half-state)

```go
next := buildNewSnapshot()  // a panic here leaves current untouched
current.Store(next)         // single atomic publish
```

### Pattern: bound the restarts (no infinite "let it crash")

```go
if restartsInWindow > maxRestarts { return errEscalate } // trip the breaker
```

### Pattern: make the panic strategy and isolation design agree

```toml
# If you rely on catch_unwind for isolation, you MUST keep unwind. Document it.
[profile.release]
panic = "unwind"   # REQUIRED: worker pool isolates panics via catch_unwind
```

### Pattern: last-resort handler reports, then exits — never resumes

```js
process.on("uncaughtException", (e) => { report(e); flush(); process.exit(1); });
```

---

## Clean Code

- **One written panic policy per service**, enforced in lint/review — not a per-call-site decision.
- **The only recover sites are infrastructure boundaries** (middleware, worker loop, spawn wrapper, supervisor detector). Zero `recover()`/`catch(Throwable)` in business logic.
- **Every concurrency spawn goes through a guarded wrapper** (`SafeGo`, `Supervise`, a `catch_unwind` runner, a Worker pool). Ban raw `go fn()` / `new Thread` / detached `tokio::spawn` for panic-prone work.
- **Authoritative writes before derived updates**, so a failure can't leave half-state. Prefer copy-on-write / atomic swap for shared state.
- **A panic mid-mutation under a lock crashes** (re-panic / abort). Recover-and-continue is reserved for *provably isolated* state.
- **Runtime strategy is explicit and documented**: `GOTRACEBACK=crash` in prod; Rust `panic =` profile matched to the isolation design; libraries correct under both.
- **Last-resort handlers report and exit**; they never resume an undefined-state process.
- **A correctness alert, not just a liveness probe** — a "healthy" server can serve corrupt data.

---

## Best Practices

1. **Decide crash-vs-recover from restart cost × state recoverability, and write it down.** When in doubt, crash.
2. **Default to crash-only for stateless/checkpointed services**; reserve in-process recovery for expensive-to-restart, isolated state.
3. **Match the panic strategy to the isolation design.** `catch_unwind` ↔ `panic = "unwind"`; FFI/leaf ↔ `panic = "abort"`. Never let them disagree silently.
4. **Use supervision (restart-from-clean) over recover-and-continue for anything stateful** — and always bound the restarts with a budget.
5. **Treat Go goroutines as process-level liabilities.** Every spawn guarded; lint bans raw `go fn()`.
6. **Never recover *into* corruption.** A panic mid-mutation under a lock → crash. Design half-state out via atomic swap / authoritative-first ordering.
7. **Wire the right last-resort handler per runtime**, and make it report-then-exit, never resume (especially Node).
8. **Design the death**: `GOTRACEBACK=crash`, core dumps, flush the crash reporter, dump threads/goroutines, then exit — turn every crash into a post-mortem artifact.
9. **Alert on correctness, not just liveness** — and on `CrashLoopBackOff` / restart-budget-exceeded.
10. **Classify upstream**: recoverable failures are errors; broken invariants are panics. Misclassification is the root of most "recover hid the bug" incidents.

---

## Edge Cases & Pitfalls

- **Go fatal errors are not recoverable.** Concurrent map write, stack overflow, OOM print `fatal error:` and ignore `recover()`. You cannot contain these — only prevent them.
- **`panic = "abort"` makes `catch_unwind` a no-op.** A worker pool that relies on it will kill the whole process on the first panic. Verify the profile.
- **Rust drops a detached task's panic silently.** A `tokio::spawn` whose `JoinHandle` you drop swallows the panic. Keep the handle or use `JoinSet`.
- **Java `submit()` swallows exceptions into the `Future`.** Never-called `get()` = invisible failure. Use `afterExecute` or `execute()`.
- **`ProcessPoolExecutor` segfault breaks the pool.** A native crash (not a Python exception) yields `BrokenProcessPool`; the pool is unusable until recreated.
- **Resuming after Node `uncaughtException`** runs on undefined state. The "robust" handler that logs-and-continues is a latent corruption bug.
- **Unwinding across FFI is UB** (historically). Use `catch_unwind` at the boundary or `extern "C-unwind"`; never let a panic cross a plain `extern "C"`.
- **Lock poisoning ignored.** `poisoned.into_inner()` on autopilot reintroduces the corruption bug poisoning exists to flag.
- **`CrashLoopBackOff`** is crash-only failing: a *deterministic* crash restarts forever. Bound restarts; handle poison inputs out-of-band.
- **Re-panic loses the original stack.** `panic(rec)` keeps the value, resets the stack to the re-panic site. Log the original stack first.

---

## Common Mistakes

1. **Recovering into corruption** — catching a panic that happened mid-mutation and continuing on a poisoned shared structure (the payments-cache class of bug).
2. **Treating a recover boundary as the resilience strategy for stateful work** instead of restart-from-clean-state via supervision.
3. **Raw `go fn()` for panic-prone work** — one bad input, whole process down, despite a perfect request boundary.
4. **Setting `panic = "abort"` while depending on `catch_unwind`** — silent in dev, process death in prod.
5. **Unbounded "let it crash"** — no restart budget → `CrashLoopBackOff` storm that can take down dependencies.
6. **`submit()` without `get()`** in Java/Python — failures vanish into Futures.
7. **Resuming the event loop after Node `uncaughtException`** instead of exiting.
8. **Unwinding a panic across an FFI boundary** — undefined behavior, intermittent corruption.
9. **Promoting a recoverable error to a panic** (e.g. `panic(dbErr)`) — then catching and hiding it at the boundary.
10. **Only a liveness probe, no correctness alert** — a healthy process serving wrong data goes unnoticed.

---

## Tricky Points

- **A boundary recover is correct for *availability* and dangerous for *correctness* simultaneously** — the payments case kept the server up *and* corrupted the cache. Both are true; you must reason about each separately.
- **"Let it crash" is more reliable than defensive code precisely because the restart path is exercised constantly** — the opposite of intuition that says "more error handling = more robust."
- **Rust unwind across FFI is now sometimes defined** (`extern "C-unwind"`, Rust 1.71+) but the *default* `extern "C"` aborts on unwind to stay safe — know which ABI you wrote.
- **Go's `recover` works for `panic` but never for `fatal error`** — there are two failure tiers and only one is catchable, and you don't choose which is which.
- **A Tokio task panic doesn't crash the runtime, but a panic in a *blocking* closure on `spawn_blocking` is also captured** — Rust's async runtime is consistently safer than Go here.
- **`panic = "abort"` is often *faster* and *smaller*, not just "safer"** — no unwind tables, no landing pads. It's a legitimate performance choice, not only a correctness one.
- **Supervision's `one-for-all` exists because some children share state** — restarting one without the others would leave coupled state inconsistent. The strategy choice encodes your coupling.
- **A re-panic and an abort both kill the process, but a re-panic still unwinds** (runs destructors over possibly-corrupt data) while `abort` doesn't. When the data is corrupt, `abort` is sometimes the *safer* death.

---

## Apply it

1. State the system invariant that **Panic & Recovery** must protect.
2. Mark ownership, state, and failure propagation at each boundary.
3. Compare two designs under load, dependency failure, and future change.
4. Define recovery and compatibility behavior before implementation.
5. Test the riskiest assumption with a focused experiment.

## Verify your work

- The experiment supports the design with evidence, not preference.
- Failure injection shows the blast radius and recovery path.
- Compatibility checks cover old and new callers or data.
- Operational signals reveal invariant violations and recovery progress.

## Review questions

- Which invariant must remain true when Panic & Recovery fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
