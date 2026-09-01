# Mutex - Junior

A mutex allows one thread to update protected state at a time. Always release it, including on errors.

```mermaid
sequenceDiagram
    participant A as Loader A
    participant M as Mutex
    participant B as Loader B
    A->>M: lock
    B->>M: lock and wait
    A->>M: update batch; unlock
    M-->>B: acquired
```

Use `with lock:` in Python, `defer mu.Unlock()` in Go, or a guard in Rust/C++. Keep parsing and warehouse I/O outside. Protect all reads and writes that participate in the same invariant.

Continue to [`middle.md`](middle.md).

## Test yourself

1. What state does the mutex protect?
2. Why should I/O stay outside the critical section?
3. How does a guard prevent forgotten unlocks?
