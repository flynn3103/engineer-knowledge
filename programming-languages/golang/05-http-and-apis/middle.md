# HTTP and APIs — Middle

> **Topic:** [HTTP and APIs](../README.md)
> **Focus:** Graceful shutdown, connection pooling and reuse on the client side, retries with backoff, middleware chains done right, and structuring an API's error responses consistently.

---

## Introduction

A junior-level server survives a demo. A middle-level server survives a deploy — it drains in-flight requests instead of dropping them, reuses connections to downstream services efficiently instead of exhausting sockets under load, and retries transient failures without amplifying an outage.

---

## Prerequisites

- Comfortable with `http.Server`/`http.Client` timeouts and basic middleware (junior level).

---

## Core Concepts

### 1. Graceful shutdown drains, it doesn't just stop

```go
srv := &http.Server{Addr: ":8080", Handler: mux}
go srv.ListenAndServe()

sig := make(chan os.Signal, 1)
signal.Notify(sig, syscall.SIGTERM, syscall.SIGINT)
<-sig

ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
defer cancel()
srv.Shutdown(ctx) // stops accepting new connections, waits for in-flight ones
```

`Shutdown` stops accepting new connections immediately but lets in-flight requests complete (up to the deadline you give it). This is what makes a rolling deploy or a Kubernetes pod termination not drop live user requests.

### 2. The default `http.Transport` pools connections — don't defeat it

```go
client := &http.Client{
    Timeout: 5 * time.Second,
    Transport: &http.Transport{
        MaxIdleConns:        100,
        MaxIdleConnsPerHost: 20,
        IdleConnTimeout:     90 * time.Second,
    },
}
```

Reusing an `http.Client` (and its `Transport`) across requests is what enables connection reuse via keep-alive. Creating a new `http.Client` per request defeats pooling entirely, forcing a new TCP (and TLS, if HTTPS) handshake every single call — a significant, often invisible, latency and resource cost under load.

### 3. Retries need backoff and jitter, and a cap

```go
func doWithRetry(ctx context.Context, fn func() error) error {
    backoff := 100 * time.Millisecond
    for i := 0; i < 5; i++ {
        err := fn()
        if err == nil || !isRetryable(err) {
            return err
        }
        jitter := time.Duration(rand.Int63n(int64(backoff)))
        select {
        case <-time.After(backoff + jitter):
        case <-ctx.Done():
            return ctx.Err()
        }
        backoff *= 2
    }
    return errors.New("retries exhausted")
}
```

Fixed-interval retries from many clients synchronize into a "thundering herd" against a recovering downstream service. Exponential backoff with jitter spreads retries out in time.

### 4. Middleware ordering matters

```go
handler := withRecover(withLogging(withAuth(mux)))
```

Read right-to-left for execution order on the way in: `withAuth` runs first (closest to the actual handler in call order but often placed to run early), `withRecover` should wrap everything so a panic in *any* inner layer, including other middleware, is caught. A common bug is placing `withRecover` too far inside the chain, leaving earlier middleware unprotected.

### 5. Structure API error responses consistently

```json
{"error": {"code": "not_found", "message": "user not found", "request_id": "abc-123"}}
```

A consistent envelope (not sometimes-a-string, sometimes-an-object) means every client can parse errors the same way, and adding a `request_id` gives users a token to reference in support tickets that support/on-call can trace directly to server-side logs.

---

## Code Examples

### Example 1 — Panic-recovery middleware placed correctly

```go
func withRecover(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        defer func() {
            if rec := recover(); rec != nil {
                log.Printf("panic: %v\n%s", rec, debug.Stack())
                http.Error(w, "internal error", http.StatusInternalServerError)
            }
        }()
        next.ServeHTTP(w, r)
    })
}
// Must be the OUTERMOST wrapper:
handler := withRecover(withLogging(withAuth(mux)))
```

### Example 2 — Full graceful shutdown with active-connection tracking

```go
srv := &http.Server{Addr: ":8080", Handler: handler}
idleConnsClosed := make(chan struct{})
go func() {
    sig := make(chan os.Signal, 1)
    signal.Notify(sig, syscall.SIGTERM)
    <-sig
    ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
    defer cancel()
    if err := srv.Shutdown(ctx); err != nil {
        log.Printf("shutdown error: %v", err)
    }
    close(idleConnsClosed)
}()
if err := srv.ListenAndServe(); err != http.ErrServerClosed {
    log.Fatal(err)
}
<-idleConnsClosed
```

