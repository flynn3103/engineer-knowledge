# Evaluation Strategies (call-by-x) — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Evaluation Strategies (call-by-x)** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Calling Convention Is the Real Strategy

"Call-by-value" is a source-language idea; the **ABI** decides what actually happens. Under System V AMD64:

- A small trivially-copyable struct passed by value may travel **in registers** — essentially free.
- A large struct passed by value is materialized in the caller's frame and passed **by hidden pointer**, and the callee may copy it — a real `memcpy`.
- A return of a large value uses **sret**: the caller passes a hidden destination pointer; the callee constructs the result in place. This is the ABI mechanism that makes RVO real — no copy *and* no move on return.

So "by value" can be free (registers) or expensive (memcpy) depending entirely on size and triviality. Reasoning about cost requires the ABI, not just the keyword.

### 2. The Performance Profile of Each Strategy

| Strategy | Shows up in a profile as | Typical hot-path cost |
|----------|--------------------------|------------------------|
| by-value (small/trivial) | nothing — args in registers | ~free |
| by-value (large) | `memcpy`/`__memmove` frames; high resident copies | O(size) per call |
| by-const-ref / pointer | pointer deref; cache misses on cold data | O(1) + memory latency |
| by-move | move ctor frames; near-zero copies | O(1) handle transfer |
| call-by-need / thunk | allocation profile churn; GC pressure; `force`/closure frames | alloc + force per arg |
| call-by-sharing | refcount inc/dec (CPython); write barriers (JVM/Go) | small but ubiquitous |

The two most common production findings: (a) a large value silently passed by value on a hot path → `memcpy` dominates the flame graph; (b) thunk/closure allocation per request → GC pauses and allocation-rate alerts.

### 3. Go: Call-by-Value With Sharing Hiding Inside

Go is strictly call-by-value — *every* argument is copied. The trap is **what** gets copied:

- A `[]T` slice copies its 3-word header but **shares the backing array** → mutating elements through the parameter leaks to the caller (call-by-sharing semantics on top of call-by-value).
- A `map[K]V` and `chan` are reference types: the copied value is a pointer to the same map/channel → shared.
- A large array `[N]T` or big struct copies the **whole thing** → silent O(N) copy on every call. Pass `*[N]T` or `[]T` instead.

So Go forces you to know which types are "headers over shared storage." `append` adds another twist: it may or may not reallocate, so whether a caller sees appended elements depends on capacity — a notorious source of bugs.

### 4. Python/JVM: Sharing Plus Lifetime Effects

In CPython, every argument is a `PyObject*` passed by value, with a **refcount bump** on bind and a decrement on scope exit. Implications at scale: refcount writes are cache-line traffic, they prevent some compiler optimizations, and they're why CPython's GIL and refcounting are intertwined. Passing a huge object is cheap (one pointer + one refcount op) but **shared** — defensive copies cost real memory.

On the JVM, arguments are references (call-by-sharing) or primitives (by value). **Escape analysis** can prove a passed object doesn't escape the callee and **stack-allocate or scalar-replace** it, erasing the heap allocation entirely — so "everything is heap" is false in practice. But escape analysis is fragile: storing the argument in a field, returning it, or passing it to an un-inlined method defeats it. Knowing what keeps an argument from escaping is a real JIT-performance skill.

### 5. The API Signature Is a Misuse-Prevention Tool

At scale, the parameter-passing choice in a signature is the cheapest, most durable safety mechanism you have, because the compiler enforces it for everyone:

- `const T&` / `&T` (immutable borrow) says "I will read, not keep, not mutate" — and the compiler enforces no-mutate (C++ `const`, Rust shared borrow).
- `T&&` / `T` by value (sink) says "give me ownership" — Rust makes the source unusable, preventing accidental later use.
- A by-value copy of a small immutable type makes a function provably side-effect-free in its argument.
- Returning a new value instead of mutating an out-param removes the aliasing question entirely.

A correct signature turns a class of runtime bugs into compile errors. That leverage is why senior+ engineers obsess over signatures.

### 6. Cost vs Safety Is a Real Tradeoff, Not a Dogma

"Always pass by const-reference for big objects" is a good default but not a law. A const-reference can **alias** the caller's mutable state, enabling TOCTOU and re-entrancy bugs; it can **dangle** if stored; and pointer-chasing has its own cache cost. Sometimes a defensive copy (or a move) is *both* safer and, after escape analysis/RVO, not measurably slower. The professional move is to **measure**, not to recite a rule.

---

## Code Examples

### Example 1: The Hot-Path By-Value Copy (and Its Fix)

```cpp
// BEFORE: each call deep-copies a potentially huge config (memcpy in the flame graph)
Result handle(Config cfg, const Request& req);   // Config by value

// AFTER: borrow it; the caller still owns it; zero copy
Result handle(const Config& cfg, const Request& req);

// If 'handle' must STORE the config, take it by value and move (sink idiom):
struct Handler {
    Config cfg_;
    explicit Handler(Config cfg) : cfg_(std::move(cfg)) {}  // copy-or-move once, then steal
};
```

### Example 2: The Go Slice Aliasing Trap

```go
func normalize(xs []float64) {
    for i := range xs {
        xs[i] /= total(xs)   // mutates the CALLER's backing array — shared!
    }
}

data := []float64{1, 2, 3}
normalize(data)              // data is modified in place, even though "passed by value"

// And the append surprise:
func addZero(xs []int) []int {
    return append(xs, 0)     // may or may not realloc; caller sees the change ONLY if no realloc
}
```

