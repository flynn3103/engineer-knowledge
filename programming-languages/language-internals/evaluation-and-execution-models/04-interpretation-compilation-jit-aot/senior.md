# Interpretation, Compilation, JIT, AOT — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Interpretation, Compilation, JIT, AOT** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Deoptimization: the mechanism that makes speculation legal

A JIT's aggressive speedups (assume-int, assume-monomorphic, assume-this-branch) are *bets on the past*. Bets can be wrong. **Deoptimization** is the safety net that lets the JIT make those bets without risking correctness.

The mechanism:

1. When the JIT compiles a method under an assumption, it inserts a **guard** that checks the assumption and, at every guard, records **deopt metadata**: a precise map from the compiled code's state (which value lives in which register or stack slot) back to the *interpreter's* notion of state (which local variable, what bytecode index).
2. The compiled code runs at full speed as long as guards pass.
3. When a guard fails — a float arrives where only ints were seen, a never-taken branch finally fires, a new subclass is loaded that breaks a devirtualization — the code jumps to the **uncommon trap**.
4. The runtime uses the deopt metadata to **reconstruct an interpreter frame** from the compiled-code state, discards (or marks not-entrant) the now-invalid compiled code, and **resumes execution in the interpreter** at the exact equivalent point. The program continues correctly; only speed is lost.

The conceptual payoff: **deopt converts "this might not always be true" into "this is true until proven otherwise, and we can recover instantly when disproven."** That's what licenses a JIT to inline a virtual call to a single target, or to compile an arithmetic loop as if everything is an `int`. Without deopt, none of the speculation would be sound — you'd be limited to optimizations provable for *all* inputs, which is roughly what AOT is stuck with.

Deopt is *expensive* when it happens (rebuild frame, fall back to interpreting, possibly recompile later), so the JIT only speculates where the profile says the bet is very likely to hold. Repeated deopt at the same site ("deopt loop") is a real performance bug: the JIT compiles, a guard fails, it deopts, recompiles, fails again — thrashing. Mature runtimes detect this and recompile *without* that particular speculation.

### 2. Method JITs vs meta-tracing JITs

Two architectures, two philosophies.

**Method JITs (HotSpot, V8, RyuJIT, most mainstream)** take a whole method as the compilation unit. Hotness is per-method (and per-loop via OSR). Inlining is how they cross method boundaries: the optimizer pulls callees' bodies into the caller and optimizes the merged code. This is well-understood, maps cleanly onto profiles per method, and is the default everywhere.

**Meta-tracing JITs (PyPy, LuaJIT)** take a radically different unit: the **trace** — the actual linear sequence of operations executed on *one path* through a hot loop, *following calls across method boundaries naturally.* When a loop gets hot, the runtime switches to "tracing mode," records every operation actually executed for one iteration (including into and out of called functions), and compiles that straight-line trace, with guards at every point where control could have diverged. Subsequent iterations run the trace; if a guard fails (the path diverged), control falls back and possibly a new trace is recorded for the other path.

Why meta-tracing? For dynamic languages it's spectacularly effective: the trace is *already specialized* to the observed types and the taken path, inlining happens "for free" by following the calls, and the compiler only ever sees straight-line code (easy to optimize). PyPy is "meta" because the tracer traces the *interpreter* executing the program, not the program directly — write an interpreter, get a tracing JIT for that language almost for free. LuaJIT's tracing JIT is one of the fastest dynamic-language implementations ever built.

The failure mode is **trace explosion**: code with many branches (or many type combinations) generates many divergent traces, exploding code size and compile time, and side exits (guard failures) become frequent enough to erase the benefit. Method JITs degrade more gracefully on branchy code; tracing JITs shine on loop-dominated, type-stable code and struggle on irregular control flow. This trade-off is *the* reason mainstream general-purpose runtimes chose method JITs while specialized dynamic-language implementations chose tracing.

### 3. AOT for managed languages, and the closed-world assumption

For C/C++/Rust/Go, AOT is the native state — the compiler sees all the code (modulo dynamic linking) and there's no JIT. The interesting senior topic is AOT for languages *built around* a JIT: Java and C#.

**The motivation** is concrete and economic: JIT warmup + the JIT's memory footprint are intolerable for short-lived or scale-to-zero workloads. A serverless function that cold-starts on every burst pays warmup on every burst; a CLI never warms up at all; a containerized microservice scaled to dozens of replicas wants each replica to boot in tens of milliseconds with a small RSS, not seconds with hundreds of MB. **AOT delivers fast startup, low memory, and no warmup** — exactly the three things a JIT is worst at.

