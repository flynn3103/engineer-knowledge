# Compile-Time vs Runtime Trade-offs — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Compile-Time vs Runtime Trade-offs** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## The Two Camps

**Compile-time / build-time:** macros (Rust, Lisp), code generation (protoc, Dagger,
go generate), annotation processors (APT), C++ templates/`constexpr`/`consteval`, Rust
`derive`, static reflection. The metaprogram runs *before* the program; its output is
ordinary, optimizable, statically-checkable code.

**Runtime:** reflection, metaclasses, dynamic proxies, `eval`, monkeypatching. The
metaprogram runs *while the program runs*; it adapts to information available only then.

The same outcome is often reachable from either camp — serde (`derive`, compile-time)
vs Jackson (reflection, runtime); Dagger (compile-time DI) vs Spring (runtime DI). That
equivalence of *outcome* with divergence of *cost* is exactly why the choice matters.

---

## The Trade-off Dimensions, Head to Head

| Dimension | Compile-time | Runtime |
|---|---|---|
| **Performance** | Zero runtime cost; fully inlinable/optimizable | Per-operation overhead; defeats JIT inlining |
| **Startup time** | Fast — no scanning at boot | Pays a boot tax (reflective scanning, proxy setup) |
| **Artifact size** | Can bloat (monomorphization, generated stubs) | Reflection metadata has size too; usually smaller code |
| **Type safety / error timing** | Errors at build (fail fast); static guarantees | Errors in production ("method not found"); no static check |
| **Flexibility / dynamism** | Fixed once built (closed-world) | Adapts to data unknown until runtime (plugins, hot reload) |
| **Observability / debugging** | Generated code is real source you can step | Harder to trace, but can inspect live state |
| **Tooling** | Autocomplete/refactor on generated code | Defeats static analysis, grep, refactoring |
| **Build vs deploy complexity** | Cost pushed into the build (slow builds, generators) | Simple builds; cost shipped to runtime |
| **AOT / native-image** | Friendly (closed-world) | Needs config or breaks (GraalVM, .NET trimming, tree-shaking) |

The table is the topic. A senior reads a requirement and predicts which row dominates:
a tight inner loop → performance row → compile-time; a plugin host loading unknown
third-party code → flexibility row → runtime; a serverless function → startup + AOT rows
→ compile-time.

---

## The Modern Shift Toward Compile Time

For two decades the mainstream (especially the JVM) leaned runtime: Spring, Hibernate,
and Jackson all reflect and scan at boot, trading startup for flexibility and developer
convenience. Three forces reversed the current:

1. **Serverless cold-start.** A function that runs for 200ms can't afford a 4-second
   reflective Spring boot. Quarkus and Micronaut do the DI/ORM wiring at *build* time so
   the app starts in milliseconds.
2. **AOT / native image.** GraalVM native-image and .NET NativeAOT assume a closed world;
   runtime reflection must be exhaustively configured or it breaks. Compile-time
   techniques are AOT-native. This pushed Spring itself (Spring Boot 3 AOT) toward
   build-time processing.
3. **Observability & fail-fast.** Compile-time errors and readable generated code beat
   "NoSuchMethodError in production." serde-over-Jackson and Dagger-over-Guice trade
   authoring convenience for build-time guarantees.

The current isn't absolute — runtime metaprogramming still wins where genuine dynamism
is required — but the default for new, performance- and startup-sensitive systems has
visibly moved to compile time.

---

## Code Examples

The same serializer, two camps:

```rust
// Compile-time (Rust serde): the impl is generated at build; zero reflection at runtime.
#[derive(Serialize, Deserialize)]
struct User { name: String, age: u32 }
```

```java
// Runtime (Jackson): reflects over fields at runtime; flexible, but pays per-call and
// needs reflection config for GraalVM native-image.
String json = new ObjectMapper().writeValueAsString(user);
```

DI, two camps:

```text
Spring  (runtime DI):  scans annotations + builds the graph at startup → boot tax, flexible.
Dagger  (compile DI):  generates the graph at build → instant startup, AOT-friendly, fail-fast.
```

---

## Best Practices

- **Choose by the dominant dimension.** Identify whether performance, startup, AOT,
  flexibility, or tooling dominates the requirement, and let that pick the camp.
- **Default to compile-time for startup/perf/AOT-sensitive systems** (serverless, CLIs,
  native images); reserve runtime for genuine dynamism.
- **Prefer compile-time techniques whose output is readable** (codegen, derive) so you
  keep debuggability and tooling.
- **Don't pay runtime reflection costs for variation known at build time.**
- **If you need AOT, audit runtime reflection early** — it's the thing that breaks.

---

## Edge Cases & Pitfalls

- **Closed-world breakage:** AOT-compiling a reflection-heavy app without configuring every
  reflective access → runtime `ClassNotFound`/`NoSuchMethod` in the native image.
- **Compile-time bloat:** aggressive monomorphization/codegen can balloon binary size and
  build time — the opposite cost.
- **False equivalence:** assuming compile-time and runtime versions behave identically;
  they can differ on dynamic edge cases (runtime can see data the build couldn't).
- **Over-staging:** pushing everything to compile time sacrifices flexibility the system
  actually needed (e.g. plugins), forcing rebuilds for what should be configuration.

---

## Apply it

1. State the system invariant that **Compile-Time vs Runtime Trade-offs** must protect.
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

- Which invariant must remain true when Compile-Time vs Runtime Trade-offs fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
