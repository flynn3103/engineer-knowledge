# Reflection — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Reflection** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. JPMS: `opens` is the new `setAccessible`

Before Java 9, `field.setAccessible(true)` always worked. Now, deep reflection into another module's package requires that package to be **open**:

```java
// module-info.java
module com.example.app {
    requires com.fasterxml.jackson.databind;
    opens com.example.app.model;                       // to everyone
    opens com.example.app.secret to com.example.di;    // qualified: only this module
}
```

If `com.example.app.model` is *not* opened, Jackson's `field.setAccessible(true)` throws `InaccessibleObjectException`. Operators then bolt on:

```
--add-opens com.example.app/com.example.app.model=com.fasterxml.jackson.databind
--add-opens java.base/java.lang=ALL-UNNAMED
```

This is why production JVM startup scripts accumulate long `--add-opens` lists. The professional discipline: **prefer declaring `opens` in `module-info.java`** (intentional, reviewable, scoped) over scattering `--add-opens` flags (operational, broad, easy to over-grant). `--add-opens java.base/...=ALL-UNNAMED` in particular re-opens the JDK internals and is a smell — it's frequently a workaround for a library that reflects into `java.base` and should be fixed or replaced.

Note the trajectory: each Java release tightens this. "Strong encapsulation of JDK internals" (JEP 396/403) made `--illegal-access=deny` the default, breaking libraries that reflected into `sun.*`/`java.*`. Future releases restrict `setAccessible` further. Reflective libraries are on borrowed time unless explicitly granted access.

### 2. Native-image: the closed world wants a manifest

GraalVM native-image runs a static reachability analysis and compiles only what it can reach. Reflective access by string is unreachable to that analysis, so you must supply a manifest:

```json
// reflect-config.json
[
  {
    "name": "com.example.app.model.User",
    "allDeclaredFields": true,
    "allDeclaredConstructors": true,
    "methods": [{ "name": "getName", "parameterTypes": [] }]
  }
]
```

Three ways to produce it:

- **The tracing agent.** Run your *full test suite / representative workload* under `-agentlib:native-image-agent=config-output-dir=...`; it records every reflective access and writes the config. The risk: untested paths reflect on types the agent never saw → runtime failure in production.
- **Framework hints.** Spring AOT, Quarkus, Micronaut generate this config at build time from their knowledge of your beans/entities — a major reason these frameworks exist in native-image form.
- **Hand-authored config / `@Reflective`-style annotations** for the cases tools miss.

The failure mode is brutal: the JVM build works, the native binary builds *and starts*, then throws `ClassNotFoundException`/`NoSuchMethodException` *only* when the undeclared reflective path executes — often a rare branch in production. **Test the native binary across real paths, not just that it boots.**

### 3. Startup latency: reflection's hidden production tax

Boot-time reflection — classpath scanning for annotations, building DI graphs, materializing ORM metadata — runs *before* the first request. On a long-lived server it's amortized to nothing; on serverless (Lambda) or a CLI invoked thousands of times, it's paid on every cold start and dominates p99.

The industry pivot is explicit: **move reflection from runtime to build time.**

- **Spring Boot 3 / Spring AOT** processes beans at build, generating code + reflection hints, enabling fast native images.
- **Quarkus** does "build-time metaprogramming": it runs the heavy reflection during the build, bakes the results in, and ships a near-reflection-free runtime.
- **Micronaut** uses annotation processors (compile-time) instead of runtime reflection for DI from day one.

The senior reflect-vs-generate choice becomes, at the professional level, a *deployment-shape* choice: native-image + serverless ⇒ minimize runtime reflection; classic long-lived JVM ⇒ runtime reflection is usually fine.

### 4. Cross-language production posture

