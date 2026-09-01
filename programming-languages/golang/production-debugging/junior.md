# Production Debugging — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Production Debugging** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
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

`debug=2` gives full stack traces for every goroutine, grouped by identical stack — a large group sharing one stack is either a legitimate worker pool or a leak (see [Goroutines and Concurrency](../goroutines-and-concurrency/senior.md)).

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

## Apply it

1. Choose one small, known input for **Production Debugging**.
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

- What problem does Production Debugging solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
