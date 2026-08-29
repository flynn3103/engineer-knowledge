# Memory Profiling — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Memory Profiling** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Profiling](../README.md) → Memory Profiling
> *The senior page taught you to read a dominator tree and tell retained from shallow size. This page is about doing that against a process you can't pause, on a pod that already died, before the leak OOMs at 3 a.m. — where "what's retained?" stops being a snapshot exercise and becomes an alerting, capture, and incident-response discipline.*

---

## Detecting a Slow Leak Before It OOMs

A fast leak announces itself — the pod dies in minutes, the graph is a wall. The dangerous one is slow: 5–30 MB/hour, invisible inside the normal sawtooth of a healthy heap, surfacing only after days when the floor finally reaches the limit. The entire game is **separating the leak signal from GC noise**, and the single most important idea is this:

**Alert on the heap *after* GC, not on instantaneous heap.**

A healthy heap is a sawtooth: it climbs as the app allocates, drops sharply when GC runs, climbs again. Instantaneous heap (or RSS) bounces between the trough and the peak constantly — alerting on it gives you false pages every time traffic spikes. The leak signature is not a high peak; it's a **rising floor**: the *post-GC* low point creeps up release over release, hour over hour. That floor is the live set — memory the collector tried to reclaim and *couldn't*, because something still references it. A rising post-GC floor is the definition of a leak.

```
heap
 │        ╱│      ╱│      ╱│      ╱│      ← peaks (noisy: allocation + traffic)
 │      ╱  │    ╱  │    ╱  │    ╱  │
 │    ╱    │  ╱    │  ╱    │  ╱    │
 │  ╱      │╱      │╱      │╱      │
 │ ╱        ‾       ‾       ‾        ← post-GC floor CLIMBING = the leak signal
 │╱      ___---‾‾‾
 └─────────────────────────────────► time
   healthy: flat floor    leaking: floor slopes up
```

**Get the post-GC value as a metric.** In the JVM, scrape the after-collection pool usage rather than `jvm_memory_used`:

```promql
# Old-gen (tenured) usage sampled right AFTER a collection — the live set, GC noise removed.
# Micrometer/JMX exports this as jvm_memory_pool_collection_usage (a.k.a. *_after_gc).
jvm_memory_pool_collection_usage_bytes{pool=~"G1 Old Gen|Tenured Gen"}
```

```promql
# Alert on the SLOPE, not the level. Linear-regression of the post-GC floor over 6h.
# > ~5 MB/hour sustained = a leak that will OOM; fire a warning days before it does.
- alert: HeapPostGCFloorRising
  expr: |
    deriv(jvm_memory_pool_collection_usage_bytes{pool=~".*Old.*"}[6h]) > 5e6 / 3600
  for: 2h
  labels: { severity: warning }
  annotations:
    summary: "Post-GC old-gen floor rising on {{ $labels.app }} — probable leak"
```

For Go there's no generational GC, but the same principle applies to the live heap: alert on `go_memstats_heap_inuse_bytes` *floor* trend, or better, on `runtime.MemStats.HeapAlloc` sampled right after a GC cycle. `runtime/metrics` exposes `/gc/heap/live:bytes` (the live set at the last mark-termination) — that is Go's equivalent of the post-GC floor, and the cleanest leak signal the runtime gives you.

```promql
# Go: live heap after the last GC. Slope, not level.
deriv(go_gc_heap_live_bytes[6h]) > 5e6 / 3600
```

> **The professional reality:** instantaneous-heap alerts get silenced within a week because they cry wolf on every traffic spike, and then nobody is watching when the real leak arrives. Alerting on the **post-GC floor slope** gives you a clean signal with days of lead time — enough to capture a dump under controlled conditions instead of doing forensics on a corpse. The metric you choose is the difference between a planned investigation and a 3 a.m. page.

A second, cheaper signal worth wiring up: **`GC frequency` and `time-in-GC`**. As the live set grows toward the limit, the collector runs more often and reclaims less each time — `time-in-GC` climbs from 1–2% toward 20%+ in a death spiral well before the actual OOM. A rising GC-overhead percentage is often the *first* externally visible symptom of a leak, before the floor trend is even obvious.

---

## The Production Capture Playbook

A trend tells you a leak exists. To attribute it you need a heap dump or heap profile from the *real* process under *real* load. There are three capture modes, each with a real cost.

### 1. Auto-dump on OOM, and ship it off the dead pod

The default JVM behavior on `OutOfMemoryError` is to die with a stack trace and nothing else. Turn on the dump:

```bash
-XX:+HeapDumpOnOutOfMemoryError
-XX:HeapDumpPath=/dumps/heap-%p.hprof      # %p = PID, so concurrent dumps don't clobber
-XX:+ExitOnOutOfMemoryError                # don't limp on in a corrupted state — die clean
```

The trap in Kubernetes: the dump lands on the pod's *ephemeral* filesystem, and the OOMKill + restart **deletes the pod and the dump with it**. You captured the evidence and then threw it away. The fix is to get the file *off the pod before it dies*:

- **Mount a persistent volume at `/dumps`** (or an `emptyDir` backed by a node disk that survives the container restart but not the pod — so really, a PVC or object-store sidecar).
- **Run a sidecar / `preStop` hook** that uploads `/dumps/*.hprof` to S3/GCS before the pod terminates. A `preStop` hook buys you `terminationGracePeriodSeconds` (default 30 s) to copy a multi-GB file — raise the grace period if your dumps are large.
- **Size the volume.** A heap dump is roughly the size of the live heap — an 8 GB heap makes an ~8 GB file; a 20 GB heap makes a 20 GB file. If `/dumps` is 10 GB and the heap is 20 GB, the dump fails half-written and you have nothing.

Go's equivalent: there's no automatic heap dump on OOM, but you can register a `runtime/debug.WriteHeapDump` (low-level, for the runtime team) or, far more useful, have your service write a pprof heap profile on a `SIGUSR1` or panic path and ship it the same way.

### 2. On-demand capture from a live process

When the trend is climbing but the process is still alive, capture *without* killing it.

