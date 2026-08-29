# Tracing Garbage Collection — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Tracing Garbage Collection** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### Reachability is the definition of "alive"

The collector cannot read your mind. It does not know whether you *intend* to use an object again. It uses a simpler, mechanical rule that is provably safe:

> **An object is alive if and only if the program can reach it by following pointers from a root.**

Why is this safe? Because to *use* an object, your code must eventually hold a reference to it. References come from somewhere — a local variable, a field of another reachable object, a global. If there is no chain of pointers from any root to an object, no line of code you could possibly execute will ever touch it again. It is genuinely dead.

The flip side is important and sometimes surprising: **reachable does not mean "needed".** If you keep a pointer to a huge object in a global variable but never use it, the GC will faithfully keep it forever. That is a *memory leak in a garbage-collected language* — the collector is doing exactly what you told it.

### Roots: where tracing starts

Roots are the entry points into the object graph. They are the references the running program can touch right now without dereferencing anything:

- **The call stack:** every active function's local variables and parameters that hold references.
- **CPU registers:** values currently held in registers (a local variable may live in a register, not memory).
- **Global / static variables:** package-level variables in Go, `static` fields in Java, module globals in Python.

The collector scans all of these to build the starting set, then traces outward.

### Tracing: the graph walk

Starting from the roots, the collector visits every reachable object exactly once, following each pointer it finds:

1. Put all root-referenced objects in a "to visit" set.
2. Take one object out. Mark it. Look at every pointer field it contains.
3. For each pointer, the object it points to is reachable too — add it to "to visit" (if not already marked).
4. Repeat until "to visit" is empty.

This is just **breadth-first or depth-first search over the object graph**. When it finishes, everything marked is live; everything else is garbage.

### Mark-sweep: the simplest tracing collector

**Mark-sweep** has two phases:

1. **Mark.** Trace from roots, setting a "mark bit" on every reachable object.
2. **Sweep.** Walk the entire heap linearly. Any object whose mark bit is *not* set is garbage — reclaim it (add its space to a free list). Clear the mark bits of survivors so the next cycle starts fresh.

That is the whole algorithm. Allocation later pulls free slots off the free list. When the free list runs low, you run another GC cycle.

### Tracing vs reference counting

There is a second family of automatic memory management: **reference counting (refcount)**. Each object stores a count of how many references point to it. When the count drops to zero, the object is freed immediately. CPython uses this as its primary mechanism.

| | **Tracing GC** | **Reference Counting** |
|---|---|---|
| When work happens | In batches (GC cycles) | Continuously, on every assignment |
| Cycles (A→B→A) | Collected correctly | **Leaks** unless a backup collector exists |
| Pause behavior | Can pause the program | Spread out, but can cascade |
| Bookkeeping cost | Lower per-pointer | A count update on every reference change |

The killer weakness of plain reference counting: **reference cycles**. If A points to B and B points back to A, each has count 1 even after the program drops them, so they are never freed. Tracing GC has no such problem — if A and B are not reachable from a root, neither gets marked, so both are collected. This is the main reason tracing collectors dominate.

## Code Examples

A tiny mark-sweep, in pseudocode-flavored Go. This is deliberately naive (real collectors are far more careful), but it captures the whole idea.

```go
type Object struct {
    marked   bool
    children []*Object // pointers this object holds
}

var roots []*Object // stack vars, globals, etc.
var heap  []*Object // every object ever allocated

// MARK: trace from roots, set the mark bit on everything reachable.
func mark() {
    var worklist []*Object
    for _, r := range roots {
        worklist = append(worklist, r)
    }
    for len(worklist) > 0 {
        obj := worklist[len(worklist)-1]
        worklist = worklist[:len(worklist)-1]

        if obj == nil || obj.marked {
            continue // skip nil and already-visited (handles cycles!)
        }
        obj.marked = true
        for _, child := range obj.children {
            worklist = append(worklist, child)
        }
    }
}

// SWEEP: free the unmarked, un-mark the survivors for next time.
func sweep() {
    survivors := heap[:0]
    for _, obj := range heap {
        if obj.marked {
            obj.marked = false   // reset for the next cycle
            survivors = append(survivors, obj)
        } else {
            free(obj)            // reclaim: real GC adds to a free list
        }
    }
    heap = survivors
}

func collect() {
    mark()
    sweep()
}
```

Notice the `obj.marked` check in `mark()`: it is what makes cycles safe. If A and B point to each other, the second time we reach an already-marked object we just stop. Reference counting cannot do this for free.

## Best Practices

- **Drop references you no longer need.** Set a long-lived field to `nil`/`null` when done with a big object, especially in caches, slices, and maps. The GC can only reclaim what becomes unreachable.
- **Beware accidental retention.** A slice that still backs a giant array, a closure that captures a big struct, or a map that never deletes entries can keep memory alive forever.
- **Do not fight the GC early.** Write clear code first. Profiling, tuning, and worrying about pauses come later (and at higher tiers).
- **Understand "reachable ≠ needed".** Most "GC leaks" are really *you* holding a reference you forgot about.

## Edge Cases & Pitfalls

- **The forgotten global.** Anything reachable from a global lives forever. Unbounded global maps/caches are the #1 cause of leaks in GC languages.
- **Cycles only matter for refcounting.** New learners often worry tracing GC can't handle `A↔B`. It can — that is one of its strengths.
- **Finalizers are not destructors.** Some languages let you run code when an object is collected, but *when* (or whether) that happens is unpredictable. Never rely on a finalizer to release files, locks, or sockets.
- **Memory is not freed instantly.** An object becomes collectable the moment it is unreachable, but it is not reclaimed until the next GC cycle decides to run.

---

## Apply it

1. Choose one small, known input for **Tracing Garbage Collection**.
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

- What problem does Tracing Garbage Collection solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
