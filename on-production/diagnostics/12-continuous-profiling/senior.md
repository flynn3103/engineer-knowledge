# Continuous Profiling — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Continuous Profiling** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Continuous Profiling Roadmap](README.md)
> **Focus:** The senior moves that turn a flame-graph viewer into a debugging instrument. Differential flame graphs that catch a regression in red. Off-CPU/wall-clock profiling, where latency bugs actually live. Joining a profile to the trace that produced it via shared labels and exemplars. Enforcing an overhead budget so the profiler never becomes the incident. And tying a p99 spike to the exact flame graph at that timestamp.

---

## Core Concepts

### 1. A diff flame graph is a delta of two estimates, not a measurement

A differential flame graph subtracts an "after" profile from a "before" profile, frame by frame, and colours the result. Because both inputs are *statistical samples*, the diff inherits both noise floors — a thin red sliver may be sampling noise, not a real regression. Trust **wide** colour changes; treat thin ones as hypotheses. The diff's power is concentration: it throws away everything that *didn't* change so the change is unmissable.

### 2. Latency lives off-CPU more often than on

The junior reflex "it's slow, show me the CPU profile" is right about half the time. The other half, the CPU profile is *flat and healthy* because the time is spent **waiting** — on a lock, a pool, a syscall, the scheduler's run queue. A CPU profile is structurally blind to waiting. Senior latency debugging means knowing, from the symptom (low CPU + high latency ⇒ off-CPU), which profile to reach for before you waste an hour in the wrong one.

### 3. A profile is only as useful as the labels that join it to the other signals

A flame graph with no `service`/`version`/`region` labels is an island. The senior contribution is **consistent labels across all four signals** so a metric, a trace, and a profile for the same `service="checkout", version="v2.4.1", region="eu"` can be joined automatically. The same labels that let you query a profile by time window let you join it to the trace that produced it.

### 4. Continuous and point-in-time profiling are partners, not rivals

Continuous profiling *finds* the regression in production — under real data, real concurrency, real cache state. Point-in-time profiling on a laptop or in a benchmark *confirms and optimises* it in a tight loop. The senior workflow flows one way: prod finds it, the laptop fixes it, prod confirms the fix. Neither replaces the other.

### 5. The profiler must never become the incident

Always-on means the profiler runs during the worst moment your system ever has. A profiler that costs 2% at idle but 30% under load, or that floods the network with profile uploads during an outage, has *amplified* the incident. Senior practice is an **overhead budget with a kill switch**: bounded cost, dynamic enable/disable, and a blast radius you've reasoned about.

### 6. Leaks are found in the *trend*, not the snapshot

A single `inuse` heap profile shows what's live *now* — but "100MB live" tells you nothing about whether it's growing. A leak is a *slope*: the same allocation site's `inuse` bytes climbing across hours. Continuous profiling's superpower for leaks is the **time series of inuse**, not any one snapshot. This is exactly what one-off laptop profiling cannot give you.

### 7. Symbolization in production is a logistics problem, not a viewing problem

In prod you ship **stripped** binaries (smaller, faster to deploy) — which means the addresses in your samples can't be turned into function names *at the agent*. The fix is storing debug info keyed by **build ID** and symbolizing **server-side** (or via debuginfod). If you skip this, your flame graphs are towers of hex addresses, exactly when you need names most.

---

## Differential Flame Graphs

This is the feature that justifies storing profiles time-indexed. A single flame graph answers "where does time go?" A **diff** answers the more actionable question: "**what changed?**"

You diff two profiles whenever you have a clean "before" and "after":

| Diff axis | "Before" (base) | "After" | What it catches |
|---|---|---|---|
| **Across a deploy** | Profile from `version=v2.3` | Profile from `version=v2.4` | A regression introduced by the new code |
| **Version A vs B** | Canary `v2.4` | Stable `v2.3`, same window | Whether the canary is worse before you roll it out |
| **Incident vs baseline** | A calm window (yesterday, same hour) | The p99-spike window | What got hot *during* the incident |
| **Region / tenant** | `region=us` | `region=eu` | Why one slice is slower than another |
| **High-load vs low-load** | Off-peak | Peak | What only appears under contention |

### The Go mechanics

`go tool pprof` has first-class diff support. Capture two CPU profiles, then subtract:

```bash
# Capture "before" (old version) and "after" (new version), 30s each.
go tool pprof -proto -output old.pb.gz http://old-pod:6060/debug/pprof/profile?seconds=30
go tool pprof -proto -output new.pb.gz http://new-pod:6060/debug/pprof/profile?seconds=30

# Differential flame graph: new MINUS old. Red = grew in new, blue = shrank.
go tool pprof -http=:8080 -diff_base old.pb.gz new.pb.gz

# Same thing in the text REPL — top regressions by delta:
go tool pprof -diff_base old.pb.gz new.pb.gz
(pprof) top          # functions sorted by DELTA (largest growth first)
(pprof) list Marshal # line-level delta inside a suspect function
```

`-diff_base` makes every number in the view a **delta**: `top` now ranks by *how much each function grew or shrank*, and `list` shows the per-line change. The function at the top of `top` is your prime regression suspect.

> Normalisation caveat: if the two profiles cover different durations or different request volumes, the raw delta conflates "more traffic" with "more expensive per request." `pprof` has `-normalize` to scale the base to the same total before diffing; use it (or capture equal windows under equal load) so the diff reflects *per-unit* change, not just *more work*.

Pyroscope, Parca, and Grafana all expose the same idea in the UI — pick two time ranges (or two label sets like `version=A` / `version=B`) and the platform renders the red/blue diff for you, no manual capture needed. That is the **deploy-gate regression detector**: diff each release against the last and fail the gate (or alert) when a frame grows past a threshold. (Fleet-scale automation of this lives in [`professional.md`](professional.md).)

---

## Reading a Diff Flame Graph

The colour convention is near-universal, but internalise it because the cost of misreading it is chasing the wrong function:

```text
   DIFF FLAME GRAPH  (new MINUS old)
   ┌──────────────────────────────────────────────────────────┐
   │                          main  (≈0, grey)                  │
   ├───────────────────────────┬──────────────────────────────┤
   │      handleRequest         │        backgroundJob          │
   ├──────────────┬─────────────┼───────────────┬──────────────┤
   │  parseJSON   │  queryDB     │  compress     │   cacheLookup │
   │  ░░ (blue)   │  ·· (grey)   │  ▓▓ (RED)     │   ·· (grey)   │
   │  shrank −8%  │  unchanged   │  GREW +34%    │   unchanged   │
   └──────────────┘             └───────────────┘
        ▲                            ▲
   got faster                   the REGRESSION — start here
```

The rules:

1. **Red = grew in the "after" profile. Blue = shrank. Grey/neutral ≈ no change.** (Exact palette varies; the *direction* — warm grew, cool shrank — is the constant.)
2. **Width still encodes the magnitude of the delta**, not the absolute time. A wide red box is a *big* regression; a thin red box is a small one (or noise).
3. **Hunt for the widest red box, top-down**, exactly as you hunt the widest leaf in a normal flame graph — but now "widest" means "biggest increase."
4. **Blue is information too.** A frame that shrank tells you an optimisation landed, or that load shifted away from a path — useful for confirming a fix.
5. **A frame can be red because of more *calls*, not slower code.** The diff shows total resource delta; whether the function got called more or got slower per call is a follow-up question (check the trace/metric for call rate, or `list` for per-line cost).

> The mechanical reading: open the diff, find the single widest red tower, read its top (leaf) frame — that named function is where the regression concentrated. Then go confirm *why* (more calls vs slower-per-call) with the other signals.

---

## On-CPU vs Off-CPU for Latency Debugging

The most expensive senior mistake in profiling is debugging a *latency* problem with a *CPU* profile. They answer different questions, and latency usually answers to off-CPU.

| | **On-CPU (CPU profile)** | **Off-CPU (wall/block/mutex)** |
|---|---|---|
| Captures | Where cycles were *burned* | Where the thread *waited* (blocked, sleeping) |
| Sees a busy loop | ✅ | partially (as time not waiting) |
| Sees a lock wait | ❌ (CPU idle while waiting) | ✅ |
| Sees a slow DB call | ❌ (CPU idle during the round-trip) | ✅ |
| Sees scheduler/run-queue delay | ❌ | ✅ (wall-clock) |
| Right when | CPU is saturated; compute-bound latency | CPU is idle but latency is high |

### The diagnostic shortcut

```text
   high latency  +  high CPU   → ON-CPU profile (something is computing too much)
   high latency  +  LOW  CPU   → OFF-CPU profile (something is WAITING)
                                 → lock? pool exhaustion? slow downstream? scheduler?
```

