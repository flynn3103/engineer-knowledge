# Error Handling — Junior

> **Topic:** [Error Handling](../README.md)
> **Focus:** The `error` interface, `errors.New`/`fmt.Errorf`, checking errors immediately, wrapping with `%w`, and why Go's explicit `if err != nil` is a deliberate design choice.

---

## Introduction

Go has no exceptions for ordinary error conditions. Functions that can fail return an `error` as their last return value, and callers are expected to check it immediately:

```go
data, err := os.ReadFile("config.json")
if err != nil {
    return err
}
```

This is verbose compared to try/catch, and that's deliberate: **errors are values**, visible in every function signature, impossible to silently ignore without writing `_ = err`. The goal of this page is fluency with the basic vocabulary — `error`, wrapping, sentinel errors — that everything else in Go error handling builds on.

---

## Prerequisites

- Comfortable with functions returning multiple values.
- Basic familiarity with interfaces (see [Interfaces](../03-interfaces/junior.md)) — `error` is just an interface.

---

## Glossary

| Term | Definition |
|------|-----------|
| **`error`** | A built-in interface: `type error interface { Error() string }`. Any type with an `Error() string` method is an error. |
| **`errors.New(msg)`** | Creates a simple error from a string message. |
| **`fmt.Errorf`** | Like `Sprintf`, but returns an `error`; supports `%w` to wrap another error. |
| **Wrapping** | Embedding one error inside another so the original is still recoverable via `errors.Unwrap`/`errors.Is`/`errors.As`. |
| **Sentinel error** | A specific, exported `error` value (e.g. `io.EOF`, `sql.ErrNoRows`) compared with `==` or `errors.Is`. |
| **`errors.Is`** | Checks whether an error, or any error it wraps, matches a target sentinel error. |
| **`errors.As`** | Checks whether an error, or any error it wraps, can be assigned to a target error *type*, and extracts it. |
| **Custom error type** | A struct implementing `Error() string`, carrying structured data beyond a message string. |

---

## Core Concepts

### 1. `error` is just an interface

```go
type error interface {
    Error() string
}
```

Anything with an `Error() string` method satisfies it. This is why `errors.New("boom")` and a hand-written struct with an `Error()` method are both valid `error` values.

### 2. Check errors where they happen, not later

```go
f, err := os.Open("file.txt")
if err != nil {
    return err // handle immediately, don't keep going with a broken f
}
defer f.Close()
```

Continuing to use a value after ignoring its error (`f, _ := os.Open(...)`) is one of the most common sources of confusing downstream failures.

### 3. Wrap errors to preserve context without losing the original

```go
if err != nil {
    return fmt.Errorf("loading config %q: %w", path, err)
}
```

`%w` (not `%v` or `%s`) wraps the original error so it remains inspectable later via `errors.Is`/`errors.As`, while the message adds context about *where* the failure happened.

### 4. Sentinel errors are compared, not string-matched

```go
var ErrNotFound = errors.New("not found")

func Find(id string) (Item, error) {
    if !exists(id) {
        return Item{}, ErrNotFound
    }
    ...
}

// caller
if errors.Is(err, ErrNotFound) {
    // handle specifically
}
```

Never compare error messages with string equality — messages can change; sentinel identity via `errors.Is` is stable even through wrapping.

### 5. Custom error types carry structured data

```go
type ValidationError struct {
    Field string
    Msg   string
}
func (e *ValidationError) Error() string {
    return fmt.Sprintf("%s: %s", e.Field, e.Msg)
}

// caller
var ve *ValidationError
if errors.As(err, &ve) {
    fmt.Println("bad field:", ve.Field)
}
```

`errors.As` extracts a specific error *type* (even through wrapping), giving access to fields the plain string message can't provide.

---

## Code Examples

### Example 1 — A wrapped error chain

```go
func loadUser(id string) (User, error) {
    row, err := db.QueryRow(id)
    if err != nil {
        return User{}, fmt.Errorf("loadUser(%s): %w", id, err)
    }
    ...
}
```

If `db.QueryRow` returns `sql.ErrNoRows`, the caller can still detect it: `errors.Is(err, sql.ErrNoRows)` returns `true` even though the message now says `"loadUser(42): sql: no rows in result set"`.

### Example 2 — `errors.Is` vs. `==`

```go
_, err := loadUser("42")
if err == sql.ErrNoRows {      // FALSE — err is wrapped, not identical
    ...
}
if errors.Is(err, sql.ErrNoRows) { // TRUE — unwraps the chain
    ...
}
```

