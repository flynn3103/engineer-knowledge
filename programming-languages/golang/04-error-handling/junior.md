# Error Handling — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Error Handling** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
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

## Apply it

1. Choose one small, known input for **Error Handling**.
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

- What problem does Error Handling solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
