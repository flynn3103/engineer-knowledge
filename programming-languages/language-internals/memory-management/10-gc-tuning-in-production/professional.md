# GC Tuning in Production — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **GC Tuning in Production** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## SLO-Driven Tuning: Turning a Latency Target into GC Settings

Tuning without a number is fiddling. Tuning *to an SLO* is engineering. The workflow:

**1. State the SLO as a measurable budget.** Example: *"p999 end-to-end latency < 200 ms at 2× current peak QPS."* Note the two non-negotiables professionals add: a **percentile** (p999, not mean) and a **load condition** (2× peak — you tune for the bad day, not the average Tuesday).

**2. Decompose the latency budget.** If p999 is 200 ms and your service does ~80 ms of real work at p999, the GC pause budget is roughly the remainder minus margin — say **GC pauses must stay under ~30–40 ms even at the tail.** That number *picks your collector*: 30–40 ms is comfortable G1 territory; if the budget were 5 ms you'd be looking at ZGC/Shenandoah, and if it were 2 ms you'd be questioning whether a managed runtime fits at all (or moving to off-heap/arena allocation for the hot path).

**3. Translate the pause budget into config and validate under load.** Set `MaxGCPauseMillis` to the budget, size the heap for headroom, then **run a load test at 2× peak and read the actual p999 of pauses** — not the goal, the measured outcome. The flag is a hint; the load test is the verdict.

**4. Wire the SLO into alerting.** Alert on the *symptom that maps to the SLO*, with leading indicators:
- p999 latency (the SLO itself).
- GC pause p99 (the leading indicator — it moves before user latency does).
- **Heap-after-GC trend** (catches leaks days before they OOM).
- GC% / fraction of CPU in GC (catches allocation regressions after a deploy).

**5. Protect the budget operationally.** A collector cannot meet an SLO if allocation outruns it. Pair tuning with **load shedding / backpressure** so a traffic spike degrades gracefully instead of triggering GC thrash or allocation stalls. The GC is part of your capacity model, not separate from it.

The professional reframe: **the GC budget is a line item in your latency budget, and the heap is a line item in your capacity model.** Treat them like any other dependency.

## The Container Reality: Where GC Outages Are Born

If you run on Kubernetes, internalize one fact: **your container's memory limit is not your heap size, and getting that wrong is the most common GC outage there is.**

**The cgroup mismatch.** A pod has a memory limit (cgroup). Inside it, the runtime allocates an *object heap* — but the process also uses thread stacks, metaspace/code cache, native libraries, direct byte buffers, and the GC's own bookkeeping. If `heap + non-heap > cgroup limit`, the kernel **OOMKills** the container. The heap dashboard looks healthy right up to the kill, because the heap *was* fine — it was the total that blew the limit.

**Old, broken default:** a JVM that doesn't read cgroups sees the *host's* RAM (say 256 GB), sizes a default heap off that, and gets OOMKilled in a 4 GB pod within seconds. JDK 10+ reads cgroup limits by default; older JVMs need `-XX:+UseContainerSupport` (or you pin `-Xmx` manually).

**The correct recipes:**

*JVM — size heap as a percentage of the container limit, leaving headroom for non-heap:*
```yaml
resources:
  limits: { memory: "4Gi" }
env:
  - name: JAVA_TOOL_OPTIONS
    value: "-XX:MaxRAMPercentage=70.0 -XX:+UseG1GC -Xlog:gc*:file=/proc/1/fd/1:time,tags"
# 70% of 4Gi ≈ 2.8Gi heap, leaving ~1.2Gi for metaspace/stacks/native/GC.
```

*Go — `GOMEMLIMIT` set below the cgroup limit, with `GOMAXPROCS` matched to the CPU limit:*
```yaml
resources:
  limits: { memory: "4Gi", cpu: "2" }
env:
  - name: GOMEMLIMIT
    value: "3600MiB"      # ~90% of 4Gi: soft ceiling keeps Go reclaiming
  - name: GOMAXPROCS      # match CPU limit so the GC sizes its worker pool right
    value: "2"
```

