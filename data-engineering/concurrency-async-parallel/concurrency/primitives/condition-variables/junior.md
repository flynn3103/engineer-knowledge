# Condition Variables - Junior

A condition variable waits for shared state to change without burning CPU. It always works with a mutex and a predicate.

```mermaid
sequenceDiagram
    participant C as Consumer
    participant Q as Queue plus mutex
    C->>Q: lock; queue empty
    C->>Q: wait: unlock and sleep atomically
    Q-->>C: producer signals
    C->>Q: relock; check again
```

Use `while queue_is_empty: condition.wait()`, never `if`. Wakeups can be spurious, or another consumer can take the item first. Change the predicate while holding the same mutex, then notify.

Continue to [`middle.md`](middle.md).

## Test yourself

1. Why must wait use a loop?
2. What does wait do atomically?
3. Which mutex protects the predicate?
