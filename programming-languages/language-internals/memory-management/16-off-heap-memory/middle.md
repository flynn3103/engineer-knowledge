# Off-heap / Native Memory — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Off-heap / Native Memory** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### The four ways to get native memory from the OS

Underneath every off-heap API in every runtime is one of a small set of OS primitives:

| Primitive | Platform | What it gives you | Granularity |
|---|---|---|---|
| `malloc` / `free` | POSIX + Windows (C runtime) | A byte range from the C heap | Arbitrary size |
| `mmap` (anonymous) | POSIX | Pages mapped straight from the kernel | Page-aligned (4 KiB) |
| `mmap` (file-backed) | POSIX | A file's contents addressable as memory | Page-aligned |
| `VirtualAlloc` / `MapViewOfFile` | Windows | The Windows equivalents of the two above | Page-aligned |

`malloc` is for small-to-medium allocations and goes through a userspace allocator (glibc `malloc`, jemalloc, tcmalloc) that itself calls `mmap`/`brk` in bulk and sub-divides. `mmap` directly is for large regions, page-aligned data, and file mappings. Knowing which one your runtime call lands on tells you how the memory will show up in diagnostics: `malloc` regions appear in the allocator's arenas; large `mmap` regions appear as their own entries in `pmap` and `/proc/<pid>/smaps`.

### JVM: DirectByteBuffer and the Cleaner trap

`ByteBuffer.allocateDirect(n)` allocates `n` bytes off-heap via `Unsafe.allocateMemory` (which calls `malloc`). It returns a small **on-heap** `DirectByteBuffer` object — a few dozen bytes — that holds the native address. So a 256 MiB direct buffer is, to the GC, a tiny object. This asymmetry is the root of nearly every JVM native-memory bug.

How does the native memory get freed? Not by `close()` — `ByteBuffer` has no such method. It is freed by a `Cleaner` (historically `sun.misc.Cleaner`, now `java.lang.ref.Cleaner`) that runs **when the tiny wrapper object is garbage-collected**. This is the worst of both worlds:

