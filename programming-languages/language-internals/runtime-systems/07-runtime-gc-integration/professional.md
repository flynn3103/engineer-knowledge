# Runtime ↔ GC Integration — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Runtime ↔ GC Integration** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Metadata Economics: Budgeting GC Info

Every safepoint needs a stack map. A large server with hundreds of MB of JIT code can accumulate comparable amounts of GC metadata if encoded naively. Professionals treat this as a budget with knobs:

- **Encoding.** Bitmaps for "is-pointer" per slot; delta-encode adjacent safepoints (nearby PCs differ in a slot or two); deduplicate identical maps via a shared dictionary; pack derived-pointer base references compactly.
- **Granularity.** *Fully-interruptible* code has many safepoints (small TTSP, big maps). *Partially-interruptible* code (safepoints only at calls) shrinks maps but lengthens worst-case TTSP. The .NET JIT chooses per-method; HotSpot tiers (interpreted → C1 → C2) change safepoint density. This is a **map-size vs TTSP** dial.
- **Lazy materialization.** Some engines store compressed maps and decode on demand during a GC, trading decode CPU for resident size.
- **Code-cache pressure.** GC info competes with code for cache and memory; on memory-constrained deployments it's a real constraint, not an afterthought.

The professional question is never "do we have maps?" but "what is our maps budget, and what TTSP and stop-granularity does it buy?"

### 2. Safepoint Protocol Design

Bringing threads to a halt is a small agreement protocol. Design dimensions:

- **Poll mechanism.** Flag (portable, branchy), page-trap (single instruction, hardware-forced), or signal-based (Go async preemption; stops even poll-free code). Each has a different *worst-case* TTSP and platform dependency.
- **Global vs per-thread.** A global STW stops everyone. **Thread-local handshakes** (HotSpot) stop and operate on one thread at a time — essential for concurrent collectors (ZGC/Shenandoah) that want to scan a thread's roots without halting the world. Per-thread polling pages let the runtime arm individual threads.
- **Hijacking** (.NET) handles threads about to return: rewrite the return address so they enter the runtime on return, covering call-free stretches without a poll there.
- **Native transitions.** A thread in native code can't poll. The runtime tracks each thread's state (in-managed / in-native / transitioning). A thread *in native* is treated as already-safe (the GC can scan/relocate without it), but the *transition back* must synchronize: the thread, on return, checks whether a GC is in progress and blocks if so. Get this state machine wrong and you either corrupt memory (scan a thread mid-transition) or hang (miss a thread).

The deliverable is a **TTSP distribution**, not a single number. Your pause-time tail is dominated by the slowest thread under the worst case, so you design the protocol around stragglers: counted-loop safepoints, async preemption, bounded native critical sections, and per-thread handshakes to avoid one straggler stalling the world.

### 3. The Barrier ABI: A Codegen ↔ GC Contract

A write or read barrier is emitted by codegen but defined by the GC. At scale this is a *formal contract*:

- **Inputs/outputs.** What registers hold the object, the field address, the value; what the barrier returns (load barriers return the corrected pointer).
- **Clobbers.** Which registers the barrier may destroy. Codegen must save live values around the barrier accordingly. An under-specified clobber set is a silent miscompile.
- **Allowed operations.** May the barrier *allocate*? *Safepoint*? Usually the fast path may do neither (it must be leaf-like and non-blocking); only the out-of-line slow path may. If the fast path could safepoint, you'd need a map *inside the barrier*, which is usually forbidden by design.
- **Elision rules.** The contract specifies when codegen may omit the barrier (init stores into non-escaped allocations, null stores, same-region stores). These rules must be *exactly* aligned between codegen and GC, or codegen omits a barrier the GC needed → a live object freed.
- **Out-of-line layout.** Fast path inline, slow path in a stub, predicted-not-taken. The contract pins this so profiles and code size are predictable.

Professionals write this down, generate codegen and GC from a shared spec where possible, and **fuzz/stress test** it (run GC at every safepoint, randomize timing) because the failure mode is a rare, data-dependent, memory-corrupting crash.

### 4. Allocation Path Co-Design

Throughput is dominated by allocation, and allocation is co-designed with collection:

- **TLAB.** Each thread gets a private bump region. Allocation is: `if (top + size <= end) { p = top; top += size; }` — a few instructions, inlined, lock-free. TLAB *size* is tuned (too small → frequent slow paths and contention on the shared heap; too big → wasted memory and worse locality, plus larger "retained" slop at a GC).
- **Bump-pointer layout.** Works because the collector keeps a contiguous arena (copying/compacting young gen). The allocator and collector agree on the arena's shape; a non-moving collector can't bump-allocate as freely and uses free-lists, which are slower per-allocation.
- **Slow-path / GC handoff.** When the TLAB is exhausted, the slow path requests a new TLAB; if the heap is full, this triggers (or waits on) a GC. The handoff must be a safepoint-clean transition — the allocating thread may itself become the trigger for STW.
- **Allocation-site sampling.** Profilers (and some policies) sample 1-in-N bytes by maintaining a per-thread "bytes until next sample" counter decremented in the fast path; when it crosses zero, the slow path records a stack and possibly applies a policy. This must be near-free in the common case (a subtract and a predicted-not-taken branch) — itself a codegen/runtime contract.

The professional lever: **allocation rate is the GC's input.** Halving allocation roughly halves GC frequency, which roughly halves pause frequency and barrier executions. Capacity planning budgets allocation rate against the pause-time SLO.

### 5. Pacing: When To Start, Not Just How To Stop

A concurrent collector must *start early enough* to finish before the heap fills, or it falls back to an STW collection (a latency cliff). This is **GC pacing**: a feedback loop estimating allocation rate and collection speed to choose the trigger heap occupancy. Go's pacer (the `GOGC` / soft-memory-limit machinery), G1's prediction model, and ZGC's allocation-rate-driven start are all pacers. Pacing is part of the integration because it consumes runtime signals (allocation rate via the TLAB slow path, mark progress via barrier queues) to drive the collector. A mistuned pacer turns a concurrent collector into an STW one under load — a classic production incident.

### 6. Operating The Interface: The SLO View

A pause-time SLO decomposes into integration terms:

```text
visible_pause ≈ time_to_safepoint            (protocol: stragglers, native)
              + STW_phase_work                (root scan, flips, etc.)
              + (for concurrent) almost nothing else, IF pacing kept up
throughput_loss ≈ barrier_cost * pointer_op_rate
                + allocation_fast_path_overhead
                + concurrent_GC_CPU_share
```

You budget each term, monitor each in production (safepoint logs, barrier CPU via profiling, allocation-rate counters, pacer state), and alert on each. The runbook for "p99.9 pause regression" walks this decomposition: split TTSP from STW work; if TTSP, find the straggler; if STW work, examine root-set size and concurrent-phase fallbacks; if it's actually throughput, profile barriers and allocation.

### 7. Cross-Cutting Failure Modes At Scale

- **TTSP stragglers** from counted loops, long native calls, page-fault stalls during a poll, or a descheduled thread (noisy neighbor) that can't reach a poll. Mitigations: async preemption, per-thread handshakes (don't let one straggler stall the world), bounded native sections, and CPU isolation.
- **Pacer fallback to STW** under an allocation-rate spike; mitigations: headroom, soft memory limits, allocation-rate alerting.
- **Barrier hot spots** in pointer-graph mutation; mitigations: representation changes, conditional card marking, collector choice.
- **Metadata bloat** crowding the code cache on memory-tight nodes; mitigations: partially-interruptible regions, map compression.
- **Native-transition races** corrupting memory or hanging; mitigations: rigorous state-machine review and stress testing.

### 8. The Generational Twist For Load-Barrier Collectors

A professional note tying threads together: pure load-barrier collectors (early ZGC) were *non-generational*, scanning the whole heap each cycle — fine for latency but costly in CPU/allocation-heavy workloads. **Generational ZGC** adds a young generation, which *re-introduces a write barrier* (to track old→young pointers) on top of the load barrier. The integration lesson: collectors evolve by *adding* interface obligations (another barrier, more metadata) to buy efficiency, and your codegen/runtime must absorb each new obligation. Choosing a collector is partly choosing which barriers your hot code will pay.

---

## Code Examples

### Measuring the TTSP distribution, not the mean (JVM)

