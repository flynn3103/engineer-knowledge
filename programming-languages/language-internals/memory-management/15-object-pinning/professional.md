# Object Pinning & Movable Heaps — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Object Pinning & Movable Heaps** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### The DMA / async-IO buffer: the canonical driver

Almost every legitimate pin traces back to one scenario: **a buffer whose address is held by something outside the managed runtime for a span of real time.**

- **DMA (Direct Memory Access).** A NIC, NVMe controller, or GPU is handed a physical/virtual address and programmed to read or write that memory *itself*, asynchronously, without the CPU. The device has no notion of a managed heap. If the GC relocates the buffer after the descriptor is programmed but before the device finishes, the device scribbles into the wrong place. The buffer must stay put for the entire DMA transaction.
- **Asynchronous I/O.** `ReadFile`/`WriteFile` with `OVERLAPPED`, `io_uring`, POSIX AIO, or a `recv` that the kernel completes later — the kernel keeps the user buffer address and writes into it when data arrives. The managed call returns immediately; the buffer must remain at its address until completion, which can be arbitrarily far in the future.
- **Synchronous syscalls that block.** Even a plain blocking `read(2)` holds your buffer address inside the kernel for the duration of the call. On runtimes that can GC while a thread is parked in a syscall, the buffer needs protection.

The lifetime of the pin equals the lifetime of the *external reference to the address*, which is dictated by hardware and the kernel, not by your code's control flow. That is why long pins are so easy to create accidentally: the duration is set by an I/O completion you don't directly observe.

### Why pinning fragments a compacting heap

A compacting collector's job is to slide live objects toward one end of a region, squeezing out the gaps left by dead objects, so the free space coalesces into one contiguous block. A pinned object is a rock the river must flow around.

```
Before compaction (P = pinned, x = live, . = dead):
[ x x . . P x . x . . x P . x ]

What compaction WANTS (slide everything left):
[ x x x x x x x . . . . . . . ]   <- one big free block

What compaction GETS with pins fixed in place:
[ x x x x P . . . x x P . . . ]   <- free space split by the pins
            ^hole              ^hole
```

The pinned objects cannot move, so survivors pile up against them and the reclaimed space is broken into fragments straddling each pin. Two consequences:

1. **External fragmentation returns** — the very thing compaction exists to prevent. Large allocations can fail while plenty of total free space exists, scattered around pinned objects.
2. **The collector does more work** — it must detect pins, plan around them, and often abandon the simple "slide everything left" pass for a more expensive constrained layout.

This is precisely why .NET introduced the **Pinned Object Heap**: move all the rocks out of the river. Objects allocated with `GC.AllocateArray<T>(n, pinned: true)` live in a separate non-compacting segment, so the general heap compacts freely and the pins do their damage in a region that wasn't going to compact anyway.

### Pinning and pause time

Stop-the-world compaction time scales with the work the collector must do. Pins inflate it in two ways:

- **Planning overhead.** Constrained compaction (lay out survivors around immovable objects) is more expensive than unconstrained sliding.
- **Reduced effectiveness → more frequent GCs.** Fragmentation means each GC reclaims less usable contiguous space, so the allocator hits the next threshold sooner, so GCs run more often. More frequent GCs means more total pause time, even if each pause is similar.

On the JVM, a JNI **critical region** can be worse than a slow GC: while a thread holds a `GetPrimitiveArrayCritical` region, the VM commonly **disables GC entirely**. If another thread then needs to allocate and the heap is full, it blocks until the critical region ends. A single slow critical region (someone did blocking I/O inside it) can therefore stall *every* application thread — a latency cliff that looks like a full-heap stall but is actually one misbehaving native call.

---

## FFI Integration In Practice

### .NET: pinning across async I/O

The dangerous pattern is pinning that must survive an asynchronous completion. With `GCHandle.Pinned`, *you* own the lifetime, and it is easy to span an `await`:

```csharp
// HAZARD: pin held across an async boundary of unbounded duration
var h = GCHandle.Alloc(buffer, GCHandleType.Pinned);
try {
    await socket.ReceiveAsync(h.AddrOfPinnedObject(), buffer.Length); // could block for seconds
} finally {
    h.Free();
}
```

If thousands of connections do this concurrently, you have thousands of simultaneous pins scattered across the heap for as long as the slowest peer takes to send data. The production-grade fixes:

- **Allocate the buffer in the POH once, reuse it.** A buffer that lives in the Pinned Object Heap for its whole life never obstructs the general heap, and you stop paying per-operation pinning:

  ```csharp
  // Allocated immovable for life; no per-op GCHandle churn, no general-heap holes.
  byte[] buffer = GC.AllocateArray<byte>(8192, pinned: true);
  Span<byte> span = buffer;                // usable as a normal array too
  ```

- **Prefer `Memory<T>`-based async APIs.** `Socket.ReceiveAsync(Memory<byte>, ...)` and `Stream.ReadAsync(Memory<byte>, ...)` internally pin via `MemoryHandle` only for as long as the underlying OS operation needs, and integrate with `IMemoryOwner<T>`/`MemoryPool<T>` so buffers come from a pool rather than fresh allocations. This is the idiomatic modern path: you express intent ("read into this memory") and the runtime manages pinning.
- **Use a buffer pool of POH/native buffers.** `ArrayPool<T>` reduces allocation churn but does not pin; pairing a pool with POH allocation (or native memory) gives you reuse *and* immovability.

### Go: cgo, runtime.Pinner, and struct graphs

The cgo rules bite hardest with *graphs of pointers*. A flat `[]byte` is easy; a struct containing pointers is where teams get burned:

```go
type Request struct {
    Body    *byte   // Go pointer INSIDE a struct passed to C
    BodyLen C.size_t
}

func send(body []byte) {
    var pinner runtime.Pinner
    defer pinner.Unpin()

    req := &Request{Body: &body[0], BodyLen: C.size_t(len(body))}
    pinner.Pin(&body[0]) // pin the INNER pointer so the struct is legal to pass
    pinner.Pin(req)      // and the struct itself if C dereferences it after a move window

    C.process((*C.Request)(unsafe.Pointer(req)))
}
```

Key production realities:

- **`Unpin` releases everything on that `Pinner` at once.** The `defer pinner.Unpin()` pattern is the safe default — one cleanup covers all pins, and it runs even on panic.
- **The rules are enforced at runtime in race/cgocheck builds.** `GODEBUG=cgocheck=1` (default) catches "Go pointer to Go pointer" violations *if the pointer is reachable at the moment C is called*; `cgocheck=2` is more thorough but slower. A violation panics with `cgo argument has Go pointer to Go pointer` — the runtime is telling you to pin.
- **C must not retain.** If a C library stashes your pointer in a global for later use, pinning during the call is not enough — the moment the call returns, `Unpin` will run and the pointer becomes movable/collectable. For "C keeps it" lifetimes, allocate in C (`C.malloc`) or use a registry of pinned objects with a longer-lived `Pinner` whose `Unpin` is tied to the native object's destruction.
- **`uintptr` launders away GC tracking.** Converting through `uintptr` and back is the classic way to defeat both pinning and reachability — the GC does not see a `uintptr` as a pointer. The `unsafe.Pointer` rules exist precisely to keep the conversion atomic; pinning does not save you if you've already stored a `uintptr`.

### JVM: critical regions, copies, and off-heap

The decision tree for JNI array access in production:

- **Short, CPU-bound, no JNI calls, no blocking** → `GetPrimitiveArrayCritical`. Fast (often a true pin, no copy), but the critical-region rules are non-negotiable: no allocation, no blocking, no other JNI calls, no callbacks into Java. Keep it to a tight loop over the array and `Release` immediately.
- **Anything that might block or call back** → `Get<Type>ArrayElements`. May copy (check `isCopy`), but carries no critical-region restrictions, so it's safe to do I/O. Choose the right `Release` mode: `0` to write back and free, `JNI_ABORT` to discard (no write-back — important when you only read).
- **Long-lived sharing, high throughput** → **`DirectByteBuffer`** / off-heap. Allocate with `ByteBuffer.allocateDirect`, get the address via `GetDirectBufferAddress`, and the native side can hold it indefinitely with zero copies and zero pinning, because it was never on the Java heap. The cost is manual lifetime management (direct buffers are reclaimed only when their cleaner runs or via explicit unmapping), and allocation is more expensive than on-heap — so pool them.

The strategic JVM stance: **do not pin the managed heap for anything that lives long or might block. Copy for brief reads, go off-heap for sustained sharing.**

