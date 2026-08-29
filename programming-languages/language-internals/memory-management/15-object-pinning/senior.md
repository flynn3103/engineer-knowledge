# Object Pinning & Movable Heaps — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Object Pinning & Movable Heaps** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### Why a heap moves objects

Three forces push runtimes toward movable heaps:

- **Bump-pointer allocation.** If the live set is packed contiguously, allocation is `top += size; return old_top`. No free-list search, no size-class lookup, near-zero per-object cost. This only stays true if the collector periodically compacts away the holes left by dead objects.
- **Fragmentation control.** A non-moving allocator (think `malloc`) accumulates external fragmentation: free space exists but is chopped into pieces too small to satisfy a request. A compacting collector slides survivors together and reclaims one large contiguous region, so a 1 MB allocation never fails while 4 MB sits free-but-scattered.
- **Generational locality and promotion.** Copying collectors (Cheney-style semispace, or the young generation of most production GCs) evacuate survivors into a fresh region, which both compacts and physically separates young from old. Promotion *is* a move.

The common thread: the collector earns the right to move objects in exchange for cheap allocation and bounded fragmentation. Pinning is the localized, temporary surrender of that right.

### What "address stability" actually means

Be precise about three distinct notions, because conflating them causes bugs:

1. **Reference validity.** A managed reference (`object`, a Go pointer, a JVM `jobject`) stays valid across moves. The runtime fixes it up. You never observe the move through a managed reference.
2. **Address stability.** The *numeric machine address* stays constant. A movable heap explicitly does **not** guarantee this. Casting a reference to an integer (`GCHandle.AddrOfPinnedObject`, taking `&array[0]`, `uintptr(unsafe.Pointer(p))`) snapshots an address that may already be stale.
3. **Identity.** Object identity (reference equality) is preserved across moves and is independent of address. `RuntimeHelpers.GetHashCode`, Java's identity hash, and Go pointer comparison all remain correct because the runtime never compares raw addresses for identity — it stores a stable identity hash separately or rehomes the comparison through managed references.

Pinning is exactly the operation that *temporarily* promotes "reference validity" to "address stability."

### Pinning as the contract with the collector

Mechanically, pinning adds the object to a set the collector consults before relocating anything: "objects in the pinned set keep their current address." Different runtimes implement the set differently — a hash table of handles, a per-region flag, a side list scanned at the start of compaction — but the semantics are identical: **a pinned object is treated as immovable for the duration of the pin.**

The cost is that a pinned object becomes an obstacle. A compacting pass that wants to slide survivors leftward must stop at each pinned object, leaving a hole. Many pins, or long-lived pins, defeat the compaction the heap was designed around. This single fact drives every best practice in this topic.

---

## The Cross-Runtime Design Space

### .NET: fixed, GCHandle, and the Pinned Object Heap

.NET exposes pinning at three altitudes:

- **`fixed` statement** — lexically scoped, stack-cheap pinning. Inside the block the GC will not move the object; the pin is released at the closing brace. The pin lives in compiler-generated metadata (a "pinned local"), so it costs essentially nothing and cannot leak past the scope.

  ```csharp
  static unsafe void Hash(byte[] data) {
      fixed (byte* p = data) {           // array pinned for this block
          NativeLib.Sha256(p, data.Length);
      }                                  // unpinned here, deterministically
  }
  ```

- **`GCHandle.Alloc(obj, GCHandleType.Pinned)`** — an *unscoped* pin. The handle keeps the object pinned (and alive) until you call `Free()`. This is the right tool when the native side outlives a single call — e.g. you register a buffer with an OS object and the kernel writes into it asynchronously. It is also the classic leak: forget `Free()` and you have permanently immovable garbage.

  ```csharp
  var h = GCHandle.Alloc(buffer, GCHandleType.Pinned);
  IntPtr addr = h.AddrOfPinnedObject();
  Overlapped.RegisterForAsyncIo(addr, ...);
  // ... later, in the completion path:
  h.Free();                              // MUST run, or the pin is forever
  ```

- **`Memory<T>.Pin()` → `MemoryHandle`** — the modern, abstraction-friendly path. `Memory<T>` may be backed by a managed array, native memory, or a custom `MemoryManager<T>`; `Pin()` returns a `MemoryHandle` whose `Pointer` is stable until `Dispose()`. For an array-backed `Memory<T>` it pins the array; for native-backed memory it is a no-op pin (already immovable). This lets a library accept "some memory" and get a stable pointer without knowing the backing store.

