# Manual Memory Management — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Manual Memory Management** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### RAII: lifetime = scope

The single most important idea in modern C++ memory management is that **you almost never write `free`/`delete` directly.** Instead, you wrap each owned resource in an object whose destructor releases it. When the object goes out of scope — by normal flow, early return, *or an exception* — the destructor runs. Cleanup becomes structural rather than something you remember to do.

```cpp
{
    std::vector<int> v(1000);   // allocates
    // ... 50 lines, early returns, exceptions thrown ...
}   // v's destructor frees the buffer here, unconditionally
```

This solves the problem the C `goto`-ladder solved, but automatically and exception-safely. RAII generalizes far beyond memory: file handles, locks, sockets, transactions — anything with a paired acquire/release.

### Smart pointers and ownership semantics

| Type | Ownership model | Cost | Use when |
|------|-----------------|------|----------|
| `std::unique_ptr<T>` | **Exclusive.** One owner; move-only. | Zero overhead vs raw pointer. | The default for owning a heap object. |
| `std::shared_ptr<T>` | **Shared.** Reference-counted; freed when the last owner dies. | Atomic refcount on copy/destroy. | Genuinely shared, indeterminate-lifetime ownership. |
| `std::weak_ptr<T>` | **Non-owning observer** of a `shared_ptr`. | Cheap. | Break reference cycles; observe without keeping alive. |
| Raw `T*` / `T&` | **Non-owning** (by modern convention). | None. | Borrowing — passing without transferring ownership. |

`std::make_unique<T>(...)` and `std::make_shared<T>(...)` are the preferred constructors: they're exception-safe and, for `make_shared`, fuse the control block and object into one allocation.

The discipline: **`unique_ptr` is the default; reach for `shared_ptr` only when ownership is truly shared.** Overusing `shared_ptr` reintroduces the costs of garbage collection (atomic refcounting) and hides ownership, plus it leaks on reference cycles — `shared_ptr` is *not* a garbage collector.

### Rule of Three / Five / Zero

A class that owns a raw resource must control how it's copied, moved, and destroyed:

- **Rule of Three** (classic): if you define a destructor, copy constructor, *or* copy assignment, you almost certainly need all three — because the default copy does a shallow pointer copy, leading to double-free.
- **Rule of Five** (since C++11): add the move constructor and move assignment to enable cheap ownership transfer.
- **Rule of Zero** (the goal): **own resources through members that already manage themselves** (`unique_ptr`, `vector`, `string`), so your class needs *none* of these — the compiler-generated defaults are correct. Most well-designed classes should follow the Rule of Zero.

### Move semantics

Move is "transfer ownership without copying." `std::move` casts to an rvalue reference, letting a move constructor *steal* the internal pointer and null out the source:

```cpp
std::unique_ptr<Widget> a = std::make_unique<Widget>();
std::unique_ptr<Widget> b = std::move(a);  // b owns it; a is now empty (nullptr)
// a is safe to destroy — it owns nothing.
```

This is the C++ encoding of "ownership is a baton passed exactly once." It makes `unique_ptr` zero-cost: returning one from a factory just moves a pointer.

### Rust: ownership as compile-time RAII

Rust takes C++'s RAII and makes it *mandatory and checked*:

- Every value has exactly **one owner**; when the owner goes out of scope, `Drop::drop` runs (RAII).
- Assigning or passing a non-`Copy` value **moves** it; the source is statically unusable afterward — use-after-move is a *compile error*, not UB.
- References are **borrows**, governed by the borrow checker: either one mutable borrow *or* any number of shared borrows, never both, and no borrow may outlive its referent. This statically eliminates use-after-free, data races, and iterator invalidation.

The trade: a steep learning curve and the occasional fight with the borrow checker, in exchange for memory safety *with no garbage collector and no runtime checks*. Where you genuinely need shared ownership, Rust gives you `Rc<T>`/`Arc<T>` (the `shared_ptr` analogue) explicitly, so the cost is visible.

---

## The Cross-Language Comparison

| Dimension | C | C++ (RAII) | Rust | Managed (Java/Go) |
|-----------|---|------------|------|-------------------|
| Who proves safety | The programmer, mentally | The programmer, via RAII discipline | The compiler (borrow checker) | The runtime (GC) |
| Use-after-free | Possible (UB) | Possible if you bypass RAII | **Impossible** (safe code) | Impossible |
| Double-free | Possible | Prevented by ownership types | **Impossible** | N/A |
| Leaks | Easy | Rare, but cycles in `shared_ptr` leak | Possible (`Rc` cycles) but no UB | Rare; GC handles most |
| Runtime cost | None | None (RAII) / atomic (`shared_ptr`) | None (safe abstractions are zero-cost) | GC pauses, write barriers |
| Determinism | Total | Total | Total | Non-deterministic teardown |
| Escape hatch | n/a | n/a | `unsafe` blocks | JNI/cgo |

The throughline: **the cost of safety doesn't vanish; it moves.** C pushes it to the programmer's discipline and to runtime crashes. C++ moves it to scopes and convention. Rust moves it to compile time. GC languages move it to runtime overhead and pause latency. A senior engineer chooses based on which cost the system can afford — a trading engine cannot afford GC pauses; a CRUD service cannot afford manual-memory CVEs.

