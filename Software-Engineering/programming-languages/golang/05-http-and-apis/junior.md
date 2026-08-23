# HTTP and APIs — Junior Level

> **Topic:** [HTTP and APIs](../README.md)
> **Focus:** `net/http` handlers, `http.ServeMux`, request/response basics, setting timeouts, and the difference between a demo server and one that survives a slow client.

---

## Introduction

Go's standard library ships a complete, production-capable HTTP stack in `net/http` — no framework required to get started. A handler is just a function (or anything implementing `http.Handler`):

```go
func hello(w http.ResponseWriter, r *http.Request) {
    fmt.Fprintln(w, "Hello, world")
}

func main() {
    http.HandleFunc("/hello", hello)
    http.ListenAndServe(":8080", nil)
}
```

That's a working server in six lines — and also a server with no timeouts, no graceful shutdown, and no protection against a slow or malicious client holding a connection open forever. This page covers the basics; the gap between "it works in a demo" and "it survives production" is most of what the rest of this topic is about.

---

## Prerequisites

- Comfortable with functions, structs, and basic error handling.
- No prior web framework experience required.

---

## Glossary

| Term | Definition |
|------|-----------|
| **`http.Handler`** | Interface: `ServeHTTP(w http.ResponseWriter, r *http.Request)`. Anything satisfying it can handle requests. |
| **`http.HandlerFunc`** | An adapter letting an ordinary function serve as an `http.Handler`. |
| **`http.ServeMux`** | The standard library's request router/multiplexer, matching URL paths to handlers. |
| **Middleware** | A function wrapping a handler to add behavior (logging, auth, timeouts) before/after it runs. |
| **`http.Client`** | The standard library's HTTP client, used for outgoing requests. |
| **Timeout** | A deadline after which an operation (read, write, or the whole request) is aborted. |
| **Graceful shutdown** | Stopping a server such that in-flight requests finish before the process exits, instead of being cut off. |
| **`context.Context`** | Carries per-request cancellation/deadline; `r.Context()` gives you the request's context. |

---

## Core Concepts

### 1. A handler is just a function with a specific signature

```go
func(w http.ResponseWriter, r *http.Request)
```

`w` is how you write the response; `r` carries the request's method, URL, headers, and body.

### 2. `ServeMux` routes by path

```go
mux := http.NewServeMux()
mux.HandleFunc("/users", listUsers)
mux.HandleFunc("/users/", getUser) // trailing slash matches a subtree in older Go
```

Go 1.22+ added method- and pattern-based routing directly to `ServeMux` (`mux.HandleFunc("GET /users/{id}", handler)`), removing the need for a third-party router for many common cases.

### 3. Middleware wraps handlers

```go
func withLogging(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()
        next.ServeHTTP(w, r)
        log.Printf("%s %s %v", r.Method, r.URL.Path, time.Since(start))
    })
}
```

Wrap once, apply everywhere: `mux` becomes `withLogging(mux)`.

### 4. Never use `http.ListenAndServe` bare in production

```go
srv := &http.Server{
    Addr:         ":8080",
    Handler:      mux,
    ReadTimeout:  5 * time.Second,
    WriteTimeout: 10 * time.Second,
    IdleTimeout:  120 * time.Second,
}
srv.ListenAndServe()
```

Without explicit timeouts, a client that opens a connection and sends data slowly (or never finishes) can hold a goroutine and its resources indefinitely — a classic "Slowloris"-style resource-exhaustion risk. `http.Server`'s zero-value timeouts are unlimited.

### 5. The request carries a `context.Context` you should respect

```go
func handler(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()
    result, err := doWork(ctx) // pass it down
    ...
}
```

If the client disconnects or the server shuts down, `r.Context()` is canceled — any downstream call that respects it (a database query, an outbound HTTP call) can stop early instead of doing wasted work.

### 6. Always close response bodies on the client side

```go
resp, err := http.Get(url)
if err != nil { return err }
defer resp.Body.Close()
```

Forgetting `resp.Body.Close()` leaks the underlying connection, eventually exhausting the client's connection pool.

---

## Code Examples

### Example 1 — A server with sane defaults

```go
mux := http.NewServeMux()
mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
})

srv := &http.Server{
    Addr:              ":8080",
    Handler:           mux,
    ReadHeaderTimeout: 5 * time.Second,
    ReadTimeout:       10 * time.Second,
    WriteTimeout:      10 * time.Second,
    IdleTimeout:       120 * time.Second,
}
log.Fatal(srv.ListenAndServe())
```

