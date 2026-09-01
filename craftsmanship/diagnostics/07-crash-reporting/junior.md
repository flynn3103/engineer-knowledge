# Crash Reporting — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Crash Reporting** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Crash Reporting Roadmap](README.md)
> **Focus:** What a crash report is, the anatomy of a captured stack trace, installing your first unhandled-exception handler in each language, and why a minified or stripped trace is useless until it is symbolicated.

---

## Core Concepts

### 1. A Crash Report Is an Obituary, Not a Log

A log line is something *you* decided to write, in advance, because you guessed you might want it. A crash report is something the *runtime* writes, automatically, because something you did *not* anticipate just killed the program. You cannot `console.log` a bug you didn't know existed. That is the whole point of crash reporting: it catches the *unknown unknowns* — the exceptions you never wrote a handler for.

### 2. The Crash You Care About Is on Someone Else's Machine

Internalize this early. You will rarely debug a production crash by reproducing it. The user is gone, the state is gone, the device is in a pocket on another continent. **The report is all you get.** Everything in this roadmap exists to make that one artifact as rich and as reliably delivered as possible — because there is no second chance to collect it.

### 3. Capture Has to Be Automatic and Total

If catching crashes depended on you remembering to wrap every function in `try/catch`, you'd miss the ones that matter — the ones in code you forgot about. The correct design installs **one global handler** at the top of the program that catches *anything* that escapes everything else. One handler, installed once, at startup. That's the spine of capture.

### 4. A Raw Production Trace Is Often Unreadable

Your dev build says `chargeCard (billing.go:88)`. Your *production* build — stripped to ship smaller, minified to load faster, obfuscated to deter reverse-engineering — says `0x000000010a3f` or `t.n.a (bundle.js:1:90412)`. Same crash, useless trace. **Symbolication** is the step that maps it back. Skipping it is the single most common reason teams stare at crash dashboards full of gibberish.

### 5. A Crash Is Worthless Without Its Release

`NullPointerException in CartView` tells you almost nothing. `NullPointerException in CartView, only on v4.2.0, started 2 hours ago` tells you *which deploy broke it* and lets you roll back. Always tag the report with the app version. We'll go deeper in `senior.md`; for now, just know: **untagged crashes are noise.**

### 6. Volume ≠ Severity (Dedup First)

The same crash can fire ten thousand times in a minute. You do *not* want ten thousand dashboard entries — you want **one entry that says it happened ten thousand times.** That collapse is **deduplication / grouping**, and it's what separates a usable crash tool from a firehose. Junior takeaway: a good reporter groups by default; a naive "log it" approach drowns you.

---

## Crash vs Error vs Warning

Not everything is worth a crash report. Confusing these three is how dashboards become unusable.

| Class | What it is | Reach the crash reporter? |
|---|---|---|
| **Warning** | Something suboptimal but handled: a deprecated API, a retried request, a slow query. | No. Goes to logs/metrics. |
| **Handled error** | An error your code *expected and dealt with*: a 404, a validation failure, a network timeout you retried. | Usually no — it's normal operation. Optionally captured as a "handled exception" if it's surprising. |
| **Unhandled exception / crash** | An error that escaped *every* handler and reached the runtime. The program was about to die (or did). | **Yes.** This is the core target of crash reporting. |
| **Panic / fatal** | An unrecoverable runtime fault (segfault, OOM, Go panic, Rust panic). | **Yes**, with highest priority. |

The mental rule: **report what you did not expect.** A timeout you retried is a warning. A timeout that threw an exception nobody caught is a crash. The first belongs in metrics; the second belongs in your face.

> Caveat for `middle.md`/`senior.md`: many SDKs let you *also* capture "handled" exceptions deliberately (`captureException(e)` after a `catch`). That's useful for "this shouldn't happen but I survived it" cases. The discipline is the same: capture the *surprising*, not the *routine*.

---

## Anatomy of a Crash Report

A real crash report is a stack trace surrounded by context. Here's the shape, annotated:

```text
┌─ EXCEPTION ────────────────────────────────────────────────┐
│ TypeError: Cannot read properties of null (reading 'total')│  ← type + message
├─ STACK TRACE ──────────────────────────────────────────────┤
│   at renderCart        (CartView.tsx:212:18)   ← innermost  │  ← where it broke
│   at OrderPage         (OrderPage.tsx:88:7)                 │
│   at mountComponent    (react-dom.js:1840:5)                │  ← library frame
│   at main              (index.tsx:14:1)        ← outermost  │  ← entry point
├─ CONTEXT ──────────────────────────────────────────────────┤
│ release:    v4.2.0 (build 5510, sha a1b2c3d)   ← which deploy│
│ environment: production                                     │
│ os:         iOS 17.4 / device iPhone13,2                    │
│ user:       id=u_8831 (hashed; no email!)      ← no PII     │
├─ BREADCRUMBS (most recent last) ───────────────────────────┤
│ 12:03:41  navigation   /products → /cart                   │  ← what led up to it
│ 12:03:48  http         GET /api/cart  200  120ms           │
│ 12:03:49  ui.click     button#checkout                     │
│ 12:03:49  ← CRASH                                          │
└────────────────────────────────────────────────────────────┘
```

Read it the way you read any trace ([`../01-debugging/junior.md`](../01-debugging/junior.md)): start at the exception, find the innermost *your-code* frame (`renderCart`), and look there first. The context tells you *who* and *where*; the breadcrumbs tell you *what they were doing*. Notice what is **not** there: no email, no password, no card number. That omission is deliberate and covered in `middle.md`.

---

## The First Toolkit

Your day-one crash-reporting toolkit is small:

1. **Install one global handler** per process that catches anything uncaught.
2. **Format the captured exception** into type + message + stack.
3. **Attach the release version** so the crash is tied to a deploy.
4. **Send it somewhere** — at first, just `stderr` or a file; later, a real SDK.
5. **Symbolicate** when the build is stripped/minified (so the trace is readable).
6. **Read the report** like a stack trace: innermost-your-code frame first.

The handler is the spine. Everything else is enrichment. Let's wire the handler in every language.

---

## Code Examples

The same idea — *install a last-resort handler, turn the uncaught failure into a report* — in each language the README names.

### Python — `sys.excepthook`

`sys.excepthook` is Python's global hook for uncaught exceptions. The runtime calls it instead of printing the default traceback.

```python
# crash_reporter.py
import sys
import traceback
import platform

APP_VERSION = "4.2.0"

def report_crash(exc_type, exc_value, exc_tb):
    # In real life this POSTs to Sentry/your backend. Here we format it.
    report = {
        "type": exc_type.__name__,
        "message": str(exc_value),
        "stack": "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
        "release": APP_VERSION,
        "python": platform.python_version(),
        "os": platform.platform(),
    }
    # send(report)  <-- upload to your crash backend
    print("=== CRASH REPORT ===")
    for k in ("type", "message", "release", "os"):
        print(f"{k}: {report[k]}")
    print(report["stack"], file=sys.stderr)

sys.excepthook = report_crash

def charge(order):
    return order["price"] * order["qty"]   # KeyError if "price" missing

if __name__ == "__main__":
    charge({"qty": 2})   # boom: KeyError 'price'
```

> **Threading gotcha:** `sys.excepthook` only fires for the main thread. For threads, set `threading.excepthook` (Python 3.8+). For `asyncio`, set a loop exception handler. A "global" handler is only global if you cover every place exceptions can escape.

### Go — `recover()` then report, plus the panic fallback

Go has no exceptions; it has **panics**. A panic that reaches the top of a goroutine crashes the program. You catch it with `recover()` inside a deferred function — but only in the *same goroutine*.

