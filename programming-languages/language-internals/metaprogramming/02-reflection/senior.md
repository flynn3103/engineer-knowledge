# Reflection — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Reflection** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Why `Method.invoke` is slow: the optimizer goes blind

Consider `m.invoke(target, args)`. To the JIT, this is a call into a generic dispatch routine whose *actual* target is a field of the `Method` object, unknown at compile time. Four optimizations evaporate:

- **No inlining.** The JIT can't substitute the callee body — it doesn't statically know the callee. So the call stays a real call with full overhead.
- **No devirtualization.** Even if there's only one possible target, the reflective layer hides it.
- **Boxing kills escape analysis.** Arguments must be packed into `Object[]`, and primitive results boxed. Those allocations escape into the reflective machinery, so escape analysis can't elide them.
- **Per-call checks.** Access verification and argument-shape checks run unless suppressed (`setAccessible`, or amortized by the implementation).

The result is the 10–100× figure from `middle.md` — and crucially, *most of it is structural*, not just lookup. Caching the `Method` removes lookup but leaves boxing and opacity. To remove those, you need a fundamentally different primitive.

### 2. `MethodHandle`: a call the JIT can actually see

A `MethodHandle` is a typed, directly-invocable reference. You obtain it through a `Lookup`:

```java
MethodHandles.Lookup lk = MethodHandles.lookup();
MethodHandle mh = lk.findVirtual(User.class, "greet",
        MethodType.methodType(String.class));
String s = (String) mh.invoke(user);
```

Why it's faster than `Method.invoke`:

- **Typed signature.** A `MethodHandle` carries an exact `MethodType`; with `invokeExact`, no boxing or runtime type juggling is needed.
- **JIT transparency.** When a handle is stored in a `static final` field (a *constant* handle), the JIT can treat it like a known target and **inline through it**. This is the key: a *constant* `MethodHandle` is nearly as optimizable as a direct call.
- **Adapters without reflection.** `MethodHandles.insertArguments`, `asType`, `filterArguments` let you adapt signatures at link time, not per call.

The caveat: handles are fast *when constant*. A `MethodHandle` pulled from a `HashMap` each call is better than `Method.invoke` but not magic — the JIT can't constant-fold it. The big wins come from `invokedynamic`, which makes the handle a true constant at the call site.

### 3. `invokedynamic` + `LambdaMetafactory`: manufacturing a direct call

This is the modern trick that powers high-performance serializers and is *how Java lambdas themselves work*. The idea: instead of reflectively invoking a getter a million times, **synthesize a small class (a lambda) once** that calls the getter directly, then call *that* at full speed.

```java
// One-time: build a Function<User,String> that calls User::getName directly.
MethodHandles.Lookup lk = MethodHandles.lookup();
MethodHandle target = lk.findVirtual(User.class, "getName",
        MethodType.methodType(String.class));

CallSite site = LambdaMetafactory.metafactory(
        lk, "apply",
        MethodType.methodType(Function.class),                 // factory type
        MethodType.methodType(Object.class, Object.class),     // erased SAM sig
        target,                                                 // impl
        MethodType.methodType(String.class, User.class));      // instantiated sig

@SuppressWarnings("unchecked")
Function<User, String> getName = (Function<User, String>) site.getTarget().invoke();

// Hot path: a real, inlinable virtual call — NOT reflection.
String name = getName.apply(user);
```

After this one-time setup, `getName.apply(user)` is an ordinary interface call the JIT inlines and devirtualizes. Benchmarks routinely show this approaching hand-written getter speed, an order of magnitude over `Method.invoke`. Libraries like Jackson (afterburner/blackbird modules), and the JDK's own record/lambda machinery, use exactly this pattern. `invokedynamic` is what links such call sites lazily and caches the result.

### 4. Reflection vs. code generation: the architectural fork

The same job — "serialize any struct" — has two implementations:

- **Reflective (runtime).** Walk fields at runtime via `reflect`/`Class`. *Pros:* zero build-time machinery, works on types loaded later, simple. *Cons:* slower steady state, slow startup (scanning), opaque to shrinkers/native-image, boxing.
- **Generated (compile time).** A macro/annotation-processor/`go:generate` emits exact serialization code per type. *Pros:* direct-call speed, no runtime metadata, tool-visible (DCE/tree-shaking work), native-image-friendly. *Cons:* build complexity, code bloat, must know types at build time.