### Example 2 — JSON request/response

```go
type CreateUserReq struct{ Name string `json:"name"` }

func createUser(w http.ResponseWriter, r *http.Request) {
    var req CreateUserReq
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        http.Error(w, "invalid body", http.StatusBadRequest)
        return
    }
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(map[string]string{"name": req.Name})
}
```

### Example 3 — A client with a timeout

```go
client := &http.Client{Timeout: 5 * time.Second}
resp, err := client.Get("https://example.com")
if err != nil { return err }
defer resp.Body.Close()
```

The zero-value `http.Client{}` (or the package-level `http.Get`) has **no timeout** — always set one explicitly.

---

## Pros & Cons

| | Pros | Cons |
|---|---|---|
| **`net/http` standard library** | No dependency, well-documented, battle-tested | More boilerplate for complex routing than a full framework |
| **`ServeMux` (1.22+ patterns)** | Method + path patterns built in, no third-party router needed for basic cases | Still lacks some framework conveniences (built-in validation, OpenAPI generation) |
| **Middleware via wrapping** | Simple, composable, no magic | Ordering matters and can be easy to get wrong; no built-in dependency injection |

---

## Use Cases

| Situation | Approach |
|---|---|
| A small internal API, few routes | Plain `net/http` + `ServeMux`, no framework needed |
| Need path parameters, method routing | Go 1.22+ `ServeMux` patterns, or a router library for older Go |
| Calling another service | `http.Client` with an explicit `Timeout` |
| Every request needs logging/auth | Middleware wrapping the handler/mux |

---

## Best Practices

1. Always set `ReadTimeout`, `WriteTimeout` (or `ReadHeaderTimeout` at minimum), and `IdleTimeout` on `http.Server`.
2. Always set `Timeout` on `http.Client`; never use the zero-value client for real traffic.
3. Always `defer resp.Body.Close()` after checking the error from an HTTP client call.
4. Pass `r.Context()` down to anything the handler calls that might block.
5. Return meaningful status codes (`400` for bad input, `404` for not found, `500` for server errors) — don't return `200` with an error message in the body.

---

## Edge Cases & Pitfalls

- **Forgetting `resp.Body.Close()`** leaks connections even if you never read the body.
- **A handler that panics with no recovery middleware** crashes the entire server process by default (unless behind `http.Server`'s own per-connection recovery, which only prevents that one connection from taking down others, but still returns a broken connection to that client).
- **Reading `r.Body` without a size limit** lets a malicious client send an unbounded body — use `http.MaxBytesReader` for anything public-facing.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| `http.ListenAndServe(":8080", nil)` in production | Use an `http.Server` with explicit timeouts |
| Zero-value `http.Client{}` for outbound calls | Set an explicit `Timeout` |
| Ignoring `r.Context()` | Pass it to every downstream call that can block |
| No body size limit on public endpoints | Wrap with `http.MaxBytesReader` |

---

## Cheat Sheet

```go
srv := &http.Server{
    Addr: ":8080", Handler: mux,
    ReadHeaderTimeout: 5 * time.Second,
    ReadTimeout: 10 * time.Second, WriteTimeout: 10 * time.Second,
    IdleTimeout: 120 * time.Second,
}
client := &http.Client{Timeout: 5 * time.Second}
defer resp.Body.Close()
ctx := r.Context()
```

---

## Summary

- `net/http` gives you a complete HTTP stack with no framework; a handler is just a function with the right signature.
- Always configure explicit timeouts on both `http.Server` and `http.Client` — the zero values are unlimited.
- Always close response bodies on the client side to avoid leaking connections.
- Pass `r.Context()` down so slow or canceled requests can stop downstream work early.

---

## Further Reading

- The Go Blog — *The complete guide to Go net/http timeouts*: <https://blog.cloudflare.com/the-complete-guide-to-golang-net-http-timeouts/>
- `net/http` package docs: <https://pkg.go.dev/net/http>

---

## Related Topics

- [Error Handling](../04-error-handling/junior.md) — mapping errors to HTTP status codes.
- [Goroutines and Concurrency](../01-goroutines-and-concurrency/junior.md) — each request runs in its own goroutine.
