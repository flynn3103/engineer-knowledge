# Object Pinning & Movable Heaps — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Object Pinning & Movable Heaps** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### Why a moving heap is worth defending

Compaction buys two things: **zero fragmentation** and **bump allocation**. When live objects are packed contiguously, free memory is one large block, and allocating is `top += size`. This is dramatically faster than a free-list walk and is one reason managed allocation can outpace `malloc`. Generational collectors lean on this hard: gen0 is collected constantly, survivors are *copied* (moved) to gen1, and so on. Moving is not incidental — it is the engine.

So when you pin, you are inserting a fixed obstacle into a system whose performance *depends* on freely rearranging objects.

### A pinned object is an immovable island

During compaction, the collector slides live objects toward one end. A pinned object cannot slide. The collector must leave it exactly where it is and route the compaction *around* it. The result is a **hole**: the space objects would have occupied had they been allowed to move into the pinned object's location. Pin several objects scattered across gen0 and you get Swiss cheese — many small holes that can't be coalesced. That is **pinning-induced fragmentation**, and it is the central performance cost.

### Pinning lives at war with generational collection

Pinning is worst in the **young generation**, because gen0 is collected frequently and is meant to be cheap. A pin there forces the collector to special-case the nursery on every collection. This is the motivation behind .NET's Pinned Object Heap: move pinned objects *out* of the compacting generations entirely so the nursery stays clean.

## Mechanisms by Runtime

### .NET / CLR

.NET's GC is generational and **compacting**, so pinning is a first-class, frequently-used concept. There are several APIs, escalating in lifetime:

1. **`fixed` statement** — scoped, stack-rooted pinning for the duration of a block. The pin is recorded cheaply on the stack; the GC sees it during a collection that overlaps the block. Lowest overhead, shortest lifetime. Use this by default.

2. **`GCHandle.Alloc(obj, GCHandleType.Pinned)`** — a *heap-rooted* pin with an explicit lifetime. You get a `GCHandle`, call `AddrOfPinnedObject()` for the stable address, and must `Free()` it later. Use when the pin must outlive a single stack frame (e.g., the address is stored and used across multiple managed calls). More dangerous: forgetting `Free()` leaks the pin.

3. **`Memory<T>.Pin()` → `MemoryHandle`** — the modern, abstraction-friendly path. `MemoryHandle` is `IDisposable`; disposing it unpins. Works uniformly over arrays, native memory, and custom `MemoryManager<T>`.

4. **Pinned Object Heap (POH), .NET 5+** — allocate inherently-pinned objects via `GC.AllocateArray<T>(length, pinned: true)`. These live on a separate, non-compacting heap. Ideal for **long-lived** pinned buffers (e.g., a reused DMA/IO buffer) because they never fragment the normal generations.

### JVM / JNI

The JVM standard does **not** expose object pinning to Java code; it surfaces in **JNI** (native interop):

- **`GetPrimitiveArrayCritical` / `ReleasePrimitiveArrayCritical`** — requests a direct pointer to a primitive array's storage. Inside the **critical region** you must obey strict rules: do not block, do not make other JNI calls, do not allocate on the Java heap, keep it short. The JVM may **disable GC** for the duration (a heavyweight "stop everything" form of pinning) or it may copy — it is implementation-defined.

- **`Get<Type>ArrayElements` / `Release...`** — returns a pointer that *may be a pin or may be a copy* (`isCopy` out-parameter tells you). If copied, your writes only take effect on `Release` with mode `0` or `JNI_COMMIT`. This ambiguity is a defining JNI gotcha.

- **`DirectByteBuffer`** — the copy-free, *pin-free* alternative. Its storage is **off the Java heap** (native memory), so its address is permanently stable and no pinning is needed. Preferred for long-lived native sharing.

### Go / cgo

Go's heap is historically **non-moving for heap objects**, which made cgo simpler — a heap object's address was stable. But Go **moves goroutine stacks**: when a stack grows, it is copied to a larger region and all pointers into it are rewritten. So the real hazard is pointers to *stack-allocated* data, and the rule that **C must not retain a Go pointer after the call returns** (the GC may move/free it later, and the pointer-passing rules forbid C holding Go pointers).

- **cgo pointer-passing rules**: Go memory passed to C must not itself *contain* Go pointers (unless pinned), and C must not keep copies of Go pointers past the call. Violations are caught at runtime by `cgocheck`.
- **`runtime.Pinner` (Go 1.21)**: the official API. `var p runtime.Pinner; p.Pin(obj)` keeps `obj` (and lets you legally pass Go memory containing Go pointers to C); `p.Unpin()` releases all pins on that Pinner. This finally gives Go a clean, supported pinning primitive instead of `unsafe` hacks.