```bash
# Per-safepoint detail; post-process to get a TTSP histogram, not just the average.
java -Xlog:safepoint=info:file=safepoint.log:tags,uptime \
     -XX:+PrintGCApplicationStoppedTime -jar service.jar

# Then extract "Reaching safepoint" values and build a p50/p99/p99.9.
# A healthy service has TTSP p99.9 in the low single-digit ms; a straggler shows as a long tail.
```

The discipline: a 1 ms *mean* TTSP with a 400 ms *p99.9* is a straggler problem, invisible if you only look at the mean. SLOs live on the tail.

### Tuning the allocation fast path (TLAB sizing, JVM)

```bash
# Observe TLAB behavior: fast-path allocs, slow-path refills, waste.
java -Xlog:gc+tlab=trace -jar service.jar

# Knobs:
#   -XX:+UseTLAB (default on), -XX:TLABSize=..., -XX:-ResizeTLAB to pin a size,
#   -XX:TLABWasteTargetPercent=... to trade slow-path frequency vs end-of-TLAB waste.
```

If logs show frequent slow-path refills, the TLAB is too small for the thread's allocation rate (contention on the shared heap, more atomic ops). If they show high waste, it's too big (memory and locality cost). This is the allocation half of the co-design in operational form.

### Allocation-rate budgeting (Go)

```bash
# gctrace shows heap growth and GC frequency; allocation rate drives both.
GODEBUG=gctrace=1 ./service
# Lines: gc N @t s, heap sizes, and the wall/CPU time. Rising frequency under load
# means rising allocation rate -> tune GOGC / GOMEMLIMIT or cut allocations.

# Pprof the allocation profile to find the hot allocation sites:
go tool pprof -alloc_space ./service profile.pb.gz
```

The professional move: attack the top allocation sites (object reuse, `sync.Pool`, value semantics) to lower GC frequency *and* write-barrier execution count simultaneously.

### A barrier ABI, specified as pseudocode contract

```text
# Contract between CODEGEN and GC for the reference-store barrier.
# Inputs : OBJ in reg R_obj, FIELD_OFFSET imm, VAL in reg R_val
# Output : none (write barrier) ; corrected ref in R_ret (load barrier)
# Clobbers (fast path): R_scratch1 only. Codegen must NOT keep a live value there.
# Fast path MAY NOT: allocate, safepoint, block, throw.
# Slow path (out-of-line stub) MAY: allocate, safepoint, take locks.
# Elision: codegen MAY omit iff
#   (a) store initializes a freshly-allocated, not-yet-published object, OR
#   (b) value is statically null AND collector ignores null edges.
# Any deviation from (a)/(b) is a CORRECTNESS bug (live object may be freed).
```

Pinning this contract is what lets the codegen and GC teams ship independently. The elision clause is the dangerous one: it must be *identical* on both sides.

### Bounding native sections to protect TTSP (JNI)

```c
/* A long native loop here would either block a moving GC (if it pins) or,
   if it doesn't transition, delay the thread's return-side safepoint check. */
JNIEXPORT void JNICALL Java_X_process(JNIEnv* env, jobject self, jbyteArray data) {
    jsize n = (*env)->GetArrayLength(env, data);
    /* Copy out instead of holding a Critical (pinning) region across heavy work. */
    jbyte* buf = malloc(n);
    (*env)->GetByteArrayRegion(env, data, 0, n, buf);  /* no pin held during compute */
    heavy_compute(buf, n);                              /* GC can run/move freely */
    free(buf);
}
```

Using `GetByteArrayRegion` (copy) instead of `GetPrimitiveArrayCritical` (pin) keeps a moving collector unblocked during `heavy_compute` — a deliberate TTSP/throughput tradeoff.

---

## Coding Patterns

### Pattern 1: SLO decomposition runbook

```text
ALERT: p99.9 pause > SLO
  1. Split TTSP vs STW work (safepoint log).
  2. TTSP tail?  -> find straggler thread:
        - counted/poll-free loop?  enable strip mining / async preempt
        - long native call/pin?     bound it / copy-out
        - descheduled (noisy nbr)?  CPU isolation / pinning
  3. STW work big? -> root-set size, concurrent-phase fallback (pacer), heap sizing
  4. Throughput regressed (not pause)? -> profile barrier CPU + allocation rate
NEVER reach for GC flags before step 1-2.
```

