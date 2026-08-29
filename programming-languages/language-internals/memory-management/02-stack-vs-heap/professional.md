# Stack vs Heap — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Stack vs Heap** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### Guard pages, stack limits, and overflow in production

A thread's stack is a finite, contiguous virtual range. At its far end sits one or more **guard pages**: virtual pages mapped `PROT_NONE`. When recursion or a large `alloca` pushes the stack pointer into a guard page, the CPU raises a page fault the kernel converts into `SIGSEGV` — a *clean* crash instead of silently scribbling over adjacent memory.

Key operational facts:

- **Default main-thread stack on Linux** is governed by `ulimit -s`, commonly **8 MB**. `pthread_create` stacks default similarly but are tunable via `pthread_attr_setstacksize`.
- **Stack memory is lazily committed.** Reserving an 8 MB stack does not touch 8 MB of RAM; pages fault in as the stack deepens. A program with 10,000 threads "reserves" 80 GB of address space but may use far less physical memory — until deep call chains commit it.
- **Stack overflow ≠ heap exhaustion.** Overflow is hitting the guard page (deep recursion, huge locals, runaway `alloca`); heap exhaustion is `malloc` returning `NULL` / an `OutOfMemoryError`. They have different symptoms and fixes.
- A single guard page can be *jumped* by a frame larger than the guard region (e.g., a 16 KB local array skipping a 4 KB guard), corrupting memory below. This is why compilers emit **stack-clash protection** (`-fstack-clash-protection`): probing each page as the frame grows so no allocation can leap the guard.

Managed runtimes wrap this: the JVM throws `StackOverflowError`; Go's runtime detects the morestack failure and panics with a stack trace. But the underlying mechanism is the same guard-page fault.

### Hardware: cache, TLB, and why locality dominates

The performance gap between stack and heap is, in production, mostly a *memory-hierarchy* gap, not an *allocation* gap.

- **Caches.** L1 (~1 ns, ~32–64 KB), L2 (~4 ns), L3 (~15–40 ns), DRAM (~80–120 ns). The **stack is perpetually hot**: the top frames were touched on the last few calls and live in L1/L2. Heap objects allocated at different times and scattered across address space are frequently **cold**, costing a DRAM round-trip per pointer chase.
- **Cache lines.** Memory moves in 64-byte lines. Dense stack data and contiguous arrays use full lines; a heap structure of pointer-linked nodes wastes most of each line on one node, multiplying miss count.
- **TLB.** Each memory access needs a virtual→physical translation. The stack touches a handful of pages (great TLB locality); a pointer-chasing heap traversal can touch a new page per node, thrashing the TLB and incurring page-table walks (~10–100 cycles each).
- **Prefetching.** Hardware prefetchers detect sequential access (arrays, stack growth) and hide latency. Pointer chasing through a scattered heap defeats them.

This is why "reduce allocations" is so often the highest-leverage performance fix: cutting heap allocation simultaneously cuts allocator cost, GC pressure, *and* cache/TLB misses. A microbenchmark sum over `int[1_000_000]` vs `List<Integer>` of the same size can differ 5–10× purely from locality.

### Thread stacks at scale

A high-concurrency server's thread-stack sizing is a real capacity decision:

- A naive thread-per-connection server with the default 8 MB stack reserves 8 MB × N connections of address space; at 100K connections that is 800 GB reserved (mostly uncommitted, but it bounds you and stresses the VM subsystem).
- **Mitigations:** shrink per-thread stacks (e.g., 256 KB–1 MB) if call depth allows; or move to an event loop or a green-threaded model (Go goroutines, Java virtual threads / Project Loom) whose stacks start tiny and grow on demand.
- **Go goroutines** start at ~2 KB and grow by copying; **Java virtual threads** (Loom) likewise start small and park their stack on the heap when blocked, enabling millions of concurrent tasks where platform threads would exhaust memory.

Right-sizing stacks is a trade: too small and deep call chains overflow; too large and you waste address space and harm density.

### Allocator internals you'll actually meet

Production heap behavior is shaped by the allocator:

- **glibc malloc (ptmalloc):** arenas per thread to reduce lock contention, bins for free chunks by size, `brk`/`mmap` for growth. Prone to fragmentation under certain workloads; RSS may not shrink even after `free` (memory returned to a bin, not the OS).
- **jemalloc / tcmalloc / mimalloc:** per-thread/per-CPU caches, fine-grained size classes, better fragmentation behavior, explicit decay/`madvise` to return memory. Swapping glibc malloc for jemalloc is a classic, low-effort RSS and tail-latency win for allocation-heavy services.
- **Go's allocator:** per-P (processor) `mcache`, central `mcentral`, `mheap`; spans organized by size class; tightly integrated with the concurrent GC.
- **JVM TLABs:** each thread bump-allocates from its own TLAB in Eden; only refilling a TLAB or large objects hit the shared path. This is why most JVM allocations are nearly as cheap as a stack bump — until GC time, when the cost is paid in scanning.

The recurring theme: the fast path of every modern allocator *imitates* the stack (per-thread bump allocation) precisely because the stack's model is so cheap.

## Profiling Allocation

The professional doesn't reason about allocations — they measure them.

