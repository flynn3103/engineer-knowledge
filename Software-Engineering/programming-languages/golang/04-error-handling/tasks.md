# Error Handling — Hands-On Tasks

> **Topic:** [Error Handling](../README.md)

---

## Warm-Up

1. Write a function that reads a file and wraps any error with `fmt.Errorf("readConfig: %w", err)`. Confirm `errors.Is` still detects `os.ErrNotExist` through the wrap.
2. Define a sentinel error `ErrInsufficientFunds` and a `Withdraw` function returning it; write a caller that branches on it with `errors.Is`.
3. Define a custom `ValidationError` struct with `Field` and `Msg`, implement `Error()`, and extract it in a caller with `errors.As`.

## Core

4. Design and implement a small `Kind` enum (`NotFound`, `InvalidInput`, `Unavailable`, `Internal`) plus an `AppError` type wrapping an underlying error. Write a function that maps each `Kind` to an HTTP status code.
5. Build a `withRetry` helper that retries a function up to N times with exponential backoff, but only if the returned error is `errors.Is(err, ErrUnavailable)` — verify (with a test) that a non-retryable error returns immediately without retrying.
6. Use `errors.Join` to combine errors from closing three independent `io.Closer`s in a `defer`, and verify with `errors.Is`/`errors.As` that a specific failure among the three is still detectable in the joined result.

## Advanced

7. Build an HTTP handler that classifies errors into client-fault vs. server-fault, returns a safe, generic message for server-fault errors while logging the full detail (with a request ID from `context.Context`) server-side, and returns the specific validation message for client-fault errors.
8. Write a `safeGo` helper that runs a function in a goroutine, recovering any panic and logging it with a stack trace, and demonstrate (with a test) that a panicking function passed to it does not crash the test process.
9. Simulate the "wrapped with %v instead of %w" bug: write a function that wraps an error with `%v`, show that `errors.Is` fails to detect the sentinel through it, then fix it with `%w` and show the same check now passes.

## Capstone

10. Build a small library-boundary error contract: a package exposing a `Do(ctx context.Context) error` function that can fail in 4 distinct ways (not found, invalid input, timeout, internal), each as a distinguishable error via `errors.Is`/`errors.As`. Write a consumer that handles all 4 cases distinctly, plus a default case for anything unclassified, and a test suite covering every branch.

## If you can do all of these, you have the middle level

You can design a small error taxonomy, wrap and inspect errors reliably through multiple layers, decide correctly what's retryable, and keep panic/recover confined to true programmer-error boundaries.

---

## Related Topics

- [Junior](junior.md) · [Middle](middle.md) · [Senior](senior.md) · [Professional](professional.md) · [Interview](interview.md)
