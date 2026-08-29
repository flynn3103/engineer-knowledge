# JIT Compilation & Tiering — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **JIT Compilation & Tiering** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The code cache is a finite, shared resource

Everything the JIT compiles must be installed into the **code cache** — a fixed-size memory region reserved at startup. When it fills, the runtime cannot install new compiled methods. On HotSpot this historically meant **the JIT shuts off entirely** and prints `CodeCache is full. Compiler has been disabled.` — and any method not already compiled (or that gets flushed) runs in the **interpreter**, often halving or worse the throughput of an otherwise-warm service. This is a genuine production incident class: a deploy adds code paths, the working set of hot methods grows past the cache, compilation stops, latency doubles, and nothing in the application logs explains it.

Modern HotSpot mitigates this with a **segmented code cache** (separate regions for non-method stubs, profiled C1 code, and non-profiled C2 code) and a **sweeper** that evicts cold and superseded (`not entrant`) methods. But the cache is still finite. Applications with enormous code footprints — big frameworks, lots of generated code (proxies, lambdas, scripting), heavy reflection/megamorphic expansion — can outgrow the default `ReservedCodeCacheSize` and need it raised, *with monitoring*, not guessing.

The operational discipline: **monitor code-cache occupancy** as a first-class metric (JFR, `jcmd Compiler.codecache`, or the JMX `CodeCache` pool), alert before it saturates, and size it from observed peak working set, not folklore.

### 2. Warmup economics and the rise of AOT

Warmup is free amortized cost on a process that lives for weeks. It is the *dominant* cost on a process that lives for milliseconds. Quantify it:

- A JVM microservice may take **seconds** to reach peak throughput.
- A serverless function may run for **hundreds of milliseconds** and exit.

The function dies deep in warmup — interpreted or barely C1-compiled — having paid the JIT's overhead (compiler threads, profiling) and collected almost none of its reward. Worse, *every cold start* re-pays it. At scale (millions of invocations, frequent cold starts), this is real money and real p99 latency.

This economic mismatch is *why ahead-of-time compilation came roaring back* in managed-language ecosystems:

- **GraalVM Native Image** AOT-compiles a JVM application (with a closed-world assumption) to a native binary that starts in milliseconds with a flat, warmup-free profile — at the cost of lower peak throughput and loss of runtime dynamism (reflection/dynamic class loading must be configured).
- **.NET Native AOT / ReadyToRun (R2R)** pre-compiles IL to native to cut startup and warmup.
- **CRaC (Coordinated Restore at Checkpoint)** takes the other route: warm the JVM up *once*, snapshot the process, and restore from the snapshot — startup skips warmup because the code cache and profiles are restored.
- **Profile-guided AOT** (V8 compile caches, .NET dynamic PGO baked into AOT, Graal PGO) tries to capture *some* of the JIT's profile-driven wins without paying for runtime compilation.

The professional decision is therefore not "JIT or AOT is better" but "**what is this process's lifetime and dynamism profile, and which compilation model matches it?**" Long-lived, throughput-bound, dynamic → JIT. Short-lived, latency/startup-bound, closed-world → AOT.

### 3. Megamorphic sites as an operational cost