### Pattern 2: Cut allocation rate to cut everything downstream

```go
// Reuse buffers; fewer allocations -> fewer GCs -> fewer pauses + fewer barriers.
var bufPool = sync.Pool{New: func() any { return make([]byte, 0, 4096) }}

func handle(req *Request) {
    b := bufPool.Get().([]byte)[:0]
    b = serialize(b, req)
    write(b)
    bufPool.Put(b)        // reuse instead of re-allocating
}
```

### Pattern 3: Specify-then-fuzz the barrier contract

```text
# CI gate for runtime developers:
- Run the test suite with "GC at every safepoint" mode (stress flag).
- Randomize relocation so every load barrier slow path executes.
- Run under TSan/ASan equivalents for the runtime.
- Fuzz the thread schedule around native transitions.
A barrier/elision bug must be reproduced by the harness, never by luck in prod.
```

### Pattern 4: Keep TTSP bounded by design

```text
- No hand-written poll-free assembly hot loops.
- Bounded native critical/pinning sections (copy-out for heavy work).
- Prefer per-thread handshakes for root scan so a straggler is local, not global.
- Enable counted-loop safepoints / async preemption per the engine.
```

---

## Best Practices

- **SLO the interface, not the algorithm.** Express pause and throughput budgets in interface terms (TTSP, STW work, barrier CPU, allocation rate) and monitor each.
- **Design for the slowest thread.** Tails come from stragglers; eliminate poll-free loops and unbounded native sections; use per-thread handshakes so one straggler is contained.
- **Treat GC metadata as a budget.** Pick fully- vs partially-interruptible regions deliberately; compress maps; watch code-cache pressure on tight nodes.
- **Make the barrier ABI explicit and adversarially tested.** Clobbers, allowed operations, and elision rules must be identical across codegen and GC, and validated by stress/fuzz harnesses.
- **Co-design and tune the allocation path.** Right-size TLABs from telemetry; remember allocation rate is the GC's throttle — cutting it cuts pauses, barriers, and CPU together.
- **Mind the pacer.** Keep headroom and alert on allocation-rate spikes so a concurrent collector never falls back to STW.
- **Bound native interop.** Prefer copy-out over long pinning; design handle lifetimes; review native-transition state machines like the consensus protocols they are.

---

## Edge Cases & Pitfalls

- **Mean-vs-tail TTSP blindness.** Dashboards showing average TTSP hide the one straggler that owns p99.9. Always histogram the tail.
- **Pacer cliff under load spikes.** A concurrent collector silently degrades to STW when allocation outruns the pacer's prediction — a sudden latency cliff, not a gradual slope. Headroom and allocation-rate alerts are the guard.
- **Elision-rule skew.** If codegen's barrier-omission rules drift from the GC's expectations (e.g., after a "publication" optimization changes when an object escapes), a needed barrier is dropped and a live object is freed — extremely rare, data-dependent, catastrophic.
- **TLAB sizing pathologies.** Too-small TLABs cause shared-heap contention and slow-path storms under many threads; too-large TLABs waste memory and inflate retained slop captured at each GC. Both show in `gc+tlab` logs.
- **Native-transition races.** Scanning or moving a thread that is mid-transition (managed↔native) corrupts memory; missing a transitioning thread hangs the GC. The state machine must be exhaustively correct.
- **Metadata bloat on constrained nodes.** Fully-interruptible code plus large JIT output can make GC info a non-trivial fraction of resident memory; partially-interruptible regions trade it back for TTSP.
- **Allocation-site sampling skew.** A naive byte-counter sampler biases toward large allocations or specific sites; geometric/randomized intervals are needed for unbiased profiles, and the counter cost must stay off the hot path.
- **Generational-load-barrier double cost.** Generational ZGC pays *both* a load barrier and a young-gen write barrier; a workload that is both load- and store-heavy can see compounded overhead — measure before assuming "newer collector = strictly faster."

---

## Apply it

1. Define the user or business outcome that **Runtime ↔ GC Integration** should improve.
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

- Which measurable outcome justifies investing in Runtime ↔ GC Integration?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
