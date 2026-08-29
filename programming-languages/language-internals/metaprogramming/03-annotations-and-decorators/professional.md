# Annotations & Decorators — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Annotations & Decorators** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Compile-time vs runtime is a platform-level latency decision

The whole industry has been re-litigating this trade-off, and as a professional you must take a side per workload:

- **Runtime reflection (classic Spring, Hibernate, Jackson default):** fastest to develop, most dynamic, but pays **startup scanning** and **reflection cost** on every cold start. On a long-lived monolith this amortizes to nothing. On a serverless function invoked cold thousands of times, or under a native image with reflection disabled, it's a serious liability.
- **Compile-time generation (Dagger, Micronaut, Quarkus, Spring Native/AOT):** slower builds, but near-instant startup, native-image compatibility, and compile-time error detection. This is why the cloud-native ecosystem pushed DI/AOP to build time.

The decision drives concrete numbers: a reflection-heavy Spring app might cold-start in seconds; the equivalent Quarkus/Micronaut app in tens of milliseconds. If your SLO or cost model is cold-start-sensitive, the column you pick *is* the architecture.

### 2. The TC39 Stage-3 decorator transition — the migration you must plan

TypeScript decorators have been "experimental" for a decade. The TC39 committee standardized a **different** design (Stage-3), shipped in TypeScript 5.0 and modern engines. The differences are not cosmetic:

- **Different decorator signatures.** Stage-3 decorators receive a `(value, context)` pair; the legacy design received `(target, key, descriptor)`. Existing decorators do not work unchanged.
- **No parameter decorators in Stage-3.** The legacy design's parameter decorators — which Angular and NestJS use heavily for `@Inject()` and DI — **are not part of the standard**. Frameworks depending on them must keep `experimentalDecorators` or find another mechanism.
- **`emitDecoratorMetadata` is a legacy concept.** The standard doesn't define design-type metadata emission, so the entire `reflect-metadata`-based DI approach is tied to the legacy mode.

The practical consequence: **Angular and NestJS still run on the legacy decorators** (`experimentalDecorators: true`), while new general-purpose libraries adopt Stage-3. A large org typically ends up with both, segregated by package, and must prevent accidental flag flips that break DI. Planning this migration — or deliberately *not* migrating the DI-heavy parts — is a real professional responsibility.

### 3. Native images and reflection: the reachability problem

GraalVM native images compile ahead of time and **cannot follow arbitrary runtime reflection**. Any annotation read via reflection, any class loaded by name, any proxy generated at runtime must be declared in **reachability metadata** or it fails at native runtime. This is why:

- Reflection-heavy frameworks ship native-image agents and AOT processors that *pre-compute* the reflection config at build time — effectively converting runtime annotation processing into compile-time processing.
- Compile-time frameworks (Dagger, Micronaut) are natively native-image-friendly: there's nothing to reflect on.

If native images are on your roadmap, your annotation strategy is half the battle.

### 4. Build-performance engineering for processors

Annotation processors can wreck build times. At scale you manage:

- **Incremental processing.** Gradle classifies processors as *isolating* (one input → one output, cheap to re-run on change) or *aggregating* (may read across inputs, invalidates broadly). Prefer isolating processors; an aggregating processor in a large module forces near-full reprocessing on any change.
- **Processor ordering and rounds.** Multiple processors generating code that other processors consume increases rounds and build time; minimize cross-processor dependencies.
- **Caching.** Build caches (Gradle, Bazel) can skip processing entirely on cache hits — but only if the processor is deterministic and declares its inputs honestly. Non-deterministic generators poison the cache.

A processor that adds a second per module across a 500-module monorepo adds eight minutes to every build. This is a line item leadership notices.

### 5. AOP proxies and their leaky semantics

Spring's `@Transactional`, `@Cacheable`, `@Async`, `@Retryable`, and security annotations are implemented by **proxies**. The professional-level traps:

- **Self-invocation bypasses the proxy.** `this.cachedMethod()` from within the same bean does not go through the proxy, so the annotation is silently ignored. This causes "the cache isn't working / the transaction didn't roll back" incidents that are invisible in code review.
- **`final` methods/classes can't be proxied by CGLIB**, silently dropping the behavior.
- **Proxy creation order** interacts with bean initialization; an annotation applied to a bean used during early startup may not yet be wrapped.

