# Finalizers & Destructors — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Finalizers & Destructors** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### Memory is cleaned up for you; resources are not

In a garbage-collected language, you rarely worry about *memory* — when an object becomes unreachable, the GC reclaims its memory. The trap is assuming the GC also closes your files and sockets. It does not, at least not on time. The GC's job is to manage memory pressure, so it runs when *memory* is tight — and you can run out of file handles long before you run out of memory.

### Deterministic cleanup: you know exactly when

```
{
    open a file
    ... use it ...
}   // <- the moment we reach this brace, the file is closed
```

You can read the code and put your finger on the exact line where cleanup happens. C++ destructors, Rust's `Drop`, Go's `defer`, Python's `with`, and C#'s `using` all give you this. The release is tied to *control flow*, not to memory pressure.

### Non-deterministic cleanup: it happens "later, maybe"

```
make an object that has a finalizer
... stop using it ...
// the finalizer might run in 5 ms, in 5 minutes, or never before the program exits
```

A finalizer is attached to the object and the GC *might* call it before reclaiming the object's memory. The keyword is *might*. There is no promise about **when**, **which thread**, or even **whether** it runs at all (programs that exit can skip finalizers entirely).

### Why finalizers exist at all

If they're so unreliable, why do they exist? Two honest reasons:

1. **A safety net.** If a programmer forgets to close something, a finalizer can catch the leak eventually — better late than never, and a great place to log "hey, you forgot to close this."
2. **Native memory the GC can't see.** Some objects hold memory allocated outside the GC's world (e.g., a C library buffer). A finalizer is a way to make sure that foreign memory eventually gets freed.

Neither reason makes a finalizer a good *primary* cleanup strategy.

---

## Code Examples

### Deterministic — Python `with` (the good way)

```python
with open("data.txt") as f:        # acquire
    contents = f.read()
# <- file is GUARANTEED closed here, even if read() raised an exception
```

The `with` block closes the file at a known point. This is deterministic cleanup.

### Non-deterministic — Python `__del__` (the risky way)

```python
class FileWrapper:
    def __init__(self, path):
        self.f = open(path)
    def __del__(self):             # a finalizer
        self.f.close()             # runs "whenever", maybe at shutdown, maybe never

w = FileWrapper("data.txt")
# w.f stays open until the garbage collector decides to clean up w.
```

This *looks* convenient but the close happens at an unpredictable time. Under heavy load you can exhaust file handles waiting for it.

### Deterministic — Go `defer`

```go
f, err := os.Open("data.txt")
if err != nil {
    return err
}
defer f.Close()   // <- runs when this function returns, guaranteed, in order
// ... use f ...
```

`defer` schedules `f.Close()` to run at function exit — a known point.

### Deterministic — C++ destructor (RAII)

```cpp
{
    std::ifstream file("data.txt");   // constructor opens
    // ... use file ...
}   // <- destructor runs here, closes the file, automatically
```

The file closes at the closing brace, every time, including when an exception unwinds the stack.

---

## Best Practices

1. **Prefer the language's deterministic tool first:** `with` (Python), `using` (C#), `defer` (Go), destructors/RAII (C++), `Drop` (Rust).
2. **Never put scarce-resource release in a finalizer as the only path.** Files, sockets, and connections will run out.
3. **Pair acquire and release in the same scope** so the lifetime is visible.
4. **If you must offer a finalizer, also offer an explicit close** and document that close is the real mechanism.
5. **Don't throw exceptions from cleanup code** — it's hard to handle and often silently ignored.

---

## Edge Cases & Pitfalls

- **"It worked on my machine."** A finalizer may run quickly under light load (so your tests pass) and then far too late under production load (so you leak handles). Light testing hides the bug.
- **Program exit skips finalizers.** Many runtimes do *not* run pending finalizers when the process exits. Anything you "planned" to flush at the end may never flush.
- **Order is not guaranteed.** If two finalizable objects refer to each other, you cannot assume one runs before the other; the one you depend on might already be gone.
- **Exceptions in cleanup vanish.** Errors thrown inside finalizers are usually swallowed, so failures go unnoticed.
- **Double-close.** If both a finalizer and an explicit close run, make sure closing twice is safe (idempotent), or you'll get crashes or errors.

---

## Apply it

1. Choose one small, known input for **Finalizers & Destructors**.
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

- What problem does Finalizers & Destructors solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
