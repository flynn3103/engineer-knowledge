# Interfaces — Middle

> **Topic:** [Interfaces](../README.md)
> **Focus:** Interface design principles ("accept interfaces, return structs"), dependency injection, interface composition via embedding, generics vs. interfaces, and designing for testability.

---

## Introduction

At the junior level you learned interfaces are satisfied implicitly and should be kept small. At this level the focus shifts to **design**: how do you structure a codebase so dependencies are injectable and testable, when should you compose interfaces via embedding, and — since Go 1.18 — when should you reach for generics instead of an interface?

---

## Prerequisites

- Comfortable with implicit satisfaction, type assertions, and small consumer-defined interfaces (junior level).

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

## Pros & Cons

| | Pros | Cons |
|---|---|---|
| Dependency injection via interfaces | Testable without a mocking framework; swappable implementations | Adds a layer of indirection; overused, it obscures what's actually happening |
| Interface embedding | Composes small interfaces into larger ones cleanly | A composed interface's implementers must satisfy *all* embedded methods — can't partially implement |
| Generics for type-parameterized logic | Type-safe, no runtime assertions, one implementation for many types | Newer to the language; constraint syntax has a learning curve; overuse can reduce readability |

---

## Use Cases

| Situation | Approach |
|---|---|
| A service needs a swappable, testable dependency | Interface + dependency injection |
| Combining `Read` and `Close` behavior | Interface embedding |
| Writing a `Max`/`Sum`/`Filter` that works identically across `int`, `float64`, custom numeric types | Generics with a constraint |
| A struct has exactly one implementation and no test ever needs a fake | Skip the interface — pass the concrete type |

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

## Cheat Sheet

```go
// Dependency injection
type Store interface { Get(id string) (T, error) }
func NewSvc(s Store) *Svc { return &Svc{s} }

// Composition via embedding
type RW interface { io.Reader; io.Writer }

// Generic constraint
type Number interface { ~int | ~float64 }
func SumT Number T { ... }
```

---

## Summary

- Use interfaces for dependency injection: define them at the point of use, keep them narrow, and hand-write fakes for tests instead of reaching for a mocking framework.
- Compose interfaces via embedding rather than duplicating method sets.
- Reach for generics, not `any`, when the relationship between input and output types is fixed — reach for interfaces when the point is behavior, not type identity.
- Avoid interface pollution: don't add an interface until you actually need substitutability.

---

## Further Reading

- Go Blog — *Type Parameters Proposal*: <https://go.dev/blog/intro-generics>
- Dave Cheney — *Practical Go: Real world advice for writing maintainable Go programs* (interface design sections)

---

## Related Topics

- [Interfaces — Junior](junior.md)
- [Error Handling — Middle](../04-error-handling/middle.md) — custom error types are just another interface consumer.

---

## Check your understanding

1. Explain Interfaces — Middle Level in your own words and name the problem it solves.
2. How would you apply the ideas around Introduction, Prerequisites, Core Concepts in a realistic engineering change?
3. What failure mode or misuse should you look for, and what evidence would reveal it?
4. Which local design trade-off would make you choose or reject Interfaces — Middle Level in an existing codebase?
5. What observable result would convince you that the approach improved the system?
