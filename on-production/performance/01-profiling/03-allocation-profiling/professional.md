# Allocation Profiling — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Allocation Profiling** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Profiling](../README.md) → Allocation Profiling
> *The senior page taught you to read an allocation profile and cut a hot call site. This page is about doing it continuously, in production, across a fleet — where "allocs/op" stops being a microbenchmark number and becomes a line on the cloud bill, a p99 SLO, and a CI gate that blocks the merge that would have doubled your GC CPU.*

---

## Continuous Allocation Profiling in Production

- The earlier tiers profiled *on demand*: reproduce load, grab a profile, read it. That works for a known-bad function.
- It fails for the question that actually matters at scale — *"across the whole fleet, right now, where is the garbage coming from?"* — because the worst allocator is rarely the function you'd think to profile, and synthetic load rarely reproduces the real allocation shape (next section).

**Continuous profiling** runs a low-overhead allocation profiler always, on every instance, and ships the profiles to a central store you can query and diff over time. Two pillars:

- **Sampling, not tracing.** You do not record every allocation — that would be ruinous overhead.
  - Go's runtime records a stack every `MemProfileRate` bytes allocated (default 512 KB).
  - The JVM's JFR `ObjectAllocationSample` event samples allocations against a throughput target.
  - async-profiler's `--alloc` samples on a byte interval.
  - The sampled profile is statistically faithful for the *hot* sites — exactly what you want — at single-digit-percent or sub-percent overhead.
- **Always-on, fleet-wide, queryable.** Pyroscope, Parca, Datadog Continuous Profiler, and Google Cloud Profiler scrape these profiles continuously and let you slice by service, version, host, and (critically) custom labels. The flame graph you look at is *aggregated across the fleet over a time window*, not one host's lucky sample.

**Go** exposes this for free via `net/http/pprof`; a continuous profiler scrapes `/debug/pprof/allocs`:

```go
import _ "net/http/pprof" // registers /debug/pprof/* on the default mux

func main() {
    // runtime.MemProfileRate defaults to 512*1024 (sample one stack per ~512 KB).
    // Lower = more detail + more overhead. Leave it at the default in prod.
    go func() { log.Println(http.ListenAndServe("localhost:6060", nil)) }()
    // ... your server ...
}
```

```yaml
# Parca / Pyroscope scrape config — pull alloc_space continuously, fleet-wide.
scrape_configs:
  - job_name: 'checkout-svc'
    scrape_interval: 30s
    profiling_config:
      pprof_config:
        memory:               # the alloc profile
          enabled: true
          path: /debug/pprof/allocs
    static_configs:
      - targets: ['checkout-svc:6060']
```

**Java** uses JFR, designed from the ground up for always-on production use. Modern JFR samples object allocations rather than instrumenting every `new`, so the overhead is low enough to leave running permanently:

```bash
# Always-on JFR with allocation sampling, written to a rolling repository.
java -XX:StartFlightRecording=settings=profile,maxsize=512m,name=alloc \
     -XX:FlightRecorderOptions=repository=/var/jfr \
     -jar app.jar
# The 'profile' settings template enables ObjectAllocationSample at a low,
# throughput-bounded rate. async-profiler is the alternative:
#   asprof -e alloc -d 60 -f alloc.html <pid>   # allocation flame graph
```

> **The professional reality:** the value is not one flame graph — it's the *time series of flame graphs*. Continuous profiling lets you diff allocation between version N and N+1, see a regression the moment a deploy rolls out, and answer "what changed?" with a flame-graph diff instead of a guess. On-demand profiling answers "why is this slow *right now*"; continuous profiling answers "what is *always* generating our garbage, and when did it get worse." Treat it as infrastructure, like metrics and traces — not a tool you reach for only during an incident.

---

## Why Production Allocation Profiles Beat Synthetic Ones

This is the single most important reason to invest in continuous profiling, and it is widely underappreciated: **allocation is driven by the size and shape of real payloads, which synthetic benchmarks almost never reproduce.**

- A microbenchmark or a load test runs a fixed, usually *small*, usually *uniform* input.
- Production runs the long tail: the one tenant whose API responses are 4 MB instead of 4 KB, the request with 10,000 line items instead of 10, the deeply nested document that triggers a recursive marshaler, the user whose name has an emoji that forces a slow Unicode path that allocates.
- Allocation tracks data volume and data shape, so the profile from prod is *quantitatively and qualitatively different* from the one from your laptop:

