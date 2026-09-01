# Interfaces — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Interfaces** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
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

## Apply it

1. Choose one small, known input for **Interfaces**.
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

- What problem does Interfaces solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
