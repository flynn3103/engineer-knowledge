# Versioning & SemVer — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Versioning & SemVer** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Versioning & SemVer
> *Turning version numbers into a working policy: deciding what counts as breaking, choosing a scheme, and reading the constraint syntax of every ecosystem you touch.*

---

## Core Concept 1 — Precedence Rules in Full

SemVer precedence is defined precisely, and you should know all of it because tooling depends on it.

1. Compare MAJOR, then MINOR, then PATCH numerically. First difference wins.
2. A version **with** a pre-release has **lower** precedence than the same version without one: `1.0.0-rc.1 < 1.0.0`.
3. When both have pre-releases, compare the dot-separated identifiers left to right:
   - Numeric identifiers compare numerically (`alpha.2 < alpha.10`).
   - Alphanumeric identifiers compare in ASCII sort order.
   - Numeric identifiers are always *lower* than alphanumeric ones.
   - A larger set of fields, all else equal, has higher precedence (`alpha < alpha.1`).
4. Build metadata (`+...`) is **ignored entirely** for precedence.

```
1.0.0-alpha  <  1.0.0-alpha.1  <  1.0.0-alpha.beta  <  1.0.0-beta
            <  1.0.0-beta.2   <  1.0.0-beta.11    <  1.0.0-rc.1   <  1.0.0
```

Note `alpha.2 < alpha.10` (numeric) but if those were alphanumeric strings, `"10" < "2"` in ASCII — a classic source of "why did my RC sort wrong" bugs when people zero-pad or stringify identifiers.

## Core Concept 2 — What Actually Counts as Breaking

"Breaking" is the hardest judgment call in versioning. A breaking change is any change that requires a *correct* downstream user to modify their code, configuration, or expectations to keep working. The public API is wider than most people think:

**Clearly breaking (MAJOR):**
- Removing or renaming an exported function, type, field, flag, or endpoint.
- Changing a function signature (parameter order, types, required-ness).
- Changing a return type or the shape of a JSON/protobuf response.
- Tightening input validation so previously-accepted input now errors.
- Changing a default value that alters observable behavior.
- Removing a CLI flag or changing an exit code.

**Often-overlooked breaking changes:**
- Raising the minimum runtime/language version (`requires Node 18+`).
- Changing error types or error messages that callers match on.
- Reducing precision or changing serialization (`1.0` → `1`).
- Making a previously-optional config field required.

**Not breaking (MINOR or PATCH):**
- Adding a new optional parameter with a default.
- Adding a new function, endpoint, or enum value (usually — see note).
- Internal refactors with identical observable behavior.
- Performance improvements that keep the contract.

```go
// PATCH — fix without contract change
func Divide(a, b int) (int, error) {
    if b == 0 { return 0, errors.New("divide by zero") } // was a panic
    return a / b, nil
}

// MAJOR — return signature changed; every caller must adapt
func Divide(a, b int) int { ... }  →  func Divide(a, b int) (int, error) { ... }
```

> Adding an enum value can break consumers who `switch` exhaustively. Whether that is MINOR or MAJOR is a policy decision — document it.

## Core Concept 3 — The 0.x Special Case

SemVer carves out a deliberate escape hatch: **while MAJOR is 0, anything may change at any time.**

```
0.x.y  →  "initial development; the public API is not stable."
```

Under `0.x`, the *minor* slot acts like a major slot by convention in many ecosystems. Cargo, for instance, treats `0.2.0` and `0.3.0` as incompatible: `^0.2.1` resolves to `>=0.2.1, <0.3.0`, **not** `<1.0.0`. That mirrors how teams actually use `0.x`: each minor can break.

The corollary: **reaching `1.0.0` is a commitment, not a milestone.** It says "I will not break this without bumping MAJOR." Many mature projects stay on `0.x` precisely to avoid that commitment — see ZeroVer below.

## Core Concept 4 — Alternatives: CalVer, ZeroVer, EPOCH

SemVer answers "is this safe to upgrade?" That is the right question for **libraries**. For other software, different schemes fit better.

**CalVer (Calendar Versioning).** The version encodes the release date.

```
Ubuntu        24.04      → YY.MM
pip           24.0       → YY.MINOR
Black         24.3.0     → YY.MM.MICRO
```

CalVer fits when "newer is better" is the only question that matters and there is no stable import API to protect — operating systems, end-user apps, tools with continuous delivery, and time-boxed releases (`2024.06` tells you instantly how stale you are). It is a poor fit for libraries, because the number carries no compatibility signal.

**ZeroVer.** Deliberately never reaching `1.0.0`. Common, half-joking, and surprisingly principled: it keeps the "anything may change" license forever. Risky as a real policy because it signals "not production-ready" to cautious adopters.

**EPOCH.** When your numbering scheme itself was wrong (e.g. you switched from date strings to SemVer and the old numbers sort higher), an epoch prefix forces ordering. PEP 440 spells it `1!`:

```
old:  2024.01.0
new:  1!1.0.0      # the "1!" epoch makes this sort AFTER the date-based ones
```

**Decision guide:**

| Software type | Recommended scheme |
| --- | --- |
| Public library / SDK | SemVer |
| CLI tool with an import API | SemVer |
| End-user app, OS, distro | CalVer |
| Internal service (deploy-only, no consumers import it) | CalVer or commit-SHA + build number |
| Schema / protobuf / API contract | SemVer on the contract itself |

## Core Concept 5 — Constraint Syntax Across Ecosystems

The same intent ("accept compatible updates") is written five different ways. Memorize the table; you will read all of these.

```bash
# npm / Cargo — caret: compatible-with, treats leftmost non-zero as the breaking slot
^1.2.3   → >=1.2.3 <2.0.0
^0.2.3   → >=0.2.3 <0.3.0     # 0.x: minor is the breaking slot
^0.0.3   → >=0.0.3 <0.0.4     # 0.0.x: patch is the breaking slot

# npm — tilde: patch-level only (when minor is given)
~1.2.3   → >=1.2.3 <1.3.0

# pip / PEP 440 — compatible release
~=1.2.3  → >=1.2.3 <1.3.0
~=1.2    → >=1.2 <2.0
==1.2.*  → any 1.2 patch

# Maven — hard ranges with interval notation
[1.2.3]          exactly 1.2.3
[1.2.3,2.0.0)    >=1.2.3 and <2.0.0
1.2.3            a "soft" requirement — a recommendation, not a hard pin
```

**Go is the outlier.** It does not resolve ranges. You write a single minimum version, and the build uses **Minimal Version Selection (MVS)**: of all the minimums requested across the whole dependency graph, pick the highest. There is no `^` or `~`.

```bash
# go.mod
require github.com/pkg/errors v0.9.1   # this is a *minimum*, not a ceiling
```

Go also encodes the **major version in the import path** (Semantic Import Versioning):

```go
import "github.com/foo/bar"        // v0 or v1
import "github.com/foo/bar/v2"     // v2 — a different import path entirely
```

And for commits without a tag, Go synthesizes a **pseudo-version**:

```
v0.0.0-20240101120000-abcdef123456
  │    │              └ 12-char commit hash
  │    └ commit timestamp (UTC)
  └ the base version it sorts just above
```

## Core Concept 6 — Single Source of Truth

The version must be defined in exactly one authoritative place, and everything else derives from it. Otherwise the tag, the manifest, and the binary disagree and you cannot trust any of them.

Two common patterns:

**Manifest as source, tag follows.** The version in `package.json` / `Cargo.toml` / `pyproject.toml` is canonical; a release tool (`npm version`, `cargo release`) bumps it and creates a matching Git tag.

```bash
npm version minor   # edits package.json AND creates tag v1.5.0 AND commits
```

**Tag as source, manifest/binary derives.** The Git tag is canonical; the build reads it and injects it. Standard in Go via linker flags:

```bash
go build -ldflags "-X main.version=$(git describe --tags)" ./...
```

```go
var version = "dev"  // overwritten at build time
func main() { fmt.Println("v" + version) }
```

Whichever you pick, never let two places drift. A common CI check: assert that the manifest version equals the tag being released.

## Real-World Examples

- **The caret-zero footgun.** A team pins `^0.4.2` of a library expecting only patches. The author ships `0.5.0` with breaking changes. Because Cargo/npm treat `0.x` minors as breaking, `^0.4.2` correctly stays below `0.5.0` — but a naive `>=0.4.2` would have pulled it in and broken the build. Knowing the `0.x` rule saved them.
- **Go's MVS in action.** Module A requires `lib v1.2.0`; module B requires `lib v1.4.0`. Go selects `v1.4.0` — the maximum of the minimums — deterministically, with no SAT solver and no "latest" surprises on rebuild.
- **CalVer for an app, SemVer for its SDK.** A company ships its desktop app as `2024.6.1` (CalVer — users only care about "newest") but its public client library as `3.2.0` (SemVer — integrators need the compatibility signal). Same company, two schemes, each correct.

## Common Mistakes

- **Calling an error-message change "just a patch"** when consumers parse the message. It is breaking in practice.
- **Using `>=1.2.0` with no upper bound** in npm/pip — you will silently accept the next breaking major. Use `^` or `~=`.
- **Bumping MAJOR on a `0.x` project.** Going `0.4.0 → 1.0.0` is fine, but `0.4.0 → 0.5.0` already signals breakage; you do not need MAJOR yet.
- **Letting the tag and manifest disagree.** Add a CI assertion.
- **Picking CalVer for a library.** Integrators cannot tell a safe upgrade from a breaking one.
- **Forgetting Go's `/v2` import path.** Tagging `v2.0.0` without changing the module path means nobody can import the new major.

---

## Apply it

1. Find a real component where **Versioning & SemVer** affects an interface or dependency.
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

- Which boundary is most affected by Versioning & SemVer?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
