# Versioning & SemVer — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Versioning & SemVer** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Versioning & SemVer
> *Your first contact with version numbers: reading them, bumping them, and pinning them in a dependency file.*

---

## Core Concept 1 — Anatomy of a Version Number

A SemVer version has three required numbers separated by dots:

```
   2  .  4  .  1
   │     │     │
   │     │     └── PATCH  → bug fixes only
   │     └──────── MINOR  → new features, backward-compatible
   └────────────── MAJOR  → breaking changes
```

Read it left to right, most-significant first. `2.4.1` is newer than `2.4.0`, which is newer than `2.3.9`, which is newer than `1.99.99`. A bigger MAJOR always wins, no matter how big the other numbers are: `2.0.0` beats `1.50.7`.

The numbers do **not** behave like decimals. `1.10.0` is **newer** than `1.9.0`, because `10` is greater than `9`. Each component is its own integer, not a digit after a decimal point.

## Core Concept 2 — What Each Bump Means

The whole point of SemVer is that the *number you bump* tells your users what kind of change shipped.

| You changed... | Bump | Example |
| --- | --- | --- |
| Fixed a bug, no API change | PATCH | `1.4.2 → 1.4.3` |
| Added a feature, old code still works | MINOR | `1.4.3 → 1.5.0` |
| Removed/renamed something, old code breaks | MAJOR | `1.5.0 → 2.0.0` |

Two rules trip up beginners:

- **When you bump MINOR, reset PATCH to 0.** `1.4.3` + a feature → `1.5.0`, not `1.5.3`.
- **When you bump MAJOR, reset MINOR and PATCH to 0.** `1.5.0` + a break → `2.0.0`.

Concrete example. You maintain a small Go library:

```go
// v1.2.0
func Greet(name string) string { return "Hi " + name }

// Added an optional second function — old callers unaffected → MINOR → v1.3.0
func GreetFormal(name string) string { return "Good day, " + name }

// Renamed Greet to Hello — every caller must edit → MAJOR → v2.0.0
func Hello(name string) string { return "Hi " + name }
```

## Core Concept 3 — Pre-release and Build Metadata

Before a final release, you often publish test versions. SemVer supports this with a **pre-release** suffix after a hyphen:

```
1.0.0-alpha          earliest, expect bugs
1.0.0-alpha.1        a numbered alpha
1.0.0-beta.2         feature-complete, still testing
1.0.0-rc.1           release candidate — final unless a bug appears
1.0.0                the real thing
```

The key precedence rule: **a pre-release is always *older* than the same version without a suffix.** So `1.0.0-rc.1` < `1.0.0`. This is the opposite of intuition for some people — `1.0.0` is the *finished* product, so it sorts last.

**Build metadata** comes after a `+` and is ignored when comparing versions:

```
1.0.0+20240601           a build date
1.0.0+sha.5114f85         the commit it was built from
```

`1.0.0+sha.aaa` and `1.0.0+sha.bbb` are considered **the same version** for ordering — the `+` part is informational only.

## Core Concept 4 — Where the Version Lives

The version string is usually stored in one place per project and read from there everywhere else:

```jsonc
// package.json (Node)
{ "name": "my-app", "version": "1.4.1" }
```

```toml
# Cargo.toml (Rust)
[package]
name = "my-app"
version = "1.4.1"
```

```python
# pyproject.toml (Python)
[project]
name = "my-app"
version = "1.4.1"
```

For many tools you also create a **Git tag** so the exact source for a release is recoverable:

```bash
git tag v1.4.1
git push origin v1.4.1
```

Go is special: it has no version field in a file. The version *is* the Git tag, and the module path encodes the major version (more on that in higher tiers).

## Core Concept 5 — Pinning a Dependency

When you depend on someone else's package, you state which versions you accept. The default operators differ per ecosystem:

```bash
# npm — caret means "compatible with 1.4.1": allows 1.x.x but not 2.0.0
npm install lodash@^1.4.1

# tilde means "patch updates only": allows 1.4.x but not 1.5.0
npm install lodash@~1.4.1

# exact pin — no updates at all
npm install lodash@1.4.1
```

```python
# requirements.txt (pip / PEP 440)
requests==2.31.0     # exact
requests~=2.31.0     # >=2.31.0, <2.32.0 (compatible release)
requests>=2.31.0     # 2.31.0 or anything newer
```

```toml
# Cargo.toml — bare "1.4.1" means caret by default: ^1.4.1
serde = "1.4.1"
```

For applications, prefer a **lockfile** (`package-lock.json`, `Cargo.lock`, `poetry.lock`, `go.sum`) committed to Git. The lockfile records the *exact* versions you actually installed, so teammates and CI build the same thing you did.

## Real-World Examples

- **A safe upgrade.** Your app uses `express@^4.18.0`. A new `4.18.2` ships with a bug fix. `npm update` picks it up; nothing in your code changes. That is a PATCH working as designed.
- **A scary upgrade.** `react@17` → `react@18` is a MAJOR bump. The render API changed; you must update your `ReactDOM.render` calls. SemVer warned you with the leading `18`.
- **A pre-release in the wild.** `npm install next@canary` installs versions like `15.0.0-canary.42`, deliberately not picked up by `^15.0.0` constraints, so only people who opt in get them.

## Common Mistakes

- **Treating versions as decimals.** Thinking `1.9.0` > `1.10.0`. Wrong — `10 > 9`.
- **Bumping PATCH for a new feature.** Users who pinned `~1.4.0` will never receive it, and you have lied about what changed.
- **Forgetting to reset lower components.** `1.4.3` + feature should be `1.5.0`, not `1.5.3`.
- **Not committing the lockfile.** "Works on my machine" bugs come straight from this.
- **Editing a published version in place.** Republishing `1.4.1` with different contents breaks everyone's cache and trust. Always ship `1.4.2`.

---

## Apply it

1. Choose one small, known input for **Versioning & SemVer**.
2. Predict the output or observable behavior.
3. Run the smallest example or probe that exercises the concept.
4. Change one input to trigger a failure or boundary case.
5. Explain the evidence using the guide's vocabulary.

## Verify your work

- Record the exact input, command or code path, and output.
- Repeat the probe and confirm the result is consistent.
- Show one expected success and one expected failure.
- Resolve any difference between the prediction and the evidence.

## Review questions

- What problem does Versioning & SemVer solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