```go
// crashreport.go
package main

import (
	"fmt"
	"os"
	"runtime/debug"
)

const appVersion = "4.2.0"

func reportPanic(r any) {
	// In real life: send to Sentry via sentry-go's recover integration.
	fmt.Fprintln(os.Stderr, "=== CRASH REPORT ===")
	fmt.Fprintf(os.Stderr, "panic: %v\n", r)
	fmt.Fprintf(os.Stderr, "release: %s\n", appVersion)
	fmt.Fprintf(os.Stderr, "stack:\n%s\n", debug.Stack())
}

// guard wraps a unit of work so a panic becomes a report, not a crash.
func guard(work func()) {
	defer func() {
		if r := recover(); r != nil {
			reportPanic(r)
		}
	}()
	work()
}

func charge(order map[string]int) int {
	return order["price"] * order["qty"]
}

func main() {
	guard(func() {
		// Real panic: nil map write, index OOB, etc. Here, force one:
		var orders []map[string]int
		_ = charge(orders[3]) // index out of range -> panic
	})
	fmt.Println("survived; report was sent")
}
```

> **The goroutine trap (critical):** `recover()` only catches panics in *its own* goroutine. A panic in a bare `go func(){ ... }()` with no deferred recover **crashes the whole process**, full stop. Every goroutine you spawn needs its own guard. This is the #1 Go crash-reporting mistake. See [`../09-panic-and-recovery/`](../09-panic-and-recovery/README.md).

### Java / Kotlin — `Thread.setDefaultUncaughtExceptionHandler`

The JVM gives every thread a last-resort handler. Set the *default* one and you cover threads that don't override it.

```java
// CrashReporter.java
public final class CrashReporter {
    static final String APP_VERSION = "4.2.0";

    public static void install() {
        Thread.setDefaultUncaughtExceptionHandler((thread, throwable) -> {
            // Real impl: hand to Sentry/Crashlytics SDK.
            System.err.println("=== CRASH REPORT ===");
            System.err.println("thread:  " + thread.getName());
            System.err.println("type:    " + throwable.getClass().getName());
            System.err.println("message: " + throwable.getMessage());
            System.err.println("release: " + APP_VERSION);
            // Full stack, including the "Caused by:" chain:
            throwable.printStackTrace(System.err);
        });
    }

    public static void main(String[] args) {
        install();
        int[] xs = new int[3];
        System.out.println(xs[5]); // ArrayIndexOutOfBoundsException -> handler fires
    }
}
```

> On Android, you usually let Crashlytics/Sentry chain its handler in *front* of yours so it can capture, then still call the previous handler. Don't blindly replace an existing handler — *wrap* it. (More in `middle.md`.)

### Node.js — `uncaughtException` and `unhandledRejection`

Node has **two** escape routes you must cover: synchronous throws (`uncaughtException`) and rejected promises nobody `.catch`-ed (`unhandledRejection`). Miss the second and async crashes vanish silently.

```js
// crash-reporter.js
const APP_VERSION = "4.2.0";

function report(kind, err) {
  // Real impl: Sentry.captureException(err)
  console.error("=== CRASH REPORT ===");
  console.error("kind:    ", kind);
  console.error("type:    ", err && err.name);
  console.error("message: ", err && err.message);
  console.error("release: ", APP_VERSION);
  console.error(err && err.stack);
}

process.on("uncaughtException", (err) => {
  report("uncaughtException", err);
  process.exit(1); // a process in an unknown state should not keep serving
});

process.on("unhandledRejection", (reason) => {
  report("unhandledRejection", reason instanceof Error ? reason : new Error(String(reason)));
});

// Sync crash:
JSON.parse("{ not valid json");           // throws -> uncaughtException

// Async crash (no .catch):
Promise.reject(new Error("db connection lost")); // -> unhandledRejection
```

> **Why `process.exit(1)` after an uncaught exception?** After an uncaught throw, Node's state is undefined — half-finished work, leaked handles. The honest move is to report, then exit and let your supervisor (systemd, Kubernetes) restart a clean process. Limping along corrupts data. More on this in `senior.md`.

### Rust — the panic hook

Rust's `std::panic::set_hook` installs a global callback that runs on *every* panic, before the program unwinds or aborts.

