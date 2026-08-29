# Off-heap / Native Memory — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Off-heap / Native Memory** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### RSS vs heap: the accounting model that matters

The number the kernel cares about is **RSS** (resident set size): physical pages your process actually occupies. For a JVM, RSS is the sum of many things, and the Java heap is only one:

```
RSS ≈ Java heap (used, not -Xmx)
    + Metaspace / class metadata
    + Code cache (JIT-compiled code)
    + Thread stacks (≈ 1 MiB × thread count)
    + GC internal structures (card tables, remembered sets)
    + Direct byte buffers / Panama segments   ← off-heap
    + mmap'd files (resident pages)            ← off-heap
    + Native libraries' own malloc (JNI, zlib, ...) ← off-heap
    + malloc arena fragmentation / retention   ← off-heap
```

The classic incident: **"heap is 2 GiB, RSS is 8 GiB."** The 6 GiB delta is everything below the heap line, and a runaway entry there is your leak. The first diagnostic instinct must be to *stop looking at the heap* and start accounting for RSS.

### Sizing a container that uses off-heap

Never set the container memory limit equal to `-Xmx`. A safe starting budget:

```
container_limit = -Xmx
               + MaxDirectMemorySize
               + MaxMetaspaceSize
               + ReservedCodeCacheSize
               + (thread_count × ThreadStackSize)
               + your_explicit_off_heap_budget
               + ~10-20% headroom (malloc fragmentation, GC structures, native libs)
```

Two production essentials: (1) **always set `-XX:MaxDirectMemorySize` explicitly** — its default in modern JVMs is roughly `-Xmx`, which silently doubles your direct-memory ceiling and ruins the budget. (2) On the JVM, `-XX:+UseContainerSupport` (default on) sizes the heap from the cgroup limit, but it knows nothing about your off-heap usage — so if you're off-heap-heavy, set `-XX:MaxRAMPercentage` low enough to leave room. The same discipline applies to Go (`GOMEMLIMIT` bounds the heap, not your `mmap`) and .NET.

### The native-leak diagnosis playbook

When RSS climbs and the heap doesn't, work top-down:

1. **Confirm it's native, not heap.** Compare `Used heap` (from GC logs / `jcmd GC.heap_info`) against RSS (`ps -o rss`, `/proc/<pid>/status` → `VmRSS`). A growing gap = native growth.
2. **Categorize with Native Memory Tracking.** Start the JVM with `-XX:NativeMemoryTracking=summary` (or `detail`), then `jcmd <pid> VM.native_memory summary`. NMT buckets memory by subsystem (Java Heap, Class, Thread, Code, **Internal** — where direct buffers historically land, **Other** — Panama/Unsafe). Take a baseline (`VM.native_memory baseline`) and diff later (`VM.native_memory summary.diff`) to see which bucket is growing.
3. **Check the buffer-pool MXBeans.** `BufferPoolMXBean` exposes `direct` and `mapped` pool counts and total capacity. If `direct` capacity is climbing unbounded, you have a `DirectByteBuffer` leak (Cleaners not running, or genuine retention).
4. **Map the address space.** `pmap -X <pid>` and `/proc/<pid>/smaps` show every mapping with RSS. A single anonymous mapping growing to gigabytes points at one `malloc` arena or one giant allocation; many small ones point at fragmentation or per-request leaks.
5. **Profile the allocator itself.** If NMT's "Internal/Other" is growing but you can't tie it to Java code, the leak is below the JVM — in a JNI library or in `malloc` retention. Swap in **jemalloc with profiling** (`MALLOC_CONF=prof:true,prof_leak:true`, or `LD_PRELOAD=libjemalloc.so` + `jeprof`) to get a native allocation flame graph showing the C call stack that allocated the leaked bytes.

NMT itself adds 5–10% overhead and per-allocation bytes, so it's a "turn on to investigate" tool, not always-on.

### The tooling, in order of cost