- **Real payload sizes drive real allocation.** A JSON decoder that allocates `O(document size)` shows up as a rounding error in a benchmark with a 1 KB fixture and as the #1 allocator in prod where the p99 document is 2 MB. You cannot find this with synthetic load unless you happened to synthesize the p99 document — and you didn't.
- **Real distributions surface the tail.** The handler that allocates fine on average but explodes for the 0.5% of requests with a huge `expand=` parameter is invisible in a uniform load test and dominant in a fleet aggregate that includes those requests.
- **Real call mixes reveal the true hot path.** Your benchmark exercises the function you suspected. Production exercises the function you didn't — often a logging line, a metrics tag, or a serialization shim on a path you never profiled because it "isn't the interesting code."

> **The principle:** *profile where the payloads are real.* A synthetic allocation profile tells you how your code allocates on the inputs you imagined; a production allocation profile tells you how it allocates on the inputs you actually have. The gap between those two is where the expensive surprises live. This is the allocation analogue of "build on the oldest libc you support" — the environment that *sets the cost* is production, not your dev box, so measure there. Synthetic profiling is for *verifying a fix* (you control the input, so the signal is clean); production profiling is for *finding the problem* (the input is real, so the signal is true).

---

## The GC-Cost-to-Allocation Link as the Business Case

Allocation profiling earns its keep because there is a near-mechanical chain from allocation rate to dollars, and you can put numbers on every link. This is how you turn "this code allocates a lot" into a funded project.

**The chain:**

1. **Allocation rate drives GC frequency.** A tracing GC runs when the heap grows by some fraction since the last cycle (Go's `GOGC`, the JVM's heuristics). Halve the bytes allocated per second and you roughly halve how often the collector must run.
2. **GC frequency drives GC CPU.** Each cycle costs CPU to mark and sweep live objects. Fewer cycles → less CPU spent collecting → more CPU available for actual work. On allocation-heavy services it is routine to see the GC consuming **20–40% of total CPU**; on a pathological one it can exceed 50%.
3. **GC CPU drives instance count.** If GC is 30% of your CPU and you cut allocation rate by half, you reclaim on the order of 15% of every core. Across a 200-instance fleet at, say, $0.10/hour per instance, reclaiming 15% is ~30 instances' worth of headroom — roughly **$26,000/year** that either disappears from the bill or absorbs growth you'd otherwise have paid for.
4. **GC pauses (or GC CPU contention) drive tail latency.** Even with a concurrent collector, allocation pressure shows up at p99: more frequent collection means more time when GC threads contend with application threads, more assist work (Go makes allocating goroutines *help* the GC when they outrun it — "mutator assist"), and more chance a request lands during heavy GC activity. Cutting allocation rate routinely cuts p99 *more than it cuts the mean*, because the tail is where GC contention concentrates.

This is the origin of the canonical pattern: **"we halved p99 by cutting allocations."** The team didn't touch the algorithm or add a cache; they found the allocation hot path in a production profile, removed the garbage, the GC ran half as often, mutator assists dropped, and the tail collapsed.

> **The business case, written for the cost review:** *"Service X spends 32% of CPU in GC (measured: Go `runtime/metrics gc/cpu`, or JVM GC logs). The production allocation profile attributes 60% of allocations to one JSON re-marshaling path. Removing it (stream instead of buffer) is projected to cut allocation rate ~55%, GC CPU to ~15%, and let us run ~25 fewer instances ($22k/yr), with a p99 improvement we'll verify against the SLO."* That sentence — a measured GC cost, an attributed cause from a prod profile, a projected rate cut, and a dollar/latency outcome — is the entire reason allocation profiling is a production lever and not a microbenchmark hobby.

The *measurement* of GC cost is the load-bearing input:
- In Go, read `runtime/metrics` (`/gc/cpu/...`, `/gc/heap/allocs:bytes`) or `GODEBUG=gctrace=1`.
- In Java, read GC logs (`-Xlog:gc*`) or the JFR GC events.
- Never argue from "it feels like a lot of GC" — argue from the percentage.

---

## Attributing Allocation Cost to Endpoints and Tenants

