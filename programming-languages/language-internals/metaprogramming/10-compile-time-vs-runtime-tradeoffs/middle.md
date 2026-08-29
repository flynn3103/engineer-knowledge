# Compile-Time vs Runtime Trade-offs — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Compile-Time vs Runtime Trade-offs** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### The decision is multi-dimensional, and the dimensions conflict

There is no single ranking. Compile-time wins performance, startup, safety, tooling, and AOT; runtime wins flexibility and build simplicity, and is roughly a wash on size. A real decision weights these by *your* system:

```text
                COMPILE-TIME            RUNTIME
 performance      ████████ win           ██ lose
 startup          ████████ win           █  lose (cold start)
 binary size      ███ (bloat risk)       ███ (metadata)   ~ tie
 type safety      ████████ win (build)   █  lose (prod)
 flexibility      █  lose (frozen)       ████████ win
 observability    ██████ readable code   ███ live state    mixed
 tooling/IDE      ████████ win           █  lose
 build/deploy     build cost ↑           ████ simple build
 AOT/native-image ████████ win           █  needs config / breaks
```

The art is knowing which rows matter for the system in front of you. A long-running monolith barely cares about startup; a serverless function lives or dies by it.

### The same task lands on different points of the axis

"Serialize an object" isn't inherently compile-time or runtime — it's a *task* you can solve at either point. Jackson chose runtime (reflection), serde chose compile-time (derive). Spring chose runtime DI, Dagger chose compile-time DI. The task is identical; the *placement of the meta-level* differs, and that placement is the whole decision.

---

## The Nine Trade-Off Dimensions

### 1. Performance

**Compile-time:** the meta-work is gone by run time — the generated serializer/wiring is plain code the optimizer can inline and specialize. **Zero per-operation meta-cost.** serde's generated `Serialize` impl is essentially what you'd hand-write.

**Runtime:** every operation re-pays. Jackson reflectively reads fields, looks up getters, boxes values. Even with internal caching, the call sites are more polymorphic and harder for the JIT to inline; reflection trends toward megamorphic dispatch. Typical gap: reflection-based serialization is **several times slower** than generated code on hot paths, and the gap widens at high throughput.

> Nuance: a mature runtime library (Jackson) caches a lot — it doesn't *re-discover* fields on every call forever; it builds a plan once and reuses it. So "runtime = N× slower" is hot-path truth, not a constant. But the floor for compile-time is lower and more inlinable.

### 2. Startup Time (the cold-start dimension)

This is where the trade-off is starkest and most modern.

**Compile-time:** nothing to discover at boot — the DI graph, the routes, the serializers were all generated during the build. Quarkus and Micronaut wire everything at compile time and **boot in tens of milliseconds**.

**Runtime:** classic Spring scans the classpath, reads annotations reflectively, builds the bean graph, and creates proxies — **at startup, every time the process starts.** On a long-running server you pay this once and forget it. On **serverless**, where the process may cold-start per request burst, a 2–5 second boot is a latency disaster.

```text
            Spring (runtime DI)        Quarkus/Micronaut (compile-time DI)
 boot:      ~2–5 s (scan + wire)       ~0.02–0.1 s (graph pre-built)
 driver:    reflective classpath scan  build-time annotation processing
 native:    extra work to support      native-image is a first-class target
```

**Startup is the single biggest reason the industry moved toward compile-time.** Cold start is a real user-facing latency, and serverless made it impossible to ignore.

### 3. Binary / Artifact Size

Not a clean win for either side.

**Compile-time can bloat:** code generation emits a function per type; Rust **monomorphization** and C++ **templates** emit a specialized copy per concrete type — code size grows with the number of type combinations. A heavily generic codebase can balloon.

**Runtime has its own weight:** reflection requires keeping **metadata** (field names, type info, annotations) in the artifact, and the reflection machinery itself. You don't generate per-type code, but you carry the introspection tables.

Net: often a **wash**, sometimes compile-time is bigger (template/monomorphization explosion), sometimes runtime is bigger (metadata + framework). Measure; don't assume.

### 4. Type Safety / Error Timing

**Compile-time = fail fast.** If a derive can't generate a serializer (a field isn't serializable), or a Dagger graph is missing a binding, the **build fails** — red on your screen, before merge. The guarantee is *static*: if it built, the wiring/serialization is structurally sound.

**Runtime = fail late.** Spring's missing bean is a `NoSuchBeanDefinitionException` *at startup*; a reflective method typo is a `NoSuchMethodError` *when that path runs* — potentially in production, potentially at 3 a.m., on the one code path your tests missed. No static check caught it because the call was resolved by string/name at run time.

This is a correctness *and* a velocity argument: compile-time errors are cheaper to fix because they're closer to the keystroke that caused them.

### 5. Flexibility / Dynamism

The dimension where **runtime wins outright.**