Concretely: **Serde** (Rust) and **easyjson**/**ffjson** (Go), Java annotation processors, and `System.Text.Json` source generators all *generate*. **Jackson**, `encoding/json`, and `System.Text.Json`'s reflection mode *reflect*. The senior decision rule: if you control the types at build time and care about startup/throughput/native-image, **generate**; if you must handle arbitrary or late-bound types and value build simplicity, **reflect** (and then cache/`invokedynamic` your way to acceptable speed).

### 5. Reflection breaks whole-program reasoning

A reflective call by string is invisible to static analysis. The consequences ripple:

- **Dead-code elimination / shrinkers (ProGuard, R8).** They may remove a method that's only called reflectively, breaking the app — hence "keep rules." Or, conservatively, they keep everything, bloating output.
- **Tree-shaking (JS bundlers).** `obj[dynamicName]()` defeats it; the bundler can't prove what's used.
- **Devirtualization / inlining.** The optimizer can't specialize a call whose target is data.
- **Obfuscation.** Renaming a field breaks any reflective access keyed on the old string.
- **Refactoring tools.** "Rename symbol" misses reflective string references — silent breakage.

This is the deep reason native-image and shrinkers need explicit *reflection configuration*: you must hand the closed-world analyzer the list of reflectively-accessed members it can't infer. (`professional.md` covers the operational side.)

---

## Code Examples

### Example 1: Benchmark shape — direct vs. invoke vs. handle vs. lambda

```java
// Sketch (use JMH for real numbers). Relative ballpark after warmup:
//   direct call          : 1x   (baseline)
//   constant MethodHandle : ~1–2x
//   LambdaMetafactory SAM : ~1x  (inlines to a direct call)
//   cached Method.invoke  : ~10–30x, plus allocations from boxing
//   uncached reflection   : ~50–100x+
direct      : return user.getName();
mhConstant  : return (String) NAME_MH.invokeExact(user);   // static final handle
lambda      : return NAME_FN.apply(user);                  // from LambdaMetafactory
reflectCold : return userClass.getMethod("getName").invoke(user);
```

The lesson: **caching alone gets you to ~10–30×; only `MethodHandle`/lambda gets you back to ~1×.** That gap is the boxing + opacity tax.

### Example 2: A serializer that builds accessors once (the production pattern)

```java
final class FieldAccessor {
    final String key;
    final Function<Object, Object> getter; // built via LambdaMetafactory, NOT reflective

    FieldAccessor(String key, Function<Object, Object> getter) {
        this.key = key; this.getter = getter;
    }
}

// At type-registration time: reflect ONCE to discover getters,
// then synthesize a fast lambda per getter.
List<FieldAccessor> buildAccessors(Class<?> type) { /* reflect + LambdaMetafactory */ }

// Hot path: zero reflection.
void writeJson(Object obj, List<FieldAccessor> accessors, JsonWriter w) {
    for (FieldAccessor a : accessors) {
        w.name(a.key).value(a.getter.apply(obj)); // direct virtual call
    }
}
```

This is, in spirit, how Jackson's blackbird/afterburner and similar fast serializers operate: reflect at registration, run lambdas at runtime.

### Example 3: Go has no `MethodHandle` — so the fix is caching + codegen

Go's `reflect` has no equivalent to `invokedynamic`. The two senior moves are:

```go
// 1) Cache a compiled per-type plan (encoding/json does exactly this).
type fieldEnc struct {
    index []int
    key   string
    encode func(v reflect.Value, b *bytes.Buffer)
}
// Build []fieldEnc ONCE per type, store in a sync.Map keyed by reflect.Type.