**Go — the gold standard for low-cost capture.** If `net/http/pprof` is imported, the heap profile is one HTTP GET away and costs almost nothing (it's a sampled profile, default one sample per 512 KB allocated):

```bash
# Live retained heap, sampled — negligible pause, safe in production.
go tool pprof -inuse_space http://localhost:6060/debug/pprof/heap
# Snapshot to a file for diffing later:
curl -s http://localhost:6060/debug/pprof/heap > heap-$(date +%s).pb.gz
```

`-inuse_space` is the retention view (what's alive now); `-inuse_objects` counts live objects (catches "millions of tiny things"). These are the leak-hunting views. (`-alloc_space`/`-alloc_objects` are the *rate* side — that's [allocation profiling](../../05-memory-and-allocation-profiling/professional.md), not retention.)

**JVM — capture is heavier, plan for the pause.** A live heap dump via `jmap` or `jcmd` triggers a **full, stop-the-world pause** while it walks and writes the entire heap:

```bash
jcmd <pid> GC.heap_dump /dumps/live.hprof      # preferred; stop-the-world for the dump
jmap -dump:live,format=b,file=/dumps/live.hprof <pid>   # 'live' = full GC first, then dump
```

The `live` option runs a full GC before dumping (so you see only reachable objects — good for leak hunting, since it strips garbage), but that compounds the pause. **A 20 GB heap can pause the JVM for 10–30 seconds and write a 20 GB file** — long enough to trip liveness probes, drop the pod from the load balancer, and cause the very outage you were trying to avoid. Capture from a **canary or a deliberately drained instance** when you can, never blindly from a latency-critical node at peak.

### 3. Always-on sampling: JFR old-object-sample

The JVM's best-kept leak-hunting secret is **JDK Flight Recorder's old-object sample**. JFR tracks a sample of objects that have *survived* and reports, for each, the **allocation stack trace and the GC root that retains it** — exactly the two facts you need, captured continuously at ~1% overhead, with no stop-the-world dump:

```bash
# Always-on recording with the leak profile; old-object sampling captures retained-object roots.
-XX:StartFlightRecording=name=leak,settings=profile,maxage=6h,maxsize=500m,\
  dumponexit=true,filename=/dumps/exit.jfr

# Or attach on demand to a running process and grab the last 6h:
jcmd <pid> JFR.dump name=leak filename=/dumps/leak.jfr
```

Open the `.jfr` in JDK Mission Control → **Memory → Old Object Sample**, and you get a table of leaking objects with their retention paths — the same answer a heap dump gives, but without the 20 GB file or the multi-second freeze. For slow production leaks this is usually the *first* tool to reach for, with a full `hprof` dump as the fallback when you need to walk the whole object graph.

> **The capture cost is real and asymmetric.** A Go pprof heap profile is nearly free; a JVM full heap dump is a multi-second stop-the-world freeze and a heap-sized file that can fill a disk. Know which world you're in *before* the incident: expose `/debug/pprof` in every Go service, and run JFR old-object-sample always-on in every JVM service, so that when the trend climbs you reach for the cheap continuous source first and only pay for a full dump when you truly need the complete graph.

---

## Continuous Memory Profiling

Point-in-time capture answers "what's retained *now*." Continuous profiling answers the more useful production question: **"which function's retained (or allocated) memory has been growing over the last week?"** — a flame graph with a time axis.

Tools like **Pyroscope**, **Parca**, **Grafana's continuous profiling**, and **Datadog's heap profiler** scrape the same `/debug/pprof/heap` (Go) or JFR/async-profiler stream (JVM) on a schedule — every 10–60 s — and store it as a queryable time series of stacks. You then ask:

- **A heap flame graph of `inuse_space` *right now*** — where retained bytes live, by call stack. The widest frame at the leak's retention site is your suspect.
- **A diff flame graph between *last Tuesday* and *now*** — frames that *grew* are highlighted. A steadily widening frame across days, while traffic was flat, is the leak's signature drawn for you automatically.
- **A single function's retained bytes over time** — pick the suspect frame, plot it; a monotonic climb confirms it.

This is the production-native replacement for "SSH in and run pprof by hand." Instead of needing to *predict* when to capture, you have continuous history and can look *backward* from the moment the trend alert fired — diffing the flame graph from before the leak started against now, which points straight at the responsible call path.

```bash
# Pyroscope: a Go service push-or-pull profiling memory continuously.
# Pull mode: Pyroscope scrapes /debug/pprof/heap on an interval, tagged by service/version.
# Then in the UI: select profile type "inuse_space", compare time range A vs B → diff flame graph.
```

> **The professional shift:** continuous profiling changes leak hunting from *reactive forensics* (capture after the trend alarms) to *retrospective diff* (the history is already there; compare two points in time). The cost is modest (~1–2% overhead, plus storage), and the payoff is that "which code path grew its retained footprint since the last deploy?" becomes a query, not an expedition. For any service where OOMs have ever hurt, this is worth the overhead.

A practical caveat: continuous heap profiles are *sampled* and aggregate by stack, so they're excellent at pointing you at the *function* and *call path* but not at telling you *which specific object instance* leaked or *why* it's still referenced. For the final "what GC root holds this?" step you still drop to a full heap dump (MAT) or JFR old-object-sample. Continuous profiling narrows the haystack from the whole heap to one call path; the dump finds the needle.

---

## Triaging the OOMKill — RSS vs Heap vs Native

The most confusing production memory incident is the one where **the JVM heap looks fine and the pod died anyway**. `kubectl describe pod` shows `Reason: OOMKilled`, exit code `137` (128 + SIGKILL) — but your heap dashboards are flat and well under `-Xmx`. The leak is real; it's just not in the place you're looking.

The crux: **the kernel's OOM killer counts the container's *RSS* (resident set size) against the cgroup memory limit. The JVM heap is only one part of that RSS.** A Java process's total memory is:

```
container RSS  =  JVM heap (-Xmx)                 ← your heap dashboards show THIS
              +  Metaspace / class metadata       ← grows with loaded classes (classloader leaks!)
              +  thread stacks (~1 MB × #threads)  ← thread leaks live here
              +  code cache (JIT-compiled code)
              +  GC structures, card tables
              +  direct/off-heap ByteBuffers       ← Netty, NIO, gRPC live here, INVISIBLE to heap tools
              +  native allocations (JNI, zlib, malloc arenas, mmap)
              +  ... all of which the OOM killer counts, and -Xmx does NOT bound
```

So the killer can fire while the heap is half-empty, because Metaspace ballooned (a classloader leak), or thread count exploded, or — most commonly — **off-heap direct memory** grew unbounded. **A heap dump will not show any of this**, because by definition it's outside the Java heap. This is the single biggest source of "I profiled the heap and found nothing" wasted days.

**Triage tree for an OOMKill:**

```
Pod OOMKilled (exit 137), heap dashboards flat?
 ├─ Is RSS >> -Xmx ?  (compare container_memory_working_set_bytes to -Xmx)
 │    └─ YES → the leak is OFF-heap. A heap dump won't help. Go to NMT / native tools.
 ├─ Is Metaspace climbing?  (jvm_memory_used{area="nonheap",id="Metaspace"})
 │    └─ YES → classloader / class leak (redeploys, dynamic proxies, scripting). Cap -XX:MaxMetaspaceSize to make it fail loud.
 ├─ Is thread count climbing?  (jvm_threads_live_threads)
 │    └─ YES → thread leak; each thread is ~1 MB of stack RSS. Find the unbounded executor.
 └─ Is direct-buffer memory climbing?  (jvm_buffer_memory_used{id="direct"} / Netty's PlatformDependent metrics)
      └─ YES → off-heap / Netty / NIO leak. Use Native Memory Tracking, not a heap dump.
```

**Native Memory Tracking (NMT)** is the JVM's built-in accounting for non-heap memory. Turn it on and ask the JVM where its native memory went:

```bash
-XX:NativeMemoryTracking=summary     # ~5–10% overhead; categorizes native usage
jcmd <pid> VM.native_memory summary  # heap, class, thread, code, GC, internal, direct, ...
jcmd <pid> VM.native_memory baseline ; sleep 3600 ; jcmd <pid> VM.native_memory summary.diff
# the diff after an hour shows WHICH native category grew — Metaspace? Thread? Internal? Direct?
```

When NMT points at native allocations outside the JVM's own categories (JNI libraries, a leaking C dependency, glibc `malloc` arena fragmentation), drop to a native allocation profiler: **`jemalloc` with profiling** (`MALLOC_CONF=prof:true,...` + `jeprof`) or **`jcmd ... System.dump_map` / pmap** to see the address-space growth, or run under **`heaptrack`/`valgrind --tool=massif`** in staging. glibc's per-thread `malloc` arenas are a classic culprit: a high thread count fragments native memory; setting `MALLOC_ARENA_MAX=2` (or switching to jemalloc) often "fixes" a mysterious RSS climb that no heap tool could see.

For Go, the analogue is RSS vs `go_memstats_heap_inuse_bytes`: Go's runtime can hold freed memory as RSS before returning it to the OS (controlled by `GOMEMLIMIT` and the scavenger), and **cgo / off-heap allocations don't show in pprof's heap profile at all** — a cgo leak looks exactly like the JVM off-heap case: RSS climbs, the pprof heap is flat. Same triage: compare RSS to the runtime's reported heap; if they diverge, the leak is outside the managed heap.

> **The professional discipline:** *before* opening a heap dump for an OOMKill, compare **container RSS** (`container_memory_working_set_bytes`) to the managed-heap limit (`-Xmx` / `GOMEMLIMIT`). If RSS is far above the heap limit, **stop — the leak is off-heap, and a heap dump is the wrong tool.** Reach for NMT (JVM) or RSS-vs-runtime-heap divergence (Go) first. This one check saves the most common multi-day wild-goose chase in production memory work.

---

## Turning a Leak Into a Fixed Bug

Finding the leak is half the job; the other half is *fixing it for good* and *proving it stays fixed* — which is where production memory work meets the test suite.

**Snapshot diff in a staging soak.** The cleanest way to confirm a fix (or reproduce a suspected leak) is the **before/after comparison snapshot under sustained load**:

1. Drive steady, representative traffic at a staging instance (a load generator replaying production traffic shapes).
2. Let it warm up, force a GC, take **snapshot A** (heap dump or pprof `-inuse_space`).
3. Keep the load running for an hour (or N thousand iterations of the suspect operation).
4. Force a GC again, take **snapshot B**.
5. **Diff them.** In Eclipse MAT: open both, *Histogram → Compare to another Heap Dump* — objects whose count/retained size *grew* between A and B, with traffic steady, are the leak. In Go: `go tool pprof -base=A.pb.gz B.pb.gz` shows only the *delta* in retained memory, attributed by stack.

The diff is powerful precisely because it cancels out the steady-state: anything that's the same size in A and B is just the working set; only the *growth* is suspicious. A growing collection (an unbounded cache, a listener list nobody unregisters, a `ThreadLocal` never cleared) lights up immediately.

**Endurance / soak testing to catch slow leaks pre-release.** A unit test runs for seconds and will *never* catch a 5 MB/hour leak. The discipline that catches leaks *before* they ship is the **soak test** (a.k.a. endurance test): run the service under steady, realistic load for hours-to-days in CI/staging and **assert the post-GC heap floor is flat** at the end.

```
Soak test, run nightly or pre-release:
  • steady load (e.g., 500 rps representative mix) for 8–24h
  • sample post-GC live heap throughout (the same metric you alert on in prod)
  • PASS  if the post-GC floor is flat (slope ≈ 0 over the run)
  • FAIL  if the floor slopes up  →  a leak, caught before launch, with the test load that triggers it
```

This is the inverse of fixing a leak in prod: instead of detecting a rising floor on a live fleet, you detect the same rising floor in a controlled run *before* the code is released — and because you control the load, you already have a reproduction. A soak test that fails *is* your repro; attach a profiler to the same run and diff snapshots A and B to attribute it.

> **The closing-the-loop principle:** a leak isn't fixed when you find it — it's fixed when a **snapshot diff under load shows the growth is gone** and a **soak test in CI will fail if it ever comes back**. Production detection (post-GC floor slope) and pre-release prevention (soak test asserting a flat floor) are the *same measurement* applied at two ends of the lifecycle. Wire up both and slow leaks stop reaching production.

---

## Decision Frameworks

**Is this rising memory a leak, or just load/GC noise? Ask:**
- Is the *post-GC floor* rising, or just the instantaneous peaks? → only a rising **floor** is a leak; rising peaks with a flat floor are normal allocation under traffic.
- Did traffic/working-set grow proportionally? → if memory tracks a real load increase and then plateaus, it's working set, not a leak. A leak keeps climbing with *flat* traffic.
- Is `time-in-GC` climbing too? → a leak's late-stage signature is more frequent GCs reclaiming less; rising GC overhead corroborates a rising floor.

**Which capture do I reach for? Ask:**
- Go service, still alive? → `/debug/pprof/heap -inuse_space` — nearly free, do it first.
- JVM, still alive, slow leak? → **JFR old-object-sample** first (continuous, ~1%, gives roots); full `jcmd GC.heap_dump` only if you need the whole graph.
- JVM, latency-critical node at peak? → **don't** dump it live (multi-second STW); capture from a canary/drained instance or rely on JFR.
- Already OOMed? → the **auto-dump on OOM** you configured earlier, shipped off the pod before restart. (If you didn't configure it, your action item is to configure it for next time.)

**Heap dump or off-heap tooling? Ask (the most important branch):**
- Is container **RSS far above** `-Xmx`/`GOMEMLIMIT`? → the leak is **off-heap**; use **NMT** (JVM) or RSS-vs-runtime-heap (Go), *not* a heap dump.
- Is Metaspace/thread-count/direct-buffer the growing series? → classloader / thread / off-heap respectively — each has its own tool, none is a heap dump.
- Heap floor genuinely rising and RSS ≈ heap? → *now* a heap dump / pprof is the right tool.

**Is the leak actually fixed? Require:**
- A **snapshot diff under sustained load** showing the previously-growing type is now flat, **and**
- A **soak test in CI** that asserts a flat post-GC floor and will fail if the leak returns.

---

## Common Mistakes

1. **Alerting on instantaneous heap or RSS.** It bounces between the GC trough and peak, fires on every traffic spike, and gets muted within a week — so nobody's watching when the real leak lands. Alert on the **post-GC floor slope** (`*_collection_usage` / `/gc/heap/live`) instead.

2. **Configuring `HeapDumpOnOutOfMemoryError` but losing the dump.** The dump lands on the pod's ephemeral disk and the OOMKill + restart deletes it. Mount a PVC, ship it off in a `preStop`/sidecar before termination, and size the volume ≥ the heap.

3. **Taking a live heap dump from a latency-critical node at peak.** A 20 GB dump is a 10–30 s stop-the-world freeze that trips liveness probes and causes the outage you were preventing. Dump a canary or drained instance, or use JFR old-object-sample.

4. **Opening a heap dump for an off-heap OOM.** "OOMKilled, heap flat" almost always means off-heap (Metaspace, threads, direct buffers, native). A heap dump shows nothing because the leak is *outside the heap*. Compare RSS to `-Xmx` first; if RSS is far higher, go to NMT.

5. **Forgetting that Metaspace and direct memory are unbounded by default.** A classloader leak fills Metaspace; a `ByteBuf` leak fills direct memory; neither is capped by `-Xmx`. Set `-XX:MaxMetaspaceSize` and `-XX:MaxDirectMemorySize` so the leak fails *loud and early* and attributably, instead of as a mysterious RSS creep.

6. **Confusing allocation rate with retention.** `-alloc_space` (Go) / a high allocation flame graph tells you what *churns*, not what *leaks*. For a leak you want `-inuse_space`/`-inuse_objects` and the *retained* size in a dominator tree. (Allocation-rate work is [05 — Memory and Allocation Profiling](../../05-memory-and-allocation-profiling/professional.md).)

7. **Declaring victory without a soak test.** A fix verified only by a unit test is unverified for leaks — units run for seconds. Prove it with a snapshot diff under load and lock it in with a soak test that fails on a rising floor.

---

## Apply it

1. Define the user or business outcome that **Memory Profiling** should improve.
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

- Which measurable outcome justifies investing in Memory Profiling?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