- **Go:** no module-system fence and no JIT relinking, but `reflect` is heavily used in production serializers/ORMs. The production concern is mostly *performance* (cache per-type plans) and the fact that `reflect`-based code defeats Go's otherwise excellent dead-code elimination, bloating binaries. Go's static binaries don't have native-image's reflection-config problem because there's no AOT closed-world analysis beyond the normal build — but `unsafe` + `reflect` can still corrupt memory.
- **C#/.NET:** `System.Reflection` is mature; NativeAOT and trimming (`PublishTrimmed`) introduce the *same* closed-world problem as GraalVM — you annotate with `[DynamicallyAccessedMembers]` and `DynamicDependency`, and the linker warns on unanalyzable reflection. Source generators (e.g. `System.Text.Json`) are the codegen escape hatch.
- **Python:** no AOT/module fence, so reflection is unfenced and ubiquitous — which makes it a *security* concern above all (arbitrary `getattr`/`__import__`/`eval`-adjacent vectors).
- **Rust:** by avoiding runtime reflection, Rust sidesteps the entire module/native-image/closed-world headache — its `derive`-based codegen is closed-world by construction. This is a *production* argument for Rust's design, not just an aesthetic one.

---

## Code Examples & Configs

### Example 1: Diagnosing and fixing an `--add-opens` situation

```text
# Symptom in logs:
java.lang.reflect.InaccessibleObjectException: Unable to make field private
  java.lang.String com.example.app.model.User.name accessible: module
  com.example.app does not "opens com.example.app.model" to module com.fasterxml.jackson.databind
```

Two fixes, in order of preference:

```java
// PREFERRED: declare intent in module-info.java (reviewable, scoped)
opens com.example.app.model to com.fasterxml.jackson.databind;
```

```bash
# FALLBACK: launch flag (operational, broad). Document WHY each one exists.
java --add-opens com.example.app/com.example.app.model=com.fasterxml.jackson.databind -jar app.jar
```

Audit rule: any `--add-opens ...=ALL-UNNAMED` or `java.base/...` entry needs a written justification and a ticket to remove it.

### Example 2: Generating native-image reflection config safely

```bash
# Run the FULL representative workload, not just unit happy paths.
java -agentlib:native-image-agent=config-output-dir=src/main/resources/META-INF/native-image \
     -jar app.jar < representative-traffic-replay

# Merge across multiple runs so rare paths aren't lost:
java -agentlib:native-image-agent=config-merge-dir=... -jar app.jar < other-scenarios
```

Then *gate the native build in CI* and run integration tests against the **native binary**, so an undeclared reflective path fails the pipeline, not production.

### Example 3: .NET trimming-safe reflection

```csharp
// Tell the trimmer which members must survive, or it strips them.
[RequiresUnreferencedCode("Uses reflection over T's properties")]
static string Dump<[DynamicallyAccessedMembers(
        DynamicallyAccessedMemberTypes.PublicProperties)] T>(T value)
{
    var sb = new StringBuilder();
    foreach (var p in typeof(T).GetProperties())
        sb.Append($"{p.Name}={p.GetValue(value)};");
    return sb.ToString();
}
```

The `[DynamicallyAccessedMembers]` attribute is .NET's machine-checkable reflection manifest; the linker warns when it can't prove safety.

### Example 4: Hardening a reflective dispatcher against abuse

```java
// DANGEROUS: attacker controls the class and method.
Object o = Class.forName(req.className).getDeclaredConstructor().newInstance();
o.getClass().getMethod(req.methodName).invoke(o);

// HARDENED: allow-list, no constructor side effects, no arbitrary classes.
private static final Map<String, Handler> ALLOWED = Map.of(
    "refund", new RefundHandler(),
    "notify", new NotifyHandler());

Handler h = ALLOWED.get(req.action);   // string -> known instance, no reflection on input
if (h == null) throw new BadRequest("unknown action");
h.handle(req);
```

The fix isn't "reflect more carefully" — it's "don't reflect on attacker input at all; map to an allow-list."

---

## Operational Patterns

**Pattern 1: Declare, don't flag.** Express reflective access via `module-info.java` `opens` / `reflect-config.json` / `[DynamicallyAccessedMembers]` — version-controlled and reviewed — rather than launch flags scattered in deploy scripts.

