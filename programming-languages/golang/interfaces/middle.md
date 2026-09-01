# Interfaces — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Interfaces** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Dependency injection via interfaces

```go
type UserStore interface {
    GetUser(id string) (User, error)
}

type Service struct {
    store UserStore
}

func NewService(store UserStore) *Service { return &Service{store: store} }
```

`Service` depends on the *interface*, not a concrete database type. Production code passes a real database-backed implementation; tests pass an in-memory fake. No mocking framework required — Go's implicit satisfaction makes hand-written fakes trivial.

### 2. Interface composition via embedding

```go
type Reader interface { Read(p []byte) (n int, err error) }
type Writer interface { Write(p []byte) (n int, err error) }
type ReadWriter interface {
    Reader
    Writer
}
```

Embedding composes interfaces the same way it composes structs — `ReadWriter` requires both method sets. This is how the standard library builds `io.ReadWriter`, `io.ReadWriteCloser`, etc. from small pieces.

### 3. "Accept interfaces, return structs"

```go
func NewClient(logger Logger) *Client { // accept an interface
    return &Client{logger: logger}      // return a concrete struct
}
```

Accepting an interface parameter maximizes flexibility for callers. Returning a concrete struct gives *your* callers full access to all of that type's methods and fields, rather than an artificially narrowed interface — you can always narrow later by having them declare their own consumer interface.

### 4. Generics vs. interfaces — different problems

Interfaces describe **behavior** (a set of methods). Generics (Go 1.18+) describe **constraints on types used in a single function/type**, often when you need the *same* concrete type in and out, which an interface can't express:

```go
func MaxT cmp.Ordered T {
    if a > b { return a }
    return b
}
```

An interface-based `Max(a, b any) any` would lose type safety and require type assertions on the way out. Reach for generics when the constraint is about a type parameter's *operations* (comparable, ordered, numeric); reach for interfaces when the constraint is about an object's *behavior*.

### 5. Interface pollution — a real anti-pattern

Defining an interface for every struct "just in case" (a habit carried over from Java) adds indirection without benefit if there's only ever one implementation and no test needs a fake. The Go idiom is: **define the interface at the point of use, only when you actually need substitutability** (for tests, or for genuinely multiple implementations) — not preemptively for every type.

### 6. Designing narrow interfaces for testability

```go
type Clock interface { Now() time.Time }

type realClock struct{}
func (realClock) Now() time.Time { return time.Now() }

type fixedClock struct{ t time.Time }
func (f fixedClock) Now() time.Time { return f.t }
```

Wrapping `time.Now()` behind a one-method interface is a small amount of ceremony that makes time-dependent code deterministically testable — a pattern worth knowing for anything involving timeouts, expiry, or scheduling.

---

## Code Examples

### Example 1 — A hand-written fake, no mocking library

```go
type fakeUserStore struct{ users map[string]User }
func (f fakeUserStore) GetUser(id string) (User, error) {
    u, ok := f.users[id]
    if !ok { return User{}, ErrNotFound }
    return u, nil
}

func TestService_GetUser(t *testing.T) {
    svc := NewService(fakeUserStore{users: map[string]User{"1": {Name: "Ada"}}})
    u, err := svc.GetUser("1")
    // assertions...
}
```

### Example 2 — Composed interface via embedding

```go
type ReadCloser interface {
    io.Reader
    io.Closer
}
```

### Example 3 — Generic constraint interface

```go
type Number interface {
    ~int | ~int64 | ~float64
}
func SumT Number T {
    var total T
    for _, n := range nums { total += n }
    return total
}
```

`~int` means "any type whose underlying type is `int`," letting `Sum` work on both `int` and a named type like `type Age int`.

---

## Coding Patterns

- **Interface at the point of use**: define `type Fetcher interface { Fetch(...) }` in the package that *calls* `Fetch`, not the package that implements it.
- **Fixed clock/random pattern**: wrap non-deterministic dependencies (`time.Now`, `rand`, UUID generation) behind a one-method interface for deterministic tests.
- **Constructor injection**: `NewX(dep1, dep2)` accepting interfaces, returning a concrete struct.

---

## Best Practices

1. Don't create an interface until you have a second implementation or a concrete testing need for one.
2. Prefer embedding to compose interfaces instead of duplicating method signatures.
3. Choose generics over `any` + type assertions whenever the relationship is "same type in, same type out."
4. Keep dependency-injected interfaces narrow — one or two methods the consumer actually calls.

---

## Edge Cases & Pitfalls

- **A struct satisfying an interface accidentally**, because it happens to have a same-named method with a different intended meaning, is a real (if rare) correctness risk with structural typing — naming conventions help avoid it.
- **Embedding two interfaces with overlapping method names but different signatures** is a compile error — resolve by not embedding, or by renaming.
- **Generic constraints with `~T` unions** can get unreadable fast; keep constraints small and named.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Defining an interface for every struct "just in case" | Only add one when you have a real second implementation or test need |
| Using `any` + type assertion where a generic function would be type-safe | Use a generic function with a constraint when the shape is "same type in/out" |
| Returning an interface from a constructor instead of a concrete struct | Return the concrete type; let callers narrow if they need to |

---

## Tricky Points

- A generic function's type parameter is resolved once at the call site (monomorphized or dictionary-passed, depending on the compiler's choice) — it is *not* the same runtime mechanism as an interface's dynamic dispatch.
- Interface embedding conflicts (same method name, different signature from two embedded interfaces) are caught at compile time, not silently resolved.

---

## Apply it

1. Find a real component where **Interfaces** affects an interface or dependency.
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

- Which boundary is most affected by Interfaces?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