**The Pinned Object Heap (POH), .NET 5+.** Pre-POH, pinned objects lived in the normal generations, so each pin punched a hole in gen0/gen2 compaction. POH is a separate, *non-compacting* heap segment dedicated to pinned objects. `GC.AllocateArray<T>(length, pinned: true)` allocates straight into it. The insight: if an object is going to be pinned for its whole life (a long-lived I/O buffer), segregating it means it never obstructs the compaction of the regular heap, and the collector never has to special-case it during compaction. POH trades a small amount of internal fragmentation in a dedicated region for the removal of pinning's drag on the main heap — a textbook "segregate the irregular case" design.

### JVM: JNI critical regions vs. copying

The JVM's HotSpot collectors are heavily copying/compacting, but the JVM has no general user-facing "pin this object" API. Instead, JNI offers two interop strategies and lets the VM choose whether to pin or copy:

- **`GetPrimitiveArrayCritical` / `ReleasePrimitiveArrayCritical`** — requests a direct pointer into a primitive array. The VM *may* pin (hand back the real address) or *may* copy. The contract is brutally restrictive: between `Get…Critical` and `Release…Critical` you are in a **critical region** where you must not make other JNI calls, must not block, and must not do anything that could trigger a GC or run arbitrary Java code. In practice, while a thread sits in a critical region, the VM often disables GC globally — so a slow critical region stalls *every* thread. This is the JVM admitting that pinning is so disruptive it only allows it under a no-blocking, no-allocation straitjacket.

- **`GetIntArrayElements` / `Get<Type>ArrayElements`** — returns a pointer and an `isCopy` out-parameter. The VM is free to either pin or copy; on a copying collector it almost always **copies**. `ReleaseIntArrayElements` takes a mode (`0` = copy back and free, `JNI_COMMIT` = copy back keep, `JNI_ABORT` = discard) so you control write-back. Because it may copy, it has no critical-region restrictions — but you pay a copy in each direction.

- **`DirectByteBuffer`** — the copy-free *and* pin-free alternative. A direct buffer is backed by **off-heap native memory** (allocated outside the Java heap), so the GC never moves it and native code can hold its address indefinitely via `GetDirectBufferAddress`. This is the JVM's strategic answer: rather than pin on-heap objects, push interop buffers off-heap entirely. NIO, Netty, and most high-performance I/O paths live here.

The JVM design philosophy is clear: avoid pinning the managed heap; copy for short hops, go off-heap for long-lived sharing.

### Go: cgo pointer rules and runtime.Pinner

Go's heap is moving in one specific, important way: **goroutine stacks grow and shrink by relocation**, and the runtime is increasingly free to move heap objects too. cgo therefore imposes the **pointer-passing rules**:

- Go memory passed to C **must not itself contain Go pointers**, unless those pointers are pinned. (A `*C.char` into a Go byte slice is fine; a Go struct containing `*OtherGoStruct` is not, because C might dereference a pointer the runtime later moves.)
- **C must not retain a copy of a Go pointer after the call returns.** Once the cgo call returns, the runtime is free to move or collect that memory. C may use the pointer *during* the call only.

`runtime.Pinner` (Go 1.21) makes the legal window explicit and extendable:

```go
var pinner runtime.Pinner
defer pinner.Unpin()                 // releases all pins at once

buf := make([]byte, 4096)
pinner.Pin(&buf[0])                  // address of buf[0] now stable
C.read_into(unsafe.Pointer(&buf[0]), C.size_t(len(buf)))
// safe: buf is pinned for the lifetime of `pinner`
```

`Pin` accepts a pointer to an object (or array element) and guarantees it will not move until `Unpin`. The crucial capability is **pinning Go pointers that are stored inside other Go memory passed to C** — pin the inner pointer, and a struct-with-pointers becomes legal to hand across the boundary. `Unpin` releases *every* pin on that `Pinner` at once, which is the idiomatic deferred-cleanup shape.

### Moving stacks: the interior-pointer hazard

Go (and other runtimes with movable stacks) makes a subtle point vivid: **the stack moves too.** When a goroutine's stack grows, the runtime allocates a larger stack and copies frames over, fixing up pointers into the stack. An *interior stack pointer* — `&localVar` handed to C — would dangle after such a copy if it weren't accounted for. This is why "take the address of a stack variable and stash it in C" is doubly dangerous: not only might the heap move, the stack itself is a moving target. The safe patterns are: copy to a heap allocation and pin it, or use C-allocated memory for anything the native side keeps.

---

## Sidebar: Rust `Pin<P>` Is a Different Thing

If you arrive here from Rust, disarm one major confusion immediately. **Rust's `Pin<P>` has nothing to do with garbage collection or heap relocation.** Rust has no moving GC; it has no GC at all. `Pin<P>` is a *type-system* construct: it statically guarantees that the pointee will **never be moved in memory again** for the rest of its life, by preventing safe code from obtaining a `&mut T` it could use to move the value (unless `T: Unpin`).

