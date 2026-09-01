# Continuous Profiling — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Continuous Profiling** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Continuous Profiling Roadmap](README.md)
> **Focus:** Continuous profiling as a *fleet-wide engineering substrate* — the fourth observability signal rolled out to every process in the org. eBPF whole-system profiling that needs zero instrumentation. The pprof format as lingua franca and the emerging OpenTelemetry profiling signal. The storage and *cost* of profiles at scale. The deploy gate that fails a canary on a CPU regression. Profile-to-trace correlation across all four signals. The governance, labeling, and security of a fleet of always-on profilers.

---

## Core Concepts

### 1. eBPF moves profiling from "in every process" to "once per node, for everything"

The senior model is per-process: each service imports an SDK or exposes pprof. The fleet-scale model is **agent-based eBPF**: a single node-level DaemonSet runs a `perf_event` BPF program that samples the on-CPU stack of *whatever* is running — your Go service, a stripped C sidecar, a Python interpreter, the kernel itself — with **zero instrumentation in any of them**. One agent profiles the entire node. This is the difference between "instrument 200 services in 12 languages" and "deploy one DaemonSet." For a heterogeneous fleet, eBPF is the only rollout that scales to *everything* without per-service work.

### 2. The pprof format is the contract; everything speaks it

Just as OTel semantic conventions let one metric query span the fleet, the **pprof protobuf format** is the profiling lingua franca: Go emits it, Parca and Pyroscope store it, `go tool pprof` reads it, the OTel profiling signal is designed around it. Standardizing on pprof (and increasingly OTLP profiles) means your storage, query, and diff tooling is *language-agnostic* — a Rust profile and a Java profile are the same shape in the store. The format *is* the interoperability.

### 3. A profile store is a TSDB for flame graphs, and it has a cardinality bill