- A fleet-wide flame graph tells you *which function* allocates. It does not, by itself, tell you *which request* drove it there — and that's the question that lets you fix the right thing.
- A flame graph that says `encoding/json.Marshal` is your top allocator is true and useless; *every* endpoint marshals JSON.
- You need to know that 70% of that marshaling allocation comes from `GET /reports/export`, and within that, from one tenant exporting daily.
- The mechanism is **profile labels**: tags attached to samples so you can group and filter the allocation flame graph by dimensions that matter to *you*, not just by call stack.

**Go — `pprof.Labels`** attach to the goroutine and ride along on every allocation sample it takes:

```go
func handler(w http.ResponseWriter, r *http.Request) {
    labels := pprof.Labels(
        "endpoint", routePattern(r), // "/reports/export", not the raw URL
        "tenant", tenantID(r),       // bounded cardinality — see the warning
    )
    pprof.Do(r.Context(), labels, func(ctx context.Context) {
        serve(ctx, w, r) // every allocation sample taken here is tagged
    })
}
```

Now in Pyroscope/Parca you filter the *allocation* flame graph by `endpoint="/reports/export"` or `tenant="acme"` and see the garbage attributable to exactly that slice — turning "json.Marshal is hot" into "the report export for two tenants is 60% of our allocations."

**Java — JFR event context.** JFR allocation events (`ObjectAllocationSample`) carry the thread and stack; you attribute to an endpoint by correlating the thread/time window with your request tracing, or by naming worker threads/pools per workload, or via custom JFR events that mark a request's span. async-profiler's `--alloc` similarly attributes by stack, and you slice by the request context captured on the thread.

> **Cardinality is the trap.** Labels are not free, and high-cardinality labels (raw user ID, request ID, full URL with query string) will blow up the profile store and the scrape cost. Tag by *bounded* dimensions: the route *pattern* (`/users/{id}`, never `/users/8412`), the tenant *only if* tenants are countable in the hundreds-to-thousands, the API version, the queue name. The goal is to answer "which endpoint/tenant/workload class generates the garbage," which needs tens-to-thousands of label values, not millions.

The payoff is the **fleet-wide attribution query**: *"across every instance, over the last 6 hours, group allocation by endpoint."* That one query routinely reveals that a single handler — often an export, a search, a bulk write, or a webhook fan-out — generates a wildly disproportionate share of all garbage in the service, and it's almost never the handler anyone would have profiled by hand.

---

## Allocation Regressions in CI — The Easiest Perf Gate

Here is allocation profiling's best-kept secret as a quality gate: **`allocs/op` is deterministic.** Wall-clock latency in CI is noisy — it varies with the runner's neighbors, CPU throttling, cache state, and the phase of the moon — so latency-based perf gates are flaky and teams disable them. Allocation *counts* don't vary: a given code path on a given input allocates the same number of objects every single time, on any machine, under any load. That makes allocs/op the **cheapest, least-flaky performance gate you can run** — the one perf assertion that won't page you with false positives.

**Go** gives you the count directly from `testing.B`:

```go
func BenchmarkRenderInvoice(b *testing.B) {
    inv := fixtureInvoice()
    b.ReportAllocs() // report allocs/op and B/op alongside ns/op
    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        _ = RenderInvoice(inv)
    }
}
```

```
BenchmarkRenderInvoice-8   215000   5421 ns/op   3104 B/op   12 allocs/op
                                                  ^^^^^^^^^   ^^^^^^^^^^^^
                                                  deterministic — gate on these, not ns/op
```

The gate: capture the baseline allocs/op on `main`, fail the PR if it rises beyond a tiny threshold. Because the number is exact, the threshold can be *zero new allocations* on critical paths — a gate that is impossible to write reliably for latency:

```bash
# CI: compare PR vs base with benchstat; fail if allocs/op regressed.
go test -run=^$ -bench=. -benchmem -count=10 ./... > pr.txt
git stash && go test -run=^$ -bench=. -benchmem -count=10 ./... > base.txt && git stash pop
benchstat -col /alloc base.txt pr.txt   # shows delta + significance
# Wire a check: nonzero positive delta on a guarded benchmark → exit 1.
```

A blunt, zero-dependency variant asserts the budget *inside the test*, so the gate lives with the code:

```go
func TestRenderInvoice_AllocBudget(t *testing.T) {
    inv := fixtureInvoice()
    avg := testing.AllocsPerRun(100, func() { _ = RenderInvoice(inv) })
    if avg > 12 { // the budget; ratchet it DOWN as you optimize, never up silently
        t.Fatalf("alloc budget exceeded: got %.0f allocs, budget 12", avg)
    }
}
```

**Java** asserts allocation budgets with JMH's `gc.alloc.rate.norm` profiler, which reports normalized bytes allocated per operation — deterministic the same way:

```java
@Benchmark
public String renderInvoice(InvoiceState s) { return Invoices.render(s.invoice); }
// run: -prof gc  → reports gc.alloc.rate.norm in B/op; gate on that value
```

This is where allocation profiling links directly to the discipline of [performance budgets and regression testing](../../07-performance-budgets-and-regression-testing/professional.md): a performance budget is only enforceable if the metric is stable, and allocs/op is the most stable performance metric you have. Make it a *ratchet* — every optimization lowers the budget, and the budget can only go down with an explicit, reviewed bump. A regression then can't merge silently; someone has to consciously raise the number and justify it in review.

> **Why this is the gate to start with:** teams that try to gate on p99 or ns/op in CI get burned by noise, distrust the gate, and turn it off. Teams that gate on allocs/op get a signal that is *exact and reproducible*, so the gate is trusted, so it stays on, so regressions actually get caught at the PR. Start your performance-regression program here; add latency gates later, in a controlled environment, once allocs/op has proven the value.

---

## Diagnosing an Allocation-Driven Incident

A structured workflow beats staring at a flame graph. Allocation incidents have a recognizable signature — **CPU and/or p99 climbed, but no algorithm or traffic-*volume* change explains it** — and a repeatable triage.

**The signature and the triage tree:**

```
Symptom                                          →  Likely cause / next step
─────────────────────────────────────────────────────────────────────────────
GC CPU % climbed, traffic volume flat            →  allocation rate rose → diff alloc profile vs last good version
p99 doubled, mean ~unchanged, no algo change     →  GC contention at the tail → check gctrace/GC logs + alloc rate
allocation rate spiked at a deploy boundary      →  a code change started allocating → flame-graph DIFF across versions
allocation rate spiked WITHOUT a deploy          →  payload shape changed (a tenant, an upstream) → slice by tenant/endpoint label
"few large" allocations dominate alloc_space     →  oversized buffers/slices → preallocate, stream, cap
"many small" allocations dominate alloc_objects  →  per-item boxing/copies/log fields → batch, pool, remove boxing
```

**The command sequence (Go), prod-first:**

```bash
# 1) Confirm it's allocation-driven: is GC cost actually up?
GODEBUG=gctrace=1 ...    # or read runtime/metrics gc/cpu via your dashboard

# 2) Get the production allocation profile and DIFF it against the last good one.
go tool pprof -alloc_space -diff_base=good.pb.gz current.pb.gz
#   top / list <fn> — the diff isolates what STARTED allocating, ignoring steady-state noise

# 3) Decide the shape: rate-by-volume vs rate-by-count.
go tool pprof -alloc_space current.pb.gz   # bytes  → "few large" suspects
go tool pprof -alloc_objects current.pb.gz # counts → "many small" suspects

# 4) If there was no deploy, attribute by label to find WHICH input changed.
#    (slice the flame graph by endpoint / tenant in Pyroscope/Parca)
```

**The three culprits that cause the overwhelming majority of allocation incidents:**

1. **A serialization storm.** A change makes the service marshal/unmarshal more, or on bigger payloads, or redundantly (encode, log the encoded form, encode again). JSON is the usual offender; `encoding/json` allocates per field and reflects per type. The flame graph lights up under `Marshal`/`Unmarshal`/reflection.
2. **A logging hot path.** A log line on a per-request (or per-*item*) path that builds strings, boxes arguments (`interface{}`/varargs), or — worst — does expensive work *inside the log call* that runs even when the level is disabled. This is insidious because logging "isn't the real code," so nobody profiles it; multiplied fleet-wide it can be the #1 allocator. (See War Stories.)
3. **Reflection.** Reflection-based codecs, validators, ORMs, and mappers allocate boxed values, intermediate maps, and `reflect.Value` wrappers per call. A new validation rule or a switch to a reflection-heavy library can quietly multiply allocation.