**The cost** is the **closed-world assumption.** A native-image AOT compiler does whole-program **reachability analysis**: starting from the entry points, it computes the transitive set of reachable methods and types, and *removes everything else* (this is also why native images are small). For this to be correct, *all reachable code must be visible at build time.* That premise collides with the "open-world" features that make managed languages dynamic:

- **Reflection** — `Class.forName("com.x.Y")`, looking up a method by string name at runtime. The AOT compiler can't see that `Y` is used, so it gets dropped. Fix: declare it in a reflection config so the compiler keeps it.
- **Dynamic class loading** — loading bytecode at runtime (plugins, JSP, agents). Fundamentally incompatible with closed-world; generally not supported.
- **Runtime code generation / dynamic proxies** — frameworks that synthesize classes on the fly (many ORMs, mocking libraries, dependency-injection containers historically) must be reworked to generate that code at *build* time instead.
- **Serialization that reflects over arbitrary types** — must be told, at build time, which types to support.

So AOT for managed languages is a **trade of dynamism for startup/memory.** GraalVM native-image addresses it with build-time configuration (reflection/resource/proxy config, often auto-generated by a tracing agent run during testing) and build-time initialization (run static initializers at build time, bake the heap into the image). .NET NativeAOT makes similar demands; the framework and popular libraries have been steadily reworked to be "AOT-friendly" (source generators replacing runtime reflection — e.g. `System.Text.Json`'s source-generated serializers). **The second thing you give up is the JIT's runtime adaptive specialization** — an AOT'd managed program can't respecialize on observed types or devirtualize based on what actually loaded, so its *peak* throughput on long runs can trail a warmed-up JIT.

### 4. ReadyToRun / CrossGen: the hybrid middle

.NET offers a pragmatic in-between: **ReadyToRun (R2R)** images (produced by **CrossGen**) precompile IL to native code *at publish time*, but **keep the JIT in the process.** Startup improves because the common paths are already native — no JIT needed to begin running. But the JIT remains available to (re)optimize hot code with profiles (tiered compilation can promote R2R code to fully optimized Tier-1), and dynamic features still work because the runtime is intact. **R2R trades some of native-AOT's footprint/startup wins for keeping full dynamism and the option of peak JIT optimization.** It's the "fast startup without giving up the JIT" choice, distinct from NativeAOT's "no JIT at all." This three-way menu — full JIT, R2R hybrid, NativeAOT — is the clearest illustration that the execution model is a *spectrum you tune*, not a binary you pick.

### 5. PGO: giving AOT a taste of the profile advantage

The JIT's structural edge is *profiles*. AOT can borrow that edge **offline** with **Profile-Guided Optimization**: build an instrumented binary, run it on representative inputs to collect a profile (branch frequencies, hot functions, call targets), then build a *second* binary using that profile to guide inlining decisions, block layout, and devirtualization. C/C++/Rust/Go all support PGO; GraalVM native-image and .NET support PGO flavors too.

The key distinctions from a JIT:

- PGO's profile is from a *training* run, not the *current* run. If production behavior differs from training, the bets can be wrong — and unlike a JIT, **there's no deopt to recover**; the misprediction just costs you. So PGO profiles must be representative.
- PGO is *static*: it picks one layout for the whole program's lifetime. A JIT can *respecialize* when behavior shifts. PGO can't adapt to phase changes within a run.
- PGO still can't do what closed-world AOT forbids (runtime devirtualization on classes loaded later, etc.), but it captures most of the *common-case layout* benefit.

PGO is the senior's lever for narrowing the AOT-vs-JIT peak gap on workloads with stable, representative behavior — at the cost of a more complex build and the risk of a stale or unrepresentative profile.

### 6. Startup vs peak, framed as an engineering decision

The slogans ("Java is slow to warm, fast at peak"; "use AOT for CLIs") become a decision procedure:

```text
Estimate the workload's lifetime and start frequency, then integrate
throughput-over-time:

  • If process lifetime ≪ warmup time (CLI, scale-to-zero serverless),
    the JIT never reaches peak — AOT (native-image / NativeAOT) wins on
    every axis that matters: startup, memory, predictability.

  • If process lifetime ≫ warmup time (long-lived server, hours/days),
    warmup is amortized; the JIT's peak + adaptivity usually win,
    AND you keep full dynamism. R2R is a fine compromise to cut the
    first-request latency without losing the JIT.

  • If start frequency is high AND lifetime is moderate (autoscaling
    microservices, frequent redeploys), repeated re-warming is a real
    tax — measure it; AOT or R2R often wins on aggregate even though a
    warmed JIT would win a single steady-state benchmark.
```

This is why serverless *resurrected* AOT for managed languages: the economics of cold start inverted the decades-old "JIT is just better for servers" assumption. The senior skill is computing the area under the throughput curve for *your* lifetime distribution, not quoting a steady-state microbenchmark.

---

## Code Examples

### Forcing — and observing — a deoptimization in the JVM

```java
public class Deopt {
    // The JIT will speculate this is always called with the same concrete type.
    static int describe(Object o) {
        return o.hashCode();           // virtual call: candidate for devirtualization
    }

    public static void main(String[] args) {
        Object intArg = Integer.valueOf(7);
        // Phase 1: hammer with ONE type -> JIT devirtualizes/inlines for Integer.
        for (int i = 0; i < 1_000_000; i++) describe(intArg);

        // Phase 2: introduce a NEW type -> the speculation's guard fails -> DEOPT.
        Object strArg = "now a String";
        for (int i = 0; i < 1_000_000; i++) describe(strArg);
    }
}
```

Run with:

```bash
java -XX:+PrintCompilation -XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining Deopt
```

In phase 1, `describe` compiles and inlines `Integer.hashCode`. When phase 2 introduces `String`, the inline-cache guard fails and you'll see a `made not entrant` / uncommon-trap deopt, followed by recompilation as a more general (megamorphic) version. This is the bet → guard → deopt → recompile cycle, observable.

### Provoking a deopt loop (the anti-pattern)

```java
// Alternating types at the SAME hot call site -> repeated deopt thrash.
static final Object[] inputs = { 1, "two", 3.0, 1, "two", 3.0 };
static int hot(Object o) { return o.hashCode(); }

public static void main(String[] a) {
    for (int i = 0; i < 100_000_000; i++) hot(inputs[i % inputs.length]);
}
```

The call site is *megamorphic and unstable*: the JIT can't find a stable bet, may deopt repeatedly before giving up and emitting general (slow) dispatch. The lesson: keep hot call sites type-stable; instability poisons speculation.

### GraalVM native-image hitting the closed-world wall

```java
public class Reflect {
    public static void main(String[] args) throws Exception {
        // Class named by a runtime string -> invisible to reachability analysis.
        Class<?> c = Class.forName(args[0]);
        Object o = c.getDeclaredConstructor().newInstance();
        System.out.println(o);
    }
}
```

```bash
native-image Reflect
./reflect com.example.Thing
# -> ClassNotFoundException: the class was pruned, the AOT compiler never saw it used.
```

The fix is a `reflect-config.json` (or `@RegisterForReflection`, or running the tracing agent during tests to auto-generate the config) telling native-image to retain `com.example.Thing`. This is the closed-world assumption made tangible: *if the compiler can't see it reachable, it isn't there.*

### Building a .NET app three ways (the spectrum, as build flags)

```bash
# 1) Pure JIT: classic, full dynamism, warmup on first calls.
dotnet build -c Release

# 2) ReadyToRun (CrossGen): precompile common paths, keep the JIT.
dotnet publish -c Release -p:PublishReadyToRun=true

# 3) NativeAOT: no JIT, closed-world, fast startup + small footprint.
dotnet publish -c Release -p:PublishAot=true
```

Measure startup and steady-state for each on *your* workload. You'll typically see NativeAOT start fastest with smallest RSS, R2R in between, pure-JIT slowest to start but able to reach the highest peak after warmup. That measured table — not a slogan — is how a senior picks.

### PGO for an AOT (C) build

```bash
# 1) instrument
gcc -O2 -fprofile-generate hot.c -o hot_instrumented
# 2) train on representative input
./hot_instrumented < representative_workload.txt
# 3) rebuild using the collected profile
gcc -O2 -fprofile-use hot.c -o hot_optimized
```

`hot_optimized` lays out blocks and makes inlining/devirtualization choices guided by *observed* frequencies — an AOT approximation of the JIT's profile advantage, fixed for the binary's lifetime, only as good as the training data's representativeness.

---

## Coding Patterns

### Pattern 1: Keep speculation profitable — stabilize hot call sites

Design hot paths so the JIT's bets hold: avoid feeding one hot call site many unrelated types; prefer monomorphic or low-polymorphism dispatch where it's hot. Unstable sites cause deopt thrash and force fallback to slow general code.

### Pattern 2: Make your code AOT-ready by declaring dynamism at build time

If you target native-image or NativeAOT, push reflection/serialization/proxy needs to build time: use source generators (`System.Text.Json` source-gen, Micronaut/Quarkus build-time DI) instead of runtime reflection, and capture reflection config via the tracing agent during your test suite.

```text
runtime reflection  ──replace──▶  build-time source generation / config
dynamic proxy at runtime  ──replace──▶  compile-time generated implementation
```

### Pattern 3: Choose the execution mode per deployment, not per language

The same .NET or Java codebase can ship as full-JIT, R2R, or native-AOT depending on *where it runs.* Pattern: parameterize the build/publish mode by deployment target (CLI/lambda → AOT; long-lived web tier → JIT or R2R) rather than committing the whole org to one mode.

### Pattern 4: Treat PGO profiles as artifacts with a freshness contract

If you use PGO, version the profile, capture it from representative production-like traffic, and refresh it when behavior shifts. A stale profile silently degrades — there's no deopt to save you. Automate profile collection in the pipeline.

---

## Best Practices

- **Diagnose deopts before chasing micro-optimizations.** A hot method that keeps deoptimizing wastes far more than any arithmetic you could shave. Use `-XX:+PrintCompilation`/`--trace-deopt` to find deopt loops and remove the instability causing them.
- **Pick the compilation philosophy to match the workload's control flow.** Loop-heavy + type-stable favors tracing; branchy + polymorphic favors method JITs. Don't force a numeric kernel through a branchy general path or vice versa.
- **Budget the dynamism you actually need before choosing AOT.** Inventory reflection, dynamic loading, and runtime codegen up front; if they're load-bearing and irremovable, closed-world AOT may cost more than it saves.
- **Measure the area under the curve, not a steady-state point.** Decide JIT vs AOT vs R2R by integrating throughput over your real lifetime-and-restart distribution.
- **Keep PGO profiles representative and fresh.** Validate that training inputs match production; stale or skewed profiles can make PGO a net negative.
- **Prefer build-time over runtime metaprogramming in modern stacks.** Source generators and build-time DI keep you on the AOT-friendly path *and* often improve startup even under a JIT.

---

## Edge Cases & Pitfalls

- **Deopt loops (compile→deopt→recompile→deopt).** An unstable speculation site thrashes, often *slower* than never compiling. Caused by megamorphic/unstable hot call sites or values that violate an assumption intermittently. Stabilize the site or accept the general path.
- **Trace explosion in meta-tracing JITs.** Highly branchy code under PyPy/LuaJIT spawns many traces and frequent side exits, ballooning compile time and code size and erasing the speedup — the classic reason tracing isn't universal.
- **Reflection silently pruned by AOT.** Under native-image/NativeAOT, code reachable only via reflection is removed unless configured, surfacing as `ClassNotFoundException`/missing-member errors *at runtime in production*, not at build. Capture config via the tracing agent over a thorough test suite.
- **Build-time static initialization surprises.** native-image may run static initializers at *build* time and bake the result into the image — so a static field capturing build-machine state (a timestamp, a hostname, a random seed) gets frozen incorrectly. Control initialization timing explicitly.
- **Stale PGO profiles.** A profile from old traffic mis-guides block layout/inlining for new traffic, with no runtime recovery. Worse than no PGO if behavior drifted.
- **Assuming AOT always beats JIT at peak.** On long-lived, type-diverse workloads, a warmed JIT's runtime devirtualization and respecialization can out-throughput a closed-world AOT binary that froze its decisions at build time. Peak winner is workload-dependent.
- **Mixing tiers/modes incorrectly in benchmarks.** Comparing a cold JIT against a native-AOT binary (or a warmed JIT against AOT's first run) yields a meaningless verdict. Compare like-for-like at the lifecycle stage that matches production.
- **R2R misread as full AOT.** ReadyToRun keeps the JIT and still needs the runtime; it does not give NativeAOT's footprint or its no-runtime guarantees. Confusing the two leads to wrong deployment expectations.

---

## Apply it

1. State the system invariant that **Interpretation, Compilation, JIT, AOT** must protect.
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

- Which invariant must remain true when Interpretation, Compilation, JIT, AOT fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