Owning a Spring codebase means owning these semantics and teaching them, because they are pure action-at-a-distance.

### 6. Debugging action at a distance

The defining cost of annotations/decorators is that behavior is *not visible at the call site*. The professional methodology for the inevitable "why did this happen?" incident:

1. **Identify the reader.** Which subsystem acts on this annotation/decorator? (Compiler? Processor? Spring proxy? Angular injector?)
2. **Confirm the reader actually ran.** Right retention? Right flag? Decorator present? Proxy applied (not self-invoked)?
3. **Inspect the generated/woven artifact.** Read the generated source (Dagger), decompile the class (Lombok), or dump the proxy chain (Spring `AopUtils`).
4. **Reproduce in isolation** with the annotation removed/added to bisect the effect.

The discipline mirrors any action-at-a-distance debugging: make the invisible reader visible before proposing a fix.

### 7. Governance: keeping declarative magic debuggable

Unchecked, annotations metastasize into an unreadable web. Governance levers:

- **Catalog your custom annotations** and their readers in one place.
- **Lint for misuse:** missing retention, decorator-stacking order (auth-before-cache), required TS metadata flags.
- **Cap the "magic budget."** Prefer a small set of well-understood annotations over a bespoke one per feature.
- **Make readers discoverable.** Anyone should be able to jump from `@Custom` to the code that consumes it.

---

## Code Examples

### TypeScript — legacy vs Stage-3 decorator signatures

```typescript
// LEGACY (experimentalDecorators: true) — what Angular/Nest use
function LegacyLog(target: any, key: string, desc: PropertyDescriptor) {
  const orig = desc.value;
  desc.value = function (...args: any[]) {
    console.log(`call ${key}`);
    return orig.apply(this, args);
  };
}

// TC39 STAGE-3 — the standard (TS 5+, modern engines)
function Stage3Log(orig: Function, ctx: ClassMethodDecoratorContext) {
  return function (this: any, ...args: any[]) {
    console.log(`call ${String(ctx.name)}`);
    return orig.apply(this, args);
  };
}
```

The signatures are incompatible. A codebase cannot trivially flip flags: every decorator must be ported. Worse, **parameter decorators** (used by `@Inject()`) exist only in the legacy design, so DI-heavy frameworks are pinned to legacy until they re-architect. Planning around this is the core TS-decorator professional concern.

### Java — making a processor incremental (Gradle isolating)

```java
// An isolating processor: each annotated type maps to exactly one generated file,
// and the generated file depends only on that one originating element.
@SupportedAnnotationTypes("com.example.Value")
@SupportedOptions("org.gradle.annotation.processing.isolating")  // declare isolating
public class ValueProcessor extends AbstractProcessor {
    @Override public boolean process(Set<? extends TypeElement> a, RoundEnvironment r) {
        for (Element e : r.getElementsAnnotatedWith(Value.class)) {
            // Pass the originating element so Gradle can track the 1:1 dependency:
            // filer.createSourceFile(name, e);
        }
        return true;
    }
}
```

Declaring the processor *isolating* lets Gradle reprocess only changed inputs. An aggregating processor (one that reads all `@Value` types to emit a single registry) invalidates broadly and slows incremental builds — a deliberate trade-off you must make consciously.

### Spring — the self-invocation trap and the fix

```java
@Service
class OrderService {
    @Transactional
    public void place(Order o) { /* ... */ }

    public void placeMany(List<Order> orders) {
        for (Order o : orders) {
            this.place(o);          // BUG: self-call bypasses the proxy — NO transaction
        }
    }
}
```

Fix options: inject the bean into itself (`@Autowired private OrderService self;` then `self.place(o)`), split into two beans, or use `TransactionTemplate` programmatically. The annotation *looks* applied but the proxy never sees the internal call. This is a top production-incident source in Spring shops.

### GraalVM — declaring reflection reachability for a runtime-read annotation

```json
// reflect-config.json — tells native-image to keep reflective access
[
  {
    "name": "com.example.Entity",
    "allDeclaredFields": true,
    "allDeclaredMethods": true,
    "annotations": true
  }
]
```

