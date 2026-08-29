# Reference Counting — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Reference Counting** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### The one rule

Every counted object stores an extra integer next to its data: the reference count. Three events change it:

1. **A new reference is created → increment.** Copy a variable, pass the object to a function, store it in a list — count goes up by 1.
2. **A reference goes away → decrement.** A variable goes out of scope, gets overwritten, or is removed from a collection — count goes down by 1.
3. **Count reaches zero → free.** The last reference is gone, so the object can never be touched again. Its memory is reclaimed right away.

```
obj = make_object()      # count = 1   (one reference: obj)
other = obj              # count = 2   (obj and other)
del other                # count = 1
del obj                  # count = 0  → freed immediately
```

### Promptness is the headline feature

Notice *when* the object was freed: the instant the last reference disappeared. Not "eventually," not "at the next garbage-collection pause" — **right now, deterministically.** This is reference counting's biggest selling point. The moment you stop using a file handle, a network socket, or a chunk of memory, it can be released. We will see why this matters a lot to some languages.

### Where the count lives

There are two common places to store the count:

- **Inline** — the integer sits right inside the object's memory block, next to its fields. This is what CPython and Swift do. It is cache-friendly: touching the object and touching the count are the same cache line.
- **Side table** — the count lives in a separate structure, looked up by the object's address. Less common, used when you cannot modify the object's layout (some Swift values use a side table for weak references).

For now, just picture an extra hidden field on every object holding the count.

### The fatal flaw: cycles

Reference counting has one notorious weakness. Suppose object A holds a reference to B, and B holds a reference back to A:

```
A → B
A ← B
```

Now drop every *external* reference to both. A still has a reference from B (count = 1), and B still has a reference from A (count = 1). Neither count ever reaches zero. **They keep each other alive forever, even though nothing in your program can reach them.** That is a leak.

This is not a corner case — it happens constantly: a parent node pointing to a child that points back at its parent, a cache that holds objects which hold the cache, two callbacks that capture each other. Every reference-counted system must deal with cycles somehow. We introduce the standard fixes (weak references, cycle collectors) in the next tiers, but you should leave this page knowing that **plain reference counting cannot reclaim cycles on its own.**

## Code Examples

These examples are conceptual — they show the *mechanism*, not production code. Real languages do all of this for you automatically.

### A tiny reference-counted box (pseudocode)

```
class CountedObject:
    data
    count = 0

def retain(obj):
    obj.count += 1
    return obj

def release(obj):
    obj.count -= 1
    if obj.count == 0:
        free(obj)        # nobody points at it anymore

# usage
x = CountedObject(); retain(x)   # count = 1
y = retain(x)                    # count = 2  (y and x share it)
release(y)                       # count = 1
release(x)                       # count = 0  → freed
```

### Python — you can watch the count

CPython exposes the count via `sys.getrefcount`. (It reports one extra because the argument itself is a temporary reference.)

```python
import sys

a = []                       # one reference: a
print(sys.getrefcount(a))    # 2  (a + the temporary argument)

b = a                        # second reference
print(sys.getrefcount(a))    # 3

del b                        # drop one reference
print(sys.getrefcount(a))    # 2
```

You never call increment/decrement yourself in Python — the interpreter does it on every assignment, function call, and `del`.

### Seeing a cycle leak (conceptual)

```python
class Node:
    def __init__(self):
        self.other = None

a = Node()
b = Node()
a.other = b      # a → b
b.other = a      # b → a   (cycle!)

del a
del b            # external references gone, but a and b still
                 # reference each other: pure refcounting can't free them
```

In real CPython a separate cycle collector eventually cleans this up — but plain reference counting alone never would.

## Best Practices

- **Let the language do the counting.** In Python, Swift, Rust, and modern C++ you almost never touch the count by hand. Use the provided smart pointers / value types.
- **Watch for cycles in parent/child and observer relationships.** If two objects naturally point at each other, that's a cycle waiting to leak. (The fix — weak references — comes in the next tier.)
- **Balance retains and releases.** In low-level code (manual C, Objective-C MRC), every increment needs a matching decrement.
- **Don't try to "optimize" by caching references everywhere.** Each stored reference keeps the object alive longer than you might expect.

## Edge Cases & Pitfalls

- **The cycle leak.** Already covered — the headline pitfall. Objects pointing at each other never reach zero.
- **Forgetting to release (in manual systems).** Leaks the object. The count never reaches zero because a decrement is missing.
- **Releasing too many times (in manual systems).** The count hits zero while the object is still in use, the memory is freed, and a later access reads freed memory — a crash or corruption.
- **Surprising lifetimes.** An object can live much longer than you expect if some forgotten list or closure still holds a reference. "Why isn't this getting cleaned up?" is very often "something still points at it."
- **The count itself is invisible.** You can't see it without tools like `sys.getrefcount`, so reasoning about lifetimes is about reasoning about *who points at what.*

---

## Apply it

1. Choose one small, known input for **Reference Counting**.
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

- What problem does Reference Counting solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
