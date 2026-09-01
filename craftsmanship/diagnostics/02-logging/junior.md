# Logging — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Logging** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Logging Roadmap](README.md)
> **Focus:** What is a log line? Why `print` is not enough. Log levels, the standard libraries, where logs go, and the mistakes everyone makes first.

---

## Core Concepts

### 1. A Log Line Is an Event Record

A log line says: *at this time, this thing happened, here is some context.* It is not the same as a print statement, even when it looks similar. A `print` is a side effect; a log line is **data**. It is meant to be searchable, filterable, aggregable, and (most importantly) understandable by someone who is not you.

A useful log line has at minimum: a **timestamp**, a **level**, a **source** (which logger/module emitted it), a **message**, and **values** of the relevant variables. We'll see this concretely in every example below.

### 2. `print` Is Not Logging

A `print` writes a string to stdout. That's it. No timestamp. No level. No source. No off-switch. Once shipped, every `print` in your code will fire every time the function runs, forever, until someone notices and deletes it. There is no way to say *"emit this only in production"* or *"emit this only when DEBUG is on"* without writing your own logging system. The standard-library logger already exists; use it.

`print` is fine for: quick scripts, one-off CLI tools, REPL exploration, debugging a function on your laptop. `print` is **not fine for**: anything that will run as a service, anything multi-user, anything that other people will operate, anything that will produce more than a handful of lines per second.

### 3. Logs vs Metrics vs Traces — One-Line Each

There are three "pillars" of observability. As a junior, you mostly write logs, but it's good to know what the other two are so you don't reach for the wrong tool:

- **Logs** — discrete events, one per "thing that happened." High cardinality, high detail, expensive to store. *"User 42 logged in at 14:32 from IP 1.2.3.4."*
- **Metrics** — numbers aggregated over time. Low cardinality, cheap, perfect for dashboards. *"100 logins per second."*
- **Traces** — the path of one request through many services. Great for *"why was this one request slow?"*. *"Request abc-123 spent 200ms in auth, 800ms in db."*

A junior reaches for logs by default; a senior knows when the right answer is a metric ("count failed logins") or a trace ("show me where this one request slowed down"). The deep treatment lives in `senior.md` and the `observability-stack` skill.

### 4. Why Programs Need Logs At All

There are four reasons a program writes logs, and almost everything you ever log is in service of one of these:

- **Operations** — does the system look healthy *right now*? Are requests succeeding? Is the queue draining?
- **Post-mortem debugging** — something broke last night at 3am. What were we doing right before? What did the upstream system reply?
- **Audit** — *who* did *what* and *when*? Legally required for finance, healthcare, anything with PII. Audit logs are immutable and treated as evidence.
- **Live debugging** — you've got a bug you can't reproduce locally; turn DEBUG on in staging and watch.

Notice all four are answered by the same data type — *records of events* — but with very different consumers and very different retention needs.

### 5. Levels Are Volume Knobs

The whole point of having TRACE / DEBUG / INFO / WARN / ERROR / FATAL is so that you can turn the verbosity up or down **without changing the code**. The code says *"this is at DEBUG level"* once; the operator decides at deploy time whether DEBUG is on. The level is not a feature of the message — it's a feature of *who needs to see it*.

### 6. Operators Are the Audience

A log line written for yourself ("ok done") is useless to anyone else. A log line written for the future operator ("processed 142 orders for tenant=acme in 230ms") gives the person on call something to act on. The number-one mental shift when you start writing real logs is: **stop writing them for yourself, start writing them for the person who will read them at 3am.**

---

## Log Levels — the Six Standard Ones

Almost every logging library — `logging` in Python, `log/slog` in Go, SLF4J in Java, `pino` and `winston` in Node — supports six standard severity levels. Memorize what each is *for*; the names alone don't tell you.

### TRACE

The finest possible level. *"I entered function `foo`, x was 7, I am about to return 8."* Off in production, off in staging, off most of the time even on your laptop. Enabled when you are stepping through a tricky bug and want a play-by-play. Most production codebases barely use TRACE at all.

### DEBUG

Diagnostic information. *"Fetched user record from cache (hit), cache_key=user:42."* Useful for developers chasing a bug, not for operators running the system. **Off by default in production**, on by default in development. You can crank it on in production temporarily to investigate something specific.

### INFO

Milestones. The system is healthy and this is something an operator would want to know happened. *"Server listening on :8080"*, *"Migration v17 applied successfully"*, *"Order 1234 processed for user 42."* **On by default in production**. The bulk of production logs are INFO.

