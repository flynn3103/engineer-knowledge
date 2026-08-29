# Weak References — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Weak References** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### A weak reference can become empty at any time

This is the defining behavior. A strong reference, once set, always gives you the same object until you reassign it. A weak reference can *spontaneously* stop pointing at anything, because the GC reclaimed the object behind your back. Your code must therefore always handle two outcomes when reading a weak reference:

1. The object is still alive → you get it.
2. The object was collected → you get an explicit "nothing."

There is no third option, and you cannot prevent outcome 2 by trying harder. If you need the object to survive, hold a *strong* reference to it.

### Weak references do not extend lifetime — they observe it

Think of a weak reference as a *one-way mirror onto the GC's bookkeeping*. It lets you watch whether an object is still alive without participating in keeping it alive. You are a spectator, not a stakeholder.

### "Only weakly reachable" is the trigger

An object is collected when the *strong* references run out, even if many weak references still point at it. One strong reference anywhere is enough to keep it. So weak references matter only after every strong reference is gone.

```
Root ──strong──▶ Object   ◀──weak── WeakRef A
                          ◀──weak── WeakRef B

(Object is alive: the strong chain from Root protects it.)

Root ──╳ (strong link removed)      Object  ◀──weak── WeakRef A
                                            ◀──weak── WeakRef B

(Object is now only weakly reachable → GC may reclaim it →
 WeakRef A and WeakRef B both become "cleared".)
```

## Code Examples

The exact API differs per language, but the shape is always the same: wrap the object, then *check* before using.

**Python** (`weakref`):
```python
import weakref

class Cache:
    pass

obj = Cache()                 # strong reference in `obj`
ref = weakref.ref(obj)        # weak reference, does NOT keep obj alive

print(ref())                  # <Cache object ...>  — still alive
del obj                       # drop the only strong reference
import gc; gc.collect()       # encourage collection
print(ref())                  # None — the object is gone
```

**Java** (`java.lang.ref.WeakReference`):
```java
import java.lang.ref.WeakReference;

Object strong = new Object();
WeakReference<Object> weak = new WeakReference<>(strong);

System.out.println(weak.get()); // the object — still alive
strong = null;                  // drop the only strong reference
System.gc();                    // suggest a GC
System.out.println(weak.get()); // likely null — collected
```

**JavaScript** (`WeakRef`):
```javascript
let obj = { name: "node" };
const ref = new WeakRef(obj);

console.log(ref.deref()); // { name: "node" } — alive
obj = null;               // drop the only strong reference
// ...after a future GC...
console.log(ref.deref()); // undefined — collected
```

Notice the universal pattern: **never assume the object is there.** Always call the dereference function (`ref()`, `.get()`, `.deref()`) and check the result.

## Best Practices

- **Always check the result of a dereference.** Treat "gone" as a normal, expected outcome, not an error.
- **Keep a strong reference for as long as you actually need the object.** Dereference into a local strong variable and use *that*, so it cannot vanish mid-operation.
- **Don't reach for weak references by default.** Use them only when the leak/lifetime problem is real. A strong reference is simpler and almost always correct.

## Edge Cases & Pitfalls

- **The "use-after-check" race.** You check `ref()` is non-null, then later call `ref()` again expecting the same object — but it was collected in between. Fix: dereference *once* into a strong local and use that local.

  ```python
  obj = ref()              # one dereference
  if obj is not None:
      use(obj)             # `obj` is a strong ref now; safe to use
  ```

- **Forcing a GC to "test" weak refs is unreliable.** `gc.collect()` / `System.gc()` are *hints*. Timing of clearing is not something to depend on in production logic.
- **A lingering strong reference defeats the whole purpose.** If a weak referent "never gets collected," look for a strong reference you forgot about — a closure, a list, a static field.

---

## Apply it

1. Choose one small, known input for **Weak References**.
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

- What problem does Weak References solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
