# Allocators — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Allocators** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### The thread-scalability problem

The dominant cost in a modern allocator is not finding free space — it's **lock contention**. If all threads share one heap protected by one mutex, allocation throughput is capped no matter how many cores you have, and the contended cache line bounces between caches.

Two complementary defenses:

1. **Per-thread caches (tcache).** Each thread keeps a small private stash of free objects per size class. `malloc` pops from the local stash with *zero synchronization*; only when the stash is empty (or overfull) does it touch shared structure, and then in *batches* to amortize the lock.

2. **Multiple arenas.** Partition the heap into N independent arenas, each with its own lock. Threads are assigned to arenas (round-robin, or by core). Contention drops by roughly N. glibc and jemalloc both do this.

The flip side is the **producer-consumer / remote-free** problem: thread A allocates an object, thread B frees it. Whose cache does it go back to? Designs differ — jemalloc returns it toward the owning arena; mimalloc's per-page sharded free lists make the foreign free a single atomic push onto a "thread-free" list drained later by the owner. Getting this wrong causes **blowup**: memory that ping-pongs between threads never gets reused and RSS grows with thread count.

### The modern allocator template

Strip away the branding and nearly every fast allocator is three tiers:

```
  +-------------------------------------------------------------+
  | Thread cache (per-thread, lock-free)                        |  <- 95%+ of ops
  |   size-class free lists, small batches                      |
  +-------------------------------------------------------------+
            | refill / flush in batches (locked, rare)
            v
  +-------------------------------------------------------------+
  | Arena / central heap (sharded, locked)                      |
  |   per-size-class bins, runs/spans of pages, coalescing      |
  +-------------------------------------------------------------+
            | grow / shrink (syscall, very rare)
            v
  +-------------------------------------------------------------+
  | OS: mmap / sbrk / VirtualAlloc, madvise to return pages     |
  +-------------------------------------------------------------+
```

Small objects flow through the top two tiers and almost never reach the OS. Large objects (above a threshold) often skip straight to `mmap`. The art is choosing size-class spacing, cache sizes, arena counts, and purge timing.

### Fragmentation: internal, external, and blowup

- **Internal fragmentation:** Padding *inside* a returned block (size-class rounding, alignment, headers). Bounded by tightening size classes — but more classes mean more partly-filled runs. jemalloc and tcmalloc tune classes for ≤ ~15–25% worst-case internal waste.
- **External fragmentation:** Free memory scattered into pieces too small to satisfy a request. Size-class allocators with same-size runs largely *eliminate* per-class external fragmentation, but pay it at the *page/run* granularity — a run holding one live object still pins a whole page.
- **Blowup:** The concurrency-specific failure where per-thread caching plus remote frees inflate memory super-linearly. This is what jemalloc was originally designed to fix and why its fragmentation behavior was a selling point for FreeBSD and Facebook.

A crucial senior insight: **the metric that matters in production is RSS over time under a real workload, not synthetic alloc/free microbenchmarks.** An allocator can win a throughput benchmark and lose badly on steady-state memory.

### RSS vs. virtual size and returning memory to the OS

Your process's *virtual* size can balloon harmlessly — unused pages cost nothing until touched. What matters is **RSS**: the physical pages actually backing the process. Once an allocator frees objects, the pages may still count toward RSS until it tells the kernel to reclaim them via `madvise`:

- **`MADV_DONTNEED`** (eager): The kernel drops the pages now; RSS falls immediately; the next touch is a fresh zero page (page fault + zeroing cost).
- **`MADV_FREE`** (lazy, Linux 4.5+/BSD): The kernel *may* reclaim the pages under memory pressure but leaves them mapped; if you reuse them first, you avoid the fault. RSS may not drop until pressure arrives — which can *look like* a leak in `top` but isn't.

jemalloc and tcmalloc expose a **decay** policy: rather than purge the instant memory frees (which causes thrashing if you reallocate), they wait a tunable interval, smoothing page churn against RSS. This is the single most impactful knob for long-running services and the source of many "why won't my memory go down?" investigations.

## Cross-Allocator Comparison

