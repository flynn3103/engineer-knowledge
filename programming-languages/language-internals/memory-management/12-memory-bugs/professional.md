# Memory Bugs — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Memory Bugs** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## The Incident Playbook

When the page fires for "memory climbing / pod OOM-killed," run this sequence:

1. **Stabilize, don't lose evidence.** If OOM is imminent, you have competing goals: keep serving and capture an artifact. Add a replica or raise the limit *temporarily* to buy time — but first ensure `-XX:+HeapDumpOnOutOfMemoryError` (JVM) or equivalent is on, so even a crash yields a dump. Never just restart-and-hope; that destroys the only evidence.

2. **Read the slope, compute time-to-OOM.** From the memory dashboard, get MB/hour. `(limit − current) / burn_rate` is your clock. This decides whether you have hours to investigate live or minutes to drain and capture.

3. **Classify with the four-cause branch — fast.** Pull GC logs and RSS-vs-heap. Is the *post-GC* heap rising (retention) or flat (fragmentation/off-heap/churn)? Is native memory accounting for the gap? Ten minutes here saves hours of wrong-tool investigation.

4. **Capture the right artifact safely.** Retention → heap dump from a *drained* replica or a copy, never the one serving peak traffic in a tight cgroup. Churn → continuous allocation profiler (already running, ideally). Goroutine/thread leak → goroutine/thread dump (cheap, safe). Off-heap → NMT / `pmap` / native profiler.

5. **Bisect if the artifact doesn't immediately name the cause.** Correlate the slope's onset with the deploy timeline. Did the slope start at a specific release? Toggle the suspect feature flag on a canary and watch whether the slope follows.

6. **Mitigate now, fix properly later.** Immediate mitigations: scheduled restart / rolling recycle to cap growth, raise limit, disable the offending flag, bound the offending cache via config. These stop the bleeding. The real fix (break the reference, copy the slice, cancel the goroutine) ships after.

7. **Write it up and add a guard.** Every memory incident should leave behind a heap-growth test, a dashboard panel, or an alert that would have caught it earlier. A leak that recurs is a process failure, not a code failure.

---

## Code & Command Examples

### Capturing a heap dump safely from a constrained container

```bash
# DON'T dump the pod serving peak traffic near its cgroup limit — the dump can OOM-kill it.
# DO: drain one replica from the load balancer, then capture to a mounted volume.

kubectl cordon/drain or remove pod from service endpoints first, then:
jmap -dump:live,format=b,file=/data/heap.hprof <pid>   # 'live' forces GC, shrinks dump, confirms retention
# Pull the file off the node and analyze offline in MAT — never analyze in the live container.
```

### Always-on safety net (set these before the incident)

```text
# JVM: capture automatically at the moment of OOM
-XX:+HeapDumpOnOutOfMemoryError
-XX:HeapDumpPath=/data/oom.hprof
-Xlog:gc*:file=/data/gc.log          # GC logs reveal post-GC occupancy = the floor
-XX:NativeMemoryTracking=summary      # so off-heap is accountable when you need it
```

```go
// Go: keep pprof endpoints available and export the two leak SLIs.
import _ "net/http/pprof"
// Export as metrics on a timer:
//   runtime.NumGoroutine()              -> goroutine-leak SLI
//   runtime.ReadMemStats(&m); m.HeapInuse, m.HeapSys (RSS-ish) -> retention vs fragmentation
```

### A heap-growth leak test for CI

```go
func TestNoLeakUnderRepeatedLoad(t *testing.T) {
    var before, after runtime.MemStats
    warmUp() // let pools/caches reach steady state first
    runtime.GC(); runtime.ReadMemStats(&before)

    for i := 0; i < 100_000; i++ {
        handleRequest(uniqueRequest(i)) // distinct keys stress unbounded caches
    }

    runtime.GC(); runtime.ReadMemStats(&after)
    growth := int64(after.HeapInuse) - int64(before.HeapInuse)
    if growth > 8<<20 { // 8 MiB tolerance after warm-up
        t.Fatalf("heap grew %d MiB across 100k iterations — suspected leak", growth>>20)
    }
}
```

