# Error Handling — Interview Prep

> **Topic:** [Error Handling](../README.md)

---

## Conceptual / Foundational

**Q: What is `error` in Go?**
A: A built-in interface with one method, `Error() string`. Any type implementing it is a valid error value.

**Q: Difference between `errors.New` and `fmt.Errorf`?**
A: `errors.New` creates a plain error from a string. `fmt.Errorf` formats like `Sprintf` and, with `%w`, wraps another error so it remains inspectable via `errors.Is`/`errors.As`.

**Q: What's a sentinel error?**
A: A specific, usually exported, `error` value (like `io.EOF` or `sql.ErrNoRows`) that callers check for with `errors.Is`, rather than comparing message strings.

**Q: When should you use `panic`?**
A: Only for programmer errors / invariant violations that indicate a bug — never for expected, recoverable failure conditions like a missing file or a failed network call, which should be returned as an `error`.

## Tricky / Trap Questions

**Q: Why does `err == sql.ErrNoRows` sometimes return `false` even though the underlying cause is `ErrNoRows`?**
A: Because `err` was wrapped (`fmt.Errorf("...: %w", sql.ErrNoRows)`), making it a different value from `==`'s perspective. `errors.Is(err, sql.ErrNoRows)` unwraps the chain and correctly returns `true`.

**Q: What happens if you wrap with `%v` instead of `%w`?**
A: The resulting error's message looks identical, but the original error is no longer reachable via `errors.Unwrap`/`errors.Is`/`errors.As` — silently breaking downstream error inspection.

**Q: Can `recover()` catch a panic in a different goroutine?**
A: No — `recover` only catches a panic within its own goroutine's call stack. A panic in a goroutine with no `recover` inside it terminates the whole process, regardless of `recover` calls elsewhere.

**Q: What does `errors.Join` do differently from just returning the first error?**
A: It combines multiple independent errors into one, and `errors.Is`/`errors.As` will match against *any* of the joined errors, not just the first.

## System / Design Scenarios

**Q: Design an error-handling strategy for an HTTP API with a database backend.**
A: Define a small `Kind` enum (NotFound, InvalidInput, Unauthorized, Unavailable, Internal), wrap all errors with context using `%w`, map `Kind` to HTTP status codes at a single response-writing layer, log full detail with a request ID server-side, and never leak raw database errors to clients.

**Q: How do you decide whether an error should trigger a retry?**
A: Only retry errors explicitly classified as transient/retryable (e.g. `Unavailable`, timeouts) — never retry `InvalidInput` or `NotFound`, since retrying won't change the outcome and can amplify load during a real outage.

## Behavioral / Experience

**Q: Describe an incident caused by poor error handling, and what changed afterward.**
A: (Tailor to experience — strong answers describe a structural fix: a shared error taxonomy, a linter added to CI, or a classification bug (retrying non-retryable errors) fixed at the root, not just patched.)

---

## Cheat Sheet

```
error            → interface{ Error() string }
errors.New/Errorf → create; %w wraps, %v/%s does not
errors.Is        → sentinel match, through wrapping
errors.As        → type extraction, through wrapping
errors.Join      → combine independent errors (1.20+)
panic/recover    → programmer errors + boundary safety net, not routine control flow
```

---

## Related Topics

- [Junior](junior.md) · [Middle](middle.md) · [Senior](senior.md) · [Professional](professional.md) · [Tasks](tasks.md)