**Runtime** can do things compile-time cannot, because it can act on information that didn't exist at build time:

- Deserialize JSON whose **schema is decided at run time** (config-driven, polymorphic, `@JsonTypeInfo`).
- Load a **plugin** compiled separately and discovered in a folder at startup.
- **Hot-reload** code, swap implementations live.
- Power a **REPL** or scripting layer where users type new code.

**Compile-time** is **frozen / closed-world**: it can only handle the types and shapes you built for. If a requirement is "accept a type we'll only know about after deployment," compile-time literally can't.

The decision pivot: **is the variation known at build time, or only at run time?** If genuinely late → you *need* runtime, full stop.

### 6. Observability / Debuggability

Mixed, and subtler than it looks.

**Compile-time** generated code is **real source** (or readable bytecode). You can open the generated serializer, set a breakpoint, step through it, read it in a stack trace. Dagger's generated `*_Factory.java` files are right there in your build output. Debugging is "just debugging normal code."

**Runtime** magic is **harder to trace** — stack traces dive into framework reflection internals, proxies obscure the real call, and "where did this value come from?" leads into a reflective maze. *But* runtime has a unique power: it can **inspect live program state** — dump every bean, list every registered handler, introspect the actual running object graph. Compile-time froze that information into code; runtime can still ask the live system.

So: compile-time is easier to *step through*; runtime is better at *live introspection*. Different observability strengths.

### 7. Tooling / IDE Support

**Compile-time** plays well with static tooling. Generated code gets **autocomplete, go-to-definition, refactoring, and static analysis** because it's real code the IDE sees. A generated `UserSerializer` is as discoverable as a hand-written one.

**Runtime** **defeats static analysis.** A reflective `invoke("doThing")` is invisible to "find usages" and "rename" — refactor `doThing` and the string silently rots. IDEs, linters, and dead-code detectors can't follow reflection, so they either give up or warn. This is a real maintenance cost that compounds over a codebase's life.

### 8. Build Complexity vs Deploy Simplicity

A direct cost transfer.

**Compile-time** pushes cost **into the build**: you run generators/macros/annotation processors, builds get **slower**, and you maintain that generation machinery (a broken generator blocks everyone). The reward is a simple, fast, self-contained runtime artifact.

**Runtime** keeps the **build simple** — no codegen, fast compiles, fewer moving parts — but **ships the cost** with the program (slower startup, per-call overhead, the runtime framework). You didn't delete the work; you moved it to every machine that runs the app.

The right question: *do you want to pay in your CI once, or on every production machine forever?* For widely deployed or latency-sensitive software, paying once in CI is usually the better trade.

### 9. AOT / Native-Image Compatibility

The dimension that turned a preference into a *forcing function*.

**AOT compilers** (GraalVM native-image, .NET Native AOT) and **bundlers** (tree-shaking, .NET trimming) need a **closed world** — they must see all reachable code to eliminate the rest and produce a self-contained, instantly-starting binary.

**Compile-time** approaches are **native-image-native**: the wiring and serializers are ordinary reachable code, so AOT keeps and optimizes them. Quarkus and Micronaut were *designed* around this.

**Runtime reflection breaks the closed-world assumption.** Native-image can't know which classes you'll reflect on, so reflective code either **breaks** at run time or requires a hand-maintained **`reflect-config.json`** listing every reflected member. Tree-shaking removes "unused" code that reflection actually uses. This friction is a major modern driver pushing teams from reflection to codegen.

```text
 NATIVE-IMAGE / TREE-SHAKING / TRIMMING
   compile-time codegen → reachable code → kept & optimized ✓
   runtime reflection   → opaque to analysis → break OR hand-write config ✗
```

---

## Code Examples

### Serialization: runtime (Jackson) vs compile-time (serde)

```java
// Jackson — RUNTIME reflection. No codegen; the mapper inspects User's
// fields/getters reflectively (caching a plan after first use).
ObjectMapper mapper = new ObjectMapper();
String json = mapper.writeValueAsString(new User("Ada", 36));
// Flexible: handles polymorphism, unknown shapes, @JsonTypeInfo.
// Cost: reflective dispatch, native-image needs reflect-config.
```

```rust
// serde — COMPILE-TIME. #[derive(Serialize)] generates a User-specific
// serializer during the build. Run time = plain, inlinable code.
#[derive(serde::Serialize)]
struct User { name: String, age: u32 }

let json = serde_json::to_string(&User { name: "Ada".into(), age: 36 }).unwrap();
// Fast, AOT-native. Cost: macro expansion at build, frozen to known types.
```

### Dependency injection: runtime (Spring) vs compile-time (Dagger)

```java
// Spring — RUNTIME DI. At startup, Spring scans the classpath, reads
// @Component/@Autowired reflectively, builds the bean graph, makes proxies.
@Component class OrderService {
    @Autowired OrderService(PaymentGateway gw, Repo repo) { /* ... */ }
}
// Flexible (profiles, conditional beans, runtime config) but pays a
// reflective startup tax and needs native-image support work.
```