```rust
// src/main.rs
use std::panic;

const APP_VERSION: &str = "4.2.0";

fn install_crash_handler() {
    panic::set_hook(Box::new(|info| {
        // Real impl: sentry::integrations::panic forwards this upstream.
        eprintln!("=== CRASH REPORT ===");
        eprintln!("release: {APP_VERSION}");
        // `info` gives the panic message and the location (file:line).
        if let Some(loc) = info.location() {
            eprintln!("location: {}:{}", loc.file(), loc.line());
        }
        eprintln!("payload: {info}");
        // A real backtrace needs RUST_BACKTRACE=1 and the `backtrace` crate.
    }));
}

fn charge(prices: &[u32], idx: usize) -> u32 {
    prices[idx] // panics on out-of-bounds
}

fn main() {
    install_crash_handler();
    let prices = vec![100, 200, 300];
    println!("{}", charge(&prices, 9)); // index out of bounds -> hook fires
}
```

> The hook fires *whether or not* the panic is later caught by `catch_unwind`. To get file/line and a real backtrace symbolicated, you also need debug info in the binary (don't fully strip) and `RUST_BACKTRACE=1`. More in `professional.md`.

---

## Why Symbolication Matters

Here is the entire argument for symbolication in one before/after. A minified JavaScript production crash arrives looking like this:

```text
TypeError: undefined is not an object (evaluating 'n.total')
    at t (https://app.example.com/static/main.4f9c.js:1:90412)
    at o (https://app.example.com/static/main.4f9c.js:1:88210)
    at https://app.example.com/static/main.4f9c.js:1:1204
```

That is *technically* a stack trace. It is also *completely useless* — `t`, `o`, "line 1 column 90412" tell you nothing. The build minified `renderCart` into `t` and collapsed the file to one line.

Now apply the **source map** (`main.4f9c.js.map`, generated at build time):

```text
TypeError: Cannot read properties of undefined (reading 'total')
    at renderCart   (src/components/CartView.tsx:212:18)
    at OrderPage    (src/pages/OrderPage.tsx:88:7)
    at main         (src/index.tsx:14:1)
```

*Now* you can fix it. Same crash, same bytes on the wire — the only difference is whether you uploaded the source map so the server could decode it.

| Platform | What ships to users | The "codebook" you must keep/upload |
|---|---|---|
| **JavaScript (web/Node)** | Minified bundle (`main.4f9c.js`) | **Source map** (`.js.map`) |
| **Android (Java/Kotlin)** | R8/ProGuard-obfuscated APK | **`mapping.txt`** (ProGuard/R8 mapping) |
| **iOS / macOS (Swift/ObjC)** | Stripped binary | **`.dSYM`** files |
| **Windows (C/C++/.NET)** | Stripped `.exe`/`.dll` | **`.pdb`** files |
| **Linux / Go / Rust / C++** | Stripped binary | **DWARF** debug info (kept binary or split debug file) |

The iron rule: **the codebook is generated at build time and is unique to that build.** Lose it, and every crash from that build is permanently unreadable. So uploading symbols is a *build step*, not an afterthought. (Wiring the upload is the job of `middle.md`.)

---

## Pros & Cons of Logging vs Crash Reporting

A junior often asks: *"I already have logs — why do I need a crash reporter?"* Here's the honest comparison.

| Aspect | Logging | Crash Reporting |
|---|---|---|
| **What it captures** | Whatever you wrote in advance | The unexpected — exceptions you never anticipated |
| **Grouping** | None — every line is separate; you `grep` | Automatic — identical crashes collapse into one issue |
| **First occurrence** | Buried among millions of lines | Surfaced and timestamped: "first seen in v4.2.0" |
| **Stack + context** | Only if you logged it | Always: full stack, OS, device, release, breadcrumbs |
| **Symbolication** | You're on your own | Built in, given uploaded symbols |
| **Cost model** | Pay per byte; crashes are a fraction | Pay per event/issue; cheap because of dedup |
| **Best for** | "What did the code *say*?" | "What *broke*, how often, on which release?" |

They are complementary, not rivals. Logs and breadcrumbs *enrich* a crash report; the crash report *frames* the logs. See [`../02-logging/junior.md`](../02-logging/junior.md). The wrong move is "I'll just log exceptions and grep them" — that's a firehose with no grouping, no symbolication, and no first-occurrence signal.

---

## Coding Patterns

### Pattern 1 — Install the Handler First, Before Anything Can Fail

```python
# main.py — the FIRST thing main does
import crash_reporter   # sets sys.excepthook on import
crash_reporter.install()   # before config load, before DB connect — anything can crash
```

If you install the handler *after* your config loader, a crash *in* the config loader escapes uncaught. Initialize crash reporting as the very first line of `main`.

### Pattern 2 — Wrap Every Goroutine / Thread / Async Boundary

```go
func spawn(name string, work func()) {
	go func() {
		defer func() {
			if r := recover(); r != nil {
				reportPanic(r) // never let a goroutine die silently
			}
		}()
		work()
	}()
}
```

A global handler is only global if it covers every escape route. Bare `go func()`, raw threads, and uncaught promise rejections are the leaks.

### Pattern 3 — Always Tag the Release

```js
const event = {
  exception: err,
  release: process.env.APP_VERSION || "unknown", // never "unknown" in prod
  environment: process.env.NODE_ENV,
};
```

An untagged crash is a crash you can't roll back from. Bake the version (or git SHA) into the build and stamp every report.

### Pattern 4 — Capture, Then Re-Raise (for "Handled but Surprising")

```python
try:
    risky()
except UnexpectedError as e:
    crash_reporter.capture(e)  # tell the dashboard
    raise                       # but don't swallow — let it propagate
```

Capturing an exception is *not* the same as handling it. Report it, then decide separately whether to recover or re-raise. Swallowing-to-report is how bugs hide. See [`../03-error-handling/junior.md`](../03-error-handling/junior.md).

---

## Clean Code

- **Install crash reporting at the very top of `main`**, before any other initialization. A crash before the handler is installed is a crash you'll never see.
- **Never `catch (e) {}` to silence a crash.** A bare catch that does nothing is a deleted crash report. If you catch, either handle meaningfully or `capture(e)` and re-raise.
- **Tag every build with a version/SHA at compile time** (linker flag, env var, build constant) — not hand-typed, not "unknown."
- **Keep PII out of reports from day one.** Don't log the email into the breadcrumb "for convenience"; you'll regret it. (Scrubbing detail in `middle.md`.)
- **Treat symbol upload as part of the build, not a manual step.** If a human has to remember to upload the dSYM, some builds won't have one.
- **Don't fork your own crash format when a battle-tested SDK exists.** Sentry/Crashlytics handle offline queueing, retries, and grouping you'll get wrong by hand. The hand-rolled examples above are for *understanding*, not production.

---

## Best Practices

1. **Cover every capture surface.** Main-thread handler *and* thread/goroutine handler *and* async/promise handler. List them per language; verify each fires.
2. **Symbolicate production builds.** Upload source maps / dSYM / mapping.txt / PDB on every release build. Verify by reading a real report's trace — if it's gibberish, the symbols didn't upload.
3. **Tag release + environment** on every report. No exceptions.
4. **Add breadcrumbs for the big events** — navigation, network calls, key user actions. They turn "it crashed" into "it crashed right after checkout." (Detail in `middle.md`.)
5. **Exit after an uncaught exception in a server** rather than limping; let the supervisor restart a clean process.
6. **Scrub PII before sending.** Hash user IDs; never send emails, tokens, card numbers.
7. **Read your dashboard weekly even when nothing's on fire.** A slow-rising new crash is easier to fix at 50 occurrences than at 50,000.
8. **Test the pipeline by triggering a fake crash** in staging and confirming it arrives, symbolicated, tagged. A crash reporter you've never seen fire is a crash reporter that doesn't work.

---

## Edge Cases & Pitfalls

- **The crash that happens before the handler installs** — config load, static initializers, module top-level code. Install as early as physically possible.
- **The handler itself crashes.** If your `reportCrash` does network I/O and *that* throws, you can loop or lose the report. Keep the handler dead simple; queue to disk, upload later.
- **Out-of-memory crashes** can't allocate to build a report. Native reporters pre-allocate buffers for exactly this; pure-language handlers often can't capture an OOM. (Covered in `professional.md`.)
- **A stack overflow** leaves no stack to walk. Some handlers run on an alternate signal stack to survive it.
- **Goroutine/async leaks** (Go, Node): the most common silent crash. A panic in an uncovered goroutine kills the process with *no report* if you only set the main handler.
- **Stripped builds with no uploaded symbols** = permanently unreadable traces. The symbols for that build are gone; you can't regenerate them later.
- **Clock skew on the device** makes the report's timestamp wrong. Prefer the server receive-time for ordering.
- **Crashes in offline mode** (mobile/desktop) need on-device queueing and upload-on-next-launch — or they're lost. (Detail in `senior.md`.)

---

## Common Mistakes

1. **Only setting the main-thread handler.** The crash hides in a goroutine, worker thread, or unhandled promise rejection — and never reaches you.
2. **Shipping stripped/minified builds without uploading symbols.** The dashboard fills with `0x4a3f` and `t.n.a`. Useless.
3. **Forgetting to tag the release.** Every crash looks the same; you can't tell which deploy broke things or whether your fix worked.
4. **Swallowing exceptions to "stop the crash."** `catch (e) {}` doesn't fix the bug — it deletes the evidence and lets corrupt state spread. See [`../03-error-handling/junior.md`](../03-error-handling/junior.md).
5. **Treating crash reports like logs** — no grouping, just dumping every event into a log stream and grepping. You drown.
6. **Putting PII in the report** — email in the user field, full request body in a breadcrumb. Now your crash backend is a compliance liability.
7. **Letting a Node server keep running after `uncaughtException`** in an unknown state, corrupting data, instead of reporting and restarting.
8. **Never verifying the pipeline.** Wiring it up and *assuming* it works. Trigger a test crash and confirm it lands, readable.
9. **Reusing dev symbols for a prod build.** Symbols are per-build; the wrong dSYM symbolicates to the wrong lines, which is worse than no symbols.
10. **Capturing handled errors at full volume.** Reporting every 404 and timeout buries the real crashes. Report the *surprising*, not the routine.

---

## Tricky Points

1. **`recover()` is per-goroutine in Go.** A deferred recover in `main` will *not* catch a panic in a goroutine you spawned. Each goroutine needs its own. This trips up nearly everyone.
2. **Node has two handlers, not one.** `uncaughtException` (sync) and `unhandledRejection` (async). Promise-based crashes only fire the second; cover both.
3. **`sys.excepthook` ignores threads.** Use `threading.excepthook` (3.8+) and an `asyncio` loop handler too. "Global" is a lie unless you cover all three.
4. **Symbols are build-specific and one-way.** You can't symbolicate a v4.2.0 crash with v4.3.0's symbols. Upload per build; keep them.
5. **A panic and an exception are not the same severity.** A Go panic / segfault means the process is dying; a caught exception you chose to report means it survived. The reporter should distinguish them.
6. **Capturing ≠ handling.** `captureException(e)` tells the dashboard; it does *not* recover the program. You still must decide whether to re-raise.
7. **The "Caused by:" chain matters.** Java/Python wrap exceptions; the *root* cause is the deepest link. A report that drops the chain hides the real bug. See [`../01-debugging/junior.md`](../01-debugging/junior.md).
8. **`debug.Stack()` in Go captures the *current* goroutine's stack**, not all of them. For a full picture you need the runtime's crash dump — but for *your* recovered panic, the current stack is what you want.

---

## Apply it

1. Choose one small, known input for **Crash Reporting**.
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

- What problem does Crash Reporting solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
