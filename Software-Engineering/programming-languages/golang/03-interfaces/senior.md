# Interfaces — Senior Level

> **Topic:** [Interfaces](../README.md)
> **Focus:** Interface design at package-boundary scale, the performance cost of interface dispatch and boxing, avoiding leaky abstractions, and designing interfaces that survive years of evolution.

---

## Introduction

At scale, interface design decisions outlive the people who made them. A too-broad interface exposed at a package boundary becomes nearly impossible to change without breaking every caller; a too-narrow one forces awkward workarounds. This level is about designing interfaces as long-lived contracts, and understanding the real runtime cost of the abstraction you're introducing.

---

## Prerequisites

- Comfortable with dependency injection, interface embedding, and generics vs. interfaces (middle level).

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

## Pros & Cons

| Approach | Pros | Cons |
|---|---|---|
| Narrow, per-capability interfaces | Minimal per-consumer dependency, easy to fake in tests | More interface types to name and track |
| Adding a new interface instead of widening an existing one | Non-breaking for existing implementers | Slight proliferation of interface types over time |
| Concrete types on genuinely hot paths | Avoids indirect-call and boxing overhead | Loses substitutability; only justified with a profile showing real cost |

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

## Cheat Sheet

```
Before adding a method to a public interface: can I make a NEW interface instead?
Before removing an interface for perf: do I have a benchmark proving the cost?
Interface value ≈ {type pointer, data pointer} — method call ≈ indirect call
```

---

## Summary

- Interface values carry a real (usually small, occasionally measurable) runtime cost via indirect dispatch and potential boxing allocations.
- A good interface should still make sense if you had to write a genuinely different second implementation today.
- Public interfaces are contracts — widen them by adding new interfaces, not by adding methods to existing ones.
- Interface segregation keeps per-consumer dependencies minimal; the cost is more interface types to track, which is usually worth it.

---

## Further Reading

- Dave Cheney — *Interface Pollution*: search "Dave Cheney interface pollution" for the canonical post.
- Go Data Structures — *Interfaces* (Russ Cox): <https://research.swtch.com/interfaces>

---

## Related Topics

- [Interfaces — Middle](middle.md)
- [Go Runtime — Senior](../02-go-runtime/senior.md) — allocation cost of boxing values into interfaces.