| Allocator | Origin / users | Concurrency model | Fragmentation focus | Notable knobs |
|-----------|----------------|-------------------|---------------------|---------------|
| **glibc malloc (ptmalloc)** | Default on Linux | Multiple arenas (default ~8×cores cap), per-thread tcache (small, recent) | Moderate; bins + coalescing; can fragment under threaded churn | `MALLOC_ARENA_MAX`, `M_MMAP_THRESHOLD`, `M_TRIM_THRESHOLD`, glibc `tcache` count |
| **jemalloc** | FreeBSD, Facebook/Meta, historically Rust | Per-thread tcache + multiple arenas; explicit decay-based purging | Strong; designed to minimize fragmentation & blowup | `MALLOC_CONF` (narenas, dirty/muzzy decay, tcache, prof) |
| **tcmalloc** | Google; Chrome, server fleet | Per-thread (and per-CPU, "rseq") caches + central free lists + page heap | Strong; aggressive small-object caching | `MALLOC_CONF`-like via env / API; per-CPU mode, release rate |
| **mimalloc** | Microsoft Research | Free-list sharding *per page*; local frees lock-free, remote frees one atomic push | Strong + compact metadata; excellent locality | env vars (`MIMALLOC_*`), eager/lazy commit, purge delay |
| **scudo** | LLVM / Android default | Hardened: per-thread caches but checks integrity | Security over raw speed | hardening checks, quarantine size |

Reading the table as a senior: glibc is the safe default and fine for most workloads, but heavily threaded allocate/free churn (think a Go-style or actor service in C++) is exactly where jemalloc/tcmalloc/mimalloc pull ahead — both on throughput (less lock contention) and on RSS (better fragmentation and decay control). mimalloc's per-page sharded free lists give it unusually good cache locality and a tiny, predictable metadata footprint. scudo trades a few percent of speed for hardening (header checksums, randomized chunk placement, delayed quarantine) and is the right default where untrusted input meets C/C++ (Android).

There is no universal winner. The honest senior answer to "which allocator?" is: *measure your workload's RSS and tail latency under each; the differences are real but workload-specific, and the default is often good enough until proven otherwise.*

## Language-Level Allocator Hooks

The allocator isn't only a C concern — every systems language exposes a seam to choose or replace it.

- **C++ `operator new` / `std::pmr`.** You can override global `operator new`/`delete`, or, far better, use **polymorphic memory resources** (`std::pmr`) to give a container a *local* allocator — e.g. a `monotonic_buffer_resource` (an arena) or `unsynchronized_pool_resource` (pools), composed via `std::pmr::vector<T>`. This brings arena/pool design *into the standard library* without rewriting containers.
- **Rust `GlobalAlloc` / `#[global_allocator]`.** Implement the `GlobalAlloc` trait and register it with `#[global_allocator]` to swap the process-wide allocator (e.g. `jemallocator`, `mimalloc`). The unstable `Allocator` trait additionally allows per-collection allocators (`Vec::new_in`).
- **Go's mcache / mcentral / mheap.** Go's runtime allocator is a tcmalloc-derived design baked into the runtime: each P (logical processor) has an **mcache** (per-thread cache, lock-free fast path), backed by per-size-class **mcentral** lists, backed by the **mheap** (page-level heap managing spans, talking to the OS). You don't replace it, but understanding it explains Go's allocation profile and GC interaction.
- **Zig's allocator-passing.** Zig takes the opposite philosophy: there *is* no global allocator. Functions that allocate take an `Allocator` parameter explicitly, so the caller chooses (general-purpose, arena, fixed-buffer, testing allocator that detects leaks). This makes allocation strategy a first-class, visible part of every API.

