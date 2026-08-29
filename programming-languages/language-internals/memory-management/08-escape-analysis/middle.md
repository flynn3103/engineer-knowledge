# Escape Analysis — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Escape Analysis** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## How the Analysis Works

### Reachability over a connection graph

Conceptually the compiler:

1. Creates a node for every allocation site and every variable that can hold a reference.
2. Adds **edges** for assignments: `a = b` means `a` may point to whatever `b` points to; `p = &x` means `p` points to `x`; storing into a field/slice element adds edges into that container.
3. Marks certain nodes as **escaping roots**: function return values, globals, parameters that are themselves stored somewhere escaping, arguments to un-analyzable functions, values captured by escaping closures.
4. **Propagates:** any allocation reachable (in the graph) from an escaping root is marked as escaping. Everything not reachable from a root stays on the stack.

This is a *may* analysis: it errs toward "escape." If two paths are possible and one escapes, the value escapes.

### Conservative by necessity

The compiler must remain correct under all execution paths, so it assumes the worst whenever it loses visibility:

- **Interface method calls** — it often can't tell which concrete implementation runs, so it assumes the argument may be stored.
- **Function values / pointers** — calling through a variable hides the callee.
- **Reflection** — can do arbitrary things; treated as fully opaque.
- **Calls to functions it didn't analyze** (no inlining, separate compilation boundaries it can't see through).

Each of these collapses the analysis to "assume escape."

### Inlining is the multiplier

Escape analysis in Go and Java runs *together with* inlining. When a small callee is inlined, its allocations become part of the caller's body, and the compiler can now prove they don't escape the (larger) combined function. The same value can be stack-allocated when the call is inlined and heap-allocated when it isn't. This is why "make hot functions inlinable" is a real performance lever.

---

## The Escape Triggers (Catalog)

A value escapes to the heap when **any** of these holds:

1. **Returned by reference.** `return &local` (Go) — the pointer outlives the frame.
2. **Stored in a field of an escaping object,** a global, or a long-lived container (slice/map that survives).
3. **Captured by a closure that outlives the call.** The captured variable's storage must live as long as the closure.
4. **Converted to an interface and then used in a way that stores it** — e.g., passed to `fmt.Println`, appended to an `[]interface{}`, put in a `map[string]any`.
5. **Address taken and passed to an un-analyzable callee** (interface method, function pointer, reflection, an un-inlined external function without `//go:noescape`).
6. **Too large for the stack / unknown size.** A value whose size isn't known at compile time (e.g., a slice backing array whose length is dynamic) typically goes to the heap. Very large values may too.
7. **Sent on a channel / shared across goroutines** (Go) — becomes reachable by another goroutine, so it escapes (and can no longer be a candidate for some single-thread optimizations).

If none apply and the compiler can prove it, the value stays on the stack (Go) or becomes a candidate for scalar replacement (Java).

---

## Reading Go's `-gcflags=-m` Output

```bash
go build -gcflags='-m' ./...     # escape + inlining decisions
go build -gcflags='-m -m' ./...  # more verbose: WHY a decision was made
```

The messages you care about:

| Message | Meaning |
|---|---|
| `does not escape` | The argument/value stayed on the stack. Good. |
| `escapes to heap` | A value flowed somewhere outliving the function. |
| `moved to heap: x` | A *named local* `x` was promoted to the heap (often because `&x` leaked). |
| `... escapes to heap: ... flow:` (with `-m -m`) | The chain of assignments explaining the escape. |
| `can inline f` / `inlining call to f` | Inlining decisions — relevant because they change escape results. |
| `leaking param: p` | Parameter `p` (or what it points to) escapes through the function. |
| `leaking param content: p` | The *contents* p points to escape, but not p itself. |

The single most useful flag combo is `-gcflags='-m -m'`: the doubled `-m` prints the **flow** — the assignment chain — so you can see *why* something escaped, not just *that* it did.

---

## Code Examples

### Example 1 — Pointer return forces heap

```go
type Point struct{ X, Y int }

func makePoint() *Point {
    p := Point{1, 2}
    return &p
}
```

```
$ go build -gcflags='-m' .
./main.go:4:2: moved to heap: p
```

`p` escapes because the returned pointer outlives `makePoint`.

### Example 2 — Same value, returned by VALUE, stays on stack

```go
func makePointVal() Point {
    p := Point{1, 2}
    return p          // copy of the struct, no pointer leaks
}
```

No `moved to heap` line. The caller gets a copy; `p`'s storage dies with the frame.

### Example 3 — Interface boxing (`fmt.Println`)

```go
func logIt(n int) {
    fmt.Println(n)    // n is converted to interface{} -> boxed
}
```

```
$ go build -gcflags='-m' .
./main.go:4:13: ... n escapes to heap
```