### Example 3 — Multiple custom error types

```go
type NotFoundError struct{ ID string }
func (e *NotFoundError) Error() string { return "not found: " + e.ID }

type PermissionError struct{ User string }
func (e *PermissionError) Error() string { return "permission denied for " + e.User }

func handle(err error) {
    var nf *NotFoundError
    var pe *PermissionError
    switch {
    case errors.As(err, &nf):
        respond(404, nf.Error())
    case errors.As(err, &pe):
        respond(403, pe.Error())
    default:
        respond(500, "internal error")
    }
}
```

---

## Pros & Cons

| | Pros | Cons |
|---|---|---|
| **Explicit `if err != nil`** | Impossible to silently skip without a visible `_`; error paths are visible in the code | Verbose; repetitive boilerplate in functions with many fallible calls |
| **Wrapping with `%w`** | Preserves context and the original error simultaneously | Easy to forget and use `%v` instead, silently breaking `errors.Is`/`errors.As` downstream |
| **Sentinel errors** | Simple, fast comparison via `errors.Is` | Doesn't carry structured data — use a custom type for that |

---

## Use Cases

| Situation | Approach |
|---|---|
| A specific, well-known failure condition (not found, EOF) | Sentinel error + `errors.Is` |
| An error needs to carry extra data (which field, which ID) | Custom error type + `errors.As` |
| Adding context as an error propagates up the call stack | `fmt.Errorf("...: %w", err)` |
| A one-off, never-checked-for error | `errors.New("message")` is enough |

---

## Best Practices

1. Check every error at the call site; never discard with `_` unless you have a specific, documented reason.
2. Wrap with `%w`, not `%v`, when the caller might need to inspect the underlying error.
3. Use `errors.Is` for sentinel comparisons, `errors.As` for extracting a specific error type — never `==` or type assertions directly on a potentially-wrapped error.
4. Keep error messages lowercase and without trailing punctuation (Go convention) since they're often embedded in a larger wrapped message.
5. Don't log **and** return the same error — that usually means it gets logged twice up the call stack. Pick one place to log fully.

---

## Edge Cases & Pitfalls

- **`%v` instead of `%w` silently breaks `errors.Is`/`errors.As`** for anyone downstream — the message looks identical, but wrapping is lost.
- **Comparing a wrapped error with `==`** always fails — use `errors.Is`.
- **A custom error type with a pointer receiver on `Error()`** — `errors.As` needs a pointer-to-pointer target (`var ve *ValidationError; errors.As(err, &ve)`), a common syntax trip-up.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| `_, _ = f.Close()` — discarding errors reflexively | Handle or explicitly document why it's safe to ignore |
| Using `%v` when wrapping was intended | Use `%w` |
| Comparing wrapped errors with `==` | Use `errors.Is` |
| Returning `errors.New(fmt.Sprintf(...))` | Use `fmt.Errorf` directly — it's the same thing with less code |

---

## Cheat Sheet

```go
err := fmt.Errorf("context: %w", original) // wrap
errors.Is(err, ErrSentinel)                 // sentinel check, through wrapping
var target *MyErrType
errors.As(err, &target)                     // type extraction, through wrapping
errors.Unwrap(err)                          // one level of unwrapping
```

---

## Summary

- `error` is an interface with one method, `Error() string` — anything can be an error.
- Check errors immediately at the call site; never silently continue with a broken value.
- Wrap with `%w` to preserve the original error for later inspection while adding context.
- Use `errors.Is` for sentinel errors, `errors.As` for extracting structured custom error types — never raw `==` or type assertions on potentially-wrapped errors.

---

## Further Reading

- The Go Blog — *Working with Errors in Go 1.13*: <https://go.dev/blog/go1.13-errors>
- Go documentation — `errors` package: <https://pkg.go.dev/errors>

---

## Related Topics

- [Interfaces](../03-interfaces/junior.md) — `error` is itself an interface.
- [Production Debugging](../07-production-debugging/junior.md) — turning wrapped errors into useful logs.

---

## Check your understanding

1. Explain Error Handling — Junior Level in your own words and name the problem it solves.
2. How would you apply the ideas around Introduction, Prerequisites, Glossary in a realistic engineering change?
3. What failure mode or misuse should you look for, and what evidence would reveal it?
4. What small example would prove that you can apply Error Handling — Junior Level correctly?
5. What observable result would convince you that the approach improved the system?