Under a native image, the JVM-time reflection that read `@Entity` no longer works automatically; the framework's AOT processor (or you) must emit this metadata so the native binary keeps the access. This is runtime annotation processing being forced back to build time by the platform.

### Python — feature-flagging a decorator to bound blast radius

```python
import functools, os

def feature(name):
    def deco(func):
        @functools.wraps(func)
        def wrapper(*a, **k):
            if not _enabled(name):
                raise RuntimeError(f"feature {name} disabled")
            return func(*a, **k)
        wrapper.__feature__ = name      # metadata for governance/auditing
        return wrapper
    return deco

def _enabled(name): return os.getenv(f"FEATURE_{name.upper()}") == "1"
```

The decorator centralizes a cross-cutting policy *and* tags the function with discoverable metadata (`__feature__`) so tooling can audit every gated entry point — combining behavior and governance.

---

## Coding Patterns

### Pattern 1: Pick the processing time per workload, not per org

Use compile-time generation for cold-start- or native-image-bound services; runtime reflection where dynamism and velocity dominate. Don't mandate one globally; mandate the *decision criteria*.

### Pattern 2: Isolate decorator usage behind your own abstraction

Wrap framework decorators in thin local equivalents so a future standard/flag change has a small blast radius and one place to port.

### Pattern 3: Lint the invisible requirements

Enforce: retention matches reader; TS metadata flags + `reflect-metadata` import present; security decorators outermost; no self-invocation of proxied methods (where statically detectable).

### Pattern 4: Make every custom annotation traceable to its reader

Doc-comment the consumer, add a test asserting the reader acts, and keep a central catalog. No orphan annotations.

---

## Best Practices

- **Budget annotation cost explicitly.** Know your build-time and startup-time numbers; defend them in design reviews.
- **Decide TC39 vs legacy decorators consciously, per package,** and lint to prevent accidental flag flips that break DI.
- **Plan for native images early** if they're on the roadmap; an annotation strategy retrofit is expensive.
- **Prefer isolating annotation processors** and honest input declarations to keep incremental builds and caches effective.
- **Teach the proxy traps.** Self-invocation and `final` are recurring incidents; make them part of onboarding and code review.
- **Debug reader-first.** For metadata-driven misbehavior, verify the reader ran and could see the metadata before anything else.
- **Govern the magic.** Catalog custom annotations, cap their count, keep readers discoverable, and lint stacking order.
- **Inspect generated/woven output** when in doubt — read Dagger's output, decompile Lombok's classes, dump Spring's proxy chain.

---

## Edge Cases & Pitfalls

- **Flag-flip catastrophe.** Toggling `experimentalDecorators` or upgrading TS without porting decorators breaks every parameter-decorator-based DI site at once.
- **Native-image runtime reflection failure.** An annotation read reflectively works on the JVM but throws on the native binary unless reachability metadata was generated — caught late, in production-like environments only.
- **Aggregating-processor build blowups.** A single aggregating processor in a large module turns incremental builds into near-full rebuilds; CI times balloon mysteriously.
- **Spring self-invocation.** `this.transactionalMethod()` silently skips the transaction/cache/retry — invisible in review, surfaces as data inconsistency in prod.
- **`final` defeats CGLIB proxies.** Marking a `@Transactional` class/method `final` silently disables the behavior.
- **Cold-start regressions from added scanning.** Adding a component-scan path or a reflection-heavy library quietly raises p99 cold-start latency; only visible under load with cold instances.
- **Decorator stacking security holes at scale.** A shared `@cache` decorator placed outside `@authorize` across many endpoints leaks data; a single review miss replicates the bug widely.
- **Orphaned annotations.** A custom annotation whose reader was deleted (or whose retention was changed) becomes silent dead weight that misleads readers into thinking behavior exists.
- **Generated-source drift.** Committing generated sources causes merge conflicts and stale outputs; always regenerate in the build.
- **Cache poisoning by non-deterministic processors.** A processor whose output varies (timestamps, map ordering) breaks build caches and reproducibility.
- **`reflect-metadata` global collisions.** Multiple polyfill versions or bundlers stripping the import cause intermittent, environment-specific DI failures.

---

## Apply it

1. Define the user or business outcome that **Annotations & Decorators** should improve.
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

- Which measurable outcome justifies investing in Annotations & Decorators?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
