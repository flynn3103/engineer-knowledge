# Tracing Garbage Collection — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Tracing Garbage Collection** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### Mark-Sweep and Fragmentation

Mark-sweep marks reachable objects, then sweeps the heap freeing the unmarked into a **free list**. Cost is `O(live)` to mark plus `O(heap)` to sweep. It is **non-moving**: surviving objects never change address.

Non-moving is a feature (pointers stay valid, interop with C is easy) and a curse: over time the heap becomes a Swiss cheese of free gaps between survivors. This is **fragmentation**. You may have 100 MB free but be unable to allocate a 1 MB contiguous buffer because the largest gap is 512 KB. Allocation also slows down, because the allocator must search the free list for a gap that fits, rather than just bumping a pointer.

Mitigations include **segregated free lists** (separate lists per size class, so allocation is a quick pop from the right bucket — this is how Go and many `malloc`s work) and periodic compaction.

### Mark-Compact

Mark-compact marks like mark-sweep, but instead of sweeping into a free list it **slides all live objects to one end of the heap**, squeezing out the gaps. After compaction the free space is one contiguous block, so subsequent allocation can be a fast bump.

The hard part is **updating pointers**: when an object moves from address X to address Y, every reference to X anywhere in the heap (and in roots) must be rewritten to Y. A typical scheme (Lisp 2 / sliding compaction):

1. Mark live objects.
2. Compute each live object's new address (one pass).
3. Update every pointer to its target's new address.
4. Move the objects.

Mark-compact eliminates fragmentation and enables bump allocation, at the cost of extra passes over the live set and the complexity of moving objects. HotSpot's old-generation collectors and the full-GC fallback use compaction.

### Copying / Semispace and Cheney's Algorithm

Copying collection splits the heap into two equal halves: **from-space** and **to-space**. You allocate only in from-space (by bumping a pointer). When it fills, you **copy every live object into to-space**, compacting as you go, then swap the roles of the two halves. Everything not copied was garbage — there is no separate sweep, and no free list. Reclaiming dead objects costs *nothing*: you simply abandon from-space.

**Cheney's algorithm** does this iteratively with no recursion and no extra stack, using to-space itself as the work queue:

1. Copy all root-referenced objects to to-space. Leave a **forwarding pointer** in each old copy.
2. Keep a `scan` pointer at the start of to-space and a `free` pointer at the end of copied data.
3. Scan the object at `scan`. For each pointer it holds: if the target is already copied, follow its forwarding pointer; otherwise copy it (advancing `free`) and leave a forwarding pointer.
4. Advance `scan`. Repeat until `scan` catches `free`.

The region between `scan` and `free` is exactly the BFS frontier — the grey set, in tri-color terms.

**Trade-off:** copying is gorgeous — `O(live)` total (it never touches dead objects), bump allocation, automatic compaction, cache-friendly because survivors end up adjacent. The price is brutal: **half your heap is reserved** at all times. That is why copying is rarely used for the *whole* heap, but is the perfect collector for a *small, mostly-dead* region — which is exactly the young generation.

### Generational GC

The **weak generational hypothesis**: *most objects die young.* Empirically, in most workloads the overwhelming majority of allocations become garbage almost immediately (temporaries, intermediate values, request-scoped data), while the few that survive tend to live a long time.

Generational collectors exploit this by splitting the heap by age:

- **Young generation (nursery / eden):** where new objects are allocated. Small. Collected often, by a fast **minor GC**. Because almost everything here is dead, a copying collector shines: it only touches the rare survivors.
- **Old generation (tenured):** objects that have survived several minor GCs are **promoted** (tenured) here. Collected rarely, by a more expensive **major GC** (often mark-compact or concurrent mark-sweep).

The win is enormous: most GC work concentrates on the young generation, which is small and mostly garbage, so each collection is fast and cheap. The old generation — large, mostly live, expensive to collect — is touched only occasionally.

### Write Barriers and Remembered Sets

Generational GC has a correctness problem. A minor GC wants to collect *only* the young generation, treating roots as its starting points. But an **old object may point to a young object** (e.g., you stored a freshly-made item into a long-lived list). If the minor GC ignores the old generation, it will wrongly think that young object is garbage.

Scanning the entire old generation on every minor GC would destroy the whole benefit. The fix: track old→young pointers as they are created and treat them as extra roots.

- A **write barrier** is code the compiler injects on every pointer-store (`obj.field = value`). When it detects an old object being made to point at a young object, it records that location in the **remembered set** (often implemented as a *card table*: the heap is divided into fixed-size cards, and writing into a card marks it "dirty").
- At minor-GC time, the collector scans roots **plus** the remembered set (the dirty cards), so it never misses an old→young reference.

The write barrier costs a few instructions on every pointer write — a throughput tax paid to keep minor GCs cheap. This same machinery (barriers) reappears, in a different role, in concurrent collection.

### The Tri-Color Abstraction

