# Compile-Time vs Runtime Trade-offs — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Compile-Time vs Runtime Trade-offs** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## The Decision in Production Terms

Translate the trade-off dimensions into operational questions:

- **What is the request lifetime vs the boot time?** A long-lived server amortizes a slow
  reflective boot; a serverless function billed per-100ms cannot. Short-lived → compile-time.
- **Do you need a native image / AOT?** If yes, runtime reflection is a liability that needs
  exhaustive configuration; compile-time is native. This is increasingly a hard requirement,
  not a preference.
- **How dynamic is the workload, really?** Genuine plugin systems, hot-reload, user-defined
  schemas need runtime. "We might add a type someday" usually does not — that's build-time
  variation in disguise.
- **Where can you afford the cost — build or runtime?** Compile-time moves cost into CI
  (slower builds, generator maintenance) and out of production; runtime keeps CI simple and
  taxes every execution.
- **What's the on-call story?** Fail-fast (build-time) errors are cheaper to operate than
  runtime reflective failures discovered in production.

The professional answer is rarely "always X." It's "for this service, with these SLOs and
this deployment target, the dominant cost is Y, so the meta-level goes here."

---

## Cold Start & Native Image: The Forcing Functions

The two forces that reshaped the default:

- **Cold start.** Reflective DI/ORM frameworks scan the classpath and build object graphs
  at boot — seconds on a large app. For serverless and autoscaling, that boot tax is paid on
  every cold instance and directly hits tail latency and cost. Quarkus and Micronaut answer
  by doing the wiring at build time; Spring Boot 3 added AOT processing for the same reason.
- **Native image (closed-world AOT).** GraalVM native-image and .NET NativeAOT compile a
  closed world; anything reached only via runtime reflection must be declared in
  configuration (`reflect-config.json`, trimming descriptors) or it's absent at runtime.
  Heavy reflection makes native images painful or impossible without large config or a move
  to compile-time generation. This single constraint has pushed entire ecosystems toward
  build-time metaprogramming.

If your deployment target is serverless or native image, the compile-time/runtime choice is
largely made *for* you.

---

## Build Economics

Compile-time isn't free — it relocates cost:

- **Slower builds.** Code generation, annotation processing, and macro expansion add to
  compile time; large monomorphized generic/template code compiles slowly and bloats
  binaries. Incremental builds and caching (Gradle build cache, sccache, Bazel) matter.
- **Generator maintenance & version skew.** A schema-driven generator is another dependency
  to version and keep in lockstep with consumers; stale generated code is a real hazard.
- **Determinism/hermeticity.** Generation should be reproducible (same inputs → same output)
  so builds are cacheable and reviewable; nondeterministic generators wreck caching.

The trade is usually worth it for startup/AOT-sensitive systems, but "push it to build time"
has a CI bill you must plan for.

---

## Migrating Runtime Magic to Compile Time

The common modern project. The playbook:

1. **Find the reflective hot/critical paths** (serialization, DI, ORM mapping) and the AOT
   blockers (reflective access that breaks native-image).
2. **Replace with a compile-time equivalent** — derive macros / codegen for serialization
   (serde, generated mappers), compile-time DI (Dagger, Micronaut), annotation processors —
   keeping behavior identical under a strong test suite.
3. **Measure** startup, p99, and native-image build success before/after.
4. **Keep readable output** so you don't trade reflection's opacity for codegen's opacity.

The recurring result: more lines of code, but faster startup, AOT-compatibility, fail-fast
errors, and code the whole team can navigate.

---

## Best Practices

- **Pick the camp by deployment target and SLO**, not by familiarity.
- **For serverless/CLI/native image, default compile-time**; audit and minimize runtime
  reflection early.
- **Budget the build cost** of compile-time techniques (build cache, incremental, hermetic
  generation).
- **Reserve runtime metaprogramming for genuine dynamism** (plugins, dynamic schemas,
  hot reload).
- **Prefer readable generated output** and treat generators as versioned dependencies.
- **Test behavior parity** when migrating camps; the dynamic edge cases differ.

---

## Edge Cases & Pitfalls

- **AOT surprise in production:** an app that ran fine on the JVM fails as a native image
  because a reflective path wasn't configured — discovered late if native-image builds aren't
  in CI.
- **Cold-start regression from a new annotation:** adding a reflective/scanning library
  silently inflates boot time and tail latency.
- **Build-time blowup:** unbounded monomorphization/codegen explodes binary size and compile
  time — compile-time's own failure mode.
- **Stale generated code:** forgetting to regenerate after a schema change ships
  inconsistent behavior; enforce a generate-and-verify CI check.
- **Over-staging:** compiling away flexibility a plugin system actually needed, forcing
  redeploys for what should be runtime configuration.

---

## Apply it

1. Define the user or business outcome that **Compile-Time vs Runtime Trade-offs** should improve.
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

- Which measurable outcome justifies investing in Compile-Time vs Runtime Trade-offs?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