A continuous profile store is *metrics for code paths*: time-indexed series keyed by profile-type + labels, stored columnarly (FrostDB, Pyroscope's store). It has the same cost structure as a metrics TSDB — **series count drives storage and RAM**, and an unbounded label (`pod`, raw `endpoint`) is the same cardinality bomb here as on a metric. The professional designs profile *labels* the way they design metric attributes: bounded, queryable, fail-closed. See [Telemetry Cost and Sampling Strategy](../14-telemetry-cost-and-sampling-strategy/README.md).

### 4. The overhead budget becomes a fleet-wide SLO with a kill switch

Senior level kept *one service* under ~2%. Fleet level makes overhead a **governed SLO**: measured continuously across the fleet, alerted when breached, and *automatically disable-able* (a kill switch) per-service or fleet-wide when a profiler misbehaves (a runaway DWARF unwind, a JIT that confuses the agent). Always-on is only sustainable if you can prove — and enforce — that it stays cheap. The kill switch is what lets you say "yes" to default-on.

### 5. Diff profiles are a deploy gate, not just a debugging tool

The senior uses a diff flame graph reactively after a regression. The professional **wires the diff into CI/CD**: the canary's profile is compared to the baseline's, and a function whose CPU share grew beyond a threshold *fails the deploy automatically*. A diff is a **delta** — it shows what *grew* (red) and *shrank* (blue) between two profiles — and that delta is exactly the signal a regression gate needs. Profiling shifts from "explain the regression after it ships" to "block the regression before it ships."

### 6. The fourth signal's superpower is correlation, not standalone use

A profile alone answers "which line burned the resource?" Its *fleet* value is the **hop**: a metric alerts, a trace localizes to a span, and a **span profile** shows the flame graph *for that exact span*. The OTel profiling signal bakes trace correlation into the spec. The professional's job is to make this descent — metric → trace → profile → log — a one-click path across the whole fleet, not an archaeology project. The four signals are one system; profiling closes the "what was the code doing?" gap.

### 7. Profiles are sensitive data and a privileged endpoint — govern them

A stack frame can contain a function name, a file path, sometimes an argument-derived label, and the profiling endpoint reveals *exactly what your code does*. A profile store is a high-value target and a potential PII leak. The professional treats profiling endpoints as **privileged** (auth, internal-only, never public), audits **labels for PII**, and applies **access control** to the store — the same rigor you'd apply to logs, because a profile is arguably more revealing.

---

## Fleet-Wide Rollout Strategy

Rolling continuous profiling out to a fleet is an org project, not a config change. The decisions that define it:

### Opt-in vs default-on

| Posture | When | Trade-off |
|---------|------|-----------|
| **Opt-in (per service)** | Early adoption, untrusted overhead, regulated workloads | Slow coverage; the services that most need it (the ones nobody owns) never opt in |
| **Default-on (fleet-wide)** | Mature overhead story, agent-based eBPF, a kill switch exists | Full coverage immediately; *requires* a proven overhead SLO and a kill switch to be safe |

The professional goal is **default-on**, because the value of continuous profiling is *coverage* — the bug lives in the service nobody thought to instrument. But default-on is only responsible once you have (a) a measured, low overhead budget, and (b) a kill switch to disable a misbehaving profiler instantly. eBPF agent-based profiling makes default-on dramatically easier: there's nothing to opt *into* per service — the agent profiles everything on the node.

### Staged rollout

```text
   STAGE 1  one node, one cluster, agent-based eBPF, profiles to a dev store
            → measure REAL overhead under REAL traffic (not a benchmark)
   STAGE 2  one tier-3 service fleet, default-on, overhead SLO dashboards live
            → prove the SLO holds; exercise the kill switch deliberately
   STAGE 3  expand by tier; SDK-based profiling for languages eBPF unwinds poorly (JITs)
            → symbolization pipeline + debuginfo upload working end-to-end
   STAGE 4  default-on fleet-wide; deploy-gate diff checks on tier-1 services
            → profiling is now infrastructure, governed by SLO + access control
```

### The overhead budget as a fleet-wide SLO

The single non-negotiable: **measure the cost of profiling and bound it as an SLO.** Concretely:

- **CPU:** sampling at ~19–100 Hz typically lands well under 1% for eBPF agents; SDKs vary. Measure it per-process (CPU with vs without the profiler) and SLO the p99.
- **Memory:** the agent's in-kernel maps and userspace symbol caches; DWARF unwinding tables can be large — budget RSS per node.
- **Network:** profile upload volume (the storage section prices this).

Alert when the SLO is at risk, and have the **kill switch** (a feature flag / agent config that disables profiling per-service or fleet-wide) ready *before* you go default-on. The kill switch is the thing that makes default-on a defensible decision rather than a gamble.

---

## Agent-Based vs SDK-Based Profiling

The defining architectural choice at fleet scale: profile processes *externally* with a node agent, or *internally* with an in-process SDK.

| Dimension | **Agent-based (eBPF DaemonSet)** | **SDK-based (in-process)** |
|-----------|----------------------------------|----------------------------|
| Instrumentation | **None** — profiles any process on the node | Per-service: import a library, push profiles |
| Language coverage | Any compiled binary, kernel included; JITs are harder | Whatever the SDK supports; rich runtime context |
| Rollout | One DaemonSet, fleet-wide instantly | N services × M languages to instrument |
| Symbolization | Needs debuginfo (server-side or uploaded) | Often has symbols in-process |
| Runtime context | Limited (kernel sees stacks, not app labels easily) | Rich (can attach app-level labels, span IDs) |
| Off-CPU / custom profiles | Harder (eBPF off-CPU is possible but more work) | Native (Go off-CPU, heap, mutex profiles built in) |
| Overhead control | Centralized at the agent | Per-service; varies by SDK |
| Best for | Heterogeneous fleet, stripped binaries, default-on coverage | Rich language-specific profiles (heap, off-CPU, span labels) |

**The professional answer is usually both, layered.** Agent-based eBPF for *universal CPU coverage* — the floor that profiles everything including the C sidecar nobody owns. SDK-based for the *rich profiles eBPF can't easily get* — Go heap/off-CPU/mutex, JVM allocation with full symbols, span-labeled profiles for trace correlation. The eBPF agent gives you breadth (every process, zero work); the SDK gives you depth (every profile type, full context) where it matters.

---

## eBPF Whole-System Profiling in Depth

This is the professional-tier capability that doesn't exist at junior/middle: profiling **any language, any runtime, even stripped C and the kernel, with zero instrumentation**, from a node-level agent. This is the kernel tech the [Dynamic Instrumentation & eBPF](../13-dynamic-instrumentation-and-ebpf/README.md) roadmap covers in depth; here is the profiling-specific mechanics.

### How the eBPF perf-event profiler samples stacks in-kernel

```text
   perf subsystem fires a sampling event (e.g. every N CPU cycles, ~19-100 Hz)
                          │
                          ▼
   the kernel invokes the attached eBPF program (BPF_PROG_TYPE_PERF_EVENT)
                          │
                          ▼
   the eBPF program reads the CURRENT stack (user + kernel) via bpf_get_stackid /
   a custom unwinder, into a BPF map keyed by (pid, user_stack_id, kernel_stack_id)
                          │   (aggregation happens IN-KERNEL: identical stacks counted)
                          ▼
   userspace agent periodically drains the map, resolves pids → containers/services,
   symbolizes addresses → function names, converts to pprof, pushes to the store
```

The key properties that make this work fleet-wide:

- **Zero instrumentation.** The target process is never modified, recompiled, or restarted. The agent attaches to the *CPU*, not the application. A 10-year-old stripped C binary is profiled the same as a fresh Go service.
- **In-kernel aggregation.** Identical stacks are counted in a BPF map before crossing to userspace, so the agent isn't paying per-sample userspace cost — this is a big part of why eBPF profiling is so cheap.
- **Whole-system.** It captures the kernel stack too, so you see time spent in syscalls, the scheduler, the network stack — invisible to a userspace-only profiler.
- **One agent, every process.** As a DaemonSet, one agent per node profiles every container on it, mapping PIDs back to Kubernetes pods/services for labeling.

### The hard part: stack unwinding for arbitrary binaries

The eBPF program has to *walk the stack* of a process it knows nothing about. That is the central technical challenge of whole-system profiling, and it is where frame pointers vs DWARF (next section) becomes load-bearing. The agent must, in-kernel and fast, reconstruct `main → handler → query → scan` from raw stack memory — for a binary it didn't compile, possibly stripped, possibly a JIT.

### Where eBPF struggles, and why you still need SDKs

- **JIT runtimes (JVM, V8, .NET).** The JIT compiles bytecode to machine code at runtime; the eBPF unwinder sees machine addresses with no static symbol table, and the runtime's stack layout is non-standard. Agents add JIT-specific unwinders/agents (e.g. reading `perf-<pid>.map` files the JVM/V8 write), but coverage is harder than for AOT binaries. For deep JVM profiling, async-profiler (SDK-side) is still superior.
- **Interpreted languages (Python, Ruby).** The C-level stack shows the *interpreter* (`PyEval_EvalFrameEx`), not your Python functions. eBPF agents add interpreter-aware unwinders that walk the interpreter's frame objects to recover Python frames — clever, but interpreter-version-specific and fragile.
- **Off-CPU and non-CPU profiles.** eBPF *can* do off-CPU (sample on scheduler context-switch), heap, and lock profiling, but it's more work and less mature than the language runtime's built-in equivalents. The SDK path is often easier for these.

The professional takeaway: **eBPF agent for universal on-CPU coverage; SDKs to fill the JIT/interpreted/off-CPU gaps.**

---

## Stack Unwinding — Frame Pointers vs DWARF

Stack unwinding is *the* technical crux of whole-system profiling, and "the frame-pointer debate" is one of the more consequential performance arguments in systems engineering of the last few years.

### Frame-pointer unwinding (cheap, needs a register kept)

When a binary is compiled with frame pointers (`-fno-omit-frame-pointer`), the `rbp` register holds the base of the current stack frame, and each frame stores the caller's `rbp` — forming a linked list. Unwinding is a trivial, fast pointer-walk: follow `rbp` up the chain. This is cheap enough to do in-kernel on every sample.

**The catch:** keeping a frame pointer costs ~1 register and a small per-call overhead, so for decades compilers *omitted* it by default (`-fomit-frame-pointer`) as a micro-optimization. The result: most distro binaries shipped *without* frame pointers, and you couldn't cheaply unwind them.

### DWARF / `.eh_frame` unwinding (accurate, expensive)

Without frame pointers, you reconstruct the stack from **DWARF Call Frame Information** (`.eh_frame` tables) — per-instruction-address tables describing how to find the caller's frame. It's accurate and needs no register sacrifice, but it requires *interpreting a small bytecode program per frame per sample*, which is far too expensive to do naively in-kernel. eBPF agents implement DWARF unwinding by **pre-computing compact unwind tables** in userspace and shipping them into BPF maps so the in-kernel unwinder can do lookups quickly — a substantial engineering feat (Parca's and Pyroscope's DWARF unwinders).

### The frame-pointer debate

```text
   FRAME POINTERS ON                       FRAME POINTERS OFF (historical default)
   ─────────────────                       ─────────────────────────────────────
   + cheap, fast, in-kernel unwinding      + ~1 free register, tiny per-call save
   + works for stripped binaries           − unwinding needs DWARF tables (expensive)
   − ~1% runtime cost (varies; often less) − whole-system profilers struggle / DWARF
   → the modern consensus for profilable     → the reason eBPF profilers had to build
     fleets: TURN FRAME POINTERS ON          DWARF unwinders at all
```

The industry has swung toward **frame pointers on**: Fedora (39+) and Ubuntu (24.04+) re-enabled them distro-wide *specifically* to make continuous profiling cheap and accurate, judging the ~1% runtime cost worth the profilability. The professional decision for your own fleet: **compile your services with frame pointers** (`-fno-omit-frame-pointer`, or the runtime's equivalent), so the eBPF agent gets cheap, reliable unwinding — and fall back to DWARF unwinding only for third-party binaries you can't recompile.

### Go and JIT challenges

- **Go** historically had its own unwinding quirks (the runtime uses a non-standard calling convention and its own unwinder); modern Go binaries are generally unwindable by the agents, but Go is a frequent source of unwinding edge cases.
- **JITs** (covered above) have no static unwind tables for JIT-compiled code; the agent must consult runtime-emitted symbol maps. This is the least-reliable corner of whole-system unwinding.

---

## The pprof Format and the OTel Profiling Signal

### pprof: the lingua franca

The **pprof protobuf format** (from Go's pprof) became the de-facto profile interchange format. Its shape: a profile is a set of **samples**, each carrying a *stack* (list of locations → functions) and one or more *values* (e.g. cpu nanoseconds, alloc bytes), plus a **sample type** and **labels**. Because every major tool reads and writes pprof — `go tool pprof`, Parca, Pyroscope, the OTel signal — your storage, query, diff, and visualization tooling is *language-agnostic*. A Rust profile, a Python profile, and an eBPF profile are all pprof; one diff engine diffs them all.

```text
   pprof Profile {
     sample_type: [{cpu, nanoseconds}]
     sample:      [{ stack:[loc1,loc2,...], value:[cpu_ns], label:{...} }, ...]
     location/function/mapping tables   (for symbolization)
   }
   → samples aggregate by identical stack; value = the resource. The diff is a DELTA of values.
```

### The OpenTelemetry profiling signal (OTLP profiles)

OTel is standardizing **profiling as the fourth OTLP signal**, alongside metrics, traces, and logs. The significance for a fleet:

- **One protocol for all four signals.** Apps/agents emit OTLP; the OTel Collector receives, processes, and routes profiles just like the other signals — the same collector-in-the-middle control plane you use for metrics now governs profiles.
- **Built-in trace correlation.** The OTLP profiles data model carries trace/span context, so **profile-to-trace correlation is part of the spec**, not a bolted-on hack. A profile sample can reference the span active when it was taken — the foundation of span profiles.
- **pprof-aligned.** The OTLP profiles model is designed to interoperate with pprof, so the existing ecosystem isn't thrown away.

The professional positioning: **standardize the fleet on OTLP profiles where supported**, routed through the OTel Collector, so profiling rides the same pipeline, labeling discipline, and correlation model as your other three signals. The fourth signal becomes a first-class citizen of the observability platform, not a separate silo.

---

## Storage and Cost of Profiles at Scale

Continuous profiling produces a *lot* of data — far more raw volume than metrics — and at fleet scale the storage bill is a real budget line. The professional prices it before turning on default-on.

### The volume math

A single CPU profile is a set of aggregated stacks. The volume scales as:

```text
   raw volume ≈  processes × profile_types × profiles_per_minute × avg_profile_size
              ×  (unique stacks per profile drives size)

   example:  500 processes × 1 type (cpu) × 4 profiles/min × ~15 KB compressed
           ≈ 30 MB/min ≈ 43 GB/day  (CPU only; heap/off-CPU multiply this)
```

That is *raw ingest*; the store's job is to make it affordable to keep. The dominant cost lever is the same as metrics: **profile-series cardinality** (profile-type × label set), because that determines how many distinct time-series the store indexes.

### Time-indexed columnar storage

Modern profile stores use **columnar storage** purpose-built for profile shape:

- **Parca / FrostDB** — an embedded columnar database (Apache Arrow / Parquet lineage) that stores pprof-shaped data column-wise, so queries that touch one label or one sample-type read only the relevant columns. Symbols are deduplicated and stored separately.
- **Pyroscope's storage** — its own time-series-of-profiles store, also column-oriented, with aggressive compression of repeated stacks.

Columnar layout is the right call because profile data is *highly repetitive* (the same stacks recur across samples and across time), so column compression and stack deduplication shrink it dramatically.

### Retention, downsampling, and symbol storage

| Cost component | Lever |
|----------------|-------|
| **Recent high-resolution profiles** | Keep full resolution for a short window (e.g. days–weeks) — this is where incidents and deploy diffs live |
| **Older profiles** | **Downsample** — merge into coarser time windows, keeping the flame graph shape but fewer time points; or drop low-value profile types |
| **Symbolization storage** | Debuginfo can be large; store it deduplicated and separate from samples (Parca's `debuginfod`-style symbol store), so identical binaries share one copy |
| **Profile-series cardinality** | Bound labels (no raw `pod`/`endpoint`); fail-closed label allow-lists, exactly as for metrics |

### The cost trade-off versus metrics and traces

```text
   METRICS  — cheapest per unit; tiny payloads, huge aggregation. Always-on, full fleet, fine.
   TRACES   — sampled (1-10%) precisely BECAUSE per-request volume is high.
   PROFILES — high raw volume, but COLUMNAR + dedup + downsampling make always-on viable
              at ~1-2% overhead; the value (which LINE) justifies the storage.
   LOGS     — volume-driven; often the most expensive to retain at full fidelity.
```

The professional framing: profiling's *storage* cost is real but tamed by columnar storage, stack dedup, and downsampling, while its *compute* overhead stays at the sampling-profiler ~1–2%. Price it against the other signals deliberately — see [Telemetry Cost and Sampling Strategy](../14-telemetry-cost-and-sampling-strategy/README.md) for the cross-signal budget. The right default is "profile everything, keep recent at high resolution, downsample the rest."

---

## Diff Profiles in the Deploy Gate

The senior uses a diff flame graph reactively. The professional makes it a **deploy gate** — automated regression detection in CI/CD.

### The mechanism

```text
   deploy canary (v_new) alongside baseline (v_old) under the same traffic split
                          │
                          ▼
   collect a CPU (and/or alloc) profile for EACH, over the same window, same labels
                          │
                          ▼
   compute the DIFF (delta of per-function values, normalized by total samples)
                          │
                          ▼
   for each function: Δ_share = share_new − share_old
                          │
                          ▼
   FAIL the deploy if any function's CPU share grew > threshold (e.g. +5 pp)
   or total on-CPU samples for the service grew > X% for equal request volume
```

The diff is a **delta** — that is precisely the regression signal. A function that was 8% of CPU and is now 22% lights up red in the diff; the gate fails the canary, and the engineer sees the exact function before the change reaches the full fleet.

### Normalization is the load-bearing detail

You cannot compare raw sample counts — the canary and baseline get different traffic. **Normalize to share-of-total** (fraction of samples), or normalize per unit of work (samples per request). A naive raw-count diff flags a function as "regressed" simply because the canary served more requests. The professional gate compares *shares* or *per-request* cost, never raw totals.

### Profile-based SLO guards

Beyond per-function diffs, you can guard fleet-level profiling SLOs:

- **Allocation regression:** alloc-profile `_sum` per request grew > X% → likely a new per-request allocation → GC pressure incoming.
- **A new hot frame:** a function absent from baseline now in the top-N of the canary → a new code path went hot.
- **Off-CPU regression:** time blocked on a lock/IO grew → a new contention point.

These become *gates* (block the deploy) or *alerts* (page on a fleet-wide profile regression), the same way DORA/SLO guards work for metrics.

---

## Correlating Profiles with Traces and Metrics

The fourth signal's fleet value is correlation. The professional wires the full descent.

### The metric → trace → profile → log descent

```text
   METRIC   p99 latency spiked at 14:32            (exemplar links to a trace)
      │
      ▼
   TRACE    the slow span is search-svc / db.query (carries trace_id, span_id)
      │
      ▼
   PROFILE  span profile FOR THAT SPAN: 60% in regexp.Compile   ← the line
      │
      ▼
   LOG      "search: recompiled pattern (cache miss)"           ← the why/context
```

### Span profiles — the profiling side of trace correlation

A **span profile** is a profile scoped to a single span (or to a trace), made possible because the profiler records the active **trace ID / span ID** on each sample (via pprof labels or the OTLP profiles trace-context field). Now "show me the flame graph for *this* slow span" is a query, not an estimate. This is the profiling equivalent of metric *exemplars* — exemplars take you metric→trace; span profiles take you trace→profile.

### The plumbing

- **Profiler must see trace context at sample time.** The SDK reads the active span from context and tags samples with `trace_id`/`span_id`. Exactly like metric exemplars, **if the profiler samples outside the span scope, the correlation is lost** — the sample has no trace ID. (eBPF agents have a harder time here, since the kernel doesn't naturally see the app's span context; this is one reason SDK-based profiling matters for correlation.)
- **Common labels across signals.** The four signals must share `service.name`, `service.version`, `deployment.environment`, `region` so a dashboard can pivot metric→trace→profile by the same identity. Label consistency across signals is a governance requirement (next section).
- **The collector ties it together.** Routing all four signals through the OTel Collector with shared resource attributes is what makes the one-click descent work fleet-wide.

The `observability-stack` skill covers wiring the four-signal correlation in a real stack; this page is the profiling slice of that story.

---

## The Full Relationship Map of the Four Signals

A precise map of when each signal — and continuous vs point-in-time profiling — pays off, because at staff level you allocate observability budget across all of them.

| Signal | Answers | Granularity | Cost model | When it pays |
|--------|---------|-------------|------------|--------------|
| **Metric** | "Is something wrong?" | aggregate number | cheapest; active series | Always-on, full fleet; the alert trigger |
| **Trace** | "Which span/service?" | one request's path | sampled (1–10%) | Localizing across services; the slow span |
| **Log** | "What happened to this event?" | one event | volume-driven, costly | The error message, the context, the audit |
| **Profile (continuous)** | "Which *line* burned the resource?" | function/line, aggregated | ~1–2% CPU + columnar storage | The hot function *in production*, fleet-wide, always |
| **Point-in-time profiling** | "Why is *this function* slow, and how do I fix it?" | function/line, one run | a developer's time | Optimizing a known hot path on a laptop/benchmark |

### Continuous vs point-in-time profiling

These are *complementary*, not competing:

- **Continuous profiling** ([this roadmap](README.md)) *finds* the hot function in production, fleet-wide, with real data and concurrency. It answers "where is the time going right now, across everything?"
- **Point-in-time profiling** ([Quality Engineering → Performance → Profiling](../../../On-Production/performance/01-profiling/README.md)) *fixes* a known hot function — the developer reproduces it on a laptop/benchmark, iterates with a profiler, and optimizes. It answers "why is this specific function slow and how do I make it fast?"

The workflow is: **continuous profiling (prod) finds it → point-in-time profiling (laptop) fixes it → continuous profiling (deploy gate) confirms the fix and guards against regression.** The `profiling-techniques` skill is the point-in-time-optimization counterpart; this roadmap is the always-on-discovery side.

### When *not* to reach for profiling

- The question is "what's the error?" → that's a **log**.
- The question is "which service is slow?" → that's a **trace** (then profile the slow one).
- The question is "is the SLO being met?" → that's a **metric**.
- Profiling answers *which line burned the resource* — reach for it after a metric/trace tells you *where*.

---

## Profile Labeling and Governance

A fleet of profiles is only queryable if everyone labels them the same way. Label drift is the same enemy here as metric-name drift on the metrics side.

### Profile labels are profile-series cardinality — design them like metric attributes

Every profile carries labels; the unique combination of profile-type + labels is a **profile series**, and series count drives storage and query cost. The rules are the metrics rules:

| Label | Keep? | Why |
|-------|-------|-----|
| `service.name`, `service.version` | **Yes** | The primary query/group-by; bounded; needed for diffs across versions |
| `deployment.environment`, `region` | **Yes** | Bounded; needed for slicing |
| `pod` / `instance` | **No (or short-retention)** | Churns on every roll → cardinality bomb; you rarely query per-pod flame graphs |
| raw `endpoint` / `user_id` | **No** | Unbounded → blows up profile-series count; analytics, not profiling labels |

Standardize a **profile-label allow-list** that *fails closed*, exactly like the metrics `AllowAttributeKeys` posture — anything not explicitly permitted is dropped before storage.

### Cross-signal label consistency

The labels on profiles **must match** the resource attributes on metrics, traces, and logs (`service.name`, `service.version`, `deployment.environment`, `region`). This is what lets a dashboard pivot from a metric to its profile by the same identity. Govern it the way the metrics fleet standard is governed: a shared resource-builder / agent config that stamps the same identity on all four signals.

### Multi-language fleet standards

- **One profile-label schema** across every language and the eBPF agent — the agent maps Kubernetes pod → service labels so agent-collected profiles carry the *same* labels as SDK-collected ones.
- **pprof / OTLP profiles** as the only on-the-wire format, so the store and tooling are language-agnostic.
- **One profile store and query layer** for the whole fleet (Parca/Pyroscope), not a per-team silo.
- **Governance owner.** Like the metrics standard, profiling is a platform team's product: the agent config, label schema, store, retention, and access policy are owned, versioned, and reviewed — not left to each service.

---

## Security and PII in Profiles

Profiles are *more* sensitive than people assume, and the profiling endpoint is privileged. This is a first-class fleet concern, not an afterthought.

### What a profile can leak

- **Source structure.** Function names, file paths, and the call graph reveal exactly how your system works — a gift to an attacker mapping your code.
- **Labels.** If someone labels profiles with `user_id`, `email`, or a raw request path, that PII lands in the profile store, queryable, and retained.
- **Argument-derived names.** Some profilers can capture limited argument context; symbol names sometimes embed constants. Stack frames can carry more than just `package.Function`.
- **The endpoint itself.** Go's `/debug/pprof` and equivalents let *anyone who can reach them* trigger a profile (a small DoS) and read internals.

### The controls

1. **Profiling endpoints are internal-only and authenticated.** Never expose `/debug/pprof` (or the SDK's push/pull endpoint) publicly — bind to localhost/an admin port behind auth. (The junior-level rule, now a fleet policy.)
2. **Label PII review.** Audit profile labels the way you audit log fields — no `user_id`/`email`/raw-path as a label. The allow-list enforces this *in code*.
3. **Access control on the store.** The profile store reveals your entire codebase's runtime behavior; gate read access (RBAC), and treat it as sensitive as the log store — arguably more so.
4. **Symbol/debuginfo handling.** Debuginfo uploaded for server-side symbolization reveals symbol names; store and transmit it with the same care as source.
5. **Compliance scope.** If you operate under PII/regulatory constraints, profiles are in scope — include the profile store in data-handling, retention, and deletion policies.

The mental model: **a profile is a description of what your code did for a real request.** Treat the profiling pipeline with at least the rigor you apply to logs, and remember that the profiling *endpoint* is a privileged interface, not a debugging convenience.

---

## Code Examples

### parca-agent — node-level eBPF profiler as a Kubernetes DaemonSet

```yaml
# parca-agent: one DaemonSet profiles EVERY process on EVERY node, zero app changes.
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: parca-agent
  namespace: parca
spec:
  selector:
    matchLabels: { app: parca-agent }
  template:
    metadata:
      labels: { app: parca-agent }
    spec:
      hostPID: true                      # see all host processes (required for whole-system)
      containers:
        - name: parca-agent
          image: ghcr.io/parca-dev/parca-agent:latest
          args:
            - --node=$(NODE_NAME)
            - --remote-store-address=parca.parca.svc:7070   # push profiles to the store
            - --remote-store-insecure
            - --profiling-cpu-sampling-frequency=19          # ~19 Hz: very low overhead
            # frame-pointer unwinding is cheap; DWARF unwinder is the fallback for FP-less binaries
          securityContext:
            privileged: true             # eBPF + perf_event require elevated privileges
          env:
            - name: NODE_NAME
              valueFrom: { fieldRef: { fieldPath: spec.nodeName } }
          volumeMounts:
            - { name: debugfs, mountPath: /sys/kernel/debug }   # eBPF/perf needs debugfs
      volumes:
        - name: debugfs
          hostPath: { path: /sys/kernel/debug }
```

The point: **one manifest, fleet-wide, default-on.** No service imports anything. `hostPID` + `privileged` are what let the agent see and unwind every process; the ~19 Hz sampling frequency is the overhead lever. This is why agent-based eBPF is the rollout that scales to "everything."

### Compile with frame pointers — make your fleet cheaply unwindable

```dockerfile
# C/C++: keep frame pointers so the eBPF agent unwinds cheaply (no DWARF tables needed in-kernel).
RUN gcc -O2 -fno-omit-frame-pointer -o myservice main.c

# Rust: keep frame pointers in the release profile.
# Cargo.toml:  [profile.release]  force-frame-pointers = true   (or RUSTFLAGS="-C force-frame-pointers=yes")

# Go: modern Go keeps frame pointers on amd64/arm64 by default — generally unwindable as-is.
```

The ~1% runtime cost of keeping frame pointers buys reliable, cheap whole-system unwinding. For binaries you can't recompile (third-party), the agent falls back to DWARF unwinding from `.eh_frame`.

### SDK-based push — Go service with rich profile types + trace correlation

```go
import (
    "github.com/grafana/pyroscope-go"
    "go.opentelemetry.io/otel/trace"
)

// SDK-based profiling FILLS THE GAPS eBPF can't easily get: heap, mutex, block, goroutine,
// and SPAN-LABELED samples for trace correlation.
func initProfiling(service, version, env string) (*pyroscope.Profiler, error) {
    return pyroscope.Start(pyroscope.Config{
        ApplicationName: service,
        ServerAddress:   "http://pyroscope.observability.svc:4040",
        // Fleet-consistent labels — MUST match metric/trace/log resource attributes.
        Tags: map[string]string{
            "service_version": version,
            "environment":     env,
            // NO pod/instance/user_id here — same fail-closed label discipline as metrics.
        },
        ProfileTypes: []pyroscope.ProfileType{
            pyroscope.ProfileCPU,
            pyroscope.ProfileAllocSpace,   // heap — eBPF can't easily get this
            pyroscope.ProfileMutexCount,   // contention
            pyroscope.ProfileGoroutines,   // leaks
        },
    })
}

// Span profiles: tag the goroutine with the span context so samples carry trace_id/span_id.
// If you sample OUTSIDE the span scope, the correlation is lost (same trap as metric exemplars).
func handleWithSpanProfile(ctx context.Context, span trace.Span) {
    pyroscope.TagWrapper(ctx, pyroscope.Labels(
        "trace_id", span.SpanContext().TraceID().String(),
    ), func(c context.Context) {
        doExpensiveWork(c) // samples taken here link back to THIS span
    })
}
```

### Deploy-gate diff check — fail the canary on a CPU-share regression

```python
#!/usr/bin/env python3
# deploy-gate: compare canary vs baseline CPU profiles; fail if any function's CPU SHARE grew > threshold.
# Diff = a DELTA of per-function shares, NORMALIZED so different traffic volumes don't false-positive.
import sys, requests

THRESHOLD_PP = 5.0   # fail if any function's CPU share grew > 5 percentage points

def fetch_shares(service, version, window):
    # query the profile store (Parca/Pyroscope) for cpu profile, grouped by function
    r = requests.get("http://parca.parca.svc:7070/api/profile", params={
        "service": service, "version": version, "window": window, "type": "cpu",
    })
    samples = r.json()["functions"]               # [{ "name":..., "value":... }, ...]
    total = sum(f["value"] for f in samples) or 1
    return {f["name"]: f["value"] / total for f in samples}   # NORMALIZE to share-of-total

def main(service, baseline_ver, canary_ver):
    base = fetch_shares(service, baseline_ver, "10m")
    cand = fetch_shares(service, canary_ver,   "10m")
    regressions = []
    for fn, cand_share in cand.items():
        delta_pp = (cand_share - base.get(fn, 0.0)) * 100
        if delta_pp > THRESHOLD_PP:
            regressions.append((fn, delta_pp))
    if regressions:
        print("CPU REGRESSION — failing deploy gate:")
        for fn, d in sorted(regressions, key=lambda x: -x[1]):
            print(f"  {fn}: +{d:.1f} pp CPU share (canary {canary_ver} vs {baseline_ver})")
        sys.exit(1)                                # block the deploy
    print("No CPU-share regression > %.1f pp. Gate passed." % THRESHOLD_PP)

if __name__ == "__main__":
    main(*sys.argv[1:4])
```

`fetch_shares` normalizes to share-of-total — the load-bearing detail. A raw-count diff would flag a function as "regressed" just because the canary served more traffic. The gate compares *shares*, not raw samples.

### OTel Collector — route profiles as the fourth OTLP signal

```yaml
# The OTel Collector receives PROFILES (OTLP) alongside metrics/traces/logs — one control plane.
receivers:
  otlp:
    protocols:
      grpc: { endpoint: 0.0.0.0:4317 }
processors:
  resource:
    attributes:                          # stamp the SAME identity as the other three signals
      - { key: service.namespace, value: payments, action: upsert }
  batch: {}
exporters:
  otlp/pyroscope:
    endpoint: pyroscope.observability.svc:4040
service:
  pipelines:
    profiles:                            # profiles pipeline — first-class, like traces/metrics
      receivers:  [otlp]
      processors: [resource, batch]
      exporters:  [otlp/pyroscope]
```

Routing profiles through the collector means cross-signal label consistency, central governance, and backend-swappability — the same collector-in-the-middle payoff you get for metrics.

---

## Worked Example — Rolling Out Fleet-Wide Profiling

You're the platform engineer. The org has ~400 services across Go, Java, Python, Node, Rust, plus stripped C sidecars and a Kubernetes fleet. Leadership wants "the fourth signal" — always-on profiling — without a per-team instrumentation project and without blowing the observability budget. Here is the rollout, end to end.

**Step 1 — pick the spine: eBPF agent for breadth, SDKs for depth.** Deploy **parca-agent (or Pyroscope eBPF) as a DaemonSet** for universal on-CPU coverage — one manifest profiles every process, including the C sidecars nobody owns and the kernel. Layer **SDKs** (Go pprof/Pyroscope, async-profiler for JVM, py-spy/Pyroscope for Python) only where you need heap/off-CPU/span-labeled profiles the agent can't easily get. Breadth from the agent, depth from SDKs.

**Step 2 — make the fleet unwindable.** Mandate **frame pointers on** in the build toolchain (`-fno-omit-frame-pointer`, Rust `force-frame-pointers`, modern Go is fine by default). This makes the eBPF agent's unwinding cheap and reliable, and is the single highest-leverage decision for whole-system profile quality. DWARF unwinding is the fallback for third-party binaries.

**Step 3 — set the overhead SLO and build the kill switch.** Before default-on: measure real per-process overhead under real traffic (Stage 1), set an SLO (`p99 profiling overhead < 1%`), dashboard it, and ship a **kill switch** (agent feature flag + per-service opt-out) so a misbehaving profiler can be disabled instantly. Default-on is only defensible once the SLO and kill switch exist.

**Step 4 — standardize labels and format.** One **profile-label schema** (`service`, `version`, `environment`, `region`) matching the resource attributes on metrics/traces/logs, enforced by a **fail-closed allow-list** (no `pod`/`user_id`). One on-wire format: **pprof / OTLP profiles**, routed through the OTel Collector. The agent maps pod → service so agent profiles carry the same labels as SDK profiles.

**Step 5 — build the storage tier and its budget.** Stand up **Parca/FrostDB (or Pyroscope)** columnar storage. Set retention: full resolution for ~2 weeks (incidents + deploy diffs live here), **downsample** older profiles, dedup symbols in a separate symbol store. Price the volume (volume math above) against the cross-signal budget — see [Telemetry Cost and Sampling Strategy](../14-telemetry-cost-and-sampling-strategy/README.md).

**Step 6 — wire correlation.** Enable **span profiles** (SDK tags samples with `trace_id`/`span_id`) and ensure metrics carry **exemplars**, so the full descent metric → trace → profile → log is one click. Shared resource attributes across all four signals make the pivot work.

**Step 7 — add the deploy gate.** For tier-1 services, run a **canary diff check** in CI/CD: compare canary vs baseline CPU/alloc profiles (normalized to share), fail the deploy on a function whose CPU share grew > 5 pp or whose per-request allocations grew > X%. The regression is blocked *before* it reaches the fleet.

**Step 8 — govern security.** Profiling endpoints internal-only + authenticated; label PII review (no `user_id`/`email`); RBAC on the store; debuginfo handled as sensitive; profile store in compliance scope.

**The outcome:** every process in a 400-service, multi-language fleet is profiled continuously with *zero per-service instrumentation* (the agent) plus rich profiles where they matter (SDKs); the whole thing stays under a 1% overhead SLO with a kill switch; profiles are stored affordably with downsampling; a CPU regression fails the canary automatically; and a latency spike is one click from its flame graph. **That coverage, that gate, and that correlation are the deliverable — and every piece was a platform decision made once, not 400 times.**

---

## A Real Profiling-Caught Regression, Walked Through

A walk-through in the register of an incident timeline, because a profiling-caught regression is a *prevented* incident.

**Context (deploy at 09:14 UTC):** `checkout-api v7.3` enters canary at 5% traffic. The fleet runs eBPF agent profiling (CPU) plus the Go SDK (alloc, off-CPU), and tier-1 services have a deploy-gate diff check.

**Step 1 — the gate runs automatically (09:24).** After a 10-minute soak, the CI diff check pulls the canary's and baseline's CPU profiles, normalizes both to share-of-total, and diffs.

**Step 2 — the diff lights up red.** One function jumped: `encoding/json.(*decodeState).object` went from 6% to 24% of CPU share — a **+18 pp delta**. The gate's threshold is +5 pp. It fails the deploy and posts the diff flame graph to the PR.

**Step 3 — read the delta, not the absolute.** The diff (a *delta*) shows red concentrated under `json.Unmarshal` called from a new `validateCart` path. The baseline barely touched it; the canary spends a quarter of its CPU there. Because the gate normalized to *share* (canary and baseline served different volumes), this isn't a traffic artifact — it's a real per-request cost increase.

**Step 4 — confirm with the alloc profile.** The Go SDK's alloc diff shows the same path allocating 3× more bytes per request — `validateCart` unmarshals the entire cart into a fresh struct on *every* item, instead of once. The off-CPU profile is flat: it's pure on-CPU + allocation, not blocking.

**Step 5 — the root cause.** `v7.3` added per-item cart validation that re-parses the whole cart JSON inside a loop — O(items²) unmarshalling. On a laptop with a 2-item test cart it was invisible; under real carts (dozens of items) it's a CPU and GC disaster. **This is exactly the prod-only bug continuous profiling exists for** — the test workload never hit it.

**Step 6 — the fix and the confirmation.** Parse once, validate in-memory. `v7.4` re-enters canary; the diff gate now shows `json.object` *back at 6%* (blue in the diff — it shrank to baseline). The gate passes. The fix is *confirmed by the same tool that caught the regression*.

**Step 7 — why this never reached the fleet.** Without the gate, `v7.3` rolls to 100%, p99 latency and GC pauses climb, an alert fires, an SRE pages, someone eventually pulls a profile and finds `json.object` — an *incident*. With the gate, the diff caught it at 5% canary in 10 minutes, automatically, before a single non-canary customer was affected.

**Lessons:**
1. **A diff is a delta, and a delta is a regression detector** — the same flame-graph diff a senior reads reactively, wired into the gate, blocks the regression proactively.
2. **Normalize to share, never raw counts** — the canary served different traffic; only the share-normalized diff distinguishes a real regression from a volume artifact.
3. **The bug was prod-only** — synthetic test carts never triggered the O(items²) path; continuous production profiling (and the gate built on it) is the only thing that sees it.
4. **The same tool caught *and* confirmed the fix** — diff red → fix → diff blue is the full loop, automated.

---

## Coding Patterns

### Pattern 1 — eBPF agent for breadth, SDK for depth

```text
parca-agent DaemonSet → universal on-CPU coverage, zero instrumentation (the floor)
SDK (Pyroscope/pprof) → heap, off-CPU, mutex, span-labeled profiles (the depth, where it matters)
```

### Pattern 2 — Frame pointers on, DWARF as fallback

```dockerfile
RUN gcc -O2 -fno-omit-frame-pointer ...   # cheap in-kernel unwinding; DWARF only for FP-less binaries
```

### Pattern 3 — Fail-closed profile labels (match the other signals)

```go
Tags: map[string]string{ "service_version": ver, "environment": env } // NO pod/user_id; allow-list
```

### Pattern 4 — Span profile recorded inside the span scope

```go
pyroscope.TagWrapper(ctx, pyroscope.Labels("trace_id", traceID), func(c context.Context) { work(c) })
// outside the scope → no trace_id on samples → correlation lost (same trap as metric exemplars)
```

### Pattern 5 — Diff = normalized delta = the gate signal

```text
Δ_share(fn) = share_canary(fn) − share_baseline(fn)   # NORMALIZE; raw counts false-positive on traffic
fail deploy if max Δ_share > threshold                 # the diff is the regression detector
```

### Pattern 6 — Profiling endpoint is privileged

```go
mux.HandleFunc("/debug/pprof/", pprof.Index)
http.ListenAndServe("127.0.0.1:6060", mux)  // localhost/admin port + auth — NEVER public
```

### Pattern 7 — Retention tiering for the profile store

```text
recent (≤2w): full resolution   |   older: downsample (coarser windows)   |   symbols: deduped, separate
```

---

## Best Practices

1. **Lead with agent-based eBPF for coverage.** One DaemonSet profiles everything in every language with zero per-service work — that breadth is the whole point of continuous profiling. Layer SDKs for the depth (heap/off-CPU/span labels) eBPF can't easily reach.
2. **Turn frame pointers on fleet-wide.** ~1% runtime cost buys cheap, reliable in-kernel unwinding. It's the highest-leverage decision for whole-system profile quality; DWARF unwinding is the fallback for binaries you can't recompile.
3. **Make overhead a fleet-wide SLO with a kill switch.** Measure real overhead under real traffic, bound it (`< 1%`), alert on it, and be able to disable a misbehaving profiler instantly. The kill switch is what makes default-on responsible.
4. **Standardize on pprof / OTLP profiles and one store.** A language-agnostic format and a single columnar store (Parca/FrostDB, Pyroscope) make query, diff, and tooling fleet-wide rather than per-team.
5. **Design profile labels like metric attributes — fail closed.** Bounded, queryable, consistent with the other three signals' resource attributes; no `pod`/`user_id`. Series count is the storage bill.
6. **Wire the deploy gate.** Diff canary vs baseline, normalized to share, and fail the deploy on a function whose CPU/alloc share grew beyond threshold. Block the regression before it ships.
7. **Make correlation one click.** Span profiles + metric exemplars + shared labels → metric → trace → profile → log descent across the fleet. The fourth signal's value is the hop.
8. **Tier the storage.** Full resolution for the recent window, downsample older profiles, dedup symbols separately, bound label cardinality. Price it against the cross-signal budget.
9. **Treat profiles as sensitive.** Internal-only authenticated endpoints, PII review on labels, RBAC on the store, debuginfo handled with care, profiles in compliance scope.
10. **Own it as a platform product.** Agent config, label schema, store, retention, gate, and access policy are versioned, reviewed, and owned — not reinvented per service.

---

## Edge Cases & Pitfalls

- **JIT/interpreted unwinding gaps.** The eBPF agent sees the *interpreter* or unsymbolized JIT addresses for JVM/V8/Python unless interpreter-aware unwinders are configured — and those are version-specific and fragile. Fall back to SDK-based profiling (async-profiler, py-spy) for deep coverage of those runtimes.
- **Frame-pointer-less third-party binaries.** A vendored binary compiled with `-fomit-frame-pointer` won't FP-unwind; the agent needs DWARF tables from its `.eh_frame`, which may be stripped. You may get truncated stacks for binaries you can't recompile.
- **Span profile recorded outside the span scope.** If the profiler samples on a goroutine/thread where the span context didn't propagate (a worker pool, a background flush), samples carry no `trace_id` and the trace correlation is lost — the same trap as metric exemplars.
- **Diff on raw counts.** Comparing canary vs baseline by raw sample count flags functions as "regressed" simply because the canary got more traffic. Always normalize to share-of-total or per-request cost.
- **Unbounded profile labels.** `pod`, `instance`, or raw `endpoint` as a profile label is a profile-series cardinality bomb, exactly as on a metric — it balloons store size and churns on every roll.
- **Overhead from DWARF unwinding.** When frame pointers are off and the agent DWARF-unwinds, per-sample cost rises; a fleet with FP-less binaries can blow the overhead SLO. Frame pointers on is the fix.
- **The kill switch you never built.** Going default-on without a way to disable a misbehaving profiler means your only option during an overhead incident is a fleet-wide redeploy. Build the kill switch *before* default-on.
- **Symbolization drift.** If the debuginfo for a deployed binary isn't uploaded/available, profiles show hex addresses, not function names. Tie symbol upload to the build/deploy so every running binary has matching symbols.
- **PII in labels or symbols.** A label set to a user ID, or a symbol embedding a constant, lands in the store and is retained and queryable. Review labels; treat the store as sensitive.
- **Public profiling endpoint.** `/debug/pprof` (or the SDK endpoint) reachable publicly leaks internals and enables a profile-triggering DoS. Internal-only, authenticated, always.

---

## Common Mistakes

1. **Instrumenting 400 services by hand** instead of deploying one eBPF agent DaemonSet for universal coverage.
2. **Shipping FP-less binaries** and then wondering why whole-system profiles have truncated stacks or high overhead — turn frame pointers on.
3. **Going default-on without an overhead SLO or kill switch**, so a misbehaving profiler can only be stopped by a fleet redeploy.
4. **Diffing raw sample counts** in the deploy gate, false-positiving on traffic differences instead of normalizing to share.
5. **Unbounded profile labels** (`pod`, `user_id`, raw path) blowing up profile-series cardinality and the storage bill.
6. **Sampling outside the span scope**, so span profiles carry no trace ID and the trace correlation silently fails.
7. **Treating eBPF as a complete solution** for JIT/interpreted runtimes, missing that JVM/Python need SDK-based depth.
8. **No retention/downsampling policy**, so the profile store grows unbounded and the bill is the first signal.
9. **Exposing profiling endpoints publicly** or putting PII in labels — treating profiles as non-sensitive.
10. **Building profiling as a per-team silo** instead of a governed platform with one store, one label schema, one access policy.

---

## Tricky Points

- **eBPF profiles *anything* — but unwinding is the catch.** Zero instrumentation is real, but only as good as the agent's ability to walk the stack; FP-less binaries and JITs are where the magic frays. Frame pointers on + SDK fallback close most of the gap.
- **A diff is a *delta*, not a comparison of two pictures.** Red = grew, blue = shrank, normalized. The deploy gate reads the delta; the senior reads the same delta reactively. Same artifact, two timings.
- **Profile-series cardinality is the storage bill, exactly like metric series.** A profile store is a TSDB for flame graphs; an unbounded label is the same bomb here as there.
- **Span profiles are the trace→profile hop; exemplars are the metric→trace hop.** They're symmetric correlation mechanisms, and both require the identity (trace ID) to be present *at sample time* — record inside the scope.
- **Frame pointers cost ~1% but the industry turned them back on anyway.** Fedora/Ubuntu re-enabled them distro-wide *for profilability* — a rare case of the ecosystem paying a runtime tax for observability. Decide the same for your binaries.
- **Continuous and point-in-time profiling are complementary, not competing.** Continuous *finds* it in prod, fleet-wide; point-in-time *fixes* it on a laptop. The gate uses continuous to *confirm* the fix.
- **The OTel profiling signal makes profiles a peer of the other three** — same OTLP protocol, same collector, built-in trace correlation. The fourth signal stops being a silo.
- **A profile is the most revealing record you keep.** It describes exactly what your code did for a real request. Govern it like logs, or more strictly.

---

## Apply it

1. Define the user or business outcome that **Continuous Profiling** should improve.
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

- Which measurable outcome justifies investing in Continuous Profiling?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