The senior takeaway: arena and pool patterns aren't exotic — they're surfaced as first-class tools (`std::pmr`, `Vec::new_in`, Zig's `ArenaAllocator`) precisely because choosing the right allocator per data structure is a routine performance lever.

## Code Examples

### Swapping the global allocator in Rust

```rust
// Cargo.toml: mimalloc = "0.1"
use mimalloc::MiMalloc;

#[global_allocator]
static GLOBAL: MiMalloc = MiMalloc;   // entire process now allocates via mimalloc

fn main() {
    // Vec, Box, String, HashMap — all route through MiMalloc now.
    let v: Vec<u64> = (0..1_000_000).collect();
    println!("{}", v.len());
}
```

One attribute changes every allocation in the program. This is the granularity at which production teams pick allocators — a single line, then A/B the RSS and latency.

### A per-container arena with C++ `std::pmr`

```cpp
#include <memory_resource>
#include <vector>
#include <array>

void process_request() {
    std::array<std::byte, 64 * 1024> buffer;     // stack-backed scratch
    std::pmr::monotonic_buffer_resource arena{
        buffer.data(), buffer.size()};           // a bump allocator

    // This vector allocates from the arena, not the global heap.
    std::pmr::vector<int> ids{&arena};
    for (int i = 0; i < 1000; ++i) ids.push_back(i);

    std::pmr::vector<std::pmr::string> names{&arena};
    names.emplace_back("alice");

    // No per-element free; the arena reclaims everything when it goes
    // out of scope here. Zero calls to the global allocator in the loop.
}
```

This is the middle-tier arena pattern promoted into idiomatic, type-safe C++: request-scoped allocations served by a bump resource, freed wholesale at scope exit.

### Inspecting jemalloc fragmentation at runtime

```c
#include <jemalloc/jemalloc.h>
#include <stdio.h>

void dump_stats(void) {
    size_t sz = sizeof(size_t);
    size_t allocated, resident, retained;

    mallctl("epoch", NULL, NULL, &(uint64_t){1}, sizeof(uint64_t)); // refresh
    mallctl("stats.allocated", &allocated, &sz, NULL, 0);  // bytes in use
    mallctl("stats.resident",  &resident,  &sz, NULL, 0);  // RSS-ish
    mallctl("stats.retained",  &retained,  &sz, NULL, 0);  // returned-but-mapped

    printf("allocated=%zu resident=%zu retained=%zu\n",
           allocated, resident, retained);
    // resident >> allocated  =>  fragmentation or undecayed dirty pages.
}
```

The gap between `allocated` (what your program actually holds) and `resident` (physical pages) *is* your fragmentation + undecayed-page bill — the number to watch on a long-running service.

## Coding Patterns

- **Pick the allocator globally, optimize locally.** Set a good `#[global_allocator]` / link jemalloc for the whole process; then use `pmr`/`new_in`/arenas for the hottest specific structures.
- **Pin threads to arenas/CPUs** when you control the runtime, to keep caches warm and frees local.
- **Expose allocator stats in your metrics.** Export `allocated`/`resident`/`retained` (jemalloc `mallctl`) or tcmalloc's properties so fragmentation is observable, not guessed.
- **Tune decay, not code, first.** Many "memory growth" issues are a decay/purge configuration away from solved.

## Best Practices

- **Benchmark with your real workload and watch RSS over time**, not just ops/sec. Allocators that win microbenchmarks can lose on steady-state memory.
- **Set `MALLOC_ARENA_MAX`** (glibc) on memory-constrained containers — the default arena count can multiply RSS on high-core hosts.
- **Prefer `MADV_FREE` semantics** when you reallocate frequently (avoids fault/zeroing churn); prefer eager purge when co-tenancy / OOM pressure dominates.
- **Don't mix allocators across a free boundary.** If a library was built against jemalloc and you free its pointers with glibc `free`, you corrupt the heap. Keep the allocator consistent across a `malloc`/`free` pair and across shared-library boundaries.
- **Treat allocator choice as configuration**, swappable per deployment, not hardcoded.

## Edge Cases & Pitfalls

- **"Memory leak" that's actually undecayed pages.** RSS stays high after a burst because decay hasn't purged yet, or `MADV_FREE` pages aren't reclaimed without pressure. Confirm with allocator stats before debugging a leak.
- **Arena blowup on producer/consumer workloads.** One thread allocates, another frees; with a poor remote-free design, RSS climbs with thread count. Choose an allocator (mimalloc, modern jemalloc) that handles foreign frees cleanly.
- **`MALLOC_ARENA_MAX` unset in containers.** glibc sizes arenas to host cores, not cgroup limits — a 96-core host can inflate a small container's RSS dramatically.
- **Cross-allocator free across a shared library.** A `.so` statically linked to one allocator returns memory the main program frees with another. Subtle, catastrophic corruption.
- **Benchmarking the wrong thing.** A loop that allocates and immediately frees one size lives entirely in the thread cache and tells you nothing about fragmentation. Use representative size/lifetime mixes.
- **Assuming Go/Java let you swap allocators.** They don't expose that seam the way C/C++/Rust do; you tune the runtime/GC instead.

---

## Apply it

1. State the system invariant that **Allocators** must protect.
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

- Which invariant must remain true when Allocators fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