- You have manual memory (256 MiB the GC doesn't count toward `-Xmx`)...
- ...but freed on the GC's schedule, which you don't control.

If your heap has plenty of room, the GC has no reason to run, the wrappers are never collected, and the native memory is never freed — even though logically you're "done" with it. You can have 8 GiB of dead direct buffers behind a 200 MiB live heap. The escape hatch is `-XX:MaxDirectMemorySize`, a separate cap on direct-buffer memory; when allocation would exceed it, the JVM forces a `System.gc()` and waits, and if that doesn't free enough, throws `OutOfMemoryError: Direct buffer memory`.

### JVM: sun.misc.Unsafe (the legacy path)

`Unsafe.allocateMemory(bytes)` returns a raw `long` address; `Unsafe.freeMemory(address)` releases it; `Unsafe.putLong/getLong(address, ...)` read and write. This is `malloc`/`free` with a thin Java skin and **zero safety**: no bounds checks, no use-after-free protection, a wrong offset is a JVM crash (SIGSEGV) or silent corruption. It powers a generation of off-heap libraries (early Netty, Cassandra, Chronicle) but is being deprecated and removed in favor of the Foreign Memory API. If you see `Unsafe` in a codebase, treat it as legacy C-in-Java.

### JVM: the Foreign Function & Memory API (Panama)

Java 21+ ships the **Foreign Function & Memory API** (`java.lang.foreign`), the modern, safe, supported replacement. Two types matter:

- **`MemorySegment`** — a bounded, typed view over a region of memory (off-heap *or* on-heap). Every access is bounds-checked.
- **`Arena`** — the *owner* and *lifetime* of one or more segments. Closing the arena frees all its segments deterministically.

```java
try (Arena arena = Arena.ofConfined()) {
    MemorySegment seg = arena.allocate(256L * 1024 * 1024); // 256 MiB off-heap
    seg.set(ValueLayout.JAVA_INT, 0, 42);
    int v = seg.get(ValueLayout.JAVA_INT, 0);
} // <-- arena.close() runs here: native memory freed deterministically
```

`Arena.ofConfined()` is single-thread-confined and the cheapest; `Arena.ofShared()` allows cross-thread access at higher cost; `Arena.ofAuto()` is GC-managed (Cleaner-like, for when you genuinely can't scope it). The whole point of Panama is to make `try-with-resources` the off-heap lifetime, replacing the unpredictable Cleaner. Prefer it over `allocateDirect` and `Unsafe` in any new code.

### Memory-mapped files

`FileChannel.map(MapMode.READ_ONLY, 0, size)` (JVM), `mmap()` (Go/Rust/C), or `MapViewOfFile` (Windows) maps a file's bytes into your address space. The file *is* the memory. Reads page-fault in lazily: touching a byte that isn't resident triggers the kernel to read that 4 KiB page from disk into the **page cache** and map it. You never call `read()`; you dereference a pointer.

This is how LMDB, RocksDB, and many embedded databases work, and why they delegate caching to the OS: the page cache *is* the cache, shared across processes, sized by the kernel, evicted under pressure. `madvise(MADV_SEQUENTIAL / MADV_RANDOM / MADV_WILLNEED)` lets you hint the access pattern so the kernel reads ahead correctly. For files larger than RAM, mapping gives you a flat addressable view while the kernel pages the working set in and out — zero-copy, no explicit buffer management.

### Go, Rust, and .NET off-heap

**Go.** The runtime heap is GC-managed, but `golang.org/x/sys/unix.Mmap` gives you a `[]byte` backed by an anonymous or file `mmap` that the GC neither scans nor frees. You must `unix.Munmap` it. Go also has `GOMEMLIMIT`, but be warned: **it bounds the Go heap, not your mmap'd regions** — off-heap is invisible to it, just as it's invisible to `-Xmx` on the JVM.

**Rust.** Raw allocation via `std::alloc::alloc`/`dealloc`, or `memmap2::Mmap`/`MmapMut` for files. Rust's ownership model makes this the safest of the bunch: the `Mmap` value owns the region and `Drop` unmaps it deterministically, so "forgot to free" becomes "forgot to keep it alive," which the borrow checker catches.

**.NET.** `Marshal.AllocHGlobal(size)` / `Marshal.FreeHGlobal(ptr)` (classic, `LocalAlloc`-backed) or the newer `NativeMemory.Alloc(size)` / `NativeMemory.Free(ptr)` (Core 6+, `malloc`-backed, the recommended one). For files, `MemoryMappedFile.CreateFromFile`. As on the JVM, this memory is outside the GC and outside any managed-heap limit.

---

## Code Examples

**JVM — DirectByteBuffer (note: no deterministic free):**

```java
ByteBuffer buf = ByteBuffer.allocateDirect(64 * 1024 * 1024); // 64 MiB off-heap
buf.putInt(0, 12345);
int x = buf.getInt(0);
// There is NO buf.free(). The 64 MiB lives until the wrapper is GC'd
// and its Cleaner runs. Hold a long-lived reference and you leak native memory.
```

**JVM — Panama Arena (deterministic):**

```java
try (Arena arena = Arena.ofConfined()) {
    MemorySegment data = arena.allocate(64L * 1024 * 1024);
    data.fill((byte) 0);
    // ... use data ...
} // freed here, deterministically, regardless of heap pressure
```

**Go — anonymous mmap, manual munmap:**

```go
import "golang.org/x/sys/unix"

data, err := unix.Mmap(-1, 0, 64<<20,
    unix.PROT_READ|unix.PROT_WRITE,
    unix.MAP_ANON|unix.MAP_PRIVATE)
if err != nil {
    return err
}
defer unix.Munmap(data) // YOU free it; the GC will not
data[0] = 0x42
```

**Go — read a memory-mapped file (zero-copy):**

```go
f, _ := os.Open("big.dat")
defer f.Close()
fi, _ := f.Stat()
m, _ := unix.Mmap(int(f.Fd()), 0, int(fi.Size()),
    unix.PROT_READ, unix.MAP_SHARED)
defer unix.Munmap(m)
// m is the file's bytes; m[1<<30] page-faults in that page on first touch.
first8 := m[:8] // no read() syscall, no copy
_ = first8
```

---

## Best Practices

1. **Default to scoped ownership.** Prefer `Arena` (JVM), `defer Munmap` (Go), RAII/`Drop` (Rust), `using`/`try-finally` (.NET) over finalizer-based freeing.
2. **Always set a hard cap.** `-XX:MaxDirectMemorySize` on the JVM is not optional in production — without it, direct-buffer leaks have no ceiling but the container limit.
3. **Pool, don't churn.** Allocating and freeing native memory per request is expensive; reuse buffers (Netty's `PooledByteBufAllocator` is the canonical example).
4. **Match the primitive to the size.** Small/frequent → pooled `malloc`-backed buffers; large/page-aligned/file → `mmap`.
5. **Make off-heap accounting visible.** Export `BufferPoolMXBean` (direct/mapped) metrics or your own allocator counters so a native leak shows on a dashboard, not in a 3 a.m. OOM kill.

---

## Edge Cases & Pitfalls

- **The "small heap, huge RSS" surprise.** Process RSS is 8 GiB but the heap is 2 GiB — the other 6 GiB is off-heap the GC can't see. (Diagnosed at the senior/professional tiers.)
- **Cleaner never runs.** A `DirectByteBuffer` held by a long-lived collection is never GC'd, so its native memory is never freed even though you're logically done with it.
- **`Arena` use-after-close.** Accessing a `MemorySegment` after its `Arena` closes throws `IllegalStateException` (safe) — but the equivalent on a raw `mmap` slice after `Munmap` is a SIGSEGV (not safe).
- **mmap and file truncation.** If another process truncates a file you've mapped, touching the now-out-of-bounds pages raises `SIGBUS`, which most runtimes turn into a crash.
- **`GOMEMLIMIT`/`-Xmx` give false confidence.** Both bound the managed heap only. A container's memory limit is enforced by the kernel against *total RSS*, so off-heap growth gets you OOM-killed while your heap looks healthy.

---

## Apply it

1. Find a real component where **Off-heap / Native Memory** affects an interface or dependency.
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

- Which boundary is most affected by Off-heap / Native Memory?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
