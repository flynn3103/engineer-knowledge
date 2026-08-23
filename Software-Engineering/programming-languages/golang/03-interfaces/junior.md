# Interfaces — Junior Level

> **Topic:** [Interfaces](../README.md)
> **Focus:** Implicit interface satisfaction, defining and using interfaces, type assertions, the empty interface, and why Go interfaces feel different from Java/C# interfaces.

---

## Introduction

A Go interface is a set of method signatures. Any type that has all those methods **automatically** satisfies the interface — there's no `implements` keyword, no explicit declaration required.

```go
type Writer interface {
    Write(p []byte) (n int, err error)
}
```

Any type with a `Write([]byte) (int, error)` method satisfies `Writer`, whether or not its author ever heard of this interface. This is **structural typing**, and it's one of the most Go-idiomatic ideas in the language: interfaces are usually defined by the *consumer* of a type, describing only the behavior it needs — not by the type's author trying to anticipate every future use.

---

## Prerequisites

- Comfortable with structs and methods (value vs. pointer receivers).
- Basic familiarity with functions as parameters.

---

## Glossary

| Term | Definition |
|------|-----------|
| **Interface** | A named set of method signatures. Any type implementing all of them satisfies the interface. |
| **Implicit satisfaction** | A type satisfies an interface just by having the right methods — no explicit declaration. |
| **Empty interface (`any`)** | `interface{}` (or its alias `any`, Go 1.18+) — has zero methods, so every type satisfies it. |
| **Type assertion** | `v, ok := x.(T)` — checks/extracts the concrete type stored in an interface value. |
| **Type switch** | `switch v := x.(type) { case T1: ...; case T2: ... }` — branches on the concrete type. |
| **Method set** | The set of methods a type (or pointer to it) has, determining which interfaces it satisfies. |
| **Nil interface vs. nil concrete value in an interface** | An interface holding a `nil` pointer of a concrete type is **not** itself `== nil` — a classic Go gotcha. |
| **Mock** | A test double implementing an interface with controllable, predictable behavior, used in place of a real dependency. |

---

## Core Concepts

### 1. Interfaces are satisfied implicitly

```go
type Animal interface { Speak() string }

type Dog struct{}
func (d Dog) Speak() string { return "Woof" }

var a Animal = Dog{} // Dog satisfies Animal automatically
```

`Dog` never mentions `Animal`. This decouples the definition of behavior from any specific interface, and lets you define new interfaces around existing types you don't own (including standard-library types).

### 2. Pointer vs. value receivers change the method set

```go
type Counter struct{ n int }
func (c *Counter) Inc() { c.n++ }   // pointer receiver

var _ Interface = Counter{}   // fails: Counter (value) doesn't have Inc in its method set
var _ Interface = &Counter{}  // works: *Counter does
```

If any method uses a pointer receiver, only `*T` (not `T`) satisfies interfaces requiring that method.

### 3. The empty interface accepts anything

```go
func describe(v any) {
    fmt.Printf("%v is %T\n", v, v)
}
```

`any` (alias for `interface{}`) is how Go achieves "accepts anything" without generics — but it discards all type information at compile time, so you often need a type assertion or type switch to do anything type-specific with the value.

### 4. Type assertions extract the concrete type

```go
var w io.Writer = os.Stdout
if f, ok := w.(*os.File); ok {
    fmt.Println("it's a file:", f.Name())
}
```

The two-value form (`v, ok := x.(T)`) never panics — `ok` is `false` if the assertion fails. The single-value form (`v := x.(T)`) panics on failure; use it only when you're certain of the type.

### 5. Type switches branch on concrete type

```go
switch v := x.(type) {
case string:
    fmt.Println("string:", v)
case int:
    fmt.Println("int:", v)
default:
    fmt.Println("unknown type")
}
```

### 6. The nil-interface gotcha

```go
type MyErr struct{}
func (e *MyErr) Error() string { return "oops" }

func doWork() error {
    var e *MyErr = nil
    return e // returns a NON-nil error interface wrapping a nil *MyErr!
}

err := doWork()
fmt.Println(err == nil) // false!
```

An interface value is `nil` only if **both** its type and value are nil. A `nil` pointer of a concrete type, stored in an interface, produces a non-nil interface. Always return a literal `nil`, not a typed nil pointer, when there's no error.

---

## Code Examples

### Example 1 — Small, consumer-defined interface

