# Production Debugging — Junior Level

> **Topic:** [Production Debugging](../README.md)
> **Focus:** `net/http/pprof`, basic CPU/memory profiling, reading logs effectively, and the first mental model for approaching a live, misbehaving service instead of guessing.

---

## Introduction

Debugging a program on your laptop with a debugger attached is one skill. Debugging a live service — where you can't pause execution, can't attach `dlv` casually, and every second of downtime matters — is a different one, built on a different toolkit: profiling endpoints, structured logs, and metrics. This page covers the entry point: `net/http/pprof`, reading a CPU/memory profile, and a basic systematic approach.

---

## Prerequisites

- Comfortable with goroutines, the Go runtime basics, and structured error handling.
- Familiarity with running an HTTP server (see [HTTP and APIs](../05-http-and-apis/junior.md)).

---

## Glossary

| Term | Definition |
|------|-----------|
| **`pprof`** | Go's built-in profiling format and tooling for CPU, memory, goroutine, and block profiles. |
| **`net/http/pprof`** | A package that, when imported, exposes live profiling endpoints on an HTTP server. |
| **CPU profile** | A sampled record of which functions were executing on-CPU during a time window. |
| **Heap profile** | A snapshot of current memory allocations, by call site. |
| **Goroutine profile** | A snapshot of every currently running goroutine and its stack trace. |
| **Flame graph** | A visualization of a profile where stack depth is height and time/samples is width — wide bars are where time is spent. |
| **Structured logging** | Logging as key-value pairs (JSON) rather than free-text strings, making logs machine-parseable and queryable. |
| **P99 latency** | The 99th percentile response time — 1% of requests are slower than this value. |

---

## Core Concepts

### 1. `net/http/pprof` gives you live profiling for free

```go
import _ "net/http/pprof"

func main() {
    go http.ListenAndServe("localhost:6060", nil) // separate port, internal only
    // ... rest of your server
}
```

The blank import registers profiling handlers (`/debug/pprof/...`) on the default HTTP mux. **Never expose this on a public-facing port** — it reveals internal implementation detail and allows expensive profile captures to be triggered by anyone who can reach it.

### 2. Capturing and reading a CPU profile

```bash
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30
(pprof) top10
(pprof) web    # opens a graph visualization (requires graphviz)
```

`top10` lists the functions consuming the most CPU time during the 30-second sample window — the starting point for "what's actually slow."

### 3. Capturing a heap profile

```bash
go tool pprof http://localhost:6060/debug/pprof/heap
(pprof) top10
```

Shows current memory allocations grouped by the call site that allocated them — the starting point for "what's using all this memory."

### 4. The goroutine profile shows what every goroutine is doing right now

```bash
curl http://localhost:6060/debug/pprof/goroutine?debug=2
```

`debug=2` gives full stack traces for every goroutine, grouped by identical stack — a large group sharing one stack is either a legitimate worker pool or a leak (see [Goroutines and Concurrency](../01-goroutines-and-concurrency/senior.md)).

### 5. Structured logs are queryable; free-text logs are not

```go
// Hard to query at scale
log.Printf("user %s failed login after %d attempts", userID, attempts)

// Queryable: "find all failed_login events where attempts > 3"
logger.Info("failed_login", "user_id", userID, "attempts", attempts)
```

Go's standard `log/slog` package (1.21+) provides structured logging out of the box.

### 6. A basic systematic approach beats guessing

1. What's the symptom, precisely? (Latency? Errors? Memory growth? Which endpoint?)
2. When did it start? (Correlate with a deploy, a traffic pattern, an external event.)
3. Pull the relevant profile/log/metric for that window.
4. Form one hypothesis, check it against the data, before changing any code.

---

## Code Examples

### Example 1 — Exposing pprof on an internal-only port

```go
func main() {
    go func() {
        log.Println(http.ListenAndServe("127.0.0.1:6060", nil))
    }()
    startMainServer() // public-facing, separate port
}
```

### Example 2 — Structured logging with `slog`

```go
logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
logger.Info("request_handled", "method", r.Method, "path", r.URL.Path, "duration_ms", elapsed.Milliseconds())
```

### Example 3 — Saving a profile to a file for later analysis

```bash
curl -o cpu.pprof "http://localhost:6060/debug/pprof/profile?seconds=30"
go tool pprof cpu.pprof
```

---

## Pros & Cons

| | Pros | Cons |
|---|---|---|
| **`net/http/pprof`** | Zero external dependencies, built into the standard library | Must be secured (internal-only port), never exposed publicly |
| **Structured logging (`slog`)** | Queryable, machine-parseable, standard library | Slightly more verbose than a free-text `Printf` |
| **Goroutine profile** | Instantly shows every goroutine's exact state | Can be a very large dump on a service with many goroutines — needs grouping by stack to be useful |

---

## Use Cases

| Symptom | First tool |
|---|---|
| High CPU usage, unclear why | CPU profile (`/debug/pprof/profile`) |
| Memory growing over time | Heap profile (`/debug/pprof/heap`), sampled at intervals |
| Goroutine count climbing | Goroutine profile (`/debug/pprof/goroutine?debug=2`) |
| "Something failed for this user" | Structured logs, filtered by request/user/trace ID |

---

## Best Practices

1. Import `net/http/pprof` in every service, exposed only on an internal/localhost-only port.
2. Adopt structured logging (`log/slog` or equivalent) from day one — retrofitting is much more expensive.
3. Always include a request/trace ID in logs so a single request's full path is traceable.
4. Form one specific hypothesis before changing code — "let's try restarting it" is not debugging.

---

## Edge Cases & Pitfalls

- **Exposing `/debug/pprof` on a public port** is an information-disclosure and DoS risk — profile captures cost CPU/memory to generate.
- **A CPU profile captured during an idle period** tells you nothing about a problem that only manifests under load — capture during the actual symptom window.
- **Free-text logs with inconsistent formats** across a codebase make even basic log searches unreliable.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Exposing pprof publicly | Bind it to `127.0.0.1` or an internal-only network interface |
| Debugging by guessing and restarting | Pull a profile/log for the actual symptom window first |
| Free-text logging with no request ID | Adopt structured logging with a consistent request/trace ID field |

---

## Cheat Sheet

```bash
import _ "net/http/pprof"           # register profiling endpoints
go tool pprof <url>/debug/pprof/profile?seconds=30   # CPU
go tool pprof <url>/debug/pprof/heap                 # memory
curl <url>/debug/pprof/goroutine?debug=2             # all goroutines
(pprof) top10 / web                 # inside the pprof interactive shell
```

---

## Summary

- `net/http/pprof` gives free, built-in CPU/heap/goroutine profiling — expose it only internally.
- CPU profiles show where time goes; heap profiles show where memory goes; goroutine profiles show what every goroutine is doing right now.
- Structured logging (`log/slog`) with a consistent request/trace ID makes logs actually queryable during an incident.
- Systematic debugging (symptom → timing → data → hypothesis) beats guessing, even under time pressure.

---

## Further Reading

- The Go Blog — *Profiling Go Programs*: <https://go.dev/blog/pprof>
- `net/http/pprof` docs: <https://pkg.go.dev/net/http/pprof>
- `log/slog` docs: <https://pkg.go.dev/log/slog>

---

## Related Topics

- [Goroutines and Concurrency](../01-goroutines-and-concurrency/junior.md) — what the goroutine profile is showing you.
- [Go Runtime](../02-go-runtime/junior.md) — what a CPU/heap profile is measuring under the hood.
