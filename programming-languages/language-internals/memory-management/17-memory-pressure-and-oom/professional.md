# Memory Pressure & OOM — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Memory Pressure & OOM** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### Requests vs limits, and why limits should equal requests for memory

Kubernetes gives each container two memory numbers:

- **`requests.memory`** — what the scheduler *reserves*; it places the pod on a node with at least this much allocatable memory. Pure scheduling input.
- **`limits.memory`** — the cgroup `memory.max`; cross it and the container is OOM-killed. Pure runtime enforcement.

When `requests < limits`, the pod is allowed to *burst* above its reservation — using memory the scheduler never guaranteed it. This works until the node fills, at which point that burst memory isn't there, and the pod (or a neighbor) gets killed. The burst is a loan the node may not be able to honor.

**For memory specifically, setting `requests == limits` is the safest default.** Memory is incompressible — unlike CPU, you can't "throttle" a container to use less memory; you can only kill it. Making request equal limit means the scheduler reserves exactly what the cgroup will enforce: no surprise bursting, predictable placement, and the pod lands in the **Guaranteed** QoS class (below) with the strongest protection against eviction. The cost is lower bin-packing density — you can't oversubscribe — which is a deliberate, honest trade of utilization for predictability. Teams that oversubscribe memory to save on nodes are buying noisy-neighbor incidents.

### QoS classes and eviction order

Kubernetes derives a **Quality of Service class** from your requests/limits, and uses it to decide *who dies first* when a node runs low:

- **Guaranteed** — every container has `requests == limits` for both memory and CPU. Highest protection; evicted last.
- **Burstable** — at least one container has a request lower than its limit (or only a request). Can burst, evicted in the middle.
- **BestEffort** — no requests or limits at all. Uses whatever's left; evicted *first* and hardest.

Under **node memory pressure**, the kubelet evicts in order: BestEffort first, then Burstable pods that have exceeded their *requests* (ranked by how far over they are), and Guaranteed pods last. The practical lesson: a BestEffort pod is a sacrificial victim by design, and a Burstable pod that habitually runs above its request is volunteering to be evicted. If a pod matters, make it Guaranteed.

### Two ways a pod dies: OOMKilled vs node-pressure eviction

These look similar (pod gone, restart) but are *different mechanisms* with different fixes, and confusing them is the most common diagnostic error:

**1. OOMKilled (exit code 137) — cgroup-level, the kernel acts.**
The container exceeded *its own* `limits.memory`. The kernel's cgroup OOM killer `SIGKILL`s a process inside it (137 = 128 + signal 9). `kubectl describe pod` shows:
```
    State:          Waiting
      Reason:       CrashLoopBackOff
    Last State:     Terminated
      Reason:       OOMKilled
      Exit Code:    137
```
This is **about one container hitting its own limit**, regardless of node health. The fix lives with the container: raise the limit, fix the leak, or size the runtime correctly.

**2. Node-pressure eviction — kubelet-level, the orchestrator acts.**
The *node* (not the container) ran low on allocatable memory, so the kubelet proactively *evicts* whole pods to reclaim it before the node-wide OOM killer fires and kills things uncontrollably. The pod's status is `Evicted` with a message like `The node was low on resource: memory`. This is **about the node, not the container** — a perfectly well-behaved pod can be evicted because *neighbors* overran. The fix lives with the node/scheduling: better requests, fewer oversubscribed neighbors, more node memory.

