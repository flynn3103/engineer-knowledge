# Memory and Allocation Optimization — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Memory and Allocation Optimization** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Performance](../README.md) → Memory and Allocation Optimization
> *The senior page taught you to read a heap profile and cut allocations. This page is about memory as a production resource you pay for and get killed by — where "how much does this allocate?" stops being a benchmark question and becomes "what's our $/GB, why did the pod OOMKill at 3 a.m., and does the GC even know it's running in a 2 GiB cgroup?"*

---

## Container Memory Limits and the OOMKill

In production your process almost never owns the machine — it owns a **cgroup** with a memory limit. On Linux, `memory.max` (cgroup v2; `memory.limit_in_bytes` on v1) is a hard ceiling enforced by the kernel. The instant the cgroup's resident memory (RSS + page cache it can't reclaim + kernel accounting) crosses that line, the kernel's OOM killer terminates a process in the group — usually *your* process, with `SIGKILL`. No stack trace, no graceful shutdown, no chance to flush. In Kubernetes you see it as a pod `Reason: OOMKilled`, exit code 137 (128 + SIGKILL's signal 9).

The crucial property: **an OOMKill is not a leak; it's exceeding a number.** A perfectly healthy process that simply needed 2.1 GiB in a 2 GiB cgroup dies exactly as hard as a leaking one. This is why so much production memory work is about the *relationship between the limit and the process's real footprint*, not about the code.

```yaml
# Kubernetes: request is what the scheduler reserves; limit is the OOMKill line.
resources:
  requests:
    memory: "2Gi"   # scheduling guarantee; bin-packing uses this
  limits:
    memory: "2Gi"   # hard cap; cross it and the kernel SIGKILLs you
```

Two facts that bite teams:

- **RSS, not heap, is what gets you killed.** The kernel counts *everything* resident: the GC heap, thread stacks, the runtime/JIT, native allocations (mmap'd buffers, JNI, cgo, glibc `malloc` arenas), and code. A JVM with a 1.5 GiB `-Xmx` can easily sit at 2.2 GiB RSS once Metaspace, thread stacks, code cache, direct byte buffers, and `malloc` overhead are added. Sizing the *heap* to the limit guarantees an OOMKill on the *non-heap* overhead.
- **The kill is abrupt and lossy.** No `defer`, no shutdown hook, no in-flight request drain. Anything you cared about flushing on exit is gone.

> **The professional reality:** the limit is a contract the kernel enforces with `SIGKILL`. You don't get to negotiate it at runtime, so you negotiate it at design time — with headroom and with a GC that respects it.

---

## Making the GC Aware of Its Budget

Here is the single most common production memory bug that isn't a leak: **the runtime doesn't know about the cgroup limit, so it sizes itself for the host.** A managed runtime grows its heap toward whatever it believes the machine has. If it believes the machine has 64 GiB but lives in a 2 GiB cgroup, it will happily allocate past 2 GiB and get OOMKilled — *while convinced it has tons of room and therefore running the GC lazily.*

**The JVM "ignores the cgroup" classic.** Old JVMs read `/proc/meminfo` (the *host's* memory) and defaulted the heap to ~1/4 of it. In a 2 GiB cgroup on a 64 GiB host, the JVM would target a ~16 GiB heap and OOMKill almost immediately. Fixes, in order of how modern they are:

```bash
# Pre-fix legacy JVMs (8u131..8u191): opt in to container awareness
-XX:+UnlockExperimentalVMOptions -XX:+UseCGroupMemoryLimitForHeap

# Modern JVMs (8u192+, 11+, 17+, 21): container-aware by default. Set heap as a
# PERCENTAGE of the cgroup limit, leaving headroom for non-heap memory.
-XX:MaxRAMPercentage=75.0   # 75% of the 2Gi limit -> ~1.5Gi heap, ~0.5Gi headroom
-XX:InitialRAMPercentage=75.0 -XX:MinRAMPercentage=75.0
```

Never use `-Xmx` as a fraction-of-the-limit hardcode in a templated deployment — the day someone changes the k8s limit, the `-Xmx` doesn't follow and you either waste RAM or OOMKill. `MaxRAMPercentage` tracks the cgroup automatically.

**The Go equivalent: `GOMEMLIMIT`.** Go's GC is paced by `GOGC` (a *relative* target: collect when the heap has grown `GOGC`% over live data). A relative target has no idea about an absolute ceiling, so under a load spike Go can blow past a cgroup limit before the next GC. `GOMEMLIMIT` (Go 1.19+) gives the GC an **absolute soft limit** it will work harder and harder to stay under:

```bash
# Tell the Go GC the budget. Set it BELOW the cgroup limit for non-heap headroom.
GOMEMLIMIT=1750MiB        # in a 2Gi (2048Mi) cgroup: ~300Mi for stacks/runtime/off-heap
# Common pattern: keep GOGC default (100) but cap with GOMEMLIMIT as a safety net,
# or set GOGC=off and rely solely on GOMEMLIMIT for a fixed-budget service.
```

`GOMEMLIMIT` is a *soft* limit: as live heap approaches it, the GC runs more frequently to avoid crossing it — trading CPU for staying under the ceiling. If the live set genuinely exceeds the limit (a real leak or undersized budget), Go will GC-thrash rather than OOM-protect you; the limit buys grace, not magic. The headroom you leave (cgroup limit minus `GOMEMLIMIT`) absorbs stacks, the runtime, and cgo/off-heap.

> **The principle:** *the runtime must know its limit, and the limit it's told must be below the cgroup limit by the non-heap margin.* Heap budget = cgroup limit − (thread stacks + runtime/JIT + native/off-heap + safety). A GC tuned against the host's memory in a container is a latent OOMKill that fires the first busy hour.

---

## Tuning the GC for the Workload

There is no universal GC setting; there's a setting *for a workload's objective*. The fundamental knob every collector exposes is **how much RAM you're willing to spend to save CPU** (or how much latency you'll tolerate to save RAM). More headroom between live heap and the limit means the GC runs less often → less CPU spent collecting → but more RAM provisioned. This is the money knob.

**Latency-sensitive services (request/response, p99 matters):**

- **Java:** use a concurrent, low-pause collector. **ZGC** (`-XX:+UseZGC`) and **Shenandoah** (`-XX:+UseShenandoahGC`) do almost all work concurrently with sub-millisecond pauses, largely decoupled from heap size — at the cost of higher CPU and memory overhead than the throughput collector. **G1** (the default since JDK 9) targets a pause goal (`-XX:MaxGCPauseMillis=200`) and is the sensible middle.
- **Go:** the GC is already a concurrent low-pause design (sub-millisecond STW). Tune for latency by giving it room: keep `GOGC` moderate and set `GOMEMLIMIT` so it isn't forced into frequent emergency collections. *Lowering* `GOGC` (e.g. 50) shrinks the heap and cuts peak RSS but raises GC CPU and frequency — the opposite trade.

```bash
# Java, latency-first, 8Gi container:
-XX:+UseZGC -XX:MaxRAMPercentage=70 -XX:+ZGenerational   # JDK 21 generational ZGC
# Go, latency-first, 2Gi container:
GOGC=100 GOMEMLIMIT=1750MiB
```

**Throughput / batch jobs (total work per dollar; pauses don't matter):**

- **Java:** use the **Parallel** collector (`-XX:+UseParallelGC`) — stop-the-world but the highest raw throughput and lowest overhead. Give it a large heap and let GC pauses be long but rare.
- **Go:** raise `GOGC` (e.g. `GOGC=300` or higher) so the heap grows large between collections — fewer, bigger GCs, less CPU spent collecting, more RAM consumed. Perfect when the box is yours for the duration of the batch.

```bash
# Java batch, throughput-first:
-XX:+UseParallelGC -Xmx48g          # rare, long pauses; max work/sec
# Go batch, throughput-first:
GOGC=400 GOMEMLIMIT=60GiB           # big heap, infrequent GC, low GC CPU
```

The cost trade in one sentence: **more RAM = less CPU on GC, and RAM and CPU have different prices.** On typical cloud pricing a vCPU costs roughly 6–8× a GiB of RAM per hour, so for a CPU-bound service that's GC-heavy, *buying RAM to lower GC CPU is often the cheaper trade* — but only up to the point where you'd have to jump to a larger (pricier) instance to get that RAM. Measure GC CPU% (`gc` time in JFR / Go's `GODEBUG=gctrace=1`) and price both sides before turning the knob.

> **Rust / C++ note:** no tracing GC, so none of this applies — instead you manage allocators and arenas directly. Swapping the global allocator (`jemalloc`, `mimalloc`, `tcmalloc`) is the analogous "tuning knob," and fragmentation in long-lived processes (next section) is the dominant memory-creep mechanism rather than GC pacing.

---

## Continuous Memory Profiling in Production

The senior tier profiled *during development*. The professional tier profiles *all the time, in production*, because the memory bugs that matter — slow leaks, gradual heap growth, fragmentation — are invisible in a five-minute benchmark and only manifest after hours or days of real traffic.

**Always-on profiling.** Keep a low-overhead profiler armed in production so that when an incident happens you already have the data:

- **Go:** expose `net/http/pprof` (behind auth / a debug port). Heap and allocation profiles are sampled and cost ~1–2% — cheap enough to leave on. Continuous-profiling systems (Pyroscope, Parca, Google Cloud Profiler, Datadog) scrape `/debug/pprof/heap` on a schedule and store a time series of *where* memory lives.
- **Java:** **JFR** (`-XX:StartFlightRecording`) runs continuously at ~1–2% overhead and records allocation events, GC, and live-set samples; pair with async-profiler for allocation flame graphs. JFR is designed to be always-on in production.

**The two signals to alert on:**

1. **RSS trend.** A monotonically rising RSS that never returns to baseline after GC is the classic leak shape. Alert on a sustained upward slope over hours (e.g. RSS grew > X% over 6 h with no deploy).
2. **Live-heap divergence.** The sharper signal: **post-GC live heap rising over time.** A healthy service's *live* heap (what survives a full GC) oscillates around a stable baseline; total heap sawtooths but the troughs stay flat. A leak shows the *troughs themselves climbing* — each GC frees less than the last because retained objects accumulate. Watching the post-GC floor (Go: live heap from `gctrace`; Java: old-gen occupancy after full GC) catches a leak long before RSS alone makes it obvious.

> **The discipline:** RSS-vs-live-heap divergence is your leak detector. If RSS climbs but live heap is flat, you have fragmentation or off-heap growth, not a heap leak — a completely different fix. Wiring both into your dashboards turns "memory is weird" into a one-glance diagnosis.

---

## Diagnosing Production Memory Incidents

When a memory incident pages you, the first job is **classification**, because the four common shapes have four different fixes and confusing them wastes the incident.

```
Shape on the RSS / live-heap graph              →  Diagnosis            →  First move
──────────────────────────────────────────────────────────────────────────────────────
slow, steady climb over hours/days; live-heap   →  LEAK                 →  heap diff (two profiles
  troughs rising; never returns to baseline                                over time), find growing type
sudden step up after a deploy or input spike     →  BLOAT               →  what changed: input size,
  (big request, cache-fill, unbounded buffer)                              cache config, batch size
RSS climbs but post-GC LIVE heap is FLAT          →  FRAGMENTATION       →  allocator (jemalloc), arena
  (long-lived process, glibc malloc, mixed sizes)    / off-heap growth      tuning, or check off-heap
GC CPU% spiking toward 100%, latency exploding,   →  GC THRASH / DEATH   →  raise limit/headroom NOW,
  throughput collapsing, live heap near limit         SPIRAL               then fix allocation rate
```

**Leak.** Live heap trends up; GC can't reclaim it because something holds references (a growing map/cache without eviction, a registered-but-never-removed listener, a goroutine/thread leak holding closures). Diagnose with a **heap diff**: capture two heap profiles minutes/hours apart and look for the type whose retained bytes grew. In Go, `go tool pprof -base old.heap new.heap`; in Java, two heap dumps compared in Eclipse MAT's "dominator tree" / histogram delta.

**Bloat.** A step change, not a slope — usually traceable to a single event: a deploy that raised a buffer or batch size, a request with an unexpectedly large payload, a cache that filled. Correlate the step with the deploy/traffic timeline; the fix is bounding the input, not finding a leak.

**Fragmentation.** RSS rises while live heap stays flat — the allocator is holding pages it can't return because freed objects left holes too small to reuse and too scattered to coalesce. Endemic to long-lived processes with mixed allocation sizes under glibc `malloc`. Fixes: switch allocator (`jemalloc`/`tcmalloc`), tune `malloc` arenas (`MALLOC_ARENA_MAX`), or use slabs/arenas for the offending size class. In Go, fragmentation is mostly handled by the runtime, so RSS-flat-live divergence there usually points to *off-heap* (cgo, mmap) growth instead.

**GC thrash / death spiral.** The dangerous one. As live heap approaches the limit, the GC fires more and more often to stay under it, each cycle reclaiming less, until the process spends nearly all CPU collecting and almost none doing work. Throughput collapses, latency explodes, and — because it's slow, not crashed — health checks may still pass while the service is effectively down. The JVM's `OutOfMemoryError: GC overhead limit exceeded` is the explicit version (>98% time in GC, <2% heap recovered). **The immediate move is to add headroom (raise the limit / `GOMEMLIMIT` / heap) to break the spiral, then fix the underlying allocation rate or live-set growth** — never just leave the limit raised, or you've only deferred it.

> **The professional discipline:** classify before you fix. "Memory is high" is not a diagnosis. RSS slope + post-GC live-heap behavior + the deploy/traffic timeline tell you which of the four shapes you have, and each one has a different first move.

---

## Capacity, Cost, and Right-Sizing

Memory is a line item. At fleet scale, the difference between provisioning each instance at 16 GiB and 8 GiB is real money, and the job is to **provision the smallest footprint that survives the peak with safe headroom** — no more, no less.

**The headroom margin.** Set the limit above *peak* RSS (p99/p100 over a representative window including the worst load), not average. A limit at average RSS OOMKills on every spike; a limit at 3× peak burns money. A common starting point is **peak RSS × 1.3–1.5**, then tighten with observed data. The margin covers GC overshoot, traffic spikes, and the non-heap memory that grows with concurrency (more in-flight requests → more thread stacks and buffers).

**The three-way trade.** For a fixed total workload you can usually spend it as:

- **Bigger instances, fewer of them** — fewer per-instance fixed overheads (runtime, caches, base RSS amortized over more work), but coarser bin-packing and a bigger blast radius per failure.
- **Smaller instances, more of them** — finer scaling granularity and smaller blast radius, but the per-instance fixed memory overhead is paid many more times (N copies of the JVM/runtime base, N caches).
- **Same instances, tune the GC** — buy RAM to cut GC CPU (or the reverse) *within* an instance before changing the instance count.

**Putting numbers on it.** Suppose a service runs 40 instances at 16 GiB but p99 RSS is 5 GiB. At a representative ~$0.005/GiB-hour for provisioned memory, the 11 GiB of slack per instance is `11 × 40 × 0.005 × 730 ≈ $1,600/month` of headroom you may not need. Drop to an 8 GiB limit (peak 5 GiB × 1.5 = 7.5 GiB, round up) and you reclaim most of it — *if* the live-heap and spike data say 8 GiB survives the peak. The discipline is to let the profiling data, not fear, set the limit.

> **The reality:** right-sizing is a measured trade, not a vibe. Pull p99/peak RSS from the same continuous-profiling you set up above, add a deliberate margin, and price both the slack you're carrying and the OOMKill risk you'd take by trimming it. "16 GiB to be safe" with p99 at 5 GiB is a budget bug, not safety.

---

## Decision Frameworks

**What heap budget do I give the runtime? Compute:**
- Heap budget = cgroup limit − (thread stacks + runtime/JIT/Metaspace + native/off-heap + safety margin).
- Java: express as `-XX:MaxRAMPercentage` (~70–75% is a common start) so it tracks the limit automatically.
- Go: set `GOMEMLIMIT` below the cgroup limit by the non-heap margin; keep `GOGC` for pacing.

**Which GC / GC mode? Ask:**
- Latency-sensitive request/response? → Java: ZGC/Shenandoah (or G1 with a pause goal); Go: default GC with adequate `GOMEMLIMIT` headroom.
- Throughput batch, pauses irrelevant? → Java: Parallel GC, big heap; Go: high `GOGC`, big `GOMEMLIMIT`.
- Want to spend RAM to cut GC CPU? → raise headroom / `GOGC`; verify GC CPU% actually drops and price the RAM.

**Is this incident a leak, bloat, fragmentation, or thrash? Look at:**
- Post-GC live heap rising over time → **leak** (heap diff to find the type).
- Sudden step correlated with deploy/input → **bloat** (bound the input).
- RSS up, live heap flat → **fragmentation / off-heap** (allocator or off-heap fix).
- GC CPU% → 100%, latency exploding, live near limit → **thrash** (add headroom now, fix allocation rate after).

**What's the right limit / instance? Ask:**
- Limit ≈ peak (p99/p100) RSS × 1.3–1.5, validated against live-heap and spike data.
- Bigger/fewer vs smaller/more: weigh per-instance fixed overhead × N against blast radius and scaling granularity.

---

## Common Mistakes

1. **Letting the runtime size for the host inside a container.** A pre-container-aware JVM (or a Go service with no `GOMEMLIMIT`) sizes for the node's memory and OOMKills on the cgroup limit. Set `MaxRAMPercentage` / `GOMEMLIMIT` against the *limit*.

2. **Sizing the heap equal to the cgroup limit.** RSS = heap + stacks + runtime + native; equal heap and limit OOMKills on the overhead. Leave a non-heap margin (a chunk of the limit, not zero).

3. **Hardcoding `-Xmx` as a fraction of the limit in a template.** When the k8s limit changes, the `-Xmx` doesn't follow — you waste RAM or OOMKill. Use `MaxRAMPercentage` so it tracks automatically.

4. **Calling every high-memory incident a "leak."** Bloat, fragmentation, and GC thrash look like "memory is high" but have different fixes. Classify by live-heap slope and the deploy timeline first.

5. **Leaving a raised limit as the "fix" for GC thrash.** Adding headroom breaks the spiral but only defers it if live-set growth or allocation rate is the real cause. Mitigate fast, then fix the root cause.

6. **Provisioning for fear instead of data.** "16 GiB to be safe" with p99 RSS at 5 GiB is a budget bug. Right-size from peak RSS × a deliberate margin, using your continuous-profiling data.

7. **Profiling only in dev.** Slow leaks and fragmentation never show in a five-minute benchmark. Run an always-on profiler (JFR / continuous pprof) so the data exists *before* the incident.

---

## Apply it

1. Define the user or business outcome that **Memory and Allocation Optimization** should improve.
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

- Which measurable outcome justifies investing in Memory and Allocation Optimization?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
