# CPU Profiling — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **CPU Profiling** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Performance](../../README.md) → [Profiling](../README.md) → CPU Profiling
> *The senior page made you trust a single profile. This page is about never taking one again — because by now the profiler is always running, on every host, and the question is no longer "let me profile this" but "what does last Tuesday's fleet profile say, sliced by endpoint, diffed against the release before it, and costed in dollars per core?" CPU profiling stops being a tool you reach for during an incident and becomes a continuously-running sensor that funds itself.*

---

## Continuous, Always-On Profiling as Infrastructure

The senior page introduced continuous profiling as a capability. At the professional level it's a *system you run*, with the same operational weight as your metrics pipeline — agents, a storage backend, retention policy, query API, and an on-call rotation when it breaks.

- The lineage matters because it explains the design. Google's **Google-Wide Profiling (GWP)** (Ren et al., IEEE Micro 2010) established the model: sample a small, randomly-chosen subset of machines across the entire datacenter at low frequency, all the time, and aggregate the results centrally.
- The insight was statistical — you don't need to profile every host continuously; you need enough samples across the fleet that aggregate attribution converges.
- GWP made "which function, across all of Google, burns the most CPU" a query you ran against a table, not a study you commissioned. Every modern continuous profiler is a descendant of that idea.

The open-source and commercial successors split into two architectural camps:

- **eBPF, whole-system, zero-instrumentation** — **[Parca](https://www.parca.dev/)** / Parca Agent and the **[Pyroscope](https://pyroscope.io/)** eBPF agent attach a `perf_event` stack sampler in the kernel via eBPF, sample on-CPU stacks of *every* process on the host, aggregate stacks in a BPF map in-kernel, and ship pre-folded stacks to a server. No recompile, no SDK, no per-app config — you get a flame graph of `postgres`, your Go service, and the JVM next to it, on a host you never instrumented. **[Polar Signals Cloud](https://www.polarsignals.com/)** is the commercial Parca lineage.
- **SDK / agent, per-language, context-aware** — **Datadog Continuous Profiler**, **Grafana Cloud Profiles** (Pyroscope SDKs), and the per-language libraries link into the process and emit profiles with application context attached (request tags, trace IDs, deploy version). They cost a recompile/dependency but give you labels the kernel can't see — *which endpoint*, *which tenant*, *which trace*.

```bash
# Parca Agent: system-wide continuous profiling via eBPF, no app changes
parca-agent \
  --node="$(hostname)" \
  --remote-store-address=parca.observability.svc:7070 \
  --profiling-cpu-sampling-frequency=19   # 19 Hz: deliberately low, fleet-safe
```

```go
// Pyroscope Go SDK: per-process, with deploy/version tags the kernel can't know
pyroscope.Start(pyroscope.Config{
    ApplicationName: "checkout-service",
    ServerAddress:   "https://profiles.grafana.net",
    Tags: map[string]string{
        "version": os.Getenv("GIT_SHA"),
        "region":  os.Getenv("AWS_REGION"),
    },
})
```

- The choice between camps is the recurring professional tradeoff: eBPF agents give you *coverage* (everything, instantly, no buy-in from app teams) but only the dimensions the kernel sees (process, function, host). SDKs give you *richness* (endpoint, tenant, trace correlation) but require every team to adopt them.
- The mature answer is usually **both** — an eBPF agent for fleet-wide baseline coverage, plus SDK labels in the services where slicing by endpoint or tenant pays for the integration cost.
- What you get for running it is a profile *of the past*. Metrics tell you CPU was at 80% at 14:32; a continuous profiler tells you *which function* was burning that 80% at 14:32, queryable after the fact, without having reproduced anything. That is the capability that turns "we couldn't repro it" into "let me pull the profile from the window it happened in."

> **The professional reality:** continuous profiling is the fourth observability pillar, next to metrics, logs, and traces — and it's the only one that answers "where exactly are the cycles going" at function granularity, fleet-wide, retroactively. Standing it up is infrastructure work (agents, storage, retention, query), not a developer convenience. Once it exists, "let me profile this" is replaced by "let me query the profile that's already there."

---

## The Overhead Budget That Makes It Safe

The entire practice rests on a single number: the per-host overhead has to be small enough that running it *permanently on production* is uncontroversial. The working budget is **under 1–2% of CPU**, and everything about the design exists to hold that line.

The math is the senior overhead model applied at scale — cost per sample is roughly: take the interrupt, latch the RIP, walk the stack, record. At 19 Hz with frame-pointer or eBPF unwinding, that's a few microseconds, nineteen times a second, per core — comfortably under 1%. The levers, in order of impact:

- **Frequency.** Linear in cost. GWP-style fleet profiling runs at **~19–100 Hz**, not the 999 Hz you'd use for a focused one-off. You compensate for the lower per-host rate with the *number of hosts and duration* — aggregate samples across the fleet still converge.
- **Unwinding method.** This is where budgets are blown. Frame pointers (`-fno-omit-frame-pointer`, `-XX:+PreserveFramePointer`) and LBR are cheap; **DWARF unwinding copies kilobytes of stack per sample** and can push a continuous profiler from sub-1% to several percent — fine for a one-off, disqualifying for always-on. This is the single biggest reason Fedora and Ubuntu re-enabled frame pointers archive-wide: it converts the whole fleet from "DWARF-only, expensive to profile" to "fp, cheap to profile always."
- **In-kernel aggregation.** eBPF agents fold stacks into a BPF map *in the kernel* and hand userspace pre-aggregated counts, instead of copying every raw sample out. That slashes both data volume and the userspace CPU of the agent itself.
- **Sampling, not tracing.** Continuous profiling samples; it never instruments every function entry. Instrumentation cost scales with call frequency and would inflate hot leaf functions 10–100× (the senior instrumentation-distortion point) — fatal for an always-on tool.

```bash
# Measure your profiler's actual overhead before trusting the budget:
perf stat -e task-clock -p <pid> -- sleep 60      # baseline, profiler off
# enable continuous profiling, repeat; the delta IS your overhead budget spend
```

The discipline is to **measure** the overhead, not assume it. A misconfigured agent — DWARF unwinding on, frequency cranked, no in-kernel folding — can quietly cost 5–8% across the fleet, which on a 10,000-core footprint is 500–800 cores of pure observability tax. The budget isn't a vibe; it's a line item you verify, because the whole justification for "always on" collapses if the sensor costs more than the bugs it finds.

> **Key insight:** "always-on in production" is *earned* by the overhead budget, and the budget is won at the unwinder. Low, odd frequency (19–99 Hz) plus frame-pointer/eBPF unwinding plus in-kernel aggregation keeps it under 1–2%; DWARF unwinding or high frequency silently blows it. Verify the number with `perf stat` — on a large fleet the difference between 1% and 6% is hundreds of cores.

---

## Attributing Fleet CPU Cost to Teams, Services, and Functions

Here is the capability that makes continuous profiling fund itself: turning a fleet-wide flame graph into a **dollar-denominated cost-attribution report**. This is the artifact that gets the program budget renewed.

The chain is mechanical once the profiler exists. A flame graph is a set of (stack, sample-count) pairs. Sample count is proportional to CPU time. CPU time, multiplied by your fleet's cost-per-core-hour, is dollars:

```
fleet CPU cost of a function
  = (its share of fleet samples)
  × (total fleet cores)
  × (cost per core-hour)
  × (hours)
```

- A 12,000-core fleet on cloud instances at roughly **$0.04 per core-hour** (a typical blended on-demand-plus-savings-plan rate) costs ~$4.2M/year in compute.
- If the aggregate profile shows JSON serialization across all services is **6%** of fleet CPU, that's **720 cores, ~$250K/year**, spent encoding and decoding JSON.
- Now "should we adopt a faster codec" is not an aesthetic debate — it's a quarter-million-dollar line item with a named owner.

The same arithmetic rolls up by **service** and by **team**:

- **Per service:** sum samples tagged with each service's deploy label. This is the "top CPU consumers" leaderboard — the ten services burning the most fleet CPU. It is the single highest-leverage report a platform team produces, because it points optimization effort at the services where a 10% win is worth real money, instead of where it's satisfying.
- **Per team:** map services to owning teams (you already have this in your service catalog) and aggregate. Now compute spend is a number each team owns, which changes behavior: a team that can *see* it's burning $400K/year on CPU has a reason to profile its own services.
- **Per function:** the cross-service view — "which single function, summed across every service that calls it, costs the most?" This is GWP's original query, and it surfaces shared-library and framework hot spots (a logging formatter, a serialization path, a crypto routine) that no single team would ever find because each one's slice looks small locally but the *sum* is enormous.

```bash
# Parca / pprof: top functions across the fleet, by flat CPU, with cost annotation
go tool pprof -top -nodecount=20 'http://parca:7070/...?query=fleet&from=-7d'
# multiply each row's flat % by (fleet cores × $/core-hr × hours) → $/year per function
```

> **The economics:** continuous profiling is the rare observability investment with a legible ROI. The "top CPU consumers" report routinely identifies six- and seven-figure optimization opportunities — a serialization path here, an over-eager retry-with-full-payload there — that pay for the entire profiling program many times over in the first quarter. Frame the program in dollars per core, not flame graphs, and it funds itself.

---

## Labels and Tags — Slicing the Profile by Application Dimension

A raw fleet profile says "function X is hot." That is rarely actionable on its own, because the next question — *hot for what?* — needs an application dimension the raw stack doesn't carry. **Labels** (Go's pprof term) and **tags** (the general term) attach key/value context to each sample so you can slice the profile by endpoint, tenant, version, or any axis you choose.