To reason about *concurrent* and *incremental* tracing — where the program (the **mutator**) runs *while* the collector traces — Dijkstra's **tri-color abstraction** colors every object:

- **White:** not yet visited. At the end of tracing, white = garbage.
- **Grey:** visited (reachable), but its outgoing pointers have **not yet** been scanned. The work frontier.
- **Black:** visited *and* fully scanned (all its children are at least grey).

Tracing = repeatedly pick a grey object, scan it (its white children become grey), and turn it black. When no grey objects remain, every white object is unreachable and can be freed.

The danger in concurrent collection: while the collector traces, the mutator is rewiring pointers. It can hide a live object from the collector. This happens precisely when **both** of these occur:

1. The mutator stores a pointer to a **white** object into a **black** object, and
2. It then deletes every path to that white object that went through a **grey** object.

Now the white object is reachable (via the black one) but the collector will never revisit black objects, so it stays white and gets wrongly collected.

The defenses are stated as invariants:

- **Strong tri-color invariant:** no black object points to a white object (directly).
- **Weak tri-color invariant:** a white object pointed to by a black object is also reachable from some grey object (so it will still be found).

Collectors maintain one of these with a **write barrier**:

- **Insertion (Dijkstra) barrier / incremental-update:** when the mutator writes a pointer into a black object, shade the *target* grey. Preserves the strong invariant. Go uses a hybrid of this.
- **Deletion (Yuasa) barrier / SATB ("snapshot-at-the-beginning"):** when a pointer is *overwritten*, shade the *old* target grey, preserving the snapshot of the graph as it existed when GC started. Used by G1 and Shenandoah.

This is the single most important abstraction in modern GC. Every concurrent collector you will read about — Go's, ZGC, Shenandoah, G1 — is "tri-color marking plus a specific barrier".

## Code Examples

Cheney's copying collector, core loop:

```go
// to-space is one contiguous buffer; scan and free are indices into it.
var toSpace []byte
var scan, free int

// copy moves an object into to-space (if not already moved) and returns
// its new address, leaving a forwarding pointer behind.
func copyObj(o *Object) *Object {
    if o.forwarded != nil {
        return o.forwarded // already copied — share the new copy
    }
    newAddr := alloc(&free, sizeOf(o)) // bump 'free'
    memmove(newAddr, o)
    o.forwarded = newAddr              // leave a trail
    return newAddr
}

func cheney(roots []*Object) {
    scan, free = 0, 0
    for i := range roots {
        roots[i] = copyObj(roots[i]) // evacuate roots first
    }
    for scan < free {                 // scan == free means grey set empty
        obj := objectAt(&toSpace, scan)
        for i, child := range obj.children {
            obj.children[i] = copyObj(child) // forward each pointer
        }
        scan += sizeOf(obj)
    }
    // from-space is now entirely garbage: just reuse it next cycle.
}
```

A generational write barrier (conceptual):

```go
// Inserted by the compiler on every `slot = ptr`.
func writePointer(slot **Object, ptr *Object) {
    *slot = ptr
    if isOld(slot) && isYoung(ptr) {
        rememberedSet.markCard(slot) // old -> young: record it
    }
}
```

## Coding Patterns

- **Allocate temporaries freely, retain survivors deliberately.** Generational GC makes short-lived allocations cheap; the expensive thing is long-lived garbage you forgot to release.
- **Pool only when measured.** Object pools defeat the GC's strength (cheap young collection) and add complexity. Reach for them only after profiling shows allocation pressure.
- **Avoid mid-life crises.** Objects that live just long enough to be promoted, then die, are the worst case: they cost a promotion *and* a major-GC collection. Either keep them short-lived or make them truly long-lived.

## Best Practices

- **Reduce old→young pointers where it's free to do so.** Each one costs a remembered-set entry and write-barrier work, though you should rarely contort code for this.
- **Keep allocations small and local.** Survivors that end up adjacent (via copying/compaction) improve cache locality for free.
- **Know your collector's family** (moving vs non-moving, generational or not) before reasoning about its behavior — the algorithm dictates the trade-offs you'll hit.

## Edge Cases & Pitfalls

- **Promotion of still-live temporaries** under load: a burst of allocations can push young objects into the old generation prematurely ("promotion failure" / premature tenuring), inflating major-GC cost.
- **Write-barrier cost in pointer-heavy code:** tight loops that mutate many pointers pay the barrier on every write.
- **Fragmentation in non-moving collectors:** long-running services on mark-sweep heaps can suffer fragmentation that looks like a slow memory leak.
- **Conservative roots and moving collectors don't mix:** if you can't precisely identify pointers, you can't safely move objects (you'd have to rewrite a value that might not actually be a pointer). This is why moving GCs require *precise* root scanning.

---

## Apply it

1. Find a real component where **Tracing Garbage Collection** affects an interface or dependency.
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

- Which boundary is most affected by Tracing Garbage Collection?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
