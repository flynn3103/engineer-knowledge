# Write-Behind — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Why does the caller get a success response before the database write has
> actually happened?

---

## The flow

```mermaid
flowchart LR
    App[App write] --> Cache["Cache accepts write,\nacks IMMEDIATELY"]
    Cache -.buffers in memory\nor a local queue.-> Buffer[Pending write buffer]
    Buffer -.flushed later,\nasynchronously.-> DB[(Database)]
```

```python
def update_counter(key, delta):
    cache.increment(key, delta)      # returns instantly
    write_behind_queue.enqueue(key)  # scheduled for later flush
    return "ok"                       # caller already told it succeeded
```

Unlike write-through (`../02-write-through/junior.md`), where the caller
waits for **both** the cache and database writes to complete, write-behind
only waits for the **cache** write, then returns. The database write happens
later, on its own schedule, in the background — decoupled entirely from the
caller's request/response cycle.

> 🎓 **Takeaway:** write-behind trades "the caller knows the data is durably
> saved" for "the caller gets an instant response, and durability catches up
> shortly after." This is a real trade-off, not a free performance win —
> `senior.md` covers exactly what can go wrong in the gap.

## Test yourself

1. What does the caller actually know is true, and not true, the moment
   `update_counter` returns "ok"?
2. Compare the caller's wait time here versus write-through's — which
   completes its response faster, and why?
3. Where does the "pending write buffer" live, and what happens to its
   contents if that process crashes before flushing?

Continue to [`middle.md`](middle.md).
