# HTTP and APIs — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **HTTP and APIs** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
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

## Apply it

1. Choose one small, known input for **HTTP and APIs**.
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

- What problem does HTTP and APIs solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