> **The professional discipline:** never debug an allocation incident by reading the *current* flame graph alone — it shows you steady-state allocation (the json.Marshal that's always there), not *what changed*. Always **diff against the last known-good profile** (`-diff_base`). The diff is what separates "code that has always allocated" from "the regression you shipped Tuesday," and it turns a multi-hour flame-graph squint into a five-minute "this one frame went from 2% to 40%."

---

## Decision Frameworks

**Is this allocation worth fixing? Ask:**
- Does it show up in the *production* profile (not just a microbenchmark)? → if it's not in the prod aggregate, it's not your problem yet.
- Is GC CPU actually high (measured, e.g. >15–20%)? → if GC is 3% of CPU, cutting allocation won't move the bill or the tail; spend effort elsewhere.
- Does the fix lower p99 or instance count? → tie it to a dollar or latency outcome before funding it. "Allocates a lot" is not a reason; "30% GC, this is 60% of it, projected $22k/yr" is.

**`alloc_space` or `alloc_objects` — which lens? Ask:**
- Is GC CPU the problem? → both matter, but **`alloc_objects` (count)** correlates with GC mark cost (more objects = more to trace). Start there.
- Is memory *footprint* or large-buffer churn the problem? → **`alloc_space` (bytes)** — find the "few large" allocations.
- "Many small" in `alloc_objects` → batching, pooling, removing boxing. "Few large" in `alloc_space` → preallocation, streaming, capping sizes.

**Where do I attribute? Ask:**
- Is the hot allocator a generic function (`json.Marshal`, `append`, logging)? → slice by **endpoint label** to find the request that drives it; the function name alone is useless.
- Is one tenant suspected? → slice by **tenant label** (only if tenant cardinality is bounded).

**What gate do I add? Default to:**
- An **allocs/op** ratchet on critical paths (Go `ReportAllocs`/`AllocsPerRun`; Java JMH `gc.alloc.rate.norm`), failing on any positive delta, budget lowered only by explicit review. It's the cheapest, least-flaky perf gate — start here, before any latency gate.

---

## Common Mistakes

1. **Profiling allocation only synthetically.** A 1 KB fixture hides the decoder that allocates `O(document size)` and dominates on prod's 2 MB payloads. Use production continuous profiling to *find* hot spots; use benchmarks to *verify* the fix.

2. **Optimizing allocation when GC isn't the bottleneck.** If GC is 3% of CPU, cutting allocation buys nothing visible. *Measure* GC cost (`runtime/metrics`, GC logs) first; only chase allocation when GC is meaningfully expensive.

3. **Reading the current flame graph instead of a diff during an incident.** The current profile shows steady-state allocation; the *diff against last-good* (`-diff_base`) shows the regression. Always diff.

4. **High-cardinality profile labels.** Tagging by raw user ID, request ID, or full URL blows up the profile store and scrape cost. Tag by bounded dimensions — route *pattern*, version, queue, bounded tenant set.

5. **Gating CI on latency instead of allocs/op (first).** Wall-clock in CI is noisy; the gate flakes and gets disabled. Start with the deterministic allocs/op gate; it's trusted because it's exact.

6. **Ignoring the logging hot path.** "Logging isn't the real code," so nobody profiles it — and it's a top fleet-wide allocator because argument evaluation runs even for dropped levels, on every request. Guard expensive log args; check it in the prod profile.

7. **Confusing allocation with retention.** Allocation profiling answers "what *churns*" (rate, GC pressure); heap/retention profiling answers "what *stays alive*" (footprint, leaks). They're different questions and often different fixes — don't reach for a pool when you have a leak, or for `weak` references when you have churn.

---

## Apply it

1. Define the user or business outcome that **Allocation Profiling** should improve.
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

- Which measurable outcome justifies investing in Allocation Profiling?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
- A teammate "optimized" by adding `sync.Pool` everywhere and allocations didn't drop — what likely went wrong?
- Would you gate `allocs/op` in CI? How, and what are the failure modes?
- When is continuous allocation profiling in production worth it, and how do you keep the overhead acceptable?
- What allocation culprits would you look for first in a code review, before any profiler runs?
- How do you decide an allocation is "worth keeping" versus worth eliminating?