// 2) Or eliminate reflection entirely with code generation:
//    //go:generate easyjson -all model.go
//    which emits MarshalJSON/UnmarshalJSON with direct field access.
```

`encoding/json` itself caches a per-type encoder so it doesn't re-walk fields each call. When that isn't fast enough, the ecosystem reaches for codegen (`easyjson`, `ffjson`, protobuf's generated marshalers) — Go's answer to the reflection tax is "reflect once and cache, or generate."

### Example 4: How a shrinker breaks — and the keep rule

```java
// Only ever called reflectively:
public class Handler {
    public void onEvent() { ... } // no static caller anywhere
}
dispatcher.invoke(Class.forName(cfg.handler), "onEvent");
```

ProGuard/R8 sees `onEvent` as unreferenced and strips it → `NoSuchMethodException` at runtime. The fix is a keep rule telling the shrinker not to touch reflectively-used members:

```
-keep class com.example.Handler { public void onEvent(); }
```

This is the everyday face of "reflection violates the closed-world assumption."

---

## Coding Patterns

**Pattern 1: Reflect at registration, emit a fast accessor.** Discover members reflectively once; produce a `MethodHandle`/lambda/generated function the hot path uses.

**Pattern 2: Make handles constant.** Store `MethodHandle`s in `static final` fields or per-type immutable plans so the JIT can constant-fold and inline them.

**Pattern 3: Prefer `invokeExact` with precise `MethodType`** to avoid boxing and runtime adaptation.

**Pattern 4: Cache per-`Type` plans, never per-call lookups.** A `sync.Map`/`ClassValue` keyed by type holds the compiled plan.

**Pattern 5: Choose codegen when the closed world is known.** Native-image targets, startup-sensitive services, and shrinker-heavy builds favor generation over reflection.

**Pattern 6: Ship reflection config / keep rules alongside reflective code.** Treat the closed-world declarations as part of the library's contract.

---

## Best Practices

- **Profile allocations, not just CPU.** Reflective hot paths often bleed through boxing; a flat CPU profile can hide a churning allocator.
- **Use `ClassValue` (Java) for per-type caches** — it's designed for exactly this and is classloader-safe.
- **Wrap `MethodHandle`/`LambdaMetafactory` behind a tested factory.** The wiring is error-prone; isolate it.
- **Document the reflect-vs-generate decision** in the library README so users understand startup/size trade-offs.
- **Provide keep rules / native-image config** with any reflective library you publish.
- **Benchmark against a direct-call baseline with JMH** (warmed up), not microbenchmarks that the JIT folds away.

---

## Edge Cases & Pitfalls

- **Non-constant `MethodHandle`s don't inline.** Pulling a handle from a map per call leaves most of the win on the table.
- **`invoke` vs. `invokeExact`.** `invokeExact` requires the call's static signature to *exactly* match the handle's `MethodType`, or it throws `WrongMethodTypeException`. `invoke` adapts (and boxes). Choose deliberately.
- **`LambdaMetafactory` signature wiring is finicky.** The erased vs. instantiated `MethodType`s must be right or you get linkage errors at runtime.
- **Shrinkers over-strip reflectively-used members.** Always supply keep rules; test the shrunk artifact, not just the debug build.
- **Native-image silently no-ops missing reflection config** until the reflective call runs and throws — test the native binary.
- **`ClassValue`/`ClassLoader` leaks.** Per-type caches can pin classloaders in app servers; use weak keys or `ClassValue`.
- **Generated code drift.** If codegen isn't run on every build, generated marshalers go stale against the type — wire it into the build, not a manual step.

---

## Performance Engineering

- **Hierarchy of cost (Java):** direct ≈ constant `MethodHandle`/lambda < cached `Method.invoke` (≈10–30× + alloc) < uncached reflection (≈50–100×+). Pick the rung your latency budget needs.
- **Eliminate boxing first.** It's frequently the dominant cost in reflective serialization; typed handles or codegen remove it.
- **Move work to startup.** Reflect, scan, and synthesize at boot; keep steady state direct. Watch that this doesn't blow the cold-start budget for serverless (where codegen/AOT may win instead).
- **Measure the whole picture:** throughput, p99 latency, allocation rate, *and* startup time. Reflection trades these against each other; a win on one can be a loss on another.
- **In Go:** there is no JIT relinking trick — your levers are per-type caching and codegen. Accept that pure `reflect` will not match generated code.

---

## Apply it

1. State the system invariant that **Reflection** must protect.
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

- Which invariant must remain true when Reflection fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