In Go, the senior page showed the mechanism; the professional move is using it as a *standard middleware* so every service emits the same dimensions:

```go
// CPU samples taken inside this scope are tagged endpoint + tenant + version.
func ProfilingMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        labels := pprof.Labels(
            "endpoint", routePattern(r),     // "/checkout/{id}", not the raw path
            "tenant",   tenantID(r),
            "version",  buildSHA,
        )
        pprof.Do(r.Context(), labels, func(ctx context.Context) {
            next.ServeHTTP(w, r.WithContext(ctx))
        })
    })
}
```

```bash
# Of all fleet CPU, how much is the /checkout endpoint?
go tool pprof -tagfocus='endpoint=/checkout/{id}' fleet.pprof
# And of /checkout, which tenant dominates?
go tool pprof -tagfocus='endpoint=/checkout/{id}' -tagshow=tenant fleet.pprof
```

For the JVM, async-profiler and the continuous profilers attach context similarly — async-profiler's `--ctx` / contextual labels and the Datadog/Pyroscope agents propagate request tags and trace IDs so a CPU sample can be correlated back to the *span* that was executing. That correlation — CPU profile ↔ distributed trace — is what lets you go from "this trace was slow" to "and here's the flame graph of the CPU it burned, just for that endpoint."

The dimensions that earn their keep in practice:

- **`endpoint` / route** — turns "function X is hot" into "function X is hot *on the checkout path*," which tells you whose latency it affects. The single most useful label.
- **`version` / deploy SHA** — the prerequisite for release diffing (next section). Tag every sample with the build, and a regression diff becomes a label filter.
- **`tenant` / customer** — in multi-tenant systems, reveals when one customer's traffic shape is driving disproportionate CPU. The "why is one tenant 40% of our compute" answer.
- **`request_size` bucket / `feature_flag`** — surfaces input-dependent hot paths: a pathological large-payload case, or a flag that quietly doubled work for the cohort it's enabled for.

A caution that bites: labels must be **bounded cardinality**. Tag by *route pattern* (`/users/{id}`), never the raw path (`/users/8675309`), or you blow up the profile store's cardinality the same way unbounded metric labels blow up Prometheus. Tenant is acceptable because it's bounded by customer count; raw user ID is not.

> **Key insight:** an untagged profile answers "what is hot"; a tagged profile answers "what is hot, *for whom, on which path, in which release*" — the difference between interesting and actionable. Make `endpoint` and `version` standard labels via shared middleware, keep cardinality bounded (route patterns, not raw paths), and a fleet profile becomes a multi-dimensional query instead of a flat list.

---

## Diffing Profiles Across Releases to Catch Regressions

The marquee feature of continuous profiling is **differential**: not "what is hot" but "what got *hotter* between release N and release N+1." A flame-graph diff between two time windows — or two `version` labels — points straight at the function that regressed, and therefore at the commit that caused it.