**Pattern 2: Generate config from real traffic.** Drive the tracing agent with replayed production-shaped traffic and *merge* across scenarios; never trust a single happy-path run.

**Pattern 3: Gate the native/trimmed build in CI.** Run integration tests against the actual AOT artifact so reflection gaps fail the pipeline.

**Pattern 4: Allow-list reflective input.** Never reflect on attacker-controlled names; map strings to known handlers.

**Pattern 5: Budget boot-time reflection.** Measure cold start; if it matters, adopt an AOT framework or codegen to relocate reflection to build time.

**Pattern 6: Track the platform's tightening.** Treat `--add-opens` and `--illegal-access` reliance as tech debt with a removal plan.

---

## Best Practices

- **Inventory your reflection.** Know which libraries reflect (Jackson, Hibernate, Spring) and into which packages; that inventory drives `opens` and config.
- **Minimize the blast radius of `opens`.** Use qualified `opens ... to <module>` rather than opening to everyone.
- **Keep `reflect-config.json` close to the code** (`META-INF/native-image`) and regenerate it in CI, not by hand once.
- **Pin and patch deserialization libraries aggressively** — they're the classic reflective CVE vector.
- **Forbid reflective dispatch on untrusted input in code review** as a hard rule.
- **Prefer codegen/source generators** (`System.Text.Json` SG, Micronaut, Quarkus) for new startup-sensitive services.
- **Document every `--add-opens`** with a justification and an owner.

---

## Edge Cases & Pitfalls

- **`InaccessibleObjectException` only at runtime.** Module access is checked when reflection runs, so an unopened package passes compilation and fails in prod.
- **Native-image works on JVM, breaks as a binary.** The single most common GraalVM surprise — a reflective path not in the config.
- **Tracing agent misses untested branches.** Config is only as complete as your workload coverage.
- **`--add-opens ALL-UNNAMED` masks real problems** and silently re-exposes JDK internals — a security regression hiding as a compatibility fix.
- **Trimming/NativeAOT in .NET strips reflectively-used members** without `[DynamicallyAccessedMembers]`; warnings are easy to ignore until runtime failure.
- **Classloader/module leaks** from reflective caches in app servers and hot-reload setups.
- **Reflection defeats Go/Java/.NET dead-code elimination**, inflating binary/image size — relevant for edge and mobile.
- **Library upgrades change reflective access patterns**, silently requiring new `opens`/config.

---

## Security

Reflection is a force multiplier for attackers because it *bypasses access control by design* and *invokes behavior chosen at runtime*. The canonical incidents:

- **Java deserialization RCE (the "gadget chain" era).** `ObjectInputStream.readObject` reflectively reconstructs arbitrary objects and invokes their methods. Attackers craft payloads chaining library classes (Commons-Collections, etc.) into remote code execution. Mitigation: never deserialize untrusted data with Java native serialization; use allow-list `ObjectInputFilter`; prefer data formats without code semantics.
- **Log4Shell (CVE-2021-44228).** JNDI lookups in log messages reflectively loaded and instantiated attacker-specified classes — reflection + dynamic class loading on untrusted input. Mitigation: patch; disable lookups; never feed untrusted data to reflective loaders.
- **Spring4Shell (CVE-2022-22965).** Data binding reflectively reached `class.module.classLoader` to manipulate the running app. Mitigation: restrict bindable reflective properties; patch.

The through-line: **attacker-controlled string + reflective instantiation/invocation = RCE risk.** Defenses, in order: (1) don't reflect on untrusted input — use allow-lists; (2) deny reflective access to dangerous classes (`ClassLoader`, `Runtime`, JNDI, serialization filters); (3) keep platforms current as they tighten reflective defaults; (4) prefer codegen-based libraries that have no runtime reflective dispatch on input. `setAccessible(true)` itself is a privilege escalation primitive — audit its use, and rely on JPMS `opens` scoping to constrain what it can reach.

---

## Apply it

1. Define the user or business outcome that **Reflection** should improve.
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

- Which measurable outcome justifies investing in Reflection?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