### Rust — a different "pinning" (sidebar)

Rust's `Pin<P>` is **not** GC pinning. Rust has no moving GC. `Pin` is a **type-system guarantee** that a value will not be *moved in memory by safe code* after being pinned — needed for **self-referential types**, most importantly `async` futures that hold pointers into their own storage. It prevents the *compiler/library* from moving a value, not a *collector*. Same word, unrelated mechanism. Do not conflate the two: GC pinning protects addresses from a *relocating collector*; Rust `Pin` protects addresses from *ordinary moves* in a language that has no collector.

## Code Examples

**.NET — `GCHandle` for a pin that outlives a block:**

```csharp
byte[] buffer = new byte[4096];
GCHandle handle = GCHandle.Alloc(buffer, GCHandleType.Pinned);
try
{
    IntPtr addr = handle.AddrOfPinnedObject(); // stable while pinned
    StartAsyncNativeRead(addr, buffer.Length); // native code keeps addr briefly
    WaitForNativeReadToComplete();
}
finally
{
    handle.Free(); // <-- MUST run, or the pin leaks forever
}
```

**.NET — Pinned Object Heap for a long-lived reused buffer:**

```csharp
// Allocated already-pinned, on the POH: never fragments gen0/gen1/gen2.
byte[] dmaBuffer = GC.AllocateArray<byte>(65536, pinned: true);
// Reuse `dmaBuffer` for many native IO operations without per-use pinning.
```

**Go — `runtime.Pinner` across a cgo call:**

```go
func sendToC(data []byte) {
    var pinner runtime.Pinner
    defer pinner.Unpin()          // releases on return

    pinner.Pin(&data[0])          // pin the backing array element
    C.consume(unsafe.Pointer(&data[0]), C.int(len(data)))
    // Pin lets us legally pass Go memory to C; C must not retain it after return.
}
```

**JNI — a critical region (C side):**

```c
jint *elems = (*env)->GetPrimitiveArrayCritical(env, arr, NULL);
/* INSIDE the critical region: no blocking, no other JNI calls, keep it short. */
process(elems, length);          // may run with GC disabled
(*env)->ReleasePrimitiveArrayCritical(env, arr, elems, 0); // unpin / commit
```

## The Cost of Pinning

- **Fragmentation.** Pinned objects block compaction, leaving holes that waste memory and can force the heap to grow.
- **Longer pauses.** The collector must track and work around pins; heavy pinning lengthens GC pauses.
- **Reduced allocation throughput.** A fragmented heap loses cheap bump allocation in the affected regions.
- **Worst in gen0.** A short-lived buffer pinned in the nursery punishes the most frequent, most latency-sensitive collections — exactly why POH/off-heap exists.

## Coding Patterns

- **Scope-bound pin.** Prefer `fixed` / `using (memory.Pin())` / `defer pinner.Unpin()` so the pin is released deterministically.
- **Allocate-pinned for reuse.** For a buffer used repeatedly by native IO, allocate it pinned once (POH or off-heap) rather than pinning/unpinning each call.
- **Copy-out for hand-off.** If native code needs the data *after* the call, copy it into native memory and pin nothing.
- **`isCopy` discipline (JNI).** Always check `isCopy`; never assume you got a real pin.

## Best Practices

- **Default to the scoped API**; reach for manual-lifetime pins only when the address genuinely must outlive a block.
- **Segregate long-lived pins** onto the POH or off-heap memory; never park a long-lived pin in the normal heap.
- **Pin few, briefly.** Treat every pin as a temporary obstacle to the collector.
- **In JNI, keep critical regions tiny** and never block or re-enter JNI inside them.
- **In Go, prefer `runtime.Pinner`** over `unsafe` tricks, and never let C retain Go pointers past the call.

## Edge Cases & Pitfalls

- **Leaked `GCHandle`.** No `Free()` → a permanent immovable object → silent fragmentation. Wrap in `try/finally`.
- **Blocking inside a JNI critical region.** Can stall the whole VM (GC may be disabled). Strictly forbidden.
- **Assuming JNI pinned, but it copied.** Writes are lost if you don't `Release` with the committing mode.
- **Confusing Rust `Pin` with GC pinning.** They solve unrelated problems; mixing the concepts leads to nonsense designs.
- **Pinning interior/stack pointers in Go.** Stack copying moves stack data; never hand a stack-interior address to C without understanding the lifetime — heap-allocate and pin instead.

---

## Apply it

1. Find a real component where **Object Pinning & Movable Heaps** affects an interface or dependency.
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

- Which boundary is most affected by Object Pinning & Movable Heaps?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