`fmt.Println` takes `...interface{}`. Converting `n` to `interface{}` requires a pointer to the value, and because `Println` (via the un-analyzable `fmt` path) may keep it, `n` escapes. This is why `fmt.Println` in a hot loop allocates.

### Example 4 — "Does not escape" parameter

```go
func sum(p *Point) int {
    return p.X + p.Y  // we only READ through p; never store it
}
```

```
$ go build -gcflags='-m' .
./main.go:2:10: p does not escape
```

The pointer is only dereferenced and read. Nothing about `p` is stored, so the *caller's* value pointed to by `p` need not be heap-allocated on account of `sum`.

### Example 5 — Closure capture

```go
func counter() func() int {
    n := 0
    return func() int { n++; return n }  // closure outlives counter()
}
```

```
$ go build -gcflags='-m' .
./main.go:2:2: moved to heap: n
```

`n` is captured by a closure that's returned, so `n` must live on the heap.

### Example 6 — Slice that escapes via append to a surviving slice

```go
var sink [][]byte

func keep(b []byte) {
    sink = append(sink, b)  // b's backing array is now reachable from a global
}
```

The backing array referenced by `b` escapes because it becomes reachable from the package-level `sink`.

---

## Java / HotSpot Mechanisms

Java's escape analysis is conceptually the same question, but the *payoff* and *timing* differ.

### When it runs

Java escape analysis happens in the **JIT (C2 / the optimizing tier)**, **not** at `javac` time and **not** in the interpreter. So:

- It only fires for **hot** methods that got JIT-compiled.
- It depends heavily on **inlining** — the JIT inlines the allocation site and the methods using the object, *then* analyzes escape across the merged code.
- Cold or rarely-run code keeps allocating normally.

Enabled by default; the relevant flags are `-XX:+DoEscapeAnalysis` (on by default) and `-XX:+EliminateAllocations`.

### What it enables (three optimizations)

1. **Scalar replacement (the big one).** If an object doesn't escape, the JIT can skip allocating it and instead keep each field in a register or local. The object effectively never exists.

   ```java
   // The Point object below typically never reaches the heap when this is hot.
   int dist2(int x, int y) {
       Point p = new Point(x, y); // no-escape
       return p.x * p.x + p.y * p.y;
   }
   ```

   After inlining `Point`'s constructor and field access, `p.x`/`p.y` become plain locals; `new Point` is eliminated.

2. **Stack allocation.** A weaker form (HotSpot mostly relies on scalar replacement rather than true stack allocation of whole objects, but the concept applies).

3. **Lock elision (`-XX:+EliminateLocks`).** If a synchronized object never escapes the thread, no other thread can contend on its monitor, so the JIT removes the locking entirely. Classic example: a method that builds a string with an internally-`synchronized` `StringBuffer` that never escapes — the locks become no-ops.

### How to see it

```
java -XX:+UnlockDiagnosticVMOptions -XX:+PrintEliminateAllocations ...
java -XX:+PrintCompilation ...
```

(See the professional tier for a full workflow with JITWatch and async-profiler.)

---

## Coding Patterns

- **Return values, not pointers, for small structs** in hot code (Go) — avoids forcing the callee's result onto the heap.
- **Keep hot functions small enough to inline** so the analysis can see through the call.
- **Avoid widening to `interface{}` / `any` in hot paths.** Use concrete types; reserve interfaces for boundaries.
- **Reuse buffers** (e.g., `sync.Pool`, preallocated slices) when a value genuinely must escape and is created repeatedly.

---

## Best Practices

- **Diagnose before optimizing.** Run `go build -gcflags='-m -m'` (or HotSpot's allocation-elimination logging) and read the actual decisions.
- **Optimize the proven hot path only.** Most escapes don't matter; profile first.
- **Treat stack placement as an optimization, never a guarantee.** Don't write code whose correctness assumes it.
- **Watch the inlining budget** — large functions stop being inlined, which can silently move allocations to the heap.

---

## Edge Cases & Pitfalls

- **`fmt`/logging in hot loops** is a top allocation source via boxing. Move it out of the loop or use typed, non-boxing logging.
- **Returning an interface** (Go) almost always escapes the underlying value, because the interface header carries a pointer the caller keeps.
- **`leaking param content` vs `leaking param`** are different: the former means only what the pointer *points at* escapes, the latter the pointer itself.
- **Goroutine capture** (`go func(){ use(x) }()`) makes `x` escape to the heap *and* marks it thread-shared.
- **Java cold start:** benchmarking a method once will show allocations because the JIT hasn't compiled it yet — always warm up before concluding "escape analysis isn't working."

---

## Apply it

1. Find a real component where **Escape Analysis** affects an interface or dependency.
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

- Which boundary is most affected by Escape Analysis?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