| Tool | Cost | Tells you |
|---|---|---|
| `ps` / `/proc/<pid>/status` (`VmRSS`) | free | Total RSS — is it growing? |
| `BufferPoolMXBean` | free, always-on | Direct + mapped buffer totals (JVM) |
| `jcmd VM.native_memory` (NMT) | 5–10% | Which JVM subsystem is growing |
| `pmap -X` / `smaps` | free, snapshot | Per-mapping RSS, find the big/many mapping(s) |
| jemalloc profiling / `jeprof` | moderate | The native (C/JNI) call stack that allocated |
| `bpftrace` / eBPF on `brk`/`mmap` | low, advanced | Live syscall-level allocation tracing |

---

## Code Examples

**Enable and read NMT (the first move in any native-memory incident):**

```bash
# Launch with tracking on:
java -XX:NativeMemoryTracking=summary -XX:MaxDirectMemorySize=2g -jar app.jar

# Baseline, then diff later to find what grew:
jcmd <pid> VM.native_memory baseline
# ... wait while RSS climbs ...
jcmd <pid> VM.native_memory summary.diff
```

**Find the big mapping with pmap:**

```bash
pmap -X <pid> | sort -k3 -n | tail        # mappings by RSS, largest last
grep -A2 'rw-p' /proc/<pid>/smaps | grep Rss | sort -n | tail
```

**Expose direct-buffer usage as a metric (always-on early warning):**

```java
BufferPoolMXBean direct = ManagementFactory
    .getPlatformMXBeans(BufferPoolMXBean.class).stream()
    .filter(b -> b.getName().equals("direct")).findFirst().orElseThrow();
gauge("jvm.buffer.direct.used.bytes", direct::getMemoryUsed); // alert on growth
```

**jemalloc leak profiling for sub-JVM native leaks:**

```bash
LD_PRELOAD=/usr/lib/libjemalloc.so \
MALLOC_CONF=prof:true,prof_leak:true,lg_prof_sample:19 \
java -jar app.jar
# On exit (or via prof.dump), render the native allocation call graph:
jeprof --show_bytes --pdf $(which java) jeprof.*.heap > leak.pdf
```

---

## Best Practices

1. **Always run with `-XX:MaxDirectMemorySize` set explicitly** and alert on `BufferPoolMXBean` direct usage approaching it.
2. **Budget the container against RSS, not `-Xmx`.** Leave 10–20% headroom for fragmentation and native libs.
3. **Have NMT ready.** Document the `jcmd VM.native_memory baseline`/`summary.diff` runbook before an incident; consider running with `summary` tracking on by default if you can absorb the overhead.
4. **Consider jemalloc as the default allocator** in containers — better fragmentation behavior than glibc and built-in profiling; or set `MALLOC_ARENA_MAX` to tame glibc retention.
5. **Alert on the RSS-minus-heap gap.** A widening gap between `VmRSS` and used heap is the earliest signal of a native leak — make it a dashboard panel.
6. **Prefer deterministic freeing** (`Arena`, explicit pool return) so leaks become missed-return bugs you can detect, not Cleaner-schedule lottery.

---

## Edge Cases & Pitfalls

- **Exit 137 with a green heap dashboard.** The signature of an off-heap/native problem. Stop staring at the heap.
- **NMT undercounts third-party native allocations.** It tracks JVM-internal `malloc`, not arbitrary JNI library allocations — those need jemalloc/valgrind. Don't conclude "no leak" from a clean NMT.
- **RSS that won't shrink after freeing.** Often glibc arena retention, not a leak — verify before chasing phantom bugs (`MALLOC_ARENA_MAX`, jemalloc `purge`).
- **mmap'd file RSS counts against the container.** Resident pages of a memory-mapped file show in `VmRSS` and count toward the cgroup limit; mapping a huge file and touching it all can OOM-kill you even though it's "just the page cache."
- **Cleaner-based reclamation under low GC pressure.** With a generously sized heap, the GC may run so rarely that `DirectByteBuffer` Cleaners effectively never fire — paradoxically, a *bigger* heap can worsen a native leak.
- **`-XX:MaxRAMPercentage` ignoring off-heap.** Container-aware heap sizing fills the cgroup with heap and leaves no room for your off-heap budget unless you lower it.

---

## Apply it

1. Define the user or business outcome that **Off-heap / Native Memory** should improve.
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

- Which measurable outcome justifies investing in Off-heap / Native Memory?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