- The mechanism is subtraction. Take the aggregate profile for the week before a deploy (or filtered to `version=old`) and the week after (`version=new`), normalize both to per-request or per-unit-work (crucial — raw CPU rises with traffic, which isn't a regression), and render the *delta*.
- Functions that grew show up as hot in the diff; functions unchanged cancel to zero.
- A **differential flame graph** colors growth red and shrinkage blue, so a CPU regression is a red tower sitting on the exact frame that got more expensive.

```bash
# Go pprof: base = before the deploy, current = after
go tool pprof -diff_base=before.pprof after.pprof
(pprof) top -cum            # functions ranked by CPU DELTA, not absolute
(pprof) list regexedFunc    # line-level: which line in the regressing function grew

# Continuous-profiler UI (Parca/Pyroscope/Grafana): pick two time ranges or two
# version labels → "Diff" view renders the red/blue differential flame graph directly.
```

- The non-obvious discipline is **normalization**. If traffic grew 15% between the windows, *every* function burns ~15% more CPU — that's load, not a regression.
- Diff on a per-request basis (CPU-seconds per request, or sample-share rather than absolute samples) so genuine load growth cancels and only *relative* changes survive.
- Skipping this is the classic false alarm: a diff that lights up everything because you compared a quiet Sunday to a busy Monday.

This turns regression-hunting from archaeology into a filter:

- The old workflow was "compute spend went up, bisect through deploys, reproduce locally, profile."
- The new one is "open the diff between the two suspect versions, read the red tower, it names the function and often the line."
- Wired into CI/CD, the diff can even gate a release: capture a profile from a canary running `version=new`, diff against `version=old` on the same traffic, and **fail the rollout if any function's CPU share grew beyond a threshold** — a CPU-regression test, the profiling analog of a performance budget (see [07 — Performance Budgets and Regression Testing](../../performance-budgets-and-regression-testing/professional.md)).

> **Key insight:** the highest-value thing a continuous profiler does is *diff*. Two windows (or two `version` labels), normalized per-request, rendered as a red/blue differential flame graph, names the function that regressed and points at the commit — turning "why did CPU creep up" from a multi-day bisect into a thirty-second read. Normalize per unit of work, or load growth masquerades as regression.

---

## PGO — The Production Profile as a Build Input

Continuous profiling produces a corpus of real production profiles. **Profile-Guided Optimization (PGO)** is the downstream consumer that feeds those profiles back into the compiler, so the optimizer makes its decisions — inlining, branch layout, register allocation, code placement — based on *what production actually does* rather than static heuristics. This closes a loop: the fleet profiles itself, and the next build is optimized for the workload the fleet actually runs.

The professional point is that **the profile must come from production**, not a benchmark. PGO optimizes for the distribution it's shown; feed it a synthetic profile and it optimizes for fiction. The whole value is that your continuous-profiling pipeline already *has* the real distribution — PGO is the consumer that monetizes it a second time.

**Go PGO** (stable since Go 1.21) is the cleanest example. You drop a `default.pgo` file — a pprof CPU profile — next to `main`, and `go build` uses it automatically:

```bash
# 1. Pull a representative CPU profile from production (the real workload!)
curl 'http://prod-host:6060/debug/pprof/profile?seconds=60' -o cpu.pprof
# 2. Commit it as default.pgo at the main package
cp cpu.pprof ./cmd/server/default.pgo
# 3. Build — Go applies PGO automatically when default.pgo is present
go build ./cmd/server      # "profile-guided optimization" in build output
```

- Go's PGO primarily drives **more aggressive, profile-informed inlining** (and devirtualization of hot interface calls): functions that are hot in production get inlined past the default budget, hot interface call sites get speculatively devirtualized.
- Reported gains are typically **2–7%** CPU on real services — modest per build, but it compounds across a large fleet and costs almost nothing once the profile-collection pipeline exists.
- **Java's** equivalent is the JIT's own runtime profiling (the JIT already profiles and recompiles hot methods continuously — PGO is, in a sense, the JVM's native mode), plus ahead-of-time toolchains: **AutoFDO** (Google's pipeline that turns `perf` LBR profiles into compiler feedback for AOT/JIT) and **BOLT** (a *post-link binary optimizer* that re-lays-out an already-compiled binary's code using a production profile, improving I-cache and iTLB behavior — gains of 5–15% on large C/C++/Go binaries are common, on top of PGO). The same lineage — AutoFDO, **Propeller**, BOLT — is what Google and Meta run on their largest binaries.

The pipeline discipline that separates a working PGO setup from a footgun:

- **Refresh the profile** — a stale profile optimizes for last quarter's workload. Re-collect periodically (the continuous-profiling store makes this a query) and treat the profile as a versioned, refreshed build input.
- **Representative, merged profiles** — use a profile that reflects the *aggregate* production workload (merge profiles across hosts/time with `go tool pprof -proto a.pprof b.pprof > merged.pgo`), not one host's idiosyncratic minute.
- **Keep it deterministic** — the same source + the same `default.pgo` must produce the same binary, or you've broken reproducible builds. Pin and version the `.pgo` like any other input.
- **Verify the win** — PGO is a hypothesis; confirm it with a release diff (previous section) showing the hot paths actually got cheaper. A PGO build that doesn't move the profile isn't helping.

> **Key insight:** PGO is the second monetization of your production profiles — feed the *real* fleet profile (never a benchmark) back to the compiler and it optimizes for the workload that exists. Go PGO (`default.pgo`, ~2–7% from profile-informed inlining/devirtualization), AutoFDO/BOLT for AOT binaries (5–15% from code layout) are downstream consumers of the same pipeline that does your continuous profiling. Refresh the profile, merge for representativeness, and verify the win with a diff.

---

## Capturing a Profile During a Live Incident

Continuous profiling gives you the *past*. Sometimes you need the *present*: a service is on fire right now, CPU is pegged, and you need a profile of *this* process in *this* state — without restarting it (which would destroy the state you're trying to capture) and without taking it out of rotation. The professional skill is pulling that profile safely, live, in seconds.

The foundational property is that **on-demand profiling is built into the runtime and is cheap and safe to trigger**. It is not a special build, not a restart, not a debugger attach that pauses the world.

**Go** exposes `net/http/pprof` — register it (often on a separate admin port) and a profile is one HTTP request away:

```go
import _ "net/http/pprof"   // registers handlers on the default mux
// expose on an internal-only admin port, never the public listener
go func() { log.Println(http.ListenAndServe("localhost:6060", nil)) }()
```

```bash
# During the incident — 30s on-CPU profile of the live process, no restart:
curl 'http://incident-host:6060/debug/pprof/profile?seconds=30' -o incident.pprof
go tool pprof -http=:8080 incident.pprof          # read it immediately

# If it's NOT CPU-bound (flat profile), the senior off-CPU lenses, live:
curl 'http://incident-host:6060/debug/pprof/trace?seconds=5'  -o trace.out   # scheduler/blocking
curl 'http://incident-host:6060/debug/pprof/{goroutine,mutex,block}'         # contention/leaks
```

The CPU profile is the SIGPROF sampler running for the requested window at ~100 Hz — overhead in the low single digits *for those 30 seconds only*, which is trivial even on a struggling host. There's no global pause; the process keeps serving traffic while it's profiled.

**Java** has the equivalent in two forms. **async-profiler** attaches to a running JVM by PID and profiles live, with no restart and no safepoint bias (the senior reason it's the right tool):

```bash
# Attach to the live JVM, 30s on-CPU flame graph, no restart:
asprof -d 30 -e cpu -f /tmp/incident.html <pid>
# CPU pegged but the on-CPU profile is flat? wall-clock to see blocking:
asprof -d 30 -e wall -f /tmp/incident-wall.html <pid>
```

**JDK Flight Recorder (JFR)** — built into the JVM, designed for *always-acceptable* overhead (~1%), startable on a live process:

```bash
# Start a recording on a running JVM without restart; dump it mid-incident:
jcmd <pid> JFR.start name=incident settings=profile duration=60s
jcmd <pid> JFR.dump  name=incident filename=/tmp/incident.jfr
# analyze in JDK Mission Control or convert to a flame graph
```

At the OS level, **`perf`** profiles any process by PID with no cooperation from the target at all — the universal fallback when the runtime endpoint isn't exposed or the process is a black box:

```bash
perf record -F 99 -g -p <pid> -- sleep 30 && perf report   # any process, no SDK
```

The incident discipline:

- **Expose the endpoint *before* the incident.** `net/http/pprof` on an admin port, JFR available, async-profiler on the host — wired up in advance. Discovering during an outage that pprof isn't exposed is the failure mode; bake it into the base image.
- **Lock it down.** `/debug/pprof` leaks internals and is itself a (small) CPU cost on demand — bind it to localhost/an admin port/mesh-only, never the public listener. (See [Diagnostics → Diagnostic Endpoints](../../../../diagnostics/diagnostic-endpoints/).)
- **Profile *one* representative instance**, not the whole fleet, during the incident — you need a diagnosis, not a fleet-wide overhead spike on already-hot hosts.
- **Capture before you mitigate.** Restarting "fixes" it and destroys the evidence. Grab the profile (and a goroutine/thread dump) *first*, then mitigate — the profile is what prevents a recurrence.

> **Key insight:** the most valuable incident profile is the one of the burning process *as it burns* — captured live, no restart, in seconds, because the runtime ships the capability (`/debug/pprof`, `JFR.start`, async-profiler attach, `perf -p`). The work is *preparation*: expose the endpoint on a locked-down admin port ahead of time, and "profile the incident" is one `curl`. Capture before you mitigate — a restart cures the symptom and deletes the cause.

---

## The Org Workflow — Who Owns the Profiler

The technology is the easy half. The hard half is organizational: someone has to own the profiling infrastructure, and there has to be a *workflow* that routes a detected regression to the team that can fix it. A profiler nobody owns rots; a regression nobody is paged for is ignored.

The ownership pattern that works splits responsibilities cleanly:

- **A platform / observability team owns the *infrastructure*** — the agents, the storage backend, retention, the query layer, the cost-attribution reports. They run it like any other tier-1 service: SLOs on ingestion, on-call when it breaks, capacity planning for the profile store. They do *not* fix application regressions — they provide the sensor and the leaderboards.
- **Application teams own *their services' CPU*** — they're the consumers. The platform team's per-team cost report and per-service "top consumers" leaderboard create the incentive; the application teams act on it. Crucially, the cost report is what makes this self-sustaining: a team that can see it spends $400K/year on CPU has a reason to look.

The regression-routing workflow, end to end:

1. **Detect** — automated diff (per-deploy canary, or a scheduled fleet diff) flags a function whose CPU share grew beyond threshold, or the weekly cost report shows a service jumped.
2. **Attribute** — the `version` label localizes it to a deploy; the service/owner mapping localizes it to a team. Because the diff names the *function* and often the *line*, the regression arrives pre-triaged.
3. **Route** — file/alert to the *owning team* automatically (the service catalog already maps service → team), with the differential flame graph attached. The signal goes to whoever can fix it, not to a central queue.
4. **Fix and verify** — the team profiles, fixes, ships; the *next* diff confirms the hot path got cheaper (or the alert reopens). The loop closes on data, not assertion.

The cultural piece that makes it stick: **make the cost visible and the regression routed, so the incentive and the information land on the same team.** A "top CPU consumers" dashboard that every team can see, plus automated routing of regressions to owners, converts profiling from "the perf team's hobby" into a standing practice each team participates in because it's measured on it. The anti-pattern is a central performance team that hoards the profiler and files tickets at other teams — it doesn't scale and it breeds resentment. The profiler is a shared sensor; ownership of *the cycles* is federated.

> **The professional reality:** a continuous profiler without an owner and a routing workflow is shelfware. Platform owns the *sensor* (agents, storage, cost reports, SLOs); application teams own *their cycles* (driven by a visible cost leaderboard). A regression is auto-detected by diff, auto-attributed by `version` and service→team mapping, and auto-routed to the owning team with the flame graph attached — so the information and the incentive land together. Make CPU cost visible per team, and optimization becomes self-sustaining.

---

## Decision Frameworks

**eBPF agent or per-language SDK for continuous profiling? Ask:**
- Do I need fleet-wide coverage *now*, with zero app-team buy-in and no recompile? → eBPF agent (Parca/Pyroscope eBPF). It profiles everything, including third-party processes.
- Do I need to slice by *endpoint / tenant / trace*? → SDK with labels (Pyroscope/Datadog/Grafana), at least in the services where that slicing pays for the integration.
- Both, ideally → eBPF for baseline fleet coverage + SDK labels where dimensional slicing earns its keep. (The mature default.)

**Is my overhead budget safe for always-on? Verify:**
- Frequency 19–99 Hz (not 999+), unwinding via frame pointers / LBR / eBPF (not DWARF), in-kernel aggregation on. → measure with `perf stat`; demand < 1–2%. DWARF or high frequency disqualifies it for production.

**Should I adopt PGO? Ask:**
- Do I have a *production* profile pipeline (not just benchmarks)? → yes is the prerequisite; PGO on a synthetic profile optimizes for fiction.
- Is this a long-running, CPU-sensitive service where 2–7% compounds? → worth it. Drop `default.pgo`, refresh it periodically, verify with a diff.
- Large AOT binary, I-cache/iTLB bound? → add BOLT/AutoFDO on top of PGO (5–15% from layout).

**A service's CPU regressed — what do I do? In order:**
- Diff the profile between the two `version` labels, normalized per-request → read the red tower → it names the function/line.
- Route to the owning team (service→team map) with the flame graph attached.
- Verify the fix with the *next* diff.

**Incident, CPU pegged, need a profile now? Ask:**
- Is the endpoint exposed? (It should already be.) → `curl /debug/pprof/profile` (Go), `asprof`/`JFR.start` (Java), `perf -p` (anything).
- On-CPU profile flat but CPU high? → it's off-CPU; pull `trace`/`wall`/`mutex` (the senior lenses), live.
- Capture *before* you mitigate — the restart deletes the evidence.

---

## Common Mistakes

1. **Profiling a synthetic benchmark and calling it the production workload.** The expensive bugs (pathological inputs, real data distributions, co-tenant pressure) only appear in production. Run continuous profiling on the real fleet; the benchmark will never have production's data.
2. **Blowing the overhead budget with DWARF unwinding or high frequency, then disabling "always-on" because it's expensive.** The budget is won at the unwinder: frame pointers/LBR/eBPF + 19–99 Hz + in-kernel aggregation keeps it sub-2%. Measure with `perf stat` before declaring it too costly.
3. **Producing flame graphs but never dollars.** A profiling program justified by "we can see flame graphs" gets cut. The same data, costed as $/core per service and per team, identifies six-figure wins and funds itself. Ship the cost-attribution report.
4. **Diffing without normalizing per unit of work.** Comparing a busy window to a quiet one lights up every function — that's load, not regression. Normalize to per-request / sample-share so genuine growth cancels and only relative changes survive.
5. **Unbounded label cardinality.** Tagging by raw path (`/users/8675309`) instead of route pattern (`/users/{id}`) explodes the profile store the way unbounded Prometheus labels do. Keep `endpoint`/`tenant` bounded.
6. **Feeding PGO a stale or unrepresentative profile.** PGO optimizes for the distribution it's shown; a stale profile pessimizes the *current* workload (one team caught exactly this). Refresh from the continuous store, merge across hosts for representativeness, verify the win with a diff.
7. **Discovering during an incident that `/debug/pprof` isn't exposed.** The capability is free but must be wired up *in advance*, on a locked-down admin port. Bake it into the base image; an outage is the wrong time to learn it's missing.
8. **Restarting the burning process before profiling it.** The restart "fixes" it and deletes the evidence, guaranteeing a recurrence. Capture the live profile (and a thread/goroutine dump) *first*, then mitigate.
9. **No owner, no routing.** A profiler nobody owns rots; a regression nobody is paged for is ignored. Platform owns the sensor; regressions auto-route to the owning team with the flame graph attached.

---

## Apply it

1. Define the user or business outcome that **CPU Profiling** should improve.
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

- Which measurable outcome justifies investing in CPU Profiling?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
- What is continuous profiling, and why run a profiler in production all the time instead of only during investigations?
- How do you set and verify an overhead budget for always-on production profiling?
- During a live latency-spike incident, how does profiling fit into your response, and in what order?
- How do you distinguish profiling from benchmarking, and when do you use each?
- How would you attribute fleet-wide CPU cost to specific teams or functions, and turn it into a dollar figure?
- Who should own continuous profiling infrastructure versus who owns fixing a detected regression?
- How do you decide whether a service should adopt profile-guided optimization?