---

## Code Examples

### Same problem, three languages

**C — manual, ownership in comments:**
```c
// OWNERSHIP: caller frees with node_free().
Node *node_new(int v) {
    Node *n = malloc(sizeof *n);
    if (!n) return NULL;
    n->value = v; n->next = NULL;
    return n;
}
void node_free(Node *n) { free(n); }
```

**C++ — RAII, ownership in the type:**
```cpp
struct Node {                 // Rule of Zero: members manage themselves
    int value;
    std::unique_ptr<Node> next;   // owns the rest of the list
};
auto n = std::make_unique<Node>(Node{42, nullptr});
// No destructor written; the whole list frees automatically (mind deep recursion).
```

**Rust — ownership in the compiler:**
```rust
struct Node {
    value: i32,
    next: Option<Box<Node>>,   // Box owns the heap allocation
}
let n = Box::new(Node { value: 42, next: None });
// Drops automatically at end of scope; use-after-free is a compile error.
```

### Breaking a cycle with `weak_ptr`

```cpp
struct Child;
struct Parent { std::vector<std::shared_ptr<Child>> children; };
struct Child  { std::weak_ptr<Parent> parent; };  // weak, NOT shared — else cycle leaks
```

If `Child` held a `shared_ptr<Parent>`, parent and child would keep each other alive forever — a classic refcount leak. `weak_ptr` observes without owning.

---

## Coding Patterns

### Arena / region allocation

Bump a pointer to allocate; reset once to free everything. Ideal when many objects share a lifetime (a request, a frame, a parse).

```c
typedef struct { char *base; size_t off, cap; } Arena;

void *arena_alloc(Arena *a, size_t n) {
    n = (n + 15) & ~(size_t)15;          // 16-byte align
    if (a->off + n > a->cap) return NULL;
    void *p = a->base + a->off;
    a->off += n;
    return p;                             // no per-object free
}
void arena_reset(Arena *a) { a->off = 0; }   // frees ALL at once
```

Arenas turn N frees into one, eliminate per-object lifetime bugs, and are dramatically faster. The cost: you cannot free individual objects early. Used heavily in compilers (per-AST), game engines (per-frame), and servers (per-request).

### Pool allocator (fixed-size)

For many same-sized objects (e.g. network connections), pre-allocate slots and keep a free list. Allocation is an O(1) list pop; no fragmentation.

### Handles / generational indices

Replace raw pointers with `{ index, generation }`. The container bumps the generation when a slot is freed and reused; a stale handle's generation won't match, so dereferencing fails *detectably* instead of becoming a use-after-free. This is the standard pattern in game engines (entity IDs) and any system with many transient objects referenced across modules.

```c
typedef struct { uint32_t index; uint32_t generation; } Handle;
// lookup() compares handle.generation to slots[index].generation; mismatch => stale.
```

Handles trade a pointer dereference for an index + validity check, buying you safe, relocatable, serializable references.

---

## Best Practices

1. **Make ownership a type, not a comment.** Prefer `unique_ptr`/`Box` over raw pointers + documentation.
2. **Aim for the Rule of Zero.** Own resources through self-managing members so you write no special member functions.
3. **`unique_ptr` by default; `shared_ptr` only for genuine sharing**, and break cycles with `weak_ptr`.
4. **Model ownership as a tree.** When you reach for shared/cyclic ownership, pause — it's often a design smell.
5. **Reach for arenas/pools/handles** when lifetimes cluster or pointers churn; they fix bugs and speed at once.
6. **In Rust, keep `unsafe` tiny, audited, and wrapped in a safe API.**

---

## Edge Cases & Pitfalls

- **`shared_ptr` reference cycles leak** silently — refcounting is not garbage collection. Use `weak_ptr`.
- **Self-referential and recursive destructors**: a `unique_ptr`-based linked list of length 100k can blow the stack on destruction (recursive `~Node`); flatten teardown if depth is large.
- **`std::move` then use**: using a moved-from object is valid-but-unspecified in C++ (it's empty), and a *compile error* in Rust. Don't rely on moved-from C++ values.
- **Returning a reference/pointer to a local** (or to an arena that's been reset) is a dangling reference RAII won't catch.
- **`shared_ptr` from a raw pointer twice** creates two independent control blocks → double-free. Use `make_shared` or `enable_shared_from_this`.
- **Arenas hide leaks**: forgetting to reset an arena leaks the whole region; lifetimes must genuinely match.

---

## Apply it

1. State the system invariant that **Manual Memory Management** must protect.
2. Mark ownership, state, and failure propagation at each boundary.
3. Compare two designs under load, dependency failure, and future change.
4. Define recovery and compatibility behavior before implementation.
5. Test the riskiest assumption with a focused experiment.

## Verify your work

- The experiment supports the design with evidence, not preference.
- Failure injection shows the blast radius and recovery path.
- Compatibility checks cover old and new callers or data.
- Operational signals reveal invariant violations and recovery progress.

## Review questions

- Which invariant must remain true when Manual Memory Management fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
