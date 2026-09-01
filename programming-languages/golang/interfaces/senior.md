# Interfaces — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Interfaces** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Interface values have a real runtime representation and cost

An interface value is a two-word structure: a pointer to type information and a pointer to the underlying data (or the data itself for very small types, historically — the exact representation is `eface`/`iface` internally). Calling a method through an interface is an indirect call through this structure (roughly analogous to a vtable lookup), which is slower than a direct method call and defeats inlining. In a genuinely hot path (millions of calls/second), this cost is measurable; in most application code, it's noise next to I/O and allocation costs.

### 2. Boxing a value into an interface can allocate

```go
var w io.Writer = MyStruct{} // if MyStruct doesn't already escape, this can force a heap allocation
```

Storing a value type into an interface variable can trigger a heap allocation if the compiler can't prove the interface value's lifetime is contained — a subtlety that occasionally surfaces in allocation-focused performance work. Benchmarking (`-benchmem`) is the only reliable way to know whether a specific interface usage adds a real allocation cost.

### 3. Leaky abstractions: when the interface doesn't hide enough

An interface designed around one implementation's quirks (e.g. a `Query(sql string) (Rows, error)` interface that assumes a relational database) leaks that assumption to every caller, making a second implementation (a document store, a cache) awkward or impossible without violating the contract's implicit assumptions. Good interface design asks: "if I had to write a *second*, very different implementation of this today, would the interface still make sense?"

### 4. Interfaces at package boundaries are contracts, not conveniences

A public interface exported from a widely-used package is effectively a promise: every method signature, every documented behavior (including error conditions and nil-handling), becomes something callers depend on, sometimes in ways you can't see (reflection, type assertions to concrete types you didn't intend to expose). Changing a public interface's method set is a breaking change; adding new methods to an existing interface is *also* breaking for anyone who implements it. Prefer adding a **new**, separate interface over widening an existing one.

### 5. The "interface segregation" trade-off at scale

A single `Repository` interface with 15 methods (`Create`, `Update`, `Delete`, `FindByX`, `FindByY`, ...) forces every implementation — including test fakes — to implement all 15, even when a given consumer only calls 2. Splitting into narrow, per-capability interfaces (`Creator`, `Finder`) that a concrete type satisfies simultaneously keeps each consumer's dependency minimal, at the cost of more interface types to track.

---

## Worked Example — An Interface That Couldn't Add a Method

A `Store` interface with a single implementation (Postgres) shipped for two years. A new requirement needed a `StoreWithTTL` capability for one specific use case. Adding a `SetWithTTL` method directly to `Store` would have broken every existing test fake across a dozen services that implemented the interface for testing. The fix: a new, separate `TTLStore` interface embedding `Store` plus the new method, so only the one consumer that needed TTL support had to satisfy the wider contract — everyone else was untouched.

```go
type Store interface {
    Get(key string) (string, error)
    Set(key, value string) error
}
type TTLStore interface {
    Store
    SetWithTTL(key, value string, ttl time.Duration) error
}
```

---

## Best Practices

1. Before exporting a public interface, ask whether it would still make sense with a second, very different implementation.
2. Add new capabilities as new interfaces (possibly embedding the old one), not by widening an existing public interface.
3. Only avoid interfaces for performance reasons after a benchmark shows real, measurable cost — not by default assumption.
4. Keep interfaces at package boundaries small and stable; churn there ripples outward more than churn inside a package.

---

## Edge Cases & Pitfalls

- **Widening a shared interface breaks every implementer**, including ones in other repositories you may not control — coordinate or avoid.
- **A "God interface" with many methods** makes every mock/fake a maintenance burden, and is a common byproduct of interfaces added preemptively rather than at point of use.
- **Interface-heavy hot paths** can show up as unexpected allocations or missed inlining in a profile — verify with `-benchmem`/`pprof` before optimizing away the abstraction.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Adding a method to a widely-implemented public interface | Create a new interface (optionally embedding the old one) instead |
| Assuming interface dispatch cost matters everywhere | Profile first; it's rarely the bottleneck outside genuinely hot, high-frequency call paths |
| Designing an interface around one implementation's internals | Design it around what a second, different implementation would also need to support |

---

## Tricky Points

- Method sets and interface satisfaction are checked structurally at compile time, but the actual dispatch at runtime is dynamic — this combination is what gives Go both compile-time safety and runtime flexibility, unlike duck typing in fully dynamic languages.
- A concrete type can satisfy many unrelated interfaces simultaneously with no coordination between them — a strength for composability, but it means "what does this type implement" requires tooling (`go doc`, IDE support) to answer completely for a type with many methods.

---

## Apply it

1. State the system invariant that **Interfaces** must protect.
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

- Which invariant must remain true when Interfaces fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