**Why `GOMEMLIMIT` is the k8s game-changer.** Before Go 1.19, a Go service in a tight container would either OOM (heap grew past the limit between collections) or you'd hack a ballast. `GOMEMLIMIT` makes the GC *aware of the ceiling*: as the heap approaches it, the GC runs harder to stay under, trading CPU for survival. The idiom is **high `GOGC` (or off) + `GOMEMLIMIT`**: collect lazily for throughput on a normal day, but never breach the limit on a bad one. Set it to ~90–95% of the cgroup limit (leave room for non-heap Go memory and the kernel's slack).

**`GOMAXPROCS` and CPU limits.** A Go process not told its CPU limit may spawn 64 GC workers on a 2-CPU pod, causing throttling and *worse* pauses. Set `GOMAXPROCS` to the CPU limit (or use `automaxprocs`). The JVM analog: `ActiveProcessorCount` / cgroup CPU awareness sizing the GC thread pool.

## Code Examples

**SLO-anchored G1 config (p999 < 200 ms, ~30 ms pause budget):**
```bash
java -Xms6g -Xmx6g -XX:+UseG1GC \
  -XX:MaxGCPauseMillis=30 \
  -XX:InitiatingHeapOccupancyPercent=40 \
  -XX:+ParallelRefProcEnabled \
  -Xlog:gc*,gc+ergo*=debug:file=/var/log/gc.log:time,uptime,tags:filecount=8,filesize=32m
```

**A leak-detection alert expression (PromQL-style, conceptual):**
```
# Page if heap-after-GC floor rises >5% per hour for 3h — a leak signature.
deriv(min_over_time(jvm_gc_live_data_size_bytes[1h])[3h:]) > 0
```

**Go k8s deployment env (the full recipe):**
```yaml
env:
  - name: GOMEMLIMIT
    value: "3600MiB"
  - name: GOGC
    value: "200"            # lazy on normal days; GOMEMLIMIT caps the bad days
  - name: GOMAXPROCS
    value: "2"              # match CPU limit
  - name: GODEBUG
    value: "gctrace=1"      # narrate GC to stdout for log-based dashboards
```

## Operational Patterns

- **Canary GC metrics on every deploy.** Compare GC% and pause p99 of the canary vs. baseline before promoting. Catches allocation regressions (war story 1) automatically.
- **Heap-dump-on-OOM, automatically.** `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=...` so an OOM is debuggable post-mortem, not just a crash.
- **Continuous profiling** (async-profiler / Pyroscope / `pprof` endpoints) so the allocation flame graph is always available, not something you scramble to attach mid-incident.
- **Two-layer memory alerting:** heap-after-GC trend (leaks) *and* container RSS vs. limit (OOMKill prevention).
- **Load-test the tail at 2× peak** as a release gate for latency-critical services.

## Best Practices

- **Derive GC settings from an SLO budget** with a percentile and a load condition; validate by load test, not by the flag's promise.
- **In containers, size heap below the cgroup limit** and alert on RSS, not just heap.
- **Use `GOMEMLIMIT` + matched `GOMAXPROCS`** in k8s; `MaxRAMPercentage` + container support on the JVM.
- **Make allocation profiles a release gate**; treat a GC% jump as a regression.
- **Distinguish leak from tuning** via heap-after-GC trend before touching a flag.
- **Pair tuning with backpressure** so the collector can win the allocation race under burst.

## Edge Cases & Pitfalls

- **Off-heap memory eats the cgroup headroom** (direct buffers, native libs, memory-mapped files). Cap and account for it; heap dashboards won't show it.
- **`GOMAXPROCS`/JVM CPU-count mismatch** in throttled pods spawns too many GC workers → throttling → *worse* pauses. Match to the CPU limit.
- **Logging to a slow disk** can itself stall the app during heavy GC logging; log async or to a fast volume.
- **Tuning on a quiet environment** that doesn't reproduce production allocation rates yields settings that collapse under real load. Tune against production-like load.
- **Forgetting the bad day.** Settings validated at average QPS fail at peak; always tune and test at the load you're afraid of.

---

## Apply it

1. Define the user or business outcome that **GC Tuning in Production** should improve.
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

- Which measurable outcome justifies investing in GC Tuning in Production?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