At senior level a megamorphic site was a missed optimization. In production it is a **latency and capacity** problem. A hot path that cannot inline because a key site went megamorphic runs at a fraction of its potential speed, consuming more CPU per request, which means more instances to hold the SLO, which means more cost. The insidious part: it is invisible in the source and in ordinary CPU profiles (the time is spread thinly across generic dispatch and missed inlining), and it often *appears* after an innocuous change — a new subclass added to a hierarchy, a framework upgrade that injects proxies, a "generalization" that made a method accept more types. Diagnosing it requires inlining/IC-level tooling (`-XX:+PrintInlining`, JFR's compiler events, V8 IC state), not just a flame graph.

### 4. Compiler threads compete with the application

The optimizing compiler runs on background threads, but those threads are not free — they consume CPU cores. On a busy multi-core box this is usually fine. On a constrained container (1–2 vCPUs), a burst of compilation right after startup steals cycles from request handling, *adding* latency exactly when the service is also slow from being cold. This is why aggressively low-core serverless and sidecar deployments feel disproportionately punished by JIT warmup: there is no spare core to hide the compilation in. Tuning the number of compiler threads (`-XX:CICompilerCount`) is a real lever in tight-core environments, but again, measure first.

### 5. The tuning levers (and when to touch them)

The honest default position is **don't tune** — the tiered defaults are excellent and most tuning regresses something. Reach for these only with a measurement showing the default hurts *your* workload:

- **`-XX:TieredStopAtLevel=1`** — interpreter + C1 only, no C2. Faster, cheaper startup; lower peak throughput. Rational for short-lived JVM CLIs/tools and some serverless where C2 would never pay off.
- **`-XX:-TieredCompilation`** — go straight to C2 (no C1 profiling tier). Slow start, high peak. Niche; rarely the right call since tiered usually dominates.
- **`-XX:ReservedCodeCacheSize`** — raise when monitoring shows cache pressure on a large-code-footprint app.
- **`-XX:CICompilerCount`** — adjust compiler thread count in core-constrained environments.
- **Compile thresholds** (`-XX:Tier3/Tier4InvocationThreshold`, `-XX:CompileThreshold`) — lower to compile sooner (helps medium-lived processes warm faster), raise to compile less (saves compilation cost for very short processes). High blast radius; change with care.
- **V8 `--max-opt` / `--no-opt` / `--jitless`** — cap or disable optimization. `--jitless` disables JIT entirely for security-sandboxed contexts (no W^X-violating writable+executable pages) at a large throughput cost; `--no-opt` aids debugging/repro.

The meta-rule: **a tuning flag is a hypothesis. Test it against your real workload, in your real container shape, and keep it only if a metric you care about improved.**

### 6. Deopt storms as incidents

A single deoptimization is healthy. A **deopt storm** — a hot method that optimizes, deopts, re-optimizes, deopts, repeatedly — burns CPU on recompilation and runs the hot path at slow-tier speed in between. Causes: genuinely unstable types/branches on a hot path, profile pollution from non-representative warmup, or a guard tied to a value that flips frequently. Symptoms: high compiler CPU, sawtooth throughput, `--trace-deopt` (V8) or JFR deopt events firing repeatedly on the same method. The fix is upstream — stabilize the data or accept the general path — not a flag. (Mechanics live in the deoptimization topic; here it is an operational signal you must recognize.)

---

## Code Examples

### Example 1 — Monitoring and provoking code-cache pressure (HotSpot)

```bash
# Inspect code cache live.
jcmd <pid> Compiler.codecache

# Run an app with a deliberately tiny cache to see the failure mode.
java -XX:ReservedCodeCacheSize=8m -XX:+PrintCodeCache -XX:+PrintCompilation BigApp
```

With a tiny cache, you will eventually see `CodeCache is full. Compiler has been disabled.` and a measurable throughput drop as hot methods stop being compiled. In production, expose the `CodeCache` JMX memory pool to your metrics system and alert at, say, 80% occupancy. The point of the experiment is to *recognize the cliff* before you meet it unplanned.

### Example 2 — Quantifying warmup cost

```java
public class WarmupCost {
    static long work(int n){ long s=0; for(int i=0;i<n;i++) s += (i*2654435761L)>>>11; return s; }
    public static void main(String[] a){
        for (int r=0; r<30; r++){
            long t=System.nanoTime(); long acc=0;
            for (int k=0;k<500;k++) acc += work(50_000);
            System.out.printf("round %2d: %5d us  (acc=%d)%n", r, (System.nanoTime()-t)/1000, acc);
        }
    }
}
```

```bash
java WarmupCost                          # watch first rounds vs steady state
java -XX:TieredStopAtLevel=1 WarmupCost  # faster start, higher steady-state floor
```

Record the round at which timings flatten — that is your warmup duration. Multiply by your cold-start frequency to estimate the warmup tax on the fleet. For a serverless function, this number directly informs whether to switch to Native Image.

### Example 3 — Choosing AOT for a short-lived process (GraalVM)

```bash
# JIT build: fast peak, slow start.
java -jar app.jar              # ~seconds to warm up, high throughput

# Native Image (AOT): instant start, no warmup, lower peak.
native-image -jar app.jar
./app                          # starts in ~milliseconds, flat profile
```

For a CLI tool or a serverless handler, the native binary's startup (milliseconds, no warmup) is decisive even though its peak throughput is lower — the process never runs long enough to reach the JIT's peak anyway. This is the warmup-economics decision made concrete: **match the compilation model to the lifetime.**

### Example 4 — Disabling optimization in V8 for predictability/security

```bash
node --no-opt app.js        # keep baseline tiers, skip optimizing JIT (debug/repro)
node --jitless app.js       # no JIT at all: no writable+executable pages (sandbox), big perf cost
```

`--jitless` is used where executable-page generation is a security risk (some sandboxes, certain embedded contexts). You trade a large amount of throughput for the absence of runtime-generated code. Knowing this lever exists — and its cost — is part of operating V8 in constrained or hardened environments.

### Example 5 — Detecting a megamorphic regression in CI

```java
// Pseudocode for a guardrail test:
// 1. Warm up the hot path.
// 2. Use JFR or -XX:+PrintInlining to assert the key call inlined.
// 3. Fail the build if the critical call did NOT inline (megamorphic regression).
```

Mature teams encode "this hot call must inline" as an automated check (parse JFR compiler events or `PrintInlining` output), so a future change that adds a fourth subtype to a hot hierarchy — silently making the site megamorphic — fails CI instead of surfacing as a mysterious latency regression in production. Treat inlining of critical paths as a testable invariant.

---

## Trade-offs

- **JIT vs AOT:** peak throughput + dynamism + portability (JIT) versus instant startup + no warmup + flat latency + smaller footprint (AOT). Decided by process lifetime and closed-world feasibility.
- **Bigger code cache vs memory:** larger cache avoids the exhaustion cliff but consumes RAM that could be heap. Size from measured working set.
- **More compiler threads vs application CPU:** faster warmup vs stealing cores from request handling on constrained boxes.
- **Lower compile thresholds vs wasted compilation:** earlier peak for medium-lived processes vs compiling code that short-lived processes never reuse.
- **Pre-warming vs deploy speed/cost:** warm-before-serve removes cold-start latency but adds time and synthetic load to every deploy/scale-out.
- **Checkpoint-restore (CRaC) vs operational complexity:** skips warmup entirely but adds snapshot lifecycle, security, and state-validity concerns.

> 🎓 Every trade-off reduces to the same governing question from junior level, now with a price tag: **will this process run long enough for the JIT's investment to pay off — and can I afford the warmup, the code cache, and the compiler CPU until it does?**

---

## Coding Patterns

**Pattern 1 — Pre-warm before serving traffic.** On startup, drive the hot paths with representative synthetic requests, *then* signal readiness to the load balancer. This converts user-visible cold-start latency into invisible startup time.

**Pattern 2 — Stagger restarts and scale-outs.** Never cold-restart the whole fleet at once under load. Roll instances so warm capacity always covers traffic while new instances warm up.

**Pattern 3 — Treat code-cache occupancy as a monitored SLI.** Export it, dashboard it, alert before saturation, and size `ReservedCodeCacheSize` from observed peak — especially for large-framework or codegen-heavy apps.

**Pattern 4 — Encode inlining-critical paths as tests.** Assert in CI that key hot calls still inline (no megamorphic regression), so performance-critical assumptions are guarded by the build, not by hope.

**Pattern 5 — Pick the compilation model per workload, explicitly.** Make "JIT vs AOT vs CRaC" a deliberate, documented decision keyed to the process's lifetime and dynamism, not a default you inherited.

---

## Best Practices

- **Default first, tune with evidence.** Run the tiered defaults until a metric proves they hurt *your* workload on *your* hardware shape. Keep before/after numbers for every flag you set.
- **Make warmup a first-class part of deploys.** Pre-warm, stagger, and never put the whole fleet cold at peak. Your deploy pipeline owns warmup.
- **Monitor the JIT, not just the app.** Code-cache occupancy, compiler CPU, deopt-event rate, and inlining of critical paths are operational signals. Most teams watch heap and GC but ignore these until an incident.
- **Right-size the compilation model.** Short-lived or cold-start-heavy? Seriously evaluate Native Image / CRaC. Don't brute-force a JIT into a workload it structurally mismatches.
- **Guard against megamorphic regressions.** Adding a subtype to a hot hierarchy, introducing proxies, or "generalizing" a hot method can silently destroy inlining. Review and, ideally, test for it.
- **Respect constrained containers.** On 1–2 vCPU boxes, account for compiler-thread CPU during warmup; consider `TieredStopAtLevel=1` or AOT rather than fighting the contention.

---

## Edge Cases & Pitfalls

**Pitfall 1 — Silent code-cache exhaustion.** The cache fills, the JIT disables, throughput halves, and nothing in the app log explains it. Without code-cache monitoring you will chase the wrong cause for hours. Monitor it. (Demonstrated in Example 1.)

**Pitfall 2 — Whole-fleet cold restart at peak.** A "safe" config rollout that restarts every instance simultaneously drops the entire fleet into warmup under full load — a self-inflicted brownout. Always roll.

**Pitfall 3 — Benchmarking on a beefy box, deploying on a tiny container.** Warmup and compiler-thread contention behave very differently on 32 cores versus 1.5 vCPUs. Performance-test on the *production* container shape, or your warmup estimates will be optimistic.

**Pitfall 4 — Serverless warmup tax ignored.** A function that looks fast in a warm benchmark may be dominated by cold-start interpreter time in production, with every cold invocation re-paying it. Measure cold-path latency explicitly; consider AOT/snapshot.

**Pitfall 5 — Tuning by blog post.** Copying `-XX` flags from an article tuned for a different workload commonly regresses throughput or causes new incidents (e.g., a too-small custom code-cache size). Treat every flag as an unproven hypothesis.

**Pitfall 6 — Profile pollution from health checks / warmup traffic.** Synthetic warmup with unrepresentative types/branches teaches the JIT the wrong thing; real traffic then triggers deopts. Warm up with traffic that resembles production.

**Pitfall 7 — Megamorphic regression from a "harmless" change.** A new implementation class, a mocking framework in a perf test, or a dependency upgrade injecting proxies can push a hot site megamorphic. CPU per request creeps up, you add instances to compensate, and cost rises with no obvious culprit. (Guard with Example 5's test.)

**Pitfall 8 — Forgetting AOT's constraints.** Native Image's closed-world assumption breaks naive reflection/dynamic loading; CRaC requires snapshot-safe state (no stale connections/secrets). Adopting AOT/CRaC without honoring their constraints trades a warmup problem for a correctness problem.

---

## Apply it

1. Define the user or business outcome that **JIT Compilation & Tiering** should improve.
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

- Which measurable outcome justifies investing in JIT Compilation & Tiering?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