Same symptom (pod restarted), opposite root cause (my limit vs the node's capacity). Always check the *reason* field, not just that a restart happened.

### Noisy neighbors and node-level pressure

A node packs many pods. If pods are Burstable and oversubscribed, several can burst simultaneously and exhaust node memory even though each is "within its limit." The result is collateral damage: a well-behaved Guaranteed pod is fine, but Burstable/BestEffort neighbors get evicted, and if eviction can't keep up, the node's *global* OOM killer fires and can kill anything — including processes the kubelet wanted to protect. This is the **noisy neighbor** problem, and it's the strongest practical argument for `requests == limits` on anything that matters: oversubscription externalizes your risk onto your neighbors.

---

## Diagnosis Playbook

When a process or pod dies on memory, work the evidence in order:

1. **Get the death reason, not just the symptom.** `kubectl describe pod` → look at `Last State / Reason` (`OOMKilled` vs `Evicted`) and `Exit Code` (137 = OOM-kill). For bare metal/VM: `dmesg -T | grep -i "out of memory"` for the `Killed process … anon-rss:…` line — it names the victim, its RSS, and the triggering cgroup.

2. **OOMKilled vs Evicted?** `OOMKilled`/137 → *this container* hit *its* limit (cgroup). `Evicted` → the *node* ran low and the kubelet evicted (look at the node and its neighbors). Different root cause, different owner.

3. **Leak vs spike vs undersized limit.** Plot RSS over time:
   - **Leak** — monotonic upward trend across hours/restarts; RSS never plateaus. → find the leak.
   - **Spike** — sharp transient correlated with a traffic/job event. → bound the spike (load shed, cap request size, backpressure).
   - **Undersized limit** — RSS plateaus at a sane steady state that simply exceeds the configured limit; same peak every restart. → raise the limit / right-size.

4. **Heap vs native (managed runtimes).** Compare runtime heap-used to container RSS. A large, growing gap = native/off-heap is the problem; the heap profiler will lie to you. Use NMT (JVM) / `runtime.MemStats` + RSS (Go).

5. **Pressure, not just usage.** Check PSI (`/proc/pressure/memory`, or cgroup-scoped `memory.pressure`) and `vmstat 1` (`si`/`so` for thrash). Sustained `full` PSI or heavy swap-in/out means you're stalling on memory well before any kill.

---

## Config Recipes

**Go service in Kubernetes — `GOMEMLIMIT` matched to the cgroup limit.**
Set the soft limit to ~90% of `memory.max` so Go's GC collects hard before the kernel kills. With `requests == limits`:
```yaml
resources:
  requests: { memory: "512Mi" }
  limits:   { memory: "512Mi" }
env:
  - name: GOMEMLIMIT
    value: "460MiB"      # ~90% of 512Mi, leaving margin for non-heap + spike
  # GOGC can stay default; GOMEMLIMIT acts as the backstop
```
The downshift to ~90% reserves headroom for Go's stacks, runtime structures, and short-lived allocation spikes between GC cycles.

**JVM in a container — size relative to the limit, leave native headroom.**
```yaml
resources:
  requests: { memory: "2Gi" }
  limits:   { memory: "2Gi" }
env:
  - name: JAVA_TOOL_OPTIONS
    value: >-
      -XX:+UseContainerSupport
      -XX:MaxRAMPercentage=75.0
      -XX:MaxMetaspaceSize=256m
      -XX:NativeMemoryTracking=summary
```
`MaxRAMPercentage=75` caps the heap at ~1.5Gi of the 2Gi container, deliberately reserving ~512Mi for metaspace, thread stacks, direct buffers, and JIT code. `MaxRAMPercentage=100` would guarantee a cgroup kill.

**Reading an OOM line from `dmesg`.**
```
Out of memory: Killed process 2847 (java) total-vm:4521088kB, anon-rss:1987456kB, file-rss:12044kB, ...
oom-kill: ... oom_memcg=/kubepods/burstable/pod3f.../...,task_memcg=...,task=java,...
```
`anon-rss` (~1.9Gi here) is the real footprint; `oom_memcg` names the cgroup that hit its limit (confirming it's a *cgroup* OOM, not node-wide). `total-vm` (virtual) is large and irrelevant.

**Protecting / sacrificing a process with `oom_score_adj`.**
```bash
# Make a critical daemon (near) unkillable by the OOM killer:
echo -1000 > /proc/$(pidof critical-agent)/oom_score_adj
# Volunteer a batch worker to be killed first under pressure:
echo  1000 > /proc/$(pidof batch-worker)/oom_score_adj
```
Every process you protect pushes the kill onto another — use sparingly and deliberately.

---

## Best Practices

- **`requests == limits` for memory** on anything that matters → Guaranteed QoS, predictable scheduling, no surprise bursting, last to be evicted.
- **Right-size limits from observed working set**, not from a template or a guess. Measure peak RSS under realistic load, add headroom, set the limit there.
- **Never let the managed heap equal the container.** Reserve 25–35% (JVM) or ~10% (Go) for memory the runtime doesn't count.
- **Always read the *reason*, not just the restart.** `OOMKilled` (my limit) and `Evicted` (node pressure) demand different fixes.
- **Disable disk swap on latency-sensitive nodes** (fast clean kill > slow thrash livelock), or use zram/zswap if you need spike absorption.
- **Alert on soft limits and PSI**, not on the kill. The kill is the incident; PSI and soft-limit breaches are the early warning.
- **Compare heap-used to RSS continuously.** The gap is native memory; a growing gap is the early signal of off-heap trouble before it kills.

---

## Edge Cases & Pitfalls

- **Bumping the limit forever to stop CrashLoopBackOff** hides a leak. If RSS trends upward across restarts, raising the limit just delays the kill; find the leak.
- **Raising `-Xmx` to fix a cgroup OOM makes it worse** when the cause is off-heap — less room for native memory, sooner kill.
- **A pod evicted, not OOMKilled, is innocent.** Don't tune the evicted pod; fix the node's oversubscription / neighbors.
- **`kubectl top` lags and can mislead.** It samples; a fast spike-to-kill may not appear. Use it for trends, the OOM event for the kill.
- **JVM that ignores cgroup limits** (very old JDK or `UseContainerSupport` disabled) sizes the heap from the host → instant kill on a large multi-tenant node. Verify the JDK version.
- **Multi-container pods share the pod-level limit** in some configurations; a sidecar's growth can OOM the main container. Account for every container in the pod's budget.
- **Init/warm-up spikes exceed steady state.** A limit sized for steady-state RSS can OOM during cache warm-up or a startup migration; size for the warm-up peak, not the calm middle.

---

## Apply it

1. Define the user or business outcome that **Memory Pressure & OOM** should improve.
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

- Which measurable outcome justifies investing in Memory Pressure & OOM?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
