# Logging — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Logging** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Logging Roadmap](README.md)
> **Focus:** Structured logging, context propagation, library choice, and the discipline of *what* goes at *which* level.

---

## Core Concepts

### 1. Structured Logging — the Central Middle-Level Idea

A **structured log entry** is not a sentence. It is a record — like a row in a database. The same event "user logged in" is:

```
[INFO] 2025-05-29 14:32:11 user 42 logged in from 10.0.1.5
```

as a freeform line, and

```json
{"ts":"2025-05-29T14:32:11Z","level":"info","event":"login","user_id":42,"ip":"10.0.1.5"}
```

as a structured line. The freeform one is for *you*, sitting in front of a terminal. The structured one is for *the query engine*, sitting in front of millions of lines.

The reason the structured form wins is the moment you need to ask a question like *"how many users from this IP block logged in last hour?"* The freeform line needs a regex. The structured line needs `event="login" AND ip ~ "10.0.1.*"`. The first breaks every time the message wording changes; the second does not.

> Once you accept that logs are events for a machine, the rest of this page falls into place automatically.

### 2. JSON Logs and NDJSON

The dominant serialisation for structured logs is **newline-delimited JSON** (also called JSONL or NDJSON):

```
{"ts":"...","level":"info","event":"login","user_id":42}
{"ts":"...","level":"info","event":"page_view","user_id":42,"path":"/home"}
{"ts":"...","level":"warn","event":"rate_limit_hit","ip":"10.0.1.5"}
```

Why NDJSON specifically?

- One event per line — `tail`, `grep`, log rotation, and log aggregators all work line-by-line.
- Each line is self-contained valid JSON — partial reads don't corrupt the rest.
- It is the input format every aggregator (Loki, Elasticsearch, CloudWatch, Datadog) consumes natively.