---

## Diagnosing Pinning Problems

- **.NET:** ETW/EventPipe GC events expose pinned-object counts and fragmentation per generation. `dotnet-trace` with the GC provider, or `dotnet-gcdump` + a heap viewer, shows pinned objects and the holes around them. A rising `% Time in GC` together with gen2 fragmentation and frequent gen2 collections is the signature. `GCHandle` counts climbing without bound point to leaked pins.
- **JVM:** Async-profiler or JFR will show threads parked in JNI; correlating allocation stalls with critical-region duration exposes the "GC disabled while a thread is in a critical region" pattern. `-Xlog:gc*` reveals fragmentation-driven GC frequency. Direct-buffer leaks show up as growing off-heap/native memory with stable Java-heap usage (watch `BufferPoolMXBean`).
- **Go:** `cgocheck` panics name the violation directly. For pin pressure, there's no first-class metric, so instrument your own `Pinner` usage; a `Pinner` that is never `Unpin`'d (missing `defer`) is a pin leak that keeps objects immovable and alive. The Go heap profile plus rising RSS without a matching live-object count can indicate pinned-but-unreachable accumulation.

---

## Best Practices

- **Make pin lifetime equal to the OS operation, not your control flow.** Prefer runtime-managed pinning (`Memory<T>` async APIs, scoped `Pinner`) so the pin tracks the actual external reference, not an `await` you happened to write.
- **For sustained sharing, get off the movable heap.** POH (`pinned: true`), `DirectByteBuffer`, or native (`C.malloc`/`Marshal.AllocHGlobal`) memory. Pool these buffers; off-heap allocation is more expensive than on-heap.
- **Guarantee unpin on every path.** `using` / `defer Unpin` / `finally` / `SafeHandle`. Never free a pin only on the happy path.
- **Keep JNI critical regions microscopic.** No blocking, no JNI calls, no Java callbacks, no allocation. If you can't guarantee that, copy instead.
- **Review the full pointer graph at cgo boundaries.** A struct is only as legal as its most deeply nested embedded Go pointer. Pin inner pointers; treat new pointer fields as cgo-breaking changes.
- **Pass handles, not addresses, for long-lived identity.** A normal (non-pinned) `GCHandle` or an index into a managed table gives stable identity across the boundary without forbidding relocation.
- **Instrument pins.** Track handle/pinner counts and GC fragmentation so a slow leak or a pin-amplification regression is visible before it OOMs.

---

## Edge Cases & Pitfalls

- **Pin amplification under concurrency.** A pin held across `await`/blocking I/O multiplied by thousands of concurrent operations equals thousands of long-lived heap obstructions. This is the single most common production pinning failure.
- **Critical-region GC disablement deadlock.** Slow work inside a JNI critical region stalls every thread that needs to allocate. Looks like a full GC stall; is actually one bad native call.
- **Silently broken cgo legality.** Adding a pointer field to a struct that crosses cgo breaks the call without changing the call site. Caught only at runtime under GC pressure.
- **Retained C pointers.** Pinning during a call doesn't help if C keeps the pointer after return. Use C-allocated memory or a long-lived registry for "C keeps it" lifetimes.
- **`uintptr` / address snapshots.** An address captured while pinned is invalid after unpin; a `uintptr` is invisible to the GC and keeps nothing alive or stable.
- **Leaked pins as compounding debt.** Every leaked pin permanently obstructs compaction *and* leaks the object. The damage accumulates and degrades the whole heap, not just one allocation.
- **Empty-buffer pinning.** Pinning a zero-length array yields a null pointer in .NET; native code expecting a non-null base + zero length may fault.

---

## Apply it

1. Define the user or business outcome that **Object Pinning & Movable Heaps** should improve.
2. Assign one owner for code, contracts, operations, and incidents.
3. Split delivery into reversible increments that produce evidence early.
4. Publish responsibilities, escalation paths, and compatibility windows.
5. Stop or expand only when the agreed measures support that decision.

## Verify your work

- Each increment has an owner, rollback path, and observable exit condition.
- Adoption, reliability, delivery time, and coordination cost are measured.
- Incident and migration exercises prove that responsibility is executable.
- The old path is removed only after telemetry proves it is unused.

## Review questions

- Which measurable outcome justifies investing in Object Pinning & Movable Heaps?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