```go
type Fetcher interface {
    Fetch(url string) ([]byte, error)
}

func Summarize(f Fetcher, url string) string {
    data, err := f.Fetch(url)
    if err != nil {
        return "error"
    }
    return string(data[:100])
}
```

`Summarize` doesn't care what `Fetcher` actually is — an HTTP client, a mock, a cache-backed wrapper — as long as it has `Fetch`.

### Example 2 — A mock for testing

```go
type mockFetcher struct{ data []byte; err error }
func (m mockFetcher) Fetch(url string) ([]byte, error) { return m.data, m.err }

func TestSummarize(t *testing.T) {
    got := Summarize(mockFetcher{data: []byte("hello world")}, "any-url")
    if got != "hello world" {
        t.Errorf("got %q", got)
    }
}
```

No HTTP call, no network flakiness — the interface makes the dependency swappable.

### Example 3 — `io.Reader`/`io.Writer` composability

```go
func copyAll(dst io.Writer, src io.Reader) (int64, error) {
    return io.Copy(dst, src)
}
```

`copyAll` works with a file, a network connection, an in-memory buffer, or anything else implementing these two tiny interfaces — because the standard library defines them narrowly.

---

## Pros & Cons

| | Pros | Cons |
|---|---|---|
| **Implicit satisfaction** | Decouples types from interfaces; retrofit interfaces onto existing types freely | Can't tell from a type's definition alone which interfaces it satisfies — you have to check |
| **Small interfaces** | Easy to implement, easy to mock, compose well | Sometimes need several small interfaces instead of one big one, which can feel verbose |
| **Empty interface (`any`)** | Maximum flexibility for generic-ish code | Loses compile-time type safety; usually a sign generics (Go 1.18+) might be a better fit |

---

## Use Cases

| Situation | Approach |
|---|---|
| A function needs "something with a `Read` method," not a specific type | Accept `io.Reader`, not a concrete `*os.File` |
| Testing code that depends on an external service | Define a small interface for just the methods used; swap in a mock |
| A function genuinely needs to accept any type | `any`, with a type switch/assertion inside |

---

## Best Practices

1. Define interfaces where they're **consumed**, not where the implementing type is defined.
2. Keep interfaces small — one or two methods is common and good ("the bigger the interface, the weaker the abstraction").
3. Accept interfaces, return concrete types, as a general rule for function signatures.
4. Always use the two-value form of a type assertion unless you're certain the assertion can't fail.
5. Never return a typed `nil` pointer as an `error` — return the literal `nil`.

---

## Edge Cases & Pitfalls

- **A `nil` pointer wrapped in an interface is not `== nil`.** Always double-check functions that can return `nil` errors.
- **A single-value type assertion panics on mismatch** — use the two-value form unless you've already checked the type another way.
- **Embedding an interface in a struct doesn't automatically implement it** unless the embedded field is itself a value satisfying it.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Defining a big interface with every method a type might ever need | Split into small, focused interfaces per consumer |
| Returning a typed nil pointer as an `error` | Return literal `nil` when there's no error |
| Using single-value type assertion without knowing the type is guaranteed | Use `v, ok := x.(T)` |

---

## Cheat Sheet

```go
// Define
type Reader interface { Read(p []byte) (n int, err error) }

// Implicit satisfaction — no "implements" keyword
type MyReader struct{}
func (r MyReader) Read(p []byte) (int, error) { ... }

// Type assertion (safe)
v, ok := x.(ConcreteType)

// Type switch
switch v := x.(type) {
case string: ...
case int: ...
}

// any / empty interface
func f(v any) { ... }
```

---

## Summary

- Go interfaces are satisfied implicitly — any type with the right methods qualifies, with no explicit declaration.
- Pointer vs. value receivers determine a type's method set and which interfaces it can satisfy.
- Small, consumer-defined interfaces are idiomatic Go and make testing/mocking natural.
- `any` accepts anything but loses static type information — recover it via type assertion or type switch.
- A `nil` concrete pointer stored in an interface is **not** a `nil` interface — a classic and important gotcha.

---

## Further Reading

- Effective Go — *Interfaces*: <https://go.dev/doc/effective_go#interfaces>
- Go Wiki — *CodeReviewComments: Interfaces*: <https://go.dev/wiki/CodeReviewComments#interfaces>

---

## Related Topics

- [Error Handling](../04-error-handling/junior.md) — `error` is itself just an interface.
- [Go Runtime](../02-go-runtime/junior.md) — how interface values are represented internally.