### Example 3 — Idempotent retry-safe request

```go
req, _ := http.NewRequestWithContext(ctx, http.MethodPut, url, body) // PUT is naturally idempotent
```

Retries are only safe by default for idempotent methods (`GET`, `PUT`, `DELETE`); retrying a `POST` blindly can create duplicate resources unless the endpoint is designed to be idempotent (e.g. via an idempotency key).

---

## Pros & Cons

| Approach | Pros | Cons |
|---|---|---|
| Graceful shutdown | Zero dropped requests during deploys | Adds startup complexity; needs a correctly-tuned drain timeout |
| Reused `http.Client`/`Transport` | Major latency/resource win under load | Requires care with per-request customization (headers, timeouts) since the client is shared |
| Backoff + jitter retries | Avoids thundering herd, more resilient to transient blips | Adds latency to the failure path; needs a cap to avoid unbounded retry storms |

---

## Best Practices

1. Always implement graceful shutdown for any long-running server (`http.Server.Shutdown`).
2. Create one `http.Client` (with a tuned `Transport`) per destination and reuse it — never per-request.
3. Retry only idempotent operations, with exponential backoff and jitter, and a hard cap on attempts.
4. Place panic-recovery middleware as the outermost wrapper in the chain.
5. Standardize the API error response envelope across every endpoint.

---

## Edge Cases & Pitfalls

- **A shared `http.Client` with per-request customization needs** (different timeouts per call) requires `http.NewRequestWithContext` with a per-request context deadline, not a new client.
- **Retrying a non-idempotent `POST`** without an idempotency key can create duplicate side effects.
- **A shutdown timeout shorter than the slowest legitimate request** will forcibly cut off requests anyway — tune it to your actual P99 latency plus margin.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Creating a new `http.Client` per request | Reuse one client (and its `Transport`) per destination |
| Retrying without backoff/jitter | Exponential backoff + jitter, capped attempts |
| `withRecover` placed inside other middleware | Make it the outermost wrapper |
| No graceful shutdown | Handle `SIGTERM`/`SIGINT`, call `srv.Shutdown(ctx)` |

---

## Tricky Points

- `srv.Shutdown` does not forcibly close idle keep-alive connections until they finish or the context deadline passes — a client holding an idle keep-alive connection open can delay shutdown completion up to that deadline.
- Retrying with the *same* deadline-bound `context.Context` across attempts means the total retry budget is capped by the original deadline, not each individual attempt's timeout — worth being explicit about which behavior you want.

---

## Cheat Sheet

```go
srv.Shutdown(ctx)                          // drain in-flight requests
client := &http.Client{Transport: tr}      // reuse across requests
backoff *= 2; jitter := rand...            // exponential + jitter
handler := withRecover(withLogging(mux))   // recover outermost
```

---

## Summary

- Graceful shutdown (`Shutdown(ctx)`) drains in-flight requests instead of dropping them during deploys.
- Reuse `http.Client`/`Transport` per destination to get connection pooling; creating one per request defeats it.
- Retry only idempotent operations, with exponential backoff and jitter, capped at a fixed number of attempts.
- Panic-recovery middleware must be the outermost wrapper to protect the entire chain.
- Standardize the API's error response shape across every endpoint.

---

## Further Reading

- `net/http` — `Server.Shutdown` docs: <https://pkg.go.dev/net/http#Server.Shutdown>
- Google Cloud — *Retry strategy* guidance (language-agnostic, principles transfer): <https://cloud.google.com/storage/docs/retry-strategy>

---

## Related Topics

- [HTTP and APIs — Junior](junior.md)
- [Database and Distributed Systems — Middle](../06-database-and-distributed-systems/middle.md) — idempotency in more depth.

---

## Check your understanding

1. Explain HTTP and APIs — Middle Level in your own words and name the problem it solves.
2. How would you apply the ideas around Introduction, Prerequisites, Core Concepts in a realistic engineering change?
3. What failure mode or misuse should you look for, and what evidence would reveal it?
4. Which local design trade-off would make you choose or reject HTTP and APIs — Middle Level in an existing codebase?
5. What observable result would convince you that the approach improved the system?