A good test: would a human want to know this happened in production? If yes, INFO. If only a developer chasing a specific bug, DEBUG.

### WARN

Something is wrong but recoverable. *"Retry 1 of 3 after timeout to payment service"*, *"Cache miss exceeded threshold"*, *"Deprecated API endpoint called by client X"*. The system is still doing its job, but a human should probably notice this and consider acting.

WARN is also where "the world isn't shaped like we expected" lives — an unexpected but non-fatal config value, a row in the database with the wrong format. **Always on.**

### ERROR

A failure has happened and was handled, but the operation failed. *"Failed to send notification email to user 42: SMTP timeout"*, *"Could not write to audit log."* The request is over and someone got a bad answer; the system itself is still alive. **Always on, and usually alerted.**

If the request was *retried successfully*, log the original failure as WARN, not ERROR. ERROR is for things a user actually saw fail.

### FATAL

About to crash. *"Cannot connect to required database, shutting down."* The process is going down right after this line. Often FATAL implicitly calls `exit(1)` or terminates the program. Use rarely — most things you think are FATAL turn out to be ERROR plus a retry.

### The "what level should this be?" decision

A quick mental table:

| Situation | Level |
|-----------|-------|
| Function called and returned successfully | nothing, or TRACE |
| Cache hit | DEBUG |
| HTTP request received and answered 200 | INFO (or DEBUG if it's *every* request and noisy) |
| Server started, port bound, ready to serve | INFO |
| Config has a deprecated key | WARN |
| Transient downstream failure, retrying | WARN |
| Operation failed and was reported to user as failure | ERROR |
| Unhandled exception bubbled to top | ERROR (plus stack trace) |
| Cannot bind port, cannot reach essential db at startup | FATAL, then exit |

---

## Code Examples

We'll write the same trivial event — *"a user logged in"* — in all four languages, using each language's standard or near-standard library.

### Python — `logging` module, the standard library way

```python
import logging
import sys

# Configure once at the top of your program.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    stream=sys.stdout,
)

# One logger per module, named after the module.
log = logging.getLogger(__name__)

def login(user_id: int) -> None:
    log.info("user logged in user_id=%d", user_id)
    # Note: passing user_id as an argument, NOT building the string
    # with f"" — lets the logger skip formatting if the level is off.

    try:
        risky_thing()
    except Exception:
        # exc_info=True attaches the stack trace.
        log.error("failed to do risky thing for user_id=%d", user_id, exc_info=True)

def risky_thing() -> None:
    raise RuntimeError("downstream timeout")

if __name__ == "__main__":
    login(42)
```

Three things worth noticing:

1. `logging.getLogger(__name__)` — every module makes its own logger named after itself. This means an operator can later say *"turn DEBUG on for the `auth` module only"* and the logger hierarchy will do the right thing.
2. The format string uses **printf-style positional arguments** (`%d`, `%s`) — passed as additional args, *not* preformatted with f-strings. This lets the logger skip formatting when the level is filtered out.
3. `exc_info=True` attaches the current exception's stack trace.

### Go — `log/slog`, the modern standard library (Go 1.21+)

```go
package main

import (
	"log/slog"
	"os"
)

func main() {
	// Configure a logger that writes plain text to stdout.
	// Swap NewTextHandler for NewJSONHandler to get JSON output.
	logger := slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	}))
	slog.SetDefault(logger)

	login(42)
}

func login(userID int) {
	// Structured logging: message + key/value pairs.
	slog.Info("user logged in", "user_id", userID)

	if err := riskyThing(); err != nil {
		slog.Error("failed to do risky thing",
			"user_id", userID,
			"err", err,
		)
	}
}

func riskyThing() error {
	return &timeoutError{msg: "downstream timeout"}
}

type timeoutError struct{ msg string }

func (e *timeoutError) Error() string { return e.msg }
```

For comparison, the **old** `log` package (still in the standard library) looks like:

```go
import "log"

log.Println("user logged in user_id=42")          // no level
log.Printf("user logged in user_id=%d", 42)       // no level
log.Fatalf("can't bind port: %v", err)            // FATAL: prints + os.Exit(1)
```

Use `log/slog` in new code. The old `log` package has no levels and no structure — fine for tiny utilities, wrong for a service.

### Java — SLF4J + Logback (the de facto standard)

SLF4J is the *interface*. Logback is one implementation (the most common); Log4j2 is another. You code against SLF4J; you swap implementations at deploy time without touching code.

```java
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class AuthService {

    // One logger per class, named after the class. Convention.
    private static final Logger log = LoggerFactory.getLogger(AuthService.class);

    public void login(long userId) {
        // {} is the placeholder; arguments are formatted lazily.
        log.info("user logged in user_id={}", userId);

        try {
            riskyThing();
        } catch (Exception e) {
            // Passing the exception last attaches the stack trace.
            log.error("failed to do risky thing for user_id={}", userId, e);
        }
    }

    private void riskyThing() {
        throw new RuntimeException("downstream timeout");
    }

    public static void main(String[] args) {
        new AuthService().login(42);
    }
}
```

A default `logback.xml` on the classpath would look like:

```xml
<configuration>
  <appender name="STDOUT" class="ch.qos.logback.core.ConsoleAppender">
    <encoder>
      <pattern>%d{yyyy-MM-dd'T'HH:mm:ss'Z'} %-5level %logger{36} - %msg%n</pattern>
    </encoder>
  </appender>

  <root level="INFO">
    <appender-ref ref="STDOUT"/>
  </root>
</configuration>
```

Notice: the code never names a file, never picks a format, never sets a level. All of that is in `logback.xml` — change it at deploy time, redeploy without recompiling.

### Node — `pino`, the minimal high-performance logger

`console.log` is the `print` of Node — fine for scripts, bad for services. The two most common real loggers are `winston` (feature-rich, slower) and `pino` (minimal, very fast, JSON by default).

```javascript
// npm install pino
const pino = require('pino');

const log = pino({
  level: process.env.LOG_LEVEL || 'info',
  // pino emits JSON by default; perfect for log pipelines.
});

function login(userId) {
  log.info({ user_id: userId }, 'user logged in');

  try {
    riskyThing();
  } catch (err) {
    log.error({ user_id: userId, err }, 'failed to do risky thing');
  }
}

function riskyThing() {
  throw new Error('downstream timeout');
}

login(42);
```

The convention in `pino`: the first argument is the **structured payload** (an object of key-value fields), the second is the **message string**. That order is the opposite of most loggers — pick it up early.

Output (pretty-printed via `pino-pretty` in development):

```
[2026-05-29T14:32:01.123Z] INFO: user logged in
    user_id: 42
```

In production the same code emits JSON, one line per event, ready to be shipped to a log aggregator without parsing.

---

## Pros & Cons of Common Approaches

| Approach | Pros | Cons |
|----------|------|------|
| **`print` / `console.log`** | Zero config, works everywhere, easy to read in a terminal. | No level, no timestamp, no structure, no off-switch. Forever-on, forever-noisy. |
| **Standard-library text logger** (`logging`, old Go `log`, `java.util.logging`) | Always available, no dependency. Levels and timestamps for free. | Hard to make structured. Hard to send to multiple destinations. Default formats are often ugly. |
| **Structured logger** (`slog`, `pino`, `structlog`) | JSON output — machine-queryable, drops straight into log pipelines. Levels, fields, child loggers. | Slightly more setup. Harder to read in a terminal without a pretty-printer. |
| **High-perf logger** (`zap`, `zerolog`, Log4j2 async) | Sub-microsecond per log call. Used in hot paths. | More complex API. Often a separate field-building DSL. |
| **Log to file** | Survives crashes; rotation possible; works without a platform. | You now own rotation, retention, shipping. In a containerized world, you're swimming upstream. |
| **Log to stdout** | 12-factor; the platform handles everything (rotation, shipping, retention). | Doesn't survive if no one's collecting. Requires you to trust your orchestrator. |
| **Log to network (syslog/HTTP)** | Logs leave the machine immediately, survive crashes. | Adds a network dependency to your hot path. Buffering and failure modes are tricky. |

There is no universal "best." For a 2026-era cloud service: **stdout + structured logger** is the default. For a desktop app: a rotating file. For a CLI utility: maybe just stderr and call it done.

---

## Coding Patterns

### Pattern 1 — One logger per module

Almost every language has the same idiom: get a logger named after the current module/class/package, and use it.

```python
log = logging.getLogger(__name__)   # Python
```

```go
// Go: usually use the default slog logger, or pass a *slog.Logger via context.
```

```java
private static final Logger log = LoggerFactory.getLogger(AuthService.class); // Java
```

Why: the logger *name* becomes a category. Operators can later filter by name (*"show me only `auth.*` warnings"*) without changing code.

### Pattern 2 — Configure at the edge, not in the middle

Logging is configured **once**, at program startup (or via a config file the framework reads at startup). Library code never configures logging; it just calls it.

```python
# main.py — top of the program
logging.basicConfig(level=logging.INFO, ...)

# everywhere_else.py — never configures, just uses
log = logging.getLogger(__name__)
log.info("...")
```

### Pattern 3 — Pass values as arguments, not as formatted strings

```python
# GOOD
log.info("user logged in user_id=%d", user_id)

# BAD — formats the string even when DEBUG is off
log.debug(f"complex object: {expensive_repr(obj)}")
```

The logger may skip the format step entirely if the level is filtered out. With f-strings or `+` concatenation, you pay the cost no matter what.

### Pattern 4 — Log at the boundary

A request enters your service at an HTTP handler. *That* layer is where you log the high-level "request started" / "request finished" lines. Internal helpers do not log their own progress — they let the boundary describe the whole event.

```go
func handleLogin(w http.ResponseWriter, r *http.Request) {
    slog.Info("login attempt", "ip", r.RemoteAddr)

    user, err := authenticate(r)
    if err != nil {
        slog.Warn("login failed", "ip", r.RemoteAddr, "err", err)
        http.Error(w, "unauthorized", 401)
        return
    }

    slog.Info("login ok", "user_id", user.ID)
}
```

Don't have `authenticate` itself log "starting authenticate" / "ending authenticate". That noise is a junior reflex.

### Pattern 5 — Always attach the exception to ERROR

```java
log.error("failed to charge order id={}", orderId, e);   // 'e' is the exception
```

```python
log.error("failed to charge order id=%d", order_id, exc_info=True)
```

The error message tells *what happened*; the stack trace tells *where*. Both are valuable; ship them together.

---

## Clean Code

A junior who follows these will already write better logs than most production code:

1. **One logger per module, named.** No global "do everything" loggers.
2. **No `print` in committed code.** Use the logger. Always.
3. **No secrets, ever.** Tokens, passwords, API keys, session cookies. Treat them like radioactive material.
4. **No PII unless you've thought about it.** Email addresses, names, real IDs. Often legal questions, not just style.
5. **Past tense for facts, no jokes.** "User logged in", not "User logging in...!", not "lol yes good".
6. **Include the relevant ID(s).** Without a `user_id` or `order_id`, "operation failed" is unsearchable.
7. **Use the right level.** Not everything is INFO; not everything is ERROR. Read section 7 again.
8. **UTC and ISO 8601.** No `Mon May 29 02:32pm PDT`. Ever.

---

## Best Practices

1. **Log at the boundaries of operations** — request received, request answered; job started, job done. Not "I am calling helper X."
2. **Make every log line actionable or searchable.** If you can't grep for it later by some ID, why is it there?
3. **Prefer structured logs from day one.** Even if your output looks like text, format it as `key=value` so future-you can switch on JSON cleanly.
4. **Use the standard library by default.** Reach for `zap` / `pino` / Log4j2 when you've measured a real performance need.
5. **Set log levels via environment variable**, not in code. `LOG_LEVEL=DEBUG ./myapp` is the right shape.
6. **Log to stdout in services**, let the platform handle the rest. (Unless it's a desktop app, then files.)
7. **Test that your logger is wired up.** A common bug: nothing logs because the level was set to WARN in a config you forgot about.
8. **Never log inside a tight loop without throttling.** A million log lines per second will crash the log pipeline before your code does.
9. **Don't log and re-throw.** Either log it *here* and handle it, or pass it up. Doing both gives you the same error five times.
10. **Review your logs before shipping.** Spin up the service locally, do the main flows, and *read what your code wrote.* You'll cringe. Fix it.

---

## Edge Cases & Pitfalls

### Pitfall 1 — Time zones in timestamps

A timestamp like `14:32:01` is *useless* without a time zone. Was that PDT? UTC? Server-local? When servers move between data centers (or when daylight saving changes), local timestamps make a chronological log impossible to reconstruct. **Always log in UTC, in ISO 8601 format.**

### Pitfall 2 — Logging in hot loops

```python
for row in rows:  # rows might be 10 million
    log.debug("processing row %s", row.id)
```

Even at DEBUG level, building the format string and routing through the logger is non-zero work. In a tight inner loop it can dominate. If you must log, log a *summary* once at the end ("processed 10M rows in 4.2s"), not a line per row.

### Pitfall 3 — Logging recursively / from inside a logger handler

Custom log handlers that themselves log can loop forever. Specialized infrastructure pitfall — just be aware.

### Pitfall 4 — Multi-line log records

`log.info("got payload:\n" + huge_json)` — the resulting log record spans 200 lines. Most log aggregators key on *one line per record* by default and will split it into 200 separate "events". Either log a single line (with `\n` escaped) or use a structured field.

### Pitfall 5 — UTF-8 in log output

If your code logs user-supplied strings, those strings might contain control characters, ANSI escapes, or terminal commands. A maliciously named file *can* embed `\x1b[2J` (clear screen) into your `tail -f` view. Sanitize before logging if you have user input.

### Pitfall 6 — Logging in `__del__` / destructors / shutdown hooks

By the time a destructor runs, the logger handler may already be closed. Logs at process shutdown sometimes silently disappear. Important shutdown messages should be flushed explicitly.

### Pitfall 7 — Forgetting to redact

```python
log.info("auth attempt with body %s", request.body)  # might contain password
```

Hardly anyone *intends* to log credentials. They show up because someone logged "the whole request" as a debugging shortcut. Make a habit of logging *specific fields*, not whole objects.

---

## Common Mistakes

1. **`print` in production code.** Universal junior mistake. Use the logger.
2. **Logging passwords or tokens.** "user logged in with password=hunter2" — instant audit failure, possibly a security incident.
3. **`log.Info("ok")`** — meaningless. No timestamp helps you. No id, no context.
4. **`log.Info("entering function foo")` / `log.Info("exiting function foo")`** — noise, almost never useful. Use a profiler for that.
5. **Everything at INFO, or everything at ERROR.** Levels exist for a reason. Use them.
6. **Mixing formats in the same service.** Some lines plain text, some JSON, some pretty-printed. Log aggregators can only parse one consistently.
7. **Logging full stack traces of *expected* errors at ERROR.** A 404 from "user typed wrong URL" is not an ERROR, it's an INFO at most. Stack traces of *expected* failures swamp the real ones.
8. **Logging inside loops without throttling.** A burst of a million identical log lines tells you nothing and may DoS your own log pipeline.
9. **Forgetting time zones.** Local time in logs leads to nightmares the first time you debug across two regions.
10. **Hard-coding the log level.** `level=DEBUG` checked in to source means you can't turn it off without a redeploy.
11. **Catching an exception and only logging the message** (not the stack trace). The most-asked junior question in incident review: *"Where did that come from?"*
12. **Using stderr for "this is important" and stdout for "this is normal"** — fine convention, but only if you actually understand it. Many juniors blur the two.
13. **Building log strings with `+` or f-strings** even when the level is off. The cost is paid no matter what; use parameter substitution.
14. **`log.info("user object: " + str(user))`** — dumps an entire object, possibly including PII or secrets. Log specific fields.
15. **Logging in a library that other apps depend on.** Library logs at INFO are noise in someone else's service. Stay at DEBUG; let the app decide.

---

## Tricky Points

- **`print` and `log.info` look similar but are *worlds apart*** — only one can be turned off, routed, formatted, and parsed.
- **"Structured" doesn't mean "JSON"** — `key=value key2=value2` is also structured. The point is parseability, not the syntax.
- **The logger does the level check, *then* the format** — that's why passing args (not f-strings) matters: skipping the format saves real CPU when the level is off.
- **`log.Fatal` in Go calls `os.Exit(1)` immediately** — deferred functions do *not* run. Don't `log.Fatal` from inside a transaction.
- **In SLF4J, `log.info("hi {}", name)` formats lazily**; `log.info("hi " + name)` formats eagerly. Same line of text, very different cost.
- **`stdout` is line-buffered when attached to a terminal but *block*-buffered when piped to a file** — your logs may appear to "stop" after the last full block, until you flush. This catches a lot of juniors who think their program froze.
- **The logger hierarchy is a tree.** In Python, `auth.handlers.login` is a child of `auth.handlers`, which is a child of `auth`. Setting the level on `auth` affects all three. This is powerful and also surprising the first time.
- **Log timestamps are usually *wall clock*, not monotonic** — meaning NTP adjustments can make later lines have *earlier* timestamps. We'll see in `senior.md` why this matters for tracing.

---

## Apply it

1. Choose one small, known input for **Logging**.
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

- What problem does Logging solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