**Go:**
```bash
# escape analysis: why is this on the heap?
go build -gcflags='-m -m' ./...

# allocation counts/bytes per benchmark op
go test -bench=. -benchmem

# live + alloc heap profile
go test -memprofile=mem.prof -bench=.
go tool pprof -alloc_space mem.prof   # total allocated (rate driver)
go tool pprof -inuse_space mem.prof   # live set (leak hunting)

# GC behavior under load
GODEBUG=gctrace=1 ./server
```

**JVM:**
```bash
# allocation profiling with async-profiler
asprof -e alloc -d 30 -f alloc.html <pid>

# JFR: per-call-site allocation
java -XX:+FlightRecorder -XX:StartFlightRecording=duration=60s,filename=app.jfr ...

# confirm escape analysis / scalar replacement
java -XX:+PrintEliminateAllocations -XX:+UnlockDiagnosticVMOptions ...
```

**C/C++:**
```bash
valgrind --tool=massif ./prog        # heap usage over time
valgrind --tool=memcheck ./prog      # leaks, use-after-free
heaptrack ./prog                     # low-overhead alloc profiler
perf record -g ./prog                # CPU; spot time in malloc/free
```

Interpretation rules:
- **`alloc_space` high but `inuse_space` flat** → high churn, GC pressure, no leak. Reduce allocation rate.
- **`inuse_space` climbing forever** → leak or unbounded cache. Find the retaining reference.
- **Time in `mallocgc`/`malloc` in a CPU profile** → allocation is on the hot path; check whether those sites can stay on the stack (escape report).

## Code Examples

### Go — killing an allocation found in a profile

```go
// BEFORE: fmt.Sprintf allocates a new string + boxes args every call.
func keyBad(id int, region string) string {
    return fmt.Sprintf("%s:%d", region, id) // heap alloc per call (profile-confirmed)
}

// AFTER: reuse a buffer; avoid interface boxing and the formatter.
func keyGood(buf []byte, id int, region string) []byte {
    buf = buf[:0]
    buf = append(buf, region...)
    buf = append(buf, ':')
    buf = strconv.AppendInt(buf, int64(id), 10)
    return buf // caller reuses buf — zero allocations in steady state
}
```

`go test -bench -benchmem` will show `keyBad` at 1–2 allocs/op and `keyGood` at 0 allocs/op once the buffer is reused.

### C — controlled stack use with `alloca`, and its danger

```c
#include <alloca.h>

// OK: bounded size, freed automatically on return — no malloc/free pairing.
void process_small(size_t n) {
    if (n > 1024) return;             // GUARD the size, or you risk stack overflow
    char *tmp = alloca(n);            // on the current frame
    /* ... use tmp ... */
}                                     // implicitly reclaimed
```

`alloca` is stack-fast and self-freeing, but an unbounded `n` jumps the guard page and corrupts memory or crashes — never `alloca` an attacker-controlled size.

### Detecting a stack-overflow crash

```
# Go
runtime: goroutine stack exceeds 1000000000-byte limit
fatal error: stack overflow         ← runaway recursion

# Linux native
Segmentation fault (core dumped)
$ gdb prog core; (gdb) bt           ← backtrace shows a recursion loop into the guard page
```

## Production Playbook

1. **Tail-latency spikes correlated with GC** (`gctrace`, GC pauses in traces): reduce allocation rate (pool buffers, cut boxing, keep temporaries on the stack via escape report), then if needed raise heap headroom (`GOGC`, `-Xmx`) to trade memory for fewer collections.
2. **Steadily rising RSS**: separate churn from leak with `inuse_space`/Massif. If churn, lower allocation rate or switch allocator (jemalloc). If leak, find the retaining root.
3. **Segfault on deep/large input**: suspect stack overflow. Check recursion depth, large locals, `alloca`; raise `ulimit -s` or per-thread stack, or convert recursion to iteration/an explicit heap stack.
4. **High memory at high connection count**: shrink thread stacks or move to goroutines / virtual threads / an event loop.
5. **CPU profile dominated by allocator**: pull hot allocations onto the stack (let escape analysis help) or pool them.

## Best Practices

- Make allocation a tracked SLI: graph allocation rate and GC time alongside latency.
- Default to jemalloc/tcmalloc for allocation-heavy native services; measure RSS and p99 before/after.
- Compile with stack-clash protection and keep guard pages; never disable them to "fix" an overflow — fix the depth.
- Right-size thread stacks for your real call depth; prefer green threads / event loops for very high concurrency.
- Validate every escape-analysis assumption against the actual report; compilers change between versions.

## Edge Cases & Pitfalls

- **Lazy commit hides cost:** an 8 MB stack reserved per thread looks free until deep calls commit it under load — then RSS jumps unexpectedly.
- **RSS doesn't drop after freeing:** glibc malloc keeps freed chunks in bins; the OS still sees the pages resident. Tune `M_TRIM_THRESHOLD` or use an allocator that `madvise`s.
- **Profiler stacks broken by FPO:** without frame pointers or DWARF, flame graphs misattribute; build with `-fno-omit-frame-pointer` for profiling.
- **`StackOverflowError` swallowed:** catching it in the JVM leaves the stack in an unknown state; treat it as fatal.
- **Guard-page jump:** a single large frame can skip a one-page guard; rely on stack-clash protection, don't assume one guard page is enough.

---

## Apply it

1. Define the user or business outcome that **Stack vs Heap** should improve.
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

- Which measurable outcome justifies investing in Stack vs Heap?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
