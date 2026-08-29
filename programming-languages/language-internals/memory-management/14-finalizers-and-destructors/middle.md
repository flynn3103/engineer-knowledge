# Finalizers & Destructors — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Finalizers & Destructors** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### The deterministic side: cleanup driven by control flow

Deterministic cleanup hooks into **control flow**, not the GC.

- **C++ destructors** run during **stack unwinding**. When a block exits, automatic objects are destroyed in **reverse construction order**. This happens on normal exit *and* while an exception unwinds — the foundation of exception safety.
- **Rust `Drop`** runs when a value goes out of scope. The compiler inserts the `drop` calls. **Drop order is reverse declaration order** within a scope; struct fields drop in declaration order. Because moves can change whether a variable still owns a value, the compiler sometimes needs **drop flags** — runtime booleans tracking whether a drop is still required.
- **Go `defer`** pushes a deferred call onto a per-function stack; deferred calls run in **LIFO order** when the function returns (including on `panic`).
- **Python `with`** / **C# `using`** are syntactic contracts: `__enter__`/`__exit__` and `IDisposable.Dispose()` are called at known points, even on exceptions.

The unifying property: you can read the source and identify the exact instant cleanup happens.

### The non-deterministic side: cleanup driven by the GC

A finalizer is metadata attached to an object. When the GC discovers the object is otherwise unreachable, instead of freeing it immediately, it:

1. Notices the object has a finalizer that hasn't run.
2. **Adds it to a finalizer queue** (the object is now temporarily kept alive).
3. A **finalizer thread** later dequeues it and runs the finalizer.
4. On a *subsequent* GC cycle, if the object is still unreachable, its memory is finally reclaimed.

Two consequences fall out of this mechanism immediately:

- **At least one extra GC cycle of delay** (often more). The object lives longer than a non-finalizable one.
- **A single shared thread** (Java's finalizer thread; Go runs finalizers in a goroutine). If one finalizer blocks, the whole queue backs up — the **finalizer thread stall**.

### Resurrection

During step 3, the finalizer runs arbitrary code — including storing `this`/the object into a global. That makes the object **reachable again**, so the GC must *not* collect it. The object is "resurrected." In most runtimes the finalizer will **not run a second time** even if the object dies again later, so a resurrected-then-re-abandoned object may leak its finalization entirely. Resurrection is almost always a bug.

### Ordering among finalizers

The GC does **not** order finalizers by reference relationships. If object A's finalizer touches object B, and both are being collected, B might be finalized (or even freed) first. **Never have one finalizer depend on another finalizable object still being valid.** With reference cycles, the order is fully undefined.

---

## Code Examples

### Rust — `Drop`, drop order, and `ManuallyDrop`

```rust
struct Noisy(&'static str);
impl Drop for Noisy {
    fn drop(&mut self) {
        println!("dropping {}", self.0);
    }
}

fn main() {
    let _a = Noisy("a");   // declared first
    let _b = Noisy("b");   // declared second
    // At scope end, drop runs in REVERSE: "dropping b", then "dropping a".

    // You cannot call _a.drop() explicitly; the compiler forbids it.
    // To drop early, use std::mem::drop:
    let c = Noisy("c");
    drop(c);               // prints "dropping c" right here, deterministically

    // ManuallyDrop suppresses automatic Drop:
    let mut m = std::mem::ManuallyDrop::new(Noisy("m"));
    // m will NOT be dropped automatically; you must:
    unsafe { std::mem::ManuallyDrop::drop(&mut m); }
}
```

Key facts: drop order is reverse declaration; you can't call `drop(&mut self)` directly (you use `std::mem::drop`, which just *moves* the value and lets it fall out of scope); `ManuallyDrop` opts out of the automatic call.

### Go — `defer` (deterministic) vs `SetFinalizer` (non-deterministic)

```go
func process(path string) error {
    f, err := os.Open(path)
    if err != nil {
        return err
    }
    defer f.Close()        // LIFO; runs on every return path, including panic
    // ... use f ...
    return nil
}

// A finalizer as a leak-detector backstop only:
func newBuffer() *Buffer {
    b := &Buffer{handle: cAllocate()}
    runtime.SetFinalizer(b, func(b *Buffer) {
        // Runs in a goroutine, after >= 1 GC cycle, MAYBE before exit.
        cFree(b.handle)    // native memory the GC can't see
    })
    return b
}
```

`defer` is the real cleanup. `SetFinalizer` is the backstop for native memory; it is not guaranteed to run before the program exits.

### Python — `with` vs `__del__`

```python
# Deterministic: __exit__ runs at the end of the block, even on exception.
class Conn:
    def __enter__(self):
        self.sock = connect()
        return self
    def __exit__(self, exc_type, exc, tb):
        self.sock.close()       # known point

with Conn() as c:
    use(c)

# Non-deterministic: __del__ runs when refcount hits zero — usually prompt
# under CPython, but NOT guaranteed (cycles, gc disabled, shutdown).
class Leaky:
    def __del__(self):
        self.sock.close()       # may be late, may be skipped at shutdown
```

CPython's reference counting often calls `__del__` promptly, which *lulls* you into trusting it — but cycles, a different interpreter, or shutdown break that.

---

## Coding Patterns

### Pattern: explicit close, finalizer as backstop

The canonical "two-tier" shape (shown here in Go-style pseudocode):

```go
type Resource struct {
    handle uintptr
    closed bool
}

func (r *Resource) Close() error {
    if r.closed {
        return nil          // idempotent
    }
    r.closed = true
    return release(r.handle)
}

// Backstop: if the caller forgot Close(), the GC eventually releases native memory.
// (In Go 1.24+, prefer runtime.AddCleanup over SetFinalizer — see senior tier.)
```

Callers use `defer r.Close()`. The finalizer only fires when someone *forgot*, and it should log that mistake.

### Pattern: idempotent close

Both an explicit close and a finalizer can run. Guard with a `closed` flag (or atomic) so the second call is a no-op. Without this, double-free crashes and "already closed" errors appear under load.

---

## Best Practices

1. **Wire cleanup to control flow**, not to the GC, for anything that matters.
2. **Know your drop order** (reverse declaration in Rust/C++) when one resource depends on another — declare the dependency *first* so it drops *last*.
3. **Make close idempotent** so explicit-close + backstop-finalizer coexist safely.
4. **Never have one finalizer depend on another finalizable object.**
5. **Never resurrect** — don't store `self`/`this` somewhere live from inside a finalizer.
6. **Don't block in a finalizer** — you'll stall the shared finalizer thread.

---

## Edge Cases & Pitfalls

- **Conditional moves in Rust** create drop flags; a value moved in one branch must not be dropped in the merge — the compiler handles it, but it explains why drops sometimes seem to "disappear."
- **`defer` in a loop** stacks up until the function returns, not each iteration — can hold resources far too long. Wrap the body in a function or close explicitly.
- **CPython prompt `__del__` is a trap**: works in tests, fails on cycles or alternative runtimes.
- **Finalizer thread starvation**: a slow or blocking finalizer halts every other object's finalization behind it in the queue.
- **Shutdown skips finalizers** in most runtimes; don't "flush on exit" from a finalizer.

---

## Apply it

1. Find a real component where **Finalizers & Destructors** affects an interface or dependency.
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

- Which boundary is most affected by Finalizers & Destructors?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
