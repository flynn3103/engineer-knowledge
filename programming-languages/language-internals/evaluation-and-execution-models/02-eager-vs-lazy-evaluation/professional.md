# Eager vs. Lazy Evaluation — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Eager vs. Lazy Evaluation** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Strictness Analysis: the Compiler Makes Laziness Affordable

If Haskell literally allocated a thunk for every sub-expression, it would be unusably slow. It isn't, because GHC runs **strictness analysis** (now subsumed by **demand analysis**). The analyzer proves facts like "`f` always forces its first argument" — meaning evaluating that argument *eagerly* before the call cannot change the program's result (it can only change *when* a guaranteed-to-happen evaluation occurs). Armed with that proof, the compiler:

- Skips the thunk: pass the argument by value (often *unboxed*, e.g. a raw `Int#` in a register rather than a boxed heap `Int`).
- Applies the **worker/wrapper** transform: a strict, unboxed "worker" does the real work; a thin "wrapper" preserves the lazy interface for callers.

This is why a well-written `foldl'`-based loop compiles to a tight, allocation-free machine loop despite the source being "lazy." The senior-level discipline of inserting `seq`/`!`/`foldl'` is, in part, *helping the analyzer* — a bang pattern is a guarantee the compiler can build on. Conversely, the analyzer **cannot** prove strictness when a function is *conditionally* strict (forces an argument on some branches but not others), or across module boundaries without inlining, or when laziness is genuinely needed. Those are exactly the spots where leaks survive and where you must intervene manually.

**Key insight:** strictness analysis recovers *performance* without changing *semantics* — it only evaluates eagerly what was *going to be evaluated anyway*. It can never make a non-terminating-if-lazy program terminate, nor vice versa. That semantic-preservation guarantee is what makes it safe to apply automatically.

### 2. Lazy Initialization Is the Mainstream "Lazy" — and It Has a Concurrency Problem

In Java/C#/C++/Go/Python services, you rarely write infinite streams. You constantly write **lazy initialization**: "build this expensive thing on first use, then reuse it."

```java
// Single-threaded: simple and correct.
private Config config;
public Config getConfig() {
    if (config == null) {
        config = loadConfig();   // expensive; runs once
    }
    return config;
}
```

This is fine — *until two threads call `getConfig()` simultaneously*. Both may see `config == null`, both call `loadConfig()`, and worse, one thread may publish a *partially constructed* `Config` that another thread reads via a stale/reordered view. Lazy init, the most common laziness in production, is a **safe-publication** problem in disguise.

### 3. Double-Checked Locking: the Famous Footgun

The "obvious" optimization — avoid locking on the hot path by checking twice — is the single most infamous concurrency bug in the field:

```java
// BROKEN before Java 5, and STILL broken without 'volatile'.
private static Singleton instance;
public static Singleton getInstance() {
    if (instance == null) {                 // (1) unlocked check
        synchronized (Singleton.class) {
            if (instance == null) {         // (2) locked check
                instance = new Singleton(); // (3) NOT atomic: allocate, construct, assign
            }
        }
    }
    return instance;
}
```

The bug: step (3) is not atomic. The compiler/CPU may **reorder** it to "assign the reference, *then* finish constructing." A second thread on the unlocked path (1) can see a non-null `instance` that points at a **half-built object**, and use it. The fix in Java is `private static volatile Singleton instance;` — `volatile` forbids the harmful reordering and establishes happens-before, so a non-null read sees a fully-constructed object. The general lesson: **lazy init across threads requires a memory barrier; the language's default visibility is not enough.**

Correct, idiomatic forms differ by language:

- **Java:** prefer the **initialization-on-demand holder** idiom (a static nested class loaded lazily by the JVM's class-init lock) — laziness and thread-safety for free, no `volatile` reasoning. Or `volatile` + DCL if you must.
- **C#:** `Lazy<T>` with `LazyThreadSafetyMode.ExecutionAndPublication` (the default) — correct DCL implemented for you.
- **C++:** `static` local initialization is guaranteed thread-safe since C++11 ("magic statics"), or `std::call_once` with `std::once_flag`.
- **Go:** `sync.Once` — `once.Do(init)` runs exactly once with correct ordering.

### 4. Deferred Logging and `Supplier<T>`: Conditional Cost

A pervasive professional use of laziness: **don't build the log message unless we'll actually log it.**

```java
// EAGER: buildExpensiveDump() runs even when DEBUG is disabled — wasted work.
log.debug("state: " + buildExpensiveDump());

// LAZY: the lambda (a Supplier / thunk) runs ONLY if DEBUG is enabled.
log.debug("state: {}", () -> buildExpensiveDump());   // SLF4J / Log4j2 lazy form
```

The `Supplier<String>`/lambda is a thunk; the logging framework forces it only after checking the level. This converts *unconditional* cost into *conditional* cost. The same pattern powers lazy default values (`getOrDefault(key, () -> expensiveDefault())`), lazy assertions, and feature-flag-gated work. The trade-off: a tiny allocation (the lambda) and slightly less readable call sites, in exchange for skipping expensive work on the common path.

### 5. ORM Lazy Loading: Laziness You Didn't Ask For

ORMs (Hibernate/JPA, EF Core) lazy-load associations by default: `order.getCustomer()` fires a query *on access*, not at fetch time. This is laziness as a *framework default*, and it produces two signature production failures:

- **N+1 queries:** loop over 100 orders, touch `order.getCustomer()` each iteration → 1 query for orders + 100 for customers. A latency catastrophe invisible in code review. Fix: eager `JOIN FETCH` / `Include()` / batch fetching when you know you'll need the association.
- **`LazyInitializationException` / detached entity:** access a lazy association *after* the session/`DbContext` closed (e.g. in the view layer) → the thunk has no DB connection to force against → crash. Fix: fetch within the session boundary, use DTOs/projections, or `Open Session in View` (with caveats).

The meta-lesson: **a framework's laziness decision becomes your latency and failure surface.** "Lazy by default" at the ORM layer is convenient and routinely the root cause of production incidents.

### 6. Eager vs. Lazy as an Architecture Decision

At system scale the choice is about *moving cost and failure in time and space*:

- **Eager** front-loads cost (startup, fetch, full materialization) → predictable steady-state latency, fail-fast at boot, higher startup time and memory, possible wasted work.
- **Lazy** defers cost to first use → fast startup, pay-as-you-go, but unpredictable first-hit latency ("cold start" spikes), surprise failures at the deferred moment (lazy DB call fails mid-request), and harder capacity planning.

Real systems mix both deliberately: eager-load the critical path and config at boot (fail fast, warm caches), lazy-load rarely-used or huge resources. Serverless cold starts, JIT warmup, connection-pool pre-warming, and CDN cache priming are all explicit *eager-vs-lazy* trade-offs at the infrastructure level.

---

## Code Examples

### Thread-safe lazy init done right, four ways

```java
// Java: initialization-on-demand holder — lazy + thread-safe with NO volatile reasoning.
public final class Singleton {
    private Singleton() {}
    private static class Holder {                 // loaded lazily, on first getInstance()
        static final Singleton INSTANCE = new Singleton();   // JVM class-init lock guarantees once + safe publication
    }
    public static Singleton getInstance() { return Holder.INSTANCE; }
}
```

```java
// Java: correct double-checked locking when you need a non-static lazy field.
private volatile Config config;                   // volatile is mandatory
public Config getConfig() {
    Config c = config;                            // read volatile once into a local (perf)
    if (c == null) {
        synchronized (this) {
            c = config;
            if (c == null) {
                c = loadConfig();
                config = c;                       // volatile write: safe publication + ordering
            }
        }
    }
    return c;
}
```

```csharp
// C#: Lazy<T> implements correct, thread-safe DCL for you.
private static readonly Lazy<Config> config =
    new Lazy<Config>(LoadConfig, LazyThreadSafetyMode.ExecutionAndPublication);
public static Config Config => config.Value;       // computed once, on first access, safely
```

```go
// Go: sync.Once — exactly-once with correct memory ordering, no manual barriers.
var (
    once sync.Once
    cfg  *Config
)
func GetConfig() *Config {
    once.Do(func() { cfg = loadConfig() })          // runs init once; publishes safely
    return cfg
}
```

```cpp
// C++11+: "magic statics" — local static init is thread-safe by the standard.
Config& getConfig() {
    static Config config = loadConfig();   // initialized once, thread-safely, on first call
    return config;
}
```

### The broken DCL, annotated (what NOT to ship)

```java
private static Singleton instance;                 // ✗ NOT volatile
public static Singleton getInstance() {
    if (instance == null) {                        // unlocked read can see a half-built object
        synchronized (Singleton.class) {
            if (instance == null) {
                instance = new Singleton();        // allocate→assign-ref→construct may reorder
            }
        }
    }
    return instance;                               // another thread may use a partially-constructed Singleton
}
```

### Deferred logging with `Supplier`

```java
// Skip the expensive dump entirely when DEBUG is off.
logger.atDebug().log(() -> "snapshot=" + buildExpensiveSnapshot());

// Same idea for a lazy default that's costly to compute:
String value = cache.computeIfAbsent(key, k -> expensiveCompute(k));   // thunk runs only on miss
```

### ORM: the N+1 trap and the eager fix

```java
// N+1: 1 query for orders, then 1 per order for customer (lazy association).
for (Order o : orderRepo.findAll()) {
    process(o.getCustomer().getName());   // each .getCustomer() may fire a query
}

// Fix: eager fetch in a single join.
@Query("SELECT o FROM Order o JOIN FETCH o.customer")
List<Order> findAllWithCustomers();        // one query, no N+1
```

```java
// LazyInitializationException: touching a lazy association after the session closed.
Order o = orderRepo.findById(id).orElseThrow();   // session opens and closes here
// ... later, outside any session ...
o.getItems().size();   // ✗ throws: no session to force the lazy collection
// Fix: fetch items inside the transaction, or return a DTO with items already loaded.
```

---

## Coding Patterns

**Pattern: never hand-roll lazy init across threads.** Use `Lazy<T>` (C#), the holder idiom or `volatile`+DCL (Java), `sync.Once` (Go), `std::call_once`/magic statics (C++). These encapsulate the memory barrier correctly.

**Pattern: read a `volatile` field once into a local.** In correct DCL, cache the volatile read in a local to avoid re-reading it on the return path (a standard micro-optimization that also reads cleaner).

**Pattern: pass thunks for conditional cost.** Accept `Supplier<T>`/`Func<T>`/`() => T` for log messages, default values, and gated work, so the callee decides whether to force.

**Pattern: fetch-eager-at-the-boundary for ORMs.** When you'll iterate an association or use it outside the session, switch that path to eager fetch; keep lazy only for genuinely optional graph edges.

**Pattern: warm caches eagerly at startup.** For latency-critical lazy resources, *trigger* the lazy init at boot (a warmup call) so the first real request doesn't pay the cold cost.

**Pattern: help the strictness analyzer.** In lazy languages, annotate accumulators and hot fields strict (`!`, `foldl'`, strict data) so the compiler's worker/wrapper kicks in; profile to confirm.

---

## Best Practices

- **Treat every "compute once on first use" as a critical section.** Ask "is the first-access path thread-safe and safely published?" and reach for a vetted primitive.
- **Banish hand-rolled double-checked locking** unless you can recite the memory-model reason `volatile`/barrier is required — and even then, prefer the holder idiom / `Lazy<T>` / `sync.Once`.
- **Use lazy logging on hot paths**, but keep the thunk pure and capture-safe (no mutable shared state).
- **Audit ORM fetch plans.** Profile queries; hunt N+1 with query logging; fetch eagerly where you iterate; never let lazy associations escape the session.
- **Decide eager vs. lazy by where you want cost and failure to land.** Front-load the critical path (fail fast, predictable latency); defer the rarely-used and the huge.
- **Warm critical lazy resources at startup** to avoid first-request latency cliffs.
- **In lazy languages, profile the heap** and add strictness where demand analysis can't reach; don't assume the compiler caught every leak.
- **Document laziness at API boundaries.** If you return a deferred query, a generator, or a lazily-loaded entity, say so — the caller owns its failure modes.

---

## Edge Cases & Pitfalls

**Pitfall 1: DCL without a barrier.** The classic. Non-`volatile` (Java) / non-`atomic` (C++ pre-magic-statics, or manual flags) DCL can publish a half-constructed object. Use the holder idiom / `Lazy<T>` / `sync.Once` / `std::call_once`.

**Pitfall 2: `volatile` on the *wrong* thing.** Marking the *flag* volatile but not the *reference*, or assuming `volatile` makes compound operations atomic (it doesn't), reintroduces the race.

**Pitfall 3: the lazy-init exception is cached too.** Some lazy primitives cache a *thrown exception* — the first failed init permanently fails every future access (`Lazy<T>` default `ExecutionAndPublication` does this). If init can transiently fail, choose a mode/primitive that allows retry, or handle it explicitly.

**Pitfall 4: ORM N+1 hidden behind clean code.** A `.map(o -> o.getCustomer().getName())` reads beautifully and fires 100 queries. Only query logging / profiling reveals it. Eager-fetch where you iterate.

**Pitfall 5: `LazyInitializationException` from layering.** Returning entities to a view/controller after the session closes forces a lazy association with no connection. Use DTOs/projections or fetch within the transaction.

**Pitfall 6: cold-start latency from deferral.** Lazy init + a request-time first hit = a latency outlier exactly when a user is waiting. Warm at startup for latency-critical paths.

**Pitfall 7: strictness annotations that change semantics.** Forcing a value that the program *legitimately* needs to leave un-evaluated (an infinite structure, a `⊥` in an unused slot) can turn a working program into a hang/crash. Strictness is safe only where the value was going to be forced anyway.

**Pitfall 8: capturing mutable state in a deferred thunk.** A `Supplier` log message that reads a field which mutates before the thunk is forced logs the *wrong* value — the closure trap, at production scale.

---

## Apply it

1. Define the user or business outcome that **Eager vs. Lazy Evaluation** should improve.
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

- Which measurable outcome justifies investing in Eager vs. Lazy Evaluation?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