Other formats exist (logfmt's `key=value key=value`, Protobuf for ultra-high-volume systems) but JSON dominates because every language and every tool already speaks it.

### 3. Field Naming Conventions

Once you start writing structured logs, naming becomes a real concern. Three conventions matter:

| Choice | Example | Where you see it |
|--------|---------|------------------|
| `snake_case` | `user_id`, `http_status` | Python, Go, most observability tools |
| `camelCase` | `userId`, `httpStatus` | Java, Node ecosystems by default |
| Dotted namespaces | `http.method`, `db.statement` | OpenTelemetry semantic conventions |

The single most important rule: **be consistent across the whole codebase.** If `user_id` and `userId` both appear, half your queries miss half the data.

The **OpenTelemetry semantic conventions** are becoming the de facto schema. They define field names like `http.method`, `http.status_code`, `http.route`, `db.system`, `db.statement`, `messaging.destination`, `exception.type`, `exception.stacktrace`. If you have no internal standard, adopt theirs — every modern tool understands them and you get analytics for free.

### 4. Context Propagation — Bound Fields

The second pivot is **per-request context**. Inside a single HTTP request, you might log from ten different functions across five files. Without context, the operator sees ten disconnected lines. With context, they all share a `request_id` and you can filter to *just* this request.

The mechanism is a **bound logger**: a logger instance that carries fields, attaching them automatically to every line.

```go
log := slog.Default().With("request_id", reqID, "user_id", userID)
log.Info("started")
log.Info("queried db")
log.Info("finished")
```

All three lines now have `request_id` and `user_id` fields. No need to remember to pass them every time. This is the foundation of operator productivity.

### 5. Per-Language Idioms for Context

Every language solves "where do I stash the bound fields?" differently:

- **Go:** Pass the bound logger through `context.Context` (or as an explicit argument). `slog.NewLogger().With("request_id", id)` returns a new logger; store it in context with a typed key, retrieve it in handlers.
- **Python:** Two routes. The `logging` stdlib supports `extra={"request_id": id}` per call (verbose). `structlog.contextvars.bind_contextvars(request_id=id)` binds for the rest of the async task, picked up automatically by every log call. `LoggerAdapter` is the older middle-ground.
- **Java:** `MDC.put("requestId", id)` writes to a per-thread `ThreadLocal` map. SLF4J's pattern layout interpolates `%X{requestId}` from it. You must `MDC.clear()` (or use a filter) when the request ends, otherwise the next request on the same thread inherits the field.

### 6. Why MDC Cleanup Is the #1 Java Logging Bug

The MDC is a `ThreadLocal`. Tomcat reuses threads. If your filter does `MDC.put("requestId", id)` but never clears, the *next* request handled by the same thread sees the old request_id. Your logs lie. Operators chase ghosts.

Always pair `MDC.put` with a `try { ... } finally { MDC.clear(); }`. Better — use Spring's `MDCInsertingServletFilter` or a similar utility that does this for you.

The cross-thread version is worse. If you `ExecutorService.submit(task)`, the MDC of the calling thread does *not* propagate to the worker thread. You need to capture it (`Map<String, String> ctx = MDC.getCopyOfContextMap()`) and restore it inside the task. Frameworks like Project Reactor provide context propagation; Spring Boot's `TaskDecorator` is the standard hook.

### 7. Configuring Loggers in Real Apps

A production logger has at least three configurables:

| Config | Typical mechanism |
|--------|-------------------|
| **Global level** | Env var `LOG_LEVEL=info` (12-Factor) or YAML/JSON file |
| **Per-package level** | `logger.com.example.payments=DEBUG`, `logger.org.hibernate=WARN` |
| **Format / appenders** | Structured JSON in prod, pretty colored text in dev |

The "global level" model is too coarse for production — you want INFO globally but DEBUG only on the misbehaving package without flooding the disk. Every grown-up logging library (Logback, slog with custom handlers, `logging.dictConfig`) supports per-package levels.

### 8. Hot-Reload of Log Level

You should not have to redeploy to change the log level. The pattern is an HTTP endpoint that mutates the running logger's level:

- **Spring Boot:** Actuator's `/actuator/loggers/{logger}` endpoint accepts a `POST` with `{"configuredLevel": "DEBUG"}`.
- **Go:** Expose an HTTP handler that calls `levelVar.Set(slog.LevelDebug)` where `levelVar` is a `slog.LevelVar` you constructed your handler with.
- **Python:** Wire a small admin endpoint that calls `logging.getLogger("foo").setLevel(logging.DEBUG)`.

This is a tiny feature with enormous operational value. Every service you write past a certain scale should have it.

### 9. Log Routing — Multiple Appenders

The same log entry may need to go several places at once:

| Sink | What for |
|------|----------|
| **stdout** | Local dev, container log capture |
| **File (rotated)** | Self-hosted servers, audit retention |
| **Syslog** | OS-integrated log shipping |
| **Sentry / Bugsnag** | ERROR-level only, with stack traces |
| **HTTP collector** | Push to Loki / Elasticsearch / Datadog |

The library lets you wire several "appenders" (Logback) / "handlers" (Python, Go) / "sinks" / "transports" (Pino, Winston) to the same logger. Each can have its own level filter (errors-only to Sentry, everything to stdout).

### 10. Async Appenders and the Blocking Pitfall

If you log to a remote sink synchronously, every log call is now a network round-trip. A 50ms-slow log call called 100 times per request = +5 seconds of request latency. Worse, if the sink goes down, your service goes down.

The fix is **async appenders**: log calls enqueue to an in-memory bounded queue; a background goroutine/thread/task drains the queue to the sink.

Three policies when the queue fills:
- **Block** the producer (safe but cascades the outage into your app).
- **Drop** new entries (visible holes in logs but app stays alive).
- **Buffer to disk** (most robust; needs disk-space management).

Default in Logback's `AsyncAppender` is *drop on full queue*. Default in Pino's transports is *buffer to disk*. You should know which your library does and override it deliberately for production.

### 11. Error Logging Discipline

When you log an error, include all four of these:

1. **The error chain** — not just `err.Error()` or `e.getMessage()` but the full wrapped stack. Go: `slog.Error("failed", "err", err)` and configure the handler to print the chain. Java: `logger.error("failed", e)` — always pass `e` as a separate arg.
2. **The trace_id / request_id** — bound onto the logger, automatic if you set up context propagation.
3. **What you were trying to do** — `"failed to charge customer"` is useful, `"error"` is not.
4. **The identifying inputs** — `customer_id=42 order_id=99`. Not the whole object (PII risk) but the IDs needed to investigate.

The classic anti-pattern is **log-AND-throw**: every layer catches, logs, and rethrows. Now one error appears five times in the logs at five different levels, and the operator can't tell if it's one failure or five. **Log once at the boundary** (the HTTP handler, the message consumer, the top-level job) and let the lower layers `return err` / `throw e` cleanly.

### 12. Performance — The String Formatting Trap

```go
log.Debug("got " + getExpensiveThing())
```

Even when DEBUG is off, `getExpensiveThing()` runs. The argument is evaluated before the function call. The level check happens too late.

Three escape hatches:

- **Format-string APIs:** SLF4J's `log.debug("got {}", value)` — `value` is formatted only if DEBUG is enabled. But `value` itself must already be cheap; if it's a method call, it ran.
- **Supplier-based APIs:** Log4j 2 / SLF4J 2.x's `log.atDebug().log("got {}", () -> expensive())`. The lambda runs only on enabled level.
- **Explicit level check:** `if log.IsDebugEnabled() { ... }` around the expensive call. Verbose but safe.
- **Go `slog.LogAttrs`:** lazy attribute formatting; `slog.Any("k", expensiveValue)` still evaluates `expensiveValue`, but `slog.Attr` itself is cheap and `LogAttrs` does the level check first.

Sampling — emitting only every Nth line — is the next layer of defence. We touch it here; deep dive in `senior.md`.

### 13. What Belongs at Each Level

The discipline:

| Level | What it means | Examples |
|-------|---------------|----------|
| **DEBUG** | Detail useful only when actively diagnosing | Request body summaries, decision branches, cache hit/miss |
| **INFO** | Milestones — "what is happening" | Request started, request finished, job started, job done |
| **WARN** | Unusual but handled — operator may want to know | Retry happened, fallback used, deprecated path hit, slow query |
| **ERROR** | I failed; the caller sees a failure | Outbound call failed after retries, DB write rejected |
| **FATAL** | Process cannot continue; shutting down | Cannot bind port, cannot load config |

The biggest mistakes here:

- Logging *bugs* at ERROR. A bug is not an error — it's a stack trace, and it should go to a crash reporter (Sentry), not just spam the ERROR log.
- Logging *all* exceptions at ERROR even when the calling layer will retry. The retry succeeded; that's a WARN at most.
- INFO inside a tight loop. One INFO per 10,000 iterations is fine; one per iteration drowns the log.

### 14. Per-Request vs Background Logs

Two distinct shapes of log stream coexist in most services:

**Per-request logs** — one "access log" line per HTTP request, with method, path, status, duration, request_id, user_id. This is what nginx, Caddy, and AWS ALB emit by default. Inside your app, an HTTP middleware emits it after the response is sent.

**Background job logs** — a job starts, makes progress, finishes. The shape is "this job ran, it processed N items, took T seconds, and the result was X." A different aggregation entirely.

A mature app emits both as structured events, not freeform messages.

---

## Logging Libraries You Should Know

### Go

| Library | Status | Strengths | Use when |
|---------|--------|-----------|----------|
| `log/slog` | Stdlib since Go 1.21 | Built-in, structured by default, pluggable handlers | New code, default choice |
| `zap` (Uber) | Mature, fast | Lowest allocation, ergonomic field constructors | Hot path, ultra-high throughput |
| `zerolog` | Mature, fast | Zero allocation, chained-builder API | Hot path, JSON-only deployments |
| `logrus` | Legacy | First popular structured logger | Existing codebases only — do not pick for new code |

For new Go services in 2025, `slog` is the answer unless you have a measured reason. It's good enough, it's stdlib, and the rest of the ecosystem is converging on it.

### Java

| Library | Status | Use when |
|---------|--------|----------|
| **SLF4J** | The facade | Always — code to SLF4J, swap backends behind it |
| **Logback** | Default backend in Spring Boot | Default choice; battle-tested |
| **Log4j 2** | Alternative backend | Specific perf workloads; async logger is faster than Logback's |

Always log through SLF4J's `Logger`, never directly to a concrete backend. The CVE-2021-44228 (Log4Shell) lesson is *not* "Log4j 2 is bad" — it's "centralised logging frameworks are critical infrastructure and need security review like any other dependency." If you used SLF4J you could swap backends in 24 hours; if you imported `org.apache.logging.log4j.Logger` directly everywhere, you spent a week.

### Python

| Library | Style | Use when |
|---------|-------|----------|
| `logging` (stdlib) | Classic, hierarchical, handler-based | Anywhere — universal |
| `structlog` | "Bind keys to logger" model | Structured logging is a first-class need |
| `loguru` | Single object, decorators, pretty | Scripts and small apps, beautiful tracebacks |

The `structlog` model — *the logger carries bound fields* — is the same mental model as Go's `slog.With`, Java's MDC, Node's `pino.child`. Learn it once.

### Node

| Library | Style | Use when |
|---------|-------|----------|
| `pino` | Fast, JSON-by-default, transports for sinks | Production services — default choice |
| `winston` | Flexible, slower, more configurable | Legacy or when you need a niche transport |

Pino won because it's *fast enough that you don't think about it* and JSON-by-default matches modern aggregator expectations. The "pretty" output is a separate `pino-pretty` process you pipe into during dev.

---

## Code Examples

### Go: `slog` JSON Handler with Bound `request_id` in HTTP Middleware

```go
package main

import (
	"context"
	"log/slog"
	"net/http"
	"os"
	"time"

	"github.com/google/uuid"
)

type ctxKey string

const loggerKey ctxKey = "logger"

// LoggerFromContext returns the request-bound logger, or the default.
func LoggerFromContext(ctx context.Context) *slog.Logger {
	if l, ok := ctx.Value(loggerKey).(*slog.Logger); ok {
		return l
	}
	return slog.Default()
}

// RequestLogger middleware binds request_id + method + path onto a logger
// and stuffs it into the request context.
func RequestLogger(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		reqID := r.Header.Get("X-Request-Id")
		if reqID == "" {
			reqID = uuid.NewString()
		}
		log := slog.Default().With(
			"request_id", reqID,
			"http.method", r.Method,
			"http.route", r.URL.Path,
		)
		start := time.Now()
		log.Info("request.started")

		ctx := context.WithValue(r.Context(), loggerKey, log)
		next.ServeHTTP(w, r.WithContext(ctx))

		log.Info("request.finished", "duration_ms", time.Since(start).Milliseconds())
	})
}

func handler(w http.ResponseWriter, r *http.Request) {
	log := LoggerFromContext(r.Context())
	log.Info("handling thing", "user_id", 42)
	w.WriteHeader(http.StatusOK)
}

func main() {
	slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	})))
	http.Handle("/", RequestLogger(http.HandlerFunc(handler)))
	http.ListenAndServe(":8080", nil)
}
```

Run this and `curl -H "X-Request-Id: abc" http://localhost:8080/`. Every line emitted during the request carries `request_id=abc`.

### Python: `structlog` with `bind_contextvars` Showing Per-Request Context

```python
import logging
import sys
import uuid
from contextvars import copy_context

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

# Configure structlog to emit JSON and pick up contextvars.
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)

log = structlog.get_logger()

def charge_customer(customer_id: int, amount: int) -> None:
    log.info("charge.attempt", customer_id=customer_id, amount=amount)
    # ...payment provider call...
    log.info("charge.success", customer_id=customer_id)

def handle_request(user_id: int) -> None:
    clear_contextvars()
    bind_contextvars(
        request_id=str(uuid.uuid4()),
        user_id=user_id,
    )
    log.info("request.started")
    charge_customer(customer_id=user_id, amount=1000)
    log.info("request.finished")

if __name__ == "__main__":
    handle_request(user_id=42)
    handle_request(user_id=99)
```

Notice that `charge_customer` does not take `request_id` or `user_id` as arguments — they are picked up from `contextvars` and merged into every log entry automatically. In an `asyncio` web framework you bind once at the start of the request handler and every nested `await` inherits.

### Java: SLF4J with MDC Inside a Spring Filter

```java
package com.example.logging;

import jakarta.servlet.Filter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.UUID;

@Component
public class RequestIdFilter implements Filter {

    private static final Logger log = LoggerFactory.getLogger(RequestIdFilter.class);
    private static final String HEADER = "X-Request-Id";
    private static final String MDC_KEY = "requestId";

    @Override
    public void doFilter(ServletRequest req, ServletResponse res, FilterChain chain)
            throws IOException, ServletException {
        HttpServletRequest http = (HttpServletRequest) req;
        String reqId = http.getHeader(HEADER);
        if (reqId == null || reqId.isBlank()) {
            reqId = UUID.randomUUID().toString();
        }
        MDC.put(MDC_KEY, reqId);
        MDC.put("httpMethod", http.getMethod());
        MDC.put("httpRoute", http.getRequestURI());

        long start = System.currentTimeMillis();
        try {
            log.info("request.started");
            chain.doFilter(req, res);
            log.info("request.finished durationMs={}", System.currentTimeMillis() - start);
        } finally {
            MDC.clear();   // critical — thread will be reused
        }
    }
}
```

With Logback's pattern `%d %-5level [%X{requestId}] %logger - %msg%n`, every line from any class running in this thread is automatically tagged. The `finally { MDC.clear(); }` is the most important line — forget it, and the next request inherits the field.

### Async Log Appender — Producer/Consumer Queue

A minimal async appender for educational purposes. Real ones (Logback's `AsyncAppender`, Pino's `transport`) are more complex but the skeleton is the same.

```go
package asynclog

import (
	"context"
	"log/slog"
	"sync"
	"time"
)

// AsyncHandler wraps any slog.Handler and offloads writes to a goroutine.
type AsyncHandler struct {
	inner    slog.Handler
	queue    chan slog.Record
	wg       sync.WaitGroup
	dropped  int64
	dropLock sync.Mutex
}

func NewAsyncHandler(inner slog.Handler, bufferSize int) *AsyncHandler {
	h := &AsyncHandler{
		inner: inner,
		queue: make(chan slog.Record, bufferSize),
	}
	h.wg.Add(1)
	go h.drain()
	return h
}

func (h *AsyncHandler) Enabled(ctx context.Context, l slog.Level) bool {
	return h.inner.Enabled(ctx, l)
}

func (h *AsyncHandler) Handle(ctx context.Context, r slog.Record) error {
	select {
	case h.queue <- r:
		return nil
	default:
		// Queue full — drop and count. Tradeoff: visible holes but app stays up.
		h.dropLock.Lock()
		h.dropped++
		h.dropLock.Unlock()
		return nil
	}
}

func (h *AsyncHandler) WithAttrs(attrs []slog.Attr) slog.Handler {
	return &AsyncHandler{inner: h.inner.WithAttrs(attrs), queue: h.queue}
}

func (h *AsyncHandler) WithGroup(name string) slog.Handler {
	return &AsyncHandler{inner: h.inner.WithGroup(name), queue: h.queue}
}

func (h *AsyncHandler) drain() {
	defer h.wg.Done()
	ctx := context.Background()
	for r := range h.queue {
		_ = h.inner.Handle(ctx, r)
	}
}

// Close drains the queue and stops the worker. Call before process exit.
func (h *AsyncHandler) Close(timeout time.Duration) {
	close(h.queue)
	done := make(chan struct{})
	go func() { h.wg.Wait(); close(done) }()
	select {
	case <-done:
	case <-time.After(timeout):
	}
}
```

The producer (your `log.Info(...)` call) returns immediately after a channel send. The consumer goroutine drains and writes. The `default` branch on a full channel implements the **drop policy**. Swap to a blocking send for **block policy**. Replace with a disk-backed queue for **buffer policy**.

---

## Pros & Cons of Structured Logging

| Pros | Cons |
|------|------|
| Queryable — you can filter by field instead of grepping | Slightly more verbose to write than `log.info("msg")` |
| Aggregator-friendly — every tool indexes JSON | Harder to eyeball during local dev (mitigated with pretty-printers) |
| Field schema can evolve without breaking old logs | Field names must be governed across teams or chaos follows |
| Trace correlation is trivial once `trace_id` is a field | JSON is bigger on disk than freeform (mitigated by compression) |
| Works hand-in-hand with metrics and traces | Some teams over-bind fields and produce 50-key log entries |

---

## Coding Patterns

### Pattern: Logger-from-context Helper

Every codebase that uses bound loggers needs a one-line helper to fetch the logger from a context object:

```go
func L(ctx context.Context) *slog.Logger {
    if l, ok := ctx.Value(loggerKey).(*slog.Logger); ok { return l }
    return slog.Default()
}
// usage:
L(ctx).Info("did the thing", "n", count)
```

The single-letter name (`L`, `logger`) is intentional — you'll type it everywhere.

### Pattern: Structured Field Builder for Errors

A helper that always logs an error with the standard fields:

```python
def log_error(log, action: str, err: Exception, **fields):
    log.error(
        f"{action}.failed",
        error_type=type(err).__name__,
        error_message=str(err),
        **fields,
    )

log_error(log, "charge", err, customer_id=42, amount=1000)
```

Removes the "did you remember to include the customer_id?" question entirely.

### Pattern: HTTP Access-Log Middleware

One INFO per request, after the response is sent, with method/path/status/duration. Every framework should have this; if not, write it once and reuse.

### Pattern: Per-package Level Override at Startup

```go
levelVar := new(slog.LevelVar)
levelVar.Set(slog.LevelInfo)
// Endpoint to mutate at runtime:
http.HandleFunc("/admin/loglevel", func(w http.ResponseWriter, r *http.Request) {
    switch r.URL.Query().Get("level") {
    case "debug": levelVar.Set(slog.LevelDebug)
    case "info":  levelVar.Set(slog.LevelInfo)
    case "warn":  levelVar.Set(slog.LevelWarn)
    }
})
```

### Pattern: Lazy Logging with Suppliers

```java
log.atDebug()
   .addArgument(() -> serializeExpensiveDiagnostic(order))
   .log("order state: {}");
```

`serializeExpensiveDiagnostic` runs only if DEBUG is enabled.

---

## Clean Code

- One logger **per class / per package**, not per call. Created once, reused.
- Log **events**, not sentences. `event="login.success"` not `"User successfully logged in"`.
- Field names are **stable contracts** — changing `user_id` to `userId` breaks every dashboard.
- Never log secrets (passwords, tokens, full PANs, session cookies). Mask or omit.
- Never log entire request/response bodies at INFO — summaries only.
- Error logs always include the error chain.

---

## Best Practices

- **Pick one format and one schema, ban the rest.** Half-JSON, half-text codebases are a debugging hellscape.
- **Bind `request_id` (and `trace_id` if you have tracing) at the request boundary.** Once. The rest of the code never needs to think about it.
- **Configure level via env var, with a hot-reload endpoint.** No redeploys to debug.
- **Errors go through one boundary log.** Internal layers `return err` / `throw`. The boundary logs once.
- **Sample noisy DEBUG.** If a tight loop must DEBUG, sample 1-in-N.
- **Async-write to remote sinks** with a sane drop policy and metrics on `logs_dropped_total`.
- **Standardise field names** — adopt OpenTelemetry semantic conventions if you have no internal standard.
- **Log access lines as structured events**, not via `printf` to stdout.
- **Test your log output.** Snapshot tests on the JSON shape catch field-renaming regressions.

---

## Edge Cases & Pitfalls

| Pitfall | What happens | Fix |
|---------|--------------|-----|
| MDC not cleared between requests | Wrong `request_id` on later requests | `try/finally MDC.clear()` or a filter |
| MDC not propagated to worker thread | Background jobs lose context | Capture map, restore inside task |
| Sync log to remote sink | One slow sink = slow service | Async appender with drop policy |
| Logging a huge object | OOM or log truncation | Log IDs only; keep the object out |
| Field collision | Two callers use `user` differently — one a string, one an object | Type-check at handler level; lint field names |
| Logger created per-call | High alloc, GC pressure | One per class/package |
| Unicode in a log message handled by a non-UTF8 backend | Mangled chars in aggregator | Force UTF-8 in handler config |
| Logging INFO in a tight loop | Aggregator costs explode | Move to DEBUG; sample if needed |
| `printStackTrace()` instead of `log.error("...", e)` | Goes to stderr unstructured | Always log exceptions through the logger |
| Forgetting to log when an outbound HTTP call fails | "Why is this slow?" with no clue | Wrap every external call with timing + error log |

---

## Common Mistakes

1. **Mixing JSON and text logs in one codebase.** The aggregator can parse one or the other — not both. Pick one at the architecture-decision level.
2. **MDC bleed between requests in a thread pool.** Always `MDC.clear()` in a `finally`.
3. **Creating a `Logger` inside every function** instead of one per class/package. Wastes allocations and obscures the "who is logging" info.
4. **`printStackTrace()` in Java code.** Goes to stderr without level or context. Use `logger.error("op failed", e)`.
5. **`log.Debug("got " + computeExpensive())`.** Argument always evaluates. Use format-string or lazy-supplier form.
6. **`logger.error()` on every layer of the stack.** Caller logs, callee logs, both log — one error appears five times. Log once at the boundary.
7. **Logging INFO inside a tight loop.** A million-iteration loop emitting INFO = a million log lines = aggregator bill spike.
8. **Forgetting to log outbound HTTP/DB call failures.** Always wrap with start/finish/duration/error.
9. **Logging secrets** — passwords, tokens, raw card numbers. One screenshot in a Slack channel and you have a breach.
10. **Inconsistent field names** (`user_id` here, `userId` there, `uid` over there). Query writers cry.
11. **Using `log.Fatal` (Go) deep inside a handler.** It calls `os.Exit(1)` — your whole server dies because one request had a bad day.
12. **No request_id at all.** Filtering by user_id catches multiple concurrent requests; you can't tell which line belongs to which.

---

## Tricky Points

- **Bound loggers are immutable.** `logger.With(...)` returns a *new* logger. `logger.With("a", 1)` then logging on the original logger does not include `a=1`. Easy to miss.
- **`slog`'s `WithAttrs` is called per-handler-chain, not per-record.** Wrapping handlers (async, filtering, multi-output) must implement `WithAttrs` carefully or bound fields disappear.
- **Python's `logging` is thread-safe but the default handlers acquire a lock.** Heavy log volume across many threads can serialise on that lock — a real concern at 100k events/sec.
- **`logrus.WithField` in Go returns an `*Entry`, not a `*Logger`.** Two parallel APIs; some users confuse them.
- **Pino's `child` logger is cheap** because it pre-serialises bindings — but mutating bound objects after creating the child gives stale values.
- **Logback's `AsyncAppender` drops *INFO and below* when 80% full** by default, keeping WARN+ flowing. Few people know that knob exists.
- **MDC propagation across `CompletableFuture`** requires either a decorator or libraries like `micrometer-context-propagation`. Plain `runAsync(...)` loses it.
- **Structured logs sent to journald** (`systemd-journald`) get re-parsed and indexed — but the journal's own metadata overlays your fields. Watch for collisions on `MESSAGE`, `PRIORITY`.
- **`%s` formatting in Python `logging.info("user %s", id)`** is lazy — only formats if the level is enabled. `f"user {id}"` is not — always evaluates.
- **Zerolog and Zap pre-allocate** field arrays based on level; flipping levels at runtime can shake out hidden alloc bugs.

---

## Apply it

1. Find a real component where **Logging** affects an interface or dependency.
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

- Which boundary is most affected by Logging?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