A request that takes 300ms while the CPU sits at 20% is *not* a CPU problem. The 280ms it spent doing nothing are invisible to a CPU profile (which will look flat and innocent). An off-CPU / wall-clock profile shows the stack *at the moment it blocked* and *how long it stayed blocked* — pointing straight at the `db.Query`, the `mutex.Lock`, or the `pool.Get` that ate the time.

The scheduler/run-queue angle is the subtle one: under heavy load, a goroutine/thread can be **runnable but not running** — waiting for a CPU to free up. That delay is neither on-CPU (it isn't running) nor a classic block (it isn't waiting on I/O); a *wall-clock* profile is what captures it. When latency rises with load but no single lock or call explains it, suspect run-queue delay and reach for wall-clock.

---

## Wall-Clock, Block, and Mutex Profiles in Depth

Go gives you three distinct off-CPU lenses; the JVM gives you a unified wall-clock mode. Knowing which to enable is senior knowledge.

### Go: block and mutex profiles

Both are **off by default** because they have a cost, and both take a *rate* you must set deliberately:

```go
import "runtime"

func enableContentionProfiling() {
    // Block profile: sample goroutine-blocking events (chan ops, sync waits,
    // network blocks). The arg is "report ~1 event per N nanoseconds blocked."
    // 10_000 ⇒ sample blocking that lasts ≳10µs. Lower = more detail = more cost.
    runtime.SetBlockProfileRate(10_000)

    // Mutex profile: sample LOCK CONTENTION (time waiting to acquire).
    // The arg is "sample 1 in every N contention events." 5 ⇒ ~1/5 sampled.
    // 0 disables. Larger = cheaper, coarser.
    runtime.SetMutexProfileFraction(5)
}
```

Then collect them like any pprof profile:

```bash
go tool pprof -http=:8080 http://pod:6060/debug/pprof/block   # where goroutines blocked
go tool pprof -http=:8080 http://pod:6060/debug/pprof/mutex   # where they waited on locks
```

- **Block profile** answers "what are my goroutines waiting on?" — a channel that's never read, a slow network call, a `WaitGroup` that hangs.
- **Mutex profile** answers "which lock is serialising my concurrency?" — the classic "throughput plateaus under load even though CPU isn't saturated" symptom. A wide tower over one `sync.Mutex.Lock` in the mutex profile *is* your contention point.

> Rate-setting is a budget decision. A `SetBlockProfileRate(1)` (sample everything) on a hot path can itself dominate. Start coarse (`10_000`+) and tighten only when you're actively hunting. Treat these like the cardinality budget from metrics: detail costs, so spend it where you're looking.

### JVM: wall-clock with async-profiler

async-profiler unifies on- and off-CPU into one **wall-clock** mode, which weights every thread by elapsed time regardless of whether it was running or parked:

```bash
# Wall-clock profile: captures BOTH on-CPU and waiting (off-CPU) time.
# This is what you want for a "slow but CPU-idle" latency bug on the JVM.
./asprof -d 30 -e wall -t -f wall.html <pid>
#   -e wall : wall-clock (elapsed time) instead of -e cpu
#   -t      : per-thread split — essential, since waiting is per-thread

# Lock contention specifically:
./asprof -d 30 -e lock -f lock.html <pid>
```

`-e wall` is the JVM equivalent of "show me where the time *actually* went, including the waiting" — the antidote to a flat `-e cpu` profile on a latency bug. The `-t` per-thread split matters because off-CPU time is inherently a per-thread story (one thread blocked on the DB while others run).

---

## Correlating Profiles with Traces

A profile that can't be joined to a trace is half a tool. The senior goal: from a slow trace, jump to *the flame graph for that span*; and from a hot stack, jump to *an example trace that exercised it*.

### Three mechanisms, increasing fidelity

1. **Shared labels (the floor).** Every signal carries the same `service`, `version`, `region`, `instance`. Now "the trace says `checkout v2.4` was slow at 14:32" and "the profile for `checkout v2.4` at 14:32" are the same query key. This is the minimum and you should *never* skip it.

2. **Exemplars (the bridge).** A sample (or a metric histogram bucket) carries a sampled **trace ID**. "p99 bucket is full → click the exemplar → here's a concrete slow trace." The same idea links a hot profile sample to a trace that produced it.

3. **Span-scoped profiling (the ceiling).** The profiler tags each sample with the trace/span context active when it was taken. Now you can ask "render the flame graph using *only* samples taken during span X" — the flame graph *for one operation*, not the whole service.

### Go: attach trace context to profiles with pprof labels

Go's `pprof.Labels` / `pprof.Do` attach key/value labels to every sample taken while the labelled context is active — the native hook for span-scoped profiling:

```go
import (
    "context"
    "runtime/pprof"
    "go.opentelemetry.io/otel/trace"
)

func handleCheckout(ctx context.Context) {
    span := trace.SpanFromContext(ctx)
    // Tag every CPU sample taken during this work with the trace/span IDs and
    // the consistent service/version labels. Pyroscope/Parca can then filter the
    // flame graph to exactly these requests, and join it to the trace.
    pprof.Do(ctx, pprof.Labels(
        "trace_id", span.SpanContext().TraceID().String(),
        "service", "checkout",
        "version", buildVersion,
        "endpoint", "/checkout", // route TEMPLATE, never the concrete path (cardinality!)
    ), func(ctx context.Context) {
        doCheckout(ctx) // all samples here inherit the labels above
    })
}
```

> Cardinality discipline applies here exactly as it does to metrics: `trace_id` is acceptable as a *sampled exemplar label* on profile samples (it's high-cardinality but you only keep a fraction), but a label like `endpoint` must be the bounded **route template**, never the raw path. The same allow-list discipline from [`../04-metrics/senior.md`](../04-metrics/senior.md) governs profile labels. The `observability-stack` skill covers wiring these joins across the full telemetry pipeline.

The payoff: **all four signals keyed alike.** A metric fires, you click its exemplar to a trace, the trace's slow span links to the flame graph scoped to that span, and the flame graph names the line. That chain is the senior end state of observability.

---

## The Latency-Spike-to-Flame-Graph Workflow

The headline capability of continuous profiling: a p99 spike at 14:32, and you produce the flame graph *for that moment* without reproducing anything. The full senior workflow:

```text
1. ALERT      Metric: checkout p99 jumped 120ms → 700ms at 14:32.   (../04-metrics/)
2. LOCALISE   Trace: the time is inside checkout-service, span "serializeCart". (../05-tracing/)
3. TIME-WINDOW  Open the profile store, select the window 14:30–14:35,
                service=checkout, version=<the version live then>.
4. CHOOSE TYPE  CPU was high → CPU profile. (If CPU was flat → off-CPU/wall.)
5. FILTER       Filter by labels: endpoint="/checkout", region=<the hot one>.
                If span-scoped: restrict to samples tagged span="serializeCart".
6. DIFF         diff_base = a calm window (14:00–14:05, same labels).
                Red tower = json.Marshal grew 5× → THE regression.
7. CONFIRM      Is it more calls or slower per call? Check the metric's request
                rate and the trace's call count. Here: same calls, slower marshal.
8. HAND OFF     Reproduce + optimise on the laptop (point-in-time profiling):
                ../../performance/01-profiling/
9. VERIFY       After the fix deploys, diff new window vs the spike window →
                the red tower is gone (now blue). Close the incident.
```

The two senior skills inside this are **time-window selection** (the profile store is time-indexed exactly so you can scope to the incident) and **label filtering** (narrow to the slow slice — endpoint, region, version — instead of drowning in the whole service's aggregate). Without both, you get a fleet-wide flame graph that averages the incident away.

---

## Heap Deep Dive — Alloc vs Inuse and Leak Trends

Heap profiling has two flavours that answer opposite questions, and the senior insight is that **leaks are a trend, not a snapshot.**

| | **`alloc_space` / `alloc_objects`** | **`inuse_space` / `inuse_objects`** |
|---|---|---|
| Counts | Everything allocated *since start* (incl. freed) | What's live *right now* (not yet GC'd) |
| Answers | "What's churning the allocator / driving GC?" | "What's holding memory / leaking?" |
| Use for | GC pressure, pause reduction, alloc hotspots | Memory leaks, OOM hunting |
| In a flame graph | The widest alloc leaf = your GC pressure source | The widest inuse leaf = your live-memory holder |

### Allocation flame graphs for GC pressure

A service with frequent GC pauses but stable memory isn't leaking — it's *churning*. The `alloc` flame graph shows the allocation hotspots: a handler that builds a fresh buffer per request, a `json.Marshal` that allocates intermediate slices, a `fmt.Sprintf` in a hot loop. The widest `alloc` leaf is the line to pool/reuse/preallocate. Reducing it cuts allocations, which cuts GC frequency, which cuts pause-driven tail latency — often a bigger latency win than any CPU optimisation.

### Finding leaks via the inuse *trend*

This is where continuous profiling beats every laptop tool. A single `inuse` snapshot says "the cache holds 100MB." Is that a leak? You cannot tell from one snapshot. But the **time series of `inuse` for that allocation site**, climbing steadily across hours with no plateau, *is* the leak — a slope you can only see because the profiles are stored time-indexed.

```text
   inuse_space for cache.Set (continuous, over 6h):
     bytes ▏
       3GB ▏                                          ▁▂▄
       2GB ▏                            ▁▂▃▄▅
       1GB ▏        ▁▂▃▄▅▆▇
           ▏▂▄▆█████████████████████████████████████████►  time
           a non-plateauing climb at ONE alloc site = the leak
```

The senior move: don't chase a leak with a single heap dump. Pull the `inuse` *trend* for each top allocation site; the one that climbs without bound is the culprit. (The `memory-leak-detection` skill covers the systematic hunt — diffing two `inuse` profiles taken an hour apart is the diff-flame-graph technique applied to leaks: the red towers are exactly what grew.)

> The diff trick for leaks: `go tool pprof -diff_base heap_t0.pb.gz heap_t1.pb.gz -sample_index=inuse_space` shows *what grew between the two snapshots* — the leak, isolated, in red.

---

## Overhead Budgets & Safety

Always-on means the profiler is running during your worst incident. A profiler that becomes the bottleneck has inverted its purpose. Senior practice is to treat overhead as a *budget you enforce*, with a kill switch.

### Set actual numbers

| Resource | Typical budget | How to stay inside it |
|---|---|---|
| **CPU** | ≤1–2% | Cap sample rate (e.g. 100Hz CPU); coarse block/mutex rates |
| **Memory** | bounded, predictable | Cap profile buffer sizes; bound label cardinality on samples |
| **Network (upload)** | ≤ a few MB/min | Compress (pprof is gzipped protobuf); batch; cap upload frequency |
| **Symbolization CPU** | offloaded | Symbolize **server-side**, not on the hot agent (see next section) |

### The levers

- **Sample-rate tuning.** CPU at 100Hz is the safe default; pushing to 1000Hz quadruples cost for marginal resolution. Block/mutex rates are the sharpest cost levers — a `SetBlockProfileRate(1)` on a hot path can dominate the very CPU you're measuring.
- **Dynamic enable/disable.** Expensive profile types (block, mutex, allocation at high rate) should be *toggleable at runtime* — off by default, flip on when investigating, flip off after. A config flag or admin endpoint, not a redeploy.
- **Blast radius of a misbehaving profiler.** Reason about the worst case: if the agent OOMs, does it take the service with it (shared process) or just itself (sidecar)? If symbolization hangs, does it block request handling? Prefer designs where the profiler's failure is *isolated* — a separate goroutine/thread/sidecar with its own resource limits and a watchdog.
- **Symbolization cost.** Symbolizing on the producing host burns CPU on the box least able to spare it during an incident. Ship raw addresses + build ID; symbolize centrally. (Next section.)

> The senior framing: the profiler is infrastructure that runs *during* outages, so it must degrade *gracefully under load* and have a *kill switch*. "≤2% CPU at idle" is not a budget; "≤2% CPU at peak load, with a flag to disable in one click" is.

---

## Production Symbolization

In production you ship **stripped** binaries — debug info removed to shrink image size and speed deploys. The consequence: the addresses in your samples can't be turned into `package.Function:line` *at the agent*. Solving this is pure logistics, and getting it wrong gives you flame graphs full of hex.

### The build-ID keyed pipeline

```text
   1. BUILD    Compile with full debug info. Embed a BUILD ID (content hash) in
               the binary (Go does this automatically; ELF .note.gnu.build-id).
   2. STRIP    Ship the stripped binary to prod. Keep the debug info / unstripped
               binary in a DEBUG-INFO STORE, keyed by build ID.
   3. PROFILE  The agent collects samples as raw ADDRESSES + the binary's BUILD ID.
   4. SYMBOLIZE  Server-side: look up the build ID → fetch matching debug info →
               turn addresses into names. (Parca's debuginfo store; debuginfod.)
```

### Why each piece matters

- **Build ID is the join key.** Address `0x4a3f10` means nothing without knowing *which exact build* it came from — the same address is a different function in a different build. The build ID pins it. Mismatched debug info (wrong build) produces *confidently wrong* names, which is worse than hex.
- **Server-side symbolization** keeps the cost off the production host (overhead budget) and means you only need one copy of the debug info, not debug info on every node.
- **debuginfod** is the standardised protocol for fetching debug info by build ID on demand — the ecosystem's answer to "where do I get the symbols for *this* binary?"
- **Stripped without a debug-info store = hex forever.** If you strip and *don't* save the symbols somewhere keyed by build ID, the information is gone; you cannot symbolize after the fact. Treat the debug-info store as a build artifact you must retain for as long as you might profile that version.

> The senior rule: a build that runs in prod must have its debug info *retained and addressable by build ID*. Stripping the binary is fine — losing the symbols is not. This is the profiling analogue of "keep your source maps."

---

## Continuous vs Point-in-Time Profiling

These are partners. Continuous profiling lives here; point-in-time, laptop, "now I optimise this function" profiling lives in [`../../performance/01-profiling/`](../../performance/01-profiling/). Keep the boundary clean.

| | **Continuous (this roadmap)** | **Point-in-time (Performance → Profiling)** |
|---|---|---|
| Where | Production, fleet-wide, always-on | Laptop, benchmark, on-demand |
| Strength | *Finds* the problem under real conditions | *Fixes* the problem in a tight iterate loop |
| Data | Real traffic, real cache, real concurrency | Synthetic / controlled input |
| Question | "What's hot/regressed/leaking *in prod*?" | "Why is *this function* slow, and how do I make it fast?" |
| Overhead | Must be ≤2% (always on) | Can be high (instrumenting profilers fine here) |
| Time axis | Time-indexed history (diff, trend) | One run, one flame graph |

The handoff is the whole point: **prod finds it, the laptop fixes it, prod confirms.** Continuous profiling tells you *where to point* the deep, possibly-expensive point-in-time tools — so you don't optimise a function that prod never spends time in. The optimisation techniques themselves (the `profiling-techniques` skill, algorithmic and allocation tuning) are *not* duplicated here; they live in the performance roadmap. This page is about finding, comparing, and correlating — not about how to make a function fast.

---

## Code Examples

### Go — capture, diff, and read a deploy regression

```go
// Production service: pprof on an internal port + contention profiling on.
package main

import (
    "net/http"
    "net/http/pprof"
    "runtime"
)

var buildVersion = "v2.4.1" // injected via -ldflags "-X main.buildVersion=..."

func main() {
    // Off-CPU lenses, coarse rates to stay inside the overhead budget.
    runtime.SetBlockProfileRate(10_000) // ~events lasting ≥10µs
    runtime.SetMutexProfileFraction(5)  // ~1/5 of contention events

    // Profiling endpoints on a localhost/admin port ONLY — never public.
    admin := http.NewServeMux()
    admin.HandleFunc("/debug/pprof/", pprof.Index)
    admin.HandleFunc("/debug/pprof/profile", pprof.Profile)
    go http.ListenAndServe("127.0.0.1:6060", admin)

    // ... real server ...
    select {}
}
```

```bash
# Diff this deploy against the previous one — the deploy-gate regression check.
go tool pprof -proto -output v2.3.pb.gz http://canary-old:6060/debug/pprof/profile?seconds=30
go tool pprof -proto -output v2.4.pb.gz http://canary-new:6060/debug/pprof/profile?seconds=30

# Normalize so the diff reflects per-unit change, not just more traffic, then view.
go tool pprof -normalize -http=:8080 -diff_base v2.3.pb.gz v2.4.pb.gz
# Red towers = what v2.4 made worse. Top of `top` = the regression's leaf function.
```

### Go — span-scoped CPU profiling joined to a trace

```go
import (
    "context"
    "runtime/pprof"
    "go.opentelemetry.io/otel/trace"
)

func ServeCheckout(ctx context.Context) error {
    sc := trace.SpanFromContext(ctx).SpanContext()
    // Every sample taken inside Do() carries these labels → the profile store
    // can render the flame graph for THIS span and join it to the trace.
    var err error
    pprof.Do(ctx, pprof.Labels(
        "trace_id", sc.TraceID().String(), // sampled exemplar key
        "service", "checkout",
        "version", buildVersion,
        "endpoint", "/checkout", // bounded route template
    ), func(ctx context.Context) {
        err = doCheckout(ctx)
    })
    return err
}
```

### JVM — wall-clock profiling for a CPU-idle latency bug

```bash
# Symptom: /search p99 is 800ms but the CPU profile (-e cpu) is flat.
# Wall-clock captures the WAITING, per thread.
./asprof -d 30 -e wall -t -f search-wall.html <pid>
#   The widest tower over `SocketInputStream.read` or `Pool.borrowObject`
#   reveals the time is spent BLOCKED, not computing — invisible to -e cpu.

# Confirm lock contention specifically:
./asprof -d 30 -e lock -f search-lock.html <pid>
```

### Go — leak hunting via inuse diff over time

```bash
# Two heap snapshots an hour apart from the SAME pod.
go tool pprof -proto -output heap_t0.pb.gz http://pod:6060/debug/pprof/heap
sleep 3600
go tool pprof -proto -output heap_t1.pb.gz http://pod:6060/debug/pprof/heap

# Diff the LIVE bytes (inuse_space): red = what grew = the leak.
go tool pprof -http=:8080 -diff_base heap_t0.pb.gz heap_t1.pb.gz \
    -sample_index=inuse_space
# In continuous profiling you skip the manual capture: query the inuse TREND
# for each alloc site; the one climbing without plateau is the leak.
```

### Python — wall-clock with py-spy, no redeploy

```bash
# py-spy samples wall-clock by default (idle/GIL-waiting time included with --idle).
# Attach to a running prod process by PID — proves off-CPU latency without a restart.
py-spy record --pid 12345 --duration 30 --idle --output search-wall.svg
#   --idle : include time threads spent NOT on the CPU (waiting) — the latency time.
```

---

## Coding Patterns

### Pattern 1 — Diff against a clean baseline, normalised

```bash
go tool pprof -normalize -http=:8080 -diff_base baseline.pb.gz incident.pb.gz
# baseline = calm window, same labels. -normalize so the diff is per-unit, not "more load".
```

### Pattern 2 — Pick the profile type from the symptom

```text
high CPU + slow → CPU profile        | idle CPU + slow → off-CPU / wall-clock
GC pauses       → alloc heap profile | memory climbing → inuse TREND
plateau under load → mutex profile   | rises with load, no slow call → wall-clock (run-queue)
```

### Pattern 3 — Label every profile to join the four signals

```go
pprof.Do(ctx, pprof.Labels(
    "trace_id", traceID, "service", svc, "version", ver, "endpoint", routeTemplate,
), func(ctx context.Context) { work(ctx) })
// service/version/region MUST match the metric and trace labels exactly.
```

### Pattern 4 — Off-CPU profiling is rate-budgeted, off by default

```go
runtime.SetBlockProfileRate(10_000) // coarse; tighten only while actively hunting
runtime.SetMutexProfileFraction(5)  // 0 = off; larger = cheaper
// Make these runtime-toggleable so you can flip detail on/off without a redeploy.
```

### Pattern 5 — Strip in prod, retain debug info by build ID

```text
build with debug info → embed build ID → ship STRIPPED binary
keep debug info in a store keyed by build ID → symbolize SERVER-SIDE (debuginfod)
# Never strip without retaining symbols — the names are unrecoverable afterward.
```

### Pattern 6 — Leaks: diff two inuse snapshots

```bash
go tool pprof -diff_base heap_t0.pb.gz heap_t1.pb.gz -sample_index=inuse_space
# Red = what grew in live memory between the two = the leak, isolated.
```

---

## Best Practices

1. **Diff against a clean, comparable baseline, and normalise.** Same labels, same-length windows, similar load — or use `-normalize` so the diff reflects per-unit change, not more traffic.
2. **Choose the profile type from the symptom, before you open a viewer.** Idle CPU + high latency ⇒ off-CPU/wall; plateau under load ⇒ mutex; GC pauses ⇒ alloc; growing memory ⇒ inuse trend.
3. **Reach for off-CPU on every "slow but CPU-idle" bug.** Most latency lives off the CPU; a flat CPU profile is a signal, not a dead end.
4. **Label every signal alike** (`service`/`version`/`region`/`instance`) so metric → trace → profile join automatically. Span-scope where the platform supports it.
5. **Treat `trace_id` as a sampled exemplar label, not a metric dimension**, and keep all other profile labels bounded (route templates, not raw paths) — the cardinality discipline from metrics applies.
6. **Enforce an overhead budget with a kill switch.** ≤1–2% CPU at *peak*, bounded memory and upload, expensive profile types runtime-toggleable and off by default.
7. **Symbolize server-side, keyed by build ID.** Strip prod binaries but retain debug info; never symbolize on the hot host during an incident.
8. **Hunt leaks in the trend, not the snapshot.** The non-plateauing `inuse` climb is the leak; diff two `inuse` profiles to isolate what grew.
9. **Confirm "more calls vs slower per call"** after the diff — a red frame can be a call-rate change, not a code regression. Cross-check the metric/trace.
10. **Hand off to point-in-time profiling to *fix*.** Continuous finds it in prod; the laptop optimises it. Don't duplicate optimisation work here.

---

## Edge Cases & Pitfalls

- **Diffing a thin sliver of noise.** Both profiles are statistical; a small red frame may be sampling noise, not a regression. Trust *wide* colour changes; collect longer if a candidate is borderline.
- **Unnormalised diff over different load.** If "after" served 2× the requests, *everything* looks red — that's "more traffic," not "slower code." Normalise or equalise the windows.
- **CPU profile on an off-CPU bug.** A flat, healthy-looking CPU profile during a latency incident is the classic false negative. The time is off-CPU; switch profile type.
- **Block/mutex rate too aggressive.** `SetBlockProfileRate(1)` on a hot path can consume more CPU than the code you're profiling — the observer perturbs the observed. Start coarse.
- **Mismatched debug info during symbolization.** Symbolizing with the *wrong build's* debug info yields confidently-wrong function names. The build ID must match exactly; mismatches are worse than hex.
- **Stripped binary, no debug-info store.** Flame graphs of hex addresses, unrecoverable after the fact. Retain symbols keyed by build ID *before* you need them.
- **Span-scoped labels exploding cardinality.** A raw URL or user ID as a profile label is the same cardinality bomb as in metrics. Use bounded keys; treat `trace_id` as sampled.
- **Leak verdict from one snapshot.** "100MB live" is not a leak diagnosis. Without the *trend*, you can't tell live-and-stable from live-and-growing.
- **Profiler floods the network during an outage.** Upload frequency uncapped → the profiler competes with the recovering service for bandwidth. Cap and batch uploads; have a kill switch.
- **Inlining and the diff.** A compiler inlining change between versions can move time between frames in the diff without any real regression. Read the diff at the tower level, not a single frame, when versions differ in optimisation.

---

## Common Mistakes

1. **Debugging latency with a CPU profile** when the time is off-CPU — staring at a flat profile and concluding "the profiler is broken."
2. **Diffing without normalising**, so a traffic increase reads as a universal regression.
3. **Trusting a thin red frame** in a diff as a real regression when it's within the sampling noise floor.
4. **Reading the diff colours backwards** — chasing a blue (improved) frame, or treating red as "good."
5. **No shared labels across signals**, so the profile can't be joined to the trace or metric — every investigation starts from scratch.
6. **Symbolizing on the production host**, burning the CPU you can least spare during an incident.
7. **Stripping prod binaries without retaining debug info**, leaving permanently un-symbolizable hex.
8. **Calling a leak from one heap snapshot** instead of the `inuse` trend over time.
9. **Setting block/mutex rates so fine the profiler perturbs the workload** it's measuring.
10. **Re-deriving optimisation here** instead of handing the found hotspot to point-in-time profiling.

---

## Tricky Points

- **A diff is a delta of two estimates.** Its accuracy is bounded by the *noise of both* profiles, not just one. More samples (longer windows) tighten the diff; you cannot fix a noisy diff in the viewer.
- **Width in a diff means delta magnitude, not absolute cost.** A function that's the most expensive overall may be *grey* in the diff (it didn't change), while a small function that doubled is bright red. The diff hides "expensive but stable" by design — that's the point, but don't forget the stable cost is still there.
- **Off-CPU "time" is wall time, not CPU time.** Summing an off-CPU profile can exceed the wall-clock duration if many threads waited in parallel. Read it per-thread; don't compare its totals to a CPU profile's totals.
- **`alloc` and `inuse` are different graphs of the same heap.** A line can dominate `alloc` (churn → GC) while barely appearing in `inuse` (it's freed immediately), and vice versa. Pick by question: GC pressure vs leak.
- **A red frame ≠ slower code.** It can be the *same* code called more often. The diff measures total resource; call-rate vs per-call cost is a separate question the trace/metric answers.
- **Exemplars are sampled, so absence is weak evidence.** "No exemplar trace for this bucket" doesn't mean no slow request happened — just that none was sampled. Presence is strong; absence is not.
- **Build ID, not file path or version string, is the symbolization key.** Two builds of "v2.4.1" (rebuilt) can differ in addresses; only the content-hash build ID pins the right debug info.
- **Continuous profiling is still sampling.** A diff, a trend, an exemplar — all inherit the statistical nature. The novelty is the time axis and the joins, not exactness.

---

## Apply it

1. State the system invariant that **Continuous Profiling** must protect.
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

- Which invariant must remain true when Continuous Profiling fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