```java
// Dagger — COMPILE-TIME DI via an annotation processor. The build
// generates explicit factories; the "graph" is plain generated code.
@Component interface AppGraph { OrderService orderService(); }
// Generated at build: DaggerAppGraph + OrderService_Factory (real .java).
// Missing binding? BUILD fails. Boot is instant. Native-image friendly.
```

### The startup difference, made concrete

```text
$ time java -jar spring-app.jar      # reflective scan + wire at boot
   ... started in 2.7 s

$ time ./quarkus-native              # graph pre-built at compile time
   ... started in 0.018 s
```

Two orders of magnitude — and that gap *is* the difference between a usable and an unusable serverless function.

### Reflection vs native-image (the breakage)

```text
# Works on the JVM:
obj.getClass().getMethod("process").invoke(obj);   // fine

# Same code in native-image, no config:
#   com.oracle.svm.core.jdk.UnsupportedFeatureError /
#   ReflectiveOperationException: method not registered
#
# Fix (the tax): add to reflect-config.json
#   { "name": "com.app.Worker", "methods": [ { "name": "process" } ] }
```

---

## Coding Patterns

### Pattern 1: Identify forcing functions first

Before weighing soft dimensions, check for hard constraints: native-image? serverless cold start budget? third-party plugins at run time? A forcing function often decides it outright.

### Pattern 2: Amortize unavoidable reflection

If you must reflect, build the plan **once** (at startup or first use) and reuse it — exactly what Jackson does. Turns "pay every call" into "pay once," recovering most of the performance gap.

### Pattern 3: Confine dynamism to a boundary

Keep the open-world part (plugin loader, dynamic deserializer) at a thin edge; make everything inside it compile-time and fast. You localize the cost and the unsafety.

### Pattern 4: Prefer build-time wiring for fixed graphs

If your dependency graph or route table is fixed at build, generate it (Dagger/Micronaut-style). Reserve runtime wiring for genuinely conditional/profile-driven cases.

### Pattern 5: Make the deploy target explicit in the decision

Write down "we deploy to X" before choosing a library. The same choice (Jackson vs serde, Spring vs Quarkus) flips depending on whether X is a long-running JVM or a native-image serverless function.

---

## Best Practices

- **Decompose the trade-off into the nine dimensions** and weight them for *this* system; never argue "compile-time is better" in the abstract.
- **Treat startup as a first-class metric** if you deploy serverless or short-lived processes — it's often the deciding dimension.
- **Assume native-image/trimming will come** for anything cloud-deployed; reflection-heavy choices age into a `reflect-config.json` maintenance burden.
- **Read the generated artifacts** of compile-time tools — they're a debugging and trust advantage you should actually use.
- **Cache reflection plans** when you stay runtime; never re-discover structure per call.
- **Don't pay codegen complexity for cold paths.** A twice-a-day admin endpoint doesn't need a generator; reflection's overhead is irrelevant there.
- **Watch build times.** Heavy macros/processors can dominate CI; measure and budget for it like any other cost.

---

## Edge Cases & Pitfalls

- **"Runtime is always slower" is too strong.** A well-cached reflective library is fast enough for most paths; the gap matters on *hot* paths and at *startup*, not everywhere.
- **"Compile-time is always smaller" is false.** Monomorphization/template/codegen explosion can make compile-time *bigger* than reflection + metadata.
- **The reflect-config drift trap.** Native-image works in CI, then a new reflected class is added and someone forgets the config entry → runtime failure only on that path.
- **Hidden startup cost in "fast" frameworks.** Even compile-time frameworks can have a startup cost if they do *some* runtime discovery; measure, don't assume the label.
- **Refactor rot through reflection.** Renaming a method silently breaks `invoke("oldName")`; tooling can't help. A maintenance time bomb.
- **Generated code you can't read.** If a tool emits unreadable output, you lose the observability advantage that justified compile-time in the first place.
- **Build-time work blocking the team.** A flaky generator or slow annotation processor turns into shared pain; runtime would have kept the build simple.

---

## Apply it

1. Find a real component where **Compile-Time vs Runtime Trade-offs** affects an interface or dependency.
2. Write two plausible choices and the constraint that favors each one.
3. Make the smallest reversible change at that boundary.
4. Exercise the component alone, then exercise the integrated flow.
5. Keep the decision note with the evidence that selected the option.

## Verify your work

- A focused check proves the local behavior.
- An integrated check proves callers and dependencies still agree.
- Logs, traces, compiler output, or benchmarks expose the boundary.
- Reverting the change restores the previous behavior without unrelated edits.

## Review questions

- Which boundary is most affected by Compile-Time vs Runtime Trade-offs?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