Its purpose is **self-referential types**, the canonical case being `async` state machines (futures). A future generated by `async fn` may hold a pointer into its own body — e.g. a borrow that spans an `.await`. If that future were moved after the borrow was created, the internal pointer would dangle. `Pin` makes the move statically impossible, so self-references stay valid.

So the two "pins" answer opposite questions:

| | GC pinning (.NET / JVM / Go) | Rust `Pin<P>` |
|---|---|---|
| Problem it solves | A relocating collector might move an object out from under a raw pointer | A value with internal self-references must not be moved |
| Mechanism | Runtime/collector marks the object immovable at GC time | Compile-time type guarantee; no runtime collector involved |
| Duration | Temporary (until unpin/handle free) | Typically for the value's whole life |
| Enforced by | The garbage collector | The borrow checker / type system |

They share only the English word "pin." Treat them as unrelated when reasoning about either.

---

## Best Practices

- **Pin for the shortest possible window.** Prefer lexically scoped pins (`fixed`, a `Pinner` with `defer Unpin`) over open-ended handles. The ideal pin lasts exactly one synchronous native call.
- **For long-lived sharing, copy out or go off-heap.** If native code needs a buffer for the lifetime of a connection, allocate it where it never moves: POH (`pinned: true`), a `DirectByteBuffer`, or C-/native-allocated memory. Do not pin a normal-heap object for minutes.
- **Segregate pinned allocations.** Concentrate pins in a dedicated region (POH on .NET) so they don't perforate the general heap. Scattering pins across gen0/gen2 maximizes the holes.
- **Use stable handles as indirection, not addresses.** When you need a long-lived *identity* across the boundary (a callback context), pass a `GCHandle` (normal, not pinned) or an integer index into a managed table — not a raw address. You get stability of *reference* without forbidding relocation.
- **Treat a pin's lifetime as a resource.** `GCHandle.Free`, `MemoryHandle.Dispose`, `Pinner.Unpin`, `Release…Critical` are all "must run" cleanups. Tie them to `using`/`defer`/`finally` so an exception can't strand a pin.
- **Keep JNI critical regions tiny and non-blocking.** No JNI calls, no I/O, no locks inside `Get…Critical`/`Release…Critical`. If you need to block, copy with `Get…ArrayElements` instead.

---

## Edge Cases & Pitfalls

- **Snapshotting a stale address.** `AddrOfPinnedObject` / `&array[0]` / `uintptr(unsafe.Pointer(...))` are only valid *while pinned*. Storing the integer and using it after the pin releases reads moved or freed memory — and `uintptr` specifically is not tracked by the Go GC, so it never keeps anything alive or stable.
- **Pinning an empty array.** `fixed (byte* p = emptyArray)` yields a null pointer in .NET (there's no element zero to pin). Native code that doesn't tolerate null + length-zero will misbehave.
- **Forgetting the JVM may not pin.** `Get…ArrayElements` returning `isCopy == JNI_TRUE` means your writes are invisible until `Release` copies them back. Code that assumes a live view of the array is wrong on copying VMs.
- **GC during a critical region.** If anything inside a JNI critical region triggers a GC (an allocation, a blocking call that lets another thread allocate while GC is globally disabled), you can deadlock or stall every thread. This is why the restrictions exist.
- **cgo retaining Go pointers.** A C callback that stores a Go pointer in a global and uses it after the originating call returns is undefined behavior even if it "works" today — the runtime is allowed to move or collect that object. Pin it, or hand C a copy / a handle index.
- **Interior pointers into moving stacks.** Passing `&localStruct.field` to C is unsafe in Go beyond the call; the stack can move on the next growth. Heap-allocate and pin, or copy into C memory.
- **Pin amplification under load.** A pin held across an `await`/blocking I/O means it spans an unbounded wall-clock window. Under high concurrency this multiplies into many simultaneous long pins — the failure mode that motivated POH and `DirectByteBuffer`.

---

## Apply it

1. State the system invariant that **Object Pinning & Movable Heaps** must protect.
2. Mark ownership, state, and failure propagation at each boundary.
3. Compare two designs under load, dependency failure, and future change.
4. Define recovery and compatibility behavior before implementation.
5. Test the riskiest assumption with a focused experiment.

## Verify your work

- The experiment supports the design with evidence, not preference.
- Failure injection shows the blast radius and recovery path.
- Compatibility checks cover old and new callers or data.
- Operational signals reveal invariant violations and recovery progress.

## Review questions

- Which invariant must remain true when Object Pinning & Movable Heaps fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
