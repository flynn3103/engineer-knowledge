# Error Handling — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Error Handling** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Design an error taxonomy, not just individual error types

A service benefits from a small, deliberate set of error *categories* — e.g. `NotFound`, `InvalidInput`, `Unauthorized`, `Unavailable` (retryable), `Internal` — each mapped consistently to an HTTP status, a retry policy, and a log level. Individual error values/types then carry which category they belong to, so a single dispatch point (an HTTP middleware, an RPC interceptor) can handle all of them uniformly instead of every handler reinventing the mapping.

```go
type Kind int
const (
    KindNotFound Kind = iota
    KindInvalidInput
    KindUnauthorized
    KindUnavailable
    KindInternal
)

type AppError struct {
    Kind    Kind
    Message string
    Err     error
}
func (e *AppError) Error() string { return e.Message }
func (e *AppError) Unwrap() error { return e.Err }
```

### 2. `errors.Join` combines independent errors (Go 1.20+)

```go
err := errors.Join(closeErr, flushErr)
if err != nil {
    return err
}
```

`errors.Join` is for when *multiple independent* operations can each fail and you need to report all of them (e.g. cleaning up several resources in a `defer`) — `errors.Is`/`errors.As` still work across a joined error, checking each one in turn.

### 3. Retry only what's actually retryable

```go
var ErrUnavailable = errors.New("temporarily unavailable")

func withRetry(fn func() error, attempts int) error {
    var err error
    for i := 0; i < attempts; i++ {
        if err = fn(); err == nil || !errors.Is(err, ErrUnavailable) {
            return err
        }
        time.Sleep(backoff(i))
    }
    return err
}
```

Retrying a `KindInvalidInput` or `KindNotFound` error is pointless — the input won't become valid by trying again. Only errors explicitly marked retryable (typically transient network/availability failures) should trigger a retry loop; blindly retrying everything hides real bugs and can amplify load during an outage.

### 4. `panic`/`recover` is for programmer errors, not expected failures

```go
func mustParse(s string) int {
    n, err := strconv.Atoi(s)
    if err != nil {
        panic(fmt.Sprintf("mustParse: invalid input %q", s))
    }
    return n
}
```

`panic` is reserved for situations that indicate a bug (an invariant violated, a "this should never happen" branch) — not for ordinary, expected failure modes like a missing file or a failed network call, which should always be a returned `error`. `recover` belongs at well-defined boundaries (an HTTP middleware, a goroutine's top-level `defer`), converting an unexpected panic into a 500 response or a logged crash, rather than scattered throughout business logic.

### 5. Boring error flows beat clever ones

An error-handling strategy that's easy to explain in one sentence per function ("if X fails, wrap and return; if Y fails, it's retryable, so bubble up as `KindUnavailable`") is more valuable long-term than one that's technically elegant but requires tracing through several layers of custom logic to understand what happens on failure. Optimize for "a new engineer can predict what this does when it fails by reading it once."

---

## Code Examples

### Example 1 — A single error-to-response mapping point

```go
func writeError(w http.ResponseWriter, err error) {
    var ae *AppError
    if !errors.As(err, &ae) {
        ae = &AppError{Kind: KindInternal, Message: "internal error", Err: err}
    }
    status := map[Kind]int{
        KindNotFound:     404,
        KindInvalidInput: 400,
        KindUnauthorized: 401,
        KindUnavailable:  503,
        KindInternal:     500,
    }[ae.Kind]
    if ae.Kind == KindInternal {
        log.Printf("internal error: %v", ae.Err) // full detail server-side only
    }
    http.Error(w, ae.Message, status)
}
```

Every handler just returns an `*AppError` (or a plain error, mapped to `Internal`); the HTTP status/logging decision lives in exactly one place.

### Example 2 — `errors.Join` for cleanup

```go
func closeAll(closers ...io.Closer) error {
    var errs []error
    for _, c := range closers {
        if err := c.Close(); err != nil {
            errs = append(errs, err)
        }
    }
    return errors.Join(errs...)
}
```

### Example 3 — Recover at a goroutine boundary

```go
func safeGo(fn func()) {
    go func() {
        defer func() {
            if r := recover(); r != nil {
                log.Printf("recovered panic: %v\n%s", r, debug.Stack())
            }
        }()
        fn()
    }()
}
```

---

## Best Practices

1. Define a small, fixed set of error kinds and map them consistently to status codes/log levels in one place.
2. Never retry an error you haven't explicitly classified as transient.
3. Reserve `panic` for programmer errors; `recover` only at clear boundaries, never as routine control flow.
4. Log full error detail once, at the boundary where it's handled — not at every layer it passes through.

---

## Edge Cases & Pitfalls

- **Recovering a panic and continuing as if nothing happened** can leave a goroutine or service in an inconsistent state — recovery should usually still fail the current request/operation, just without crashing the whole process.
- **Blanket retry logic** applied to every error type can turn a brief downstream blip into a self-inflicted thundering herd.
- **`errors.Join`'s `Unwrap() []error`** (plural) means `errors.Is`/`errors.As` check *each* joined error, but a naive `errors.Unwrap(err)` (singular) call on a joined error returns nothing useful — use `errors.Is`/`errors.As`, not manual unwrapping, on joined errors.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Logging the same error at every layer it passes through | Log once, fully, at the boundary |
| Retrying everything "just in case" | Explicitly classify retryable vs. non-retryable |
| Using `panic` for expected failure conditions | Return an `error`; reserve `panic` for invariant violations |

---

## Tricky Points

- An `AppError` embedding another `AppError` via `Err` still needs its own `Unwrap()` method for `errors.Is`/`errors.As` to see through it — implementing `Error()` alone isn't enough for wrapping to work.
- `recover()` only works when called directly inside a deferred function — calling it indirectly (through another function call) returns `nil` even during an active panic.

---

## Apply it

1. Find a real component where **Error Handling** affects an interface or dependency.
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

- Which boundary is most affected by Error Handling?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
