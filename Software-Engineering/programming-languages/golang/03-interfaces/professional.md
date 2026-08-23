# Interfaces — Professional Level

> **Topic:** [Interfaces](../README.md)
> **Focus:** Interface design as an API-governance concern across teams, deprecation strategy for public interfaces, and teaching consumer-driven interface design as a team norm.

---

## Introduction

Across an organization with many services and shared internal libraries, interface design decisions compound: a poorly designed shared interface gets copy-pasted into a dozen consumers before anyone notices it doesn't generalize. At this level, the job is establishing review norms and deprecation practices that keep interfaces evolvable across team boundaries.

---

## Core Concepts

### 1. Shared internal libraries need an interface-change policy

Any interface exported from a widely-used internal library should have an explicit policy: additive changes go in new interfaces; breaking changes require a major version bump and a migration window with both old and new interfaces available simultaneously. Without this written down, individual engineers make ad hoc, inconsistent decisions under deadline pressure.

### 2. Consumer-driven interface design as a review norm

Code review should flag interfaces defined in the *implementing* package "for future flexibility" with no current second implementation or test need — and should welcome interfaces defined narrowly in a *consuming* package, scoped to exactly what that consumer calls. Making this an explicit review checklist item (not just individual taste) keeps the codebase consistent as team membership changes.

### 3. Deprecation is a first-class interface-design activity

```go
// Deprecated: use TTLStore instead. Store will be removed in v3.
type Store interface { ... }
```

A deprecation comment plus a `go vet`-visible staticcheck lint (`SA1019`) gives consumers a compile-time-adjacent signal, well before a hard removal. Pair every deprecation with a migration guide and a realistic timeline, not just a comment that lingers for years unenforced.

### 4. Interface reviews are cheaper before publication than after

Once an interface ships in a widely-imported package, changing it is expensive (see the senior-level worked example). A lightweight design-review step — a short RFC or a pairing session — for any interface intended to be exported from a shared library catches "this won't generalize" feedback while it's still a one-line diff, not a multi-team migration.

### 5. Teaching junior engineers the mental model, not just the syntax

Engineers coming from class-based OOP languages often reach for interfaces the way they'd reach for Java interfaces — declared alongside the implementation, one per concrete type "just in case." Explicit onboarding material contrasting Go's consumer-driven, implicit-satisfaction model against that instinct pays off across every PR that engineer writes afterward.

---

## Code Examples

### Example 1 — A deprecation with lint enforcement

```go
// Deprecated: use TTLStore.SetWithTTL instead; Store.Set will be removed in v3.0.
func (s *store) Set(key, value string) error { ... }
```

```bash
staticcheck ./...
# main.go:42:2: SA1019: s.Set is deprecated: use TTLStore.SetWithTTL instead (staticcheck)
```

### Example 2 — A lightweight interface RFC template

```markdown
## Proposed interface: `RateLimiter`
- Consumers: (list services/packages that will use it)
- Second implementation considered: (token bucket AND fixed window — does the interface fit both?)
- Backward-compat plan if we need to widen it later: (new interface, embed this one)
```

---

## Pros & Cons

| Approach | Pros | Cons |
|---|---|---|
| Written interface-change policy for shared libraries | Predictable, less ad hoc breakage | Requires discipline to actually follow under deadline pressure |
| Lint-enforced deprecation (`staticcheck SA1019`) | Visible signal in CI/editor, not just documentation | Requires the lint to actually run in CI and be treated as a blocking signal |
| Pre-publication interface review | Catches design issues while cheap to fix | Adds a process step; needs to stay lightweight to not become a bottleneck |

---

## Best Practices

1. Write down an interface-change policy for every shared internal library, including a deprecation and migration process.
2. Enforce deprecations with `staticcheck` (or similar) in CI, not just comments.
3. Add a lightweight review step for any interface intended to be exported from a shared library, before it ships.
4. Include Go's consumer-driven interface philosophy explicitly in onboarding material for engineers new to the language.

---

## Edge Cases & Pitfalls

- **A deprecation policy without lint enforcement** tends to be ignored under deadline pressure — pair the comment with a checked tool.
- **Pre-publication review that becomes heavyweight** (multi-day approval cycles) will be routed around — keep it to a short, fast conversation or async comment thread.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| No written policy for changing shared interfaces | Document one; review it after the first painful breakage |
| Deprecating via comment only | Add `staticcheck` (or equivalent) enforcement in CI |
| Treating interface design review as unnecessary process | Keep it lightweight — a short async comment thread, not a formal gate |

---

## Cheat Sheet

```
Shared library interface checklist:
  [ ] Has a documented change/deprecation policy
  [ ] New capabilities added as new interfaces, not by widening
  [ ] Deprecations use `// Deprecated:` + staticcheck SA1019 in CI
  [ ] At least one lightweight review before first publication
```

---

## Summary

- Shared internal libraries need an explicit, written interface-change and deprecation policy.
- Consumer-driven interface design should be an explicit code-review norm, not individual taste.
- Deprecations are only effective when lint-enforced (`staticcheck SA1019`), not just documented.
- A lightweight pre-publication review catches expensive-to-fix interface design issues while they're still cheap.

---

## Further Reading

- `staticcheck` deprecation checks: <https://staticcheck.dev/docs/checks/#SA1019>
- Google's API design guide (interface stability principles transfer across languages): <https://google.github.io/styleguide/> (see API design sections)

---

## Related Topics

- [Error Handling — Professional](../04-error-handling/professional.md) — the same governance concerns apply to error-type contracts.