The fix when you must not mutate the caller: copy explicitly with `append([]float64(nil), xs...)` or `slices.Clone`.

### Example 3: CPython — Sharing and the Defensive-Copy Cost

```python
def add_audit_fields(record: dict) -> dict:
    record["audited_at"] = now()   # MUTATES caller's dict — shared reference
    return record

# Safe version pays a copy:
def add_audit_fields_safe(record: dict) -> dict:
    record = dict(record)          # shallow copy breaks aliasing (real memory cost)
    record["audited_at"] = now()
    return record
```

At high throughput, the defensive `dict(record)` is a measurable allocation; whether to pay it is a real design decision, not an automatic "always copy."

### Example 4: JVM Escape Analysis in Action

```java
// 'point' may be scalar-replaced (no heap alloc) IF it doesn't escape:
int dist(int x, int y) {
    Point p = new Point(x, y);   // escape analysis can eliminate this allocation
    return p.x * p.x + p.y * p.y;
}

// Escape DEFEATED — now it must live on the heap:
Point cache;
int distLeaky(int x, int y) {
    Point p = new Point(x, y);
    cache = p;                   // p escapes via a field → real allocation
    return p.x * p.x + p.y * p.y;
}
```

### Example 5: Encoding the Contract in the Type System

```rust
fn read_only(cfg: &Config) { /* compiler forbids mutation */ }
fn update(cfg: &mut Config) { cfg.retries += 1; }      // exclusive, explicit
fn take(cfg: Config) { /* owns it; caller can't use cfg afterward */ }

// Misuse is a COMPILE ERROR, enforced for the whole codebase:
let c = Config::default();
take(c);
// read_only(&c);  // error: borrow of moved value 'c'
```

---

## Coding Patterns

**Pattern: Default to borrow, escalate deliberately.** Start every parameter as a read-only borrow; promote to `&mut`/owned/move only when the function's job demands it. The signature documents and enforces intent.

**Pattern: Sink-by-value-then-move** (C++/Rust) so one signature optimally handles both lvalue and rvalue callers.

**Pattern: Copy at the boundary, share within the core.** Defensive-copy untrusted/cross-thread inputs once at the edge; pass borrows freely inside the trusted core where you control aliasing.

**Pattern: Return, don't out-param.** In languages with cheap multiple returns (Go, Rust, Python), return tuples/structs and rely on RVO/sret rather than mutating caller variables.

**Pattern: Make the hot path allocation-free.** On the critical path, prefer borrows and pre-allocated buffers over by-value copies and thunks; verify with an allocation profiler.

---

## Best Practices

1. **Profile before changing a passing strategy.** "Pass by reference for speed" is a hypothesis; the flame graph (copies) and heap profile (allocations) are the evidence.
2. **Encode the contract in the signature** so the compiler enforces no-mutate / single-owner across the whole codebase.
3. **Know your language's hidden sharing:** Go slices/maps, Python/JVM object references. Treat any mutable shared argument as mutable-by-the-callee unless proven otherwise.
4. **Defensive-copy at trust and thread boundaries**, not everywhere; copies cost memory and GC time.
5. **Prefer move over copy for sinks; prefer borrow over move/copy for reads.**
6. **On hot paths, drive copies and per-call allocations toward zero**, and let escape analysis / RVO / strictness analysis do the rest — but verify they actually fired.
7. **Never store a borrowed reference past the call** unless lifetime is guaranteed; that's how dangling and use-after-free happen.

---

## Edge Cases & Pitfalls

**Pitfall 1: Large-by-value on a hot path.** A big struct/array passed by value compiles to a per-call `memcpy`. Classic flame-graph surprise; fix with a borrow or move.

**Pitfall 2: Go `append` capacity aliasing.** Whether the caller sees appended elements depends on whether `append` reallocated — non-deterministic from the call site. Clone when you need isolation.

**Pitfall 3: Defensive copy that's only shallow.** Copying the outer container but sharing inner mutable objects leaves an aliasing leak. Deep-copy when the inner objects are mutable and must be isolated.

**Pitfall 4: TOCTOU through an aliased argument.** Validate a shared mutable argument, then act on it, and a concurrent (or re-entrant) mutation between the two steps invalidates the check. Copy or snapshot before validating.

**Pitfall 5: Escape analysis silently failing.** A refactor that stores or returns a previously-local argument re-introduces a heap allocation and a latency regression with no source-level "smell." Watch allocation profiles across refactors.

**Pitfall 6: Moved-from object reused (C++).** After `std::move`, the source is valid-but-unspecified; reading it is a latent bug that may pass tests and fail under load/optimization. Treat moved-from as dead.

**Pitfall 7: Thunk/closure capturing a large object.** A deferred argument that closes over a big structure keeps it alive (and out of the nursery), inflating memory and GC time until forced.

---

## Apply it

1. Define the user or business outcome that **Evaluation Strategies (call-by-x)** should improve.
2. Assign one owner for code, contracts, operations, and incidents.
3. Split delivery into reversible increments that produce evidence early.
4. Publish responsibilities, escalation paths, and compatibility windows.
5. Stop or expand only when the agreed measures support that decision.

## Verify your work

- Each increment has an owner, rollback path, and observable exit condition.
- Adoption, reliability, delivery time, and coordination cost are measured.
- Incident and migration exercises prove that responsibility is executable.
- The old path is removed only after telemetry proves it is unused.

## Review questions

- Which measurable outcome justifies investing in Evaluation Strategies (call-by-x)?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