The `warmUp` + `runtime.GC()` framing is essential: without it, one-time initialization and pool fill-up produce false positives. The test asserts the *floor* is flat under repeated, *distinct-key* load — exactly the condition that exposes unbounded caches.

### Bisecting a leak across deploys

```bash
# Annotate the memory dashboard with deploy markers, then ask: when did the slope appear?
# If it correlates with release v1.42, diff v1.41..v1.42 for new caches/listeners/goroutines:
git log --oneline v1.41..v1.42 -- '**/cache*' '**/registry*' '**/*listener*'
# For flag-gated code, toggle the suspect flag on a canary and watch whether the slope follows.
```

---

## Coding Patterns

- **Auto-capture-on-failure:** wire `HeapDumpOnOutOfMemoryError` / core dumps / retained pprof so a crash yields evidence without human intervention.
- **Two leak SLIs always exported:** post-GC heap occupancy (retention) and goroutine/thread count (accumulation leaks).
- **Drain-then-dump:** never capture heavyweight artifacts from a replica serving peak traffic in a tight limit.
- **Warm-up-then-assert:** CI heap-growth tests warm up, force GC, then measure the floor under distinct-key load.
- **Config-bounded caches:** cache sizes/TTLs are config-tunable so you can *mitigate* a leak by tightening bounds without a deploy.

---

## Best Practices

1. **Set the safety-net flags before you need them.** `HeapDumpOnOutOfMemoryError`, GC logging, NMT, and pprof endpoints must be on *in production* — you cannot add them after the OOM.
2. **Capture before you restart.** The restart that ends the page also destroys the evidence. Drain a replica and dump first.
3. **Read the slope, compute the clock.** Let time-to-OOM dictate whether you investigate live or mitigate-and-defer.
4. **Classify before you capture.** The four-cause branch tells you *which* artifact is worth the risk of capturing in production.
5. **Bisect across deploys and flags** when the artifact is ambiguous; memory slope is a function of version and config.
6. **Mitigate with restarts/limits/flag-toggles, but never call that a fix.** The tourniquet stops bleeding; the surgery still has to happen.
7. **Leave a guard behind.** Every incident yields a heap-growth test, an SLI, or an alert. Otherwise it recurs.

---

## Edge Cases & Pitfalls

- **Dumping the wrong pod under pressure** can OOM-kill it mid-capture and corrupt the dump. Always drain first and write to durable storage off the pod's ephemeral disk.
- **The OOM killer leaves no app trace.** Engineers waste time searching application logs for a crash that lives only in `dmesg`/kernel logs. Check the orchestrator's OOM events, not just app logs.
- **Restart-masking hides slow leaks indefinitely.** If pods recycle every few hours "for hygiene," a 100 MB/hour leak is invisible. Track *memory slope between restarts*, not just crash counts.
- **Heap-growth CI tests without warm-up are flaky.** One-time init and pool fill-up look like leaks. Warm up, GC, *then* measure — and tolerate a small baseline.
- **Canary too small or too short** won't surface a slow leak; a leak that needs hours of traffic won't show in a ten-minute canary. Match canary duration to the burn rate you expect.
- **Continuous profiler overhead under an already-stressed system** can tip a borderline service over. Keep sampling cheap and validate the profiler's own footprint.
- **Native/off-heap leaks ignore `runtime.GC()` and `System.gc()`.** Forcing collection won't reclaim `mmap`/JNI/direct-buffer memory whose wrappers are still reachable — and a heap-growth test that only checks heap will miss it entirely.

---

## Apply it

1. Define the user or business outcome that **Memory Bugs** should improve.
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

- Which measurable outcome justifies investing in Memory Bugs?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
