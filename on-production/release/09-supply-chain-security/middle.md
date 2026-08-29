# Supply-Chain Security — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Supply-Chain Security** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Supply-Chain Security
>
> *An inventory you can query, dependencies you can defend, and a review workflow that scales past "trust me."*

---

## Core Concept 1 — SBOMs: an inventory you can query

An **SBOM** is a structured manifest of everything inside an artifact: every direct and transitive component, its version, ideally its license and a hash, each named with a stable identifier (a PURL). Think of it as the ingredients label on a food package — except machine-readable, so a tool can answer questions about it instantly.

Two formats dominate, and good tools speak both:

- **SPDX** — Linux Foundation, an ISO standard, strong on licensing and broad ecosystem adoption. Often required by procurement and government (see EO 14028).
- **CycloneDX** — OWASP, security-first, with first-class support for vulnerabilities and **VEX** (statements about whether a CVE actually applies to you).

The whole *point* of an SBOM is the queries it unlocks:

- **"Am I affected by CVE-X?"** — match the CVE's affected PURLs against your SBOM. Minutes, not days.
- **License audit** — "do we ship any GPL/AGPL code we shouldn't?" — answerable from the license field.
- **Drift detection** — diff today's SBOM against last release's: what changed, and why?
- **Reachability triage** — combine the SBOM with a scanner to see *which* components have known vulns.

Crucially: **an SBOM is an inventory, not a guarantee.** It tells you what's *in* the box; it says nothing about whether those components are safe, whether the build that produced them was clean, or whether the SBOM itself is accurate (a generator that misses a component produces a confidently wrong inventory). The SBOM is the *map* — it makes the incident-response question answerable. It does not, by itself, prevent the incident.

---

## Core Concept 2 — Generating and using an SBOM

`syft` generates SBOMs from a source tree or a container image:

```bash
# From a directory (reads lockfiles, manifests, installed packages)
syft dir:. -o spdx-json=sbom.spdx.json
syft dir:. -o cyclonedx-json=sbom.cdx.json

# From a built container image (sees the actual installed layers)
syft myorg/api:1.4.2 -o cyclonedx-json=sbom.cdx.json
```

**When you generate matters.** Generating from source reflects what you *declared*; generating from the built image reflects what actually *shipped* (including OS packages baked into the base image — see the `docker-best-practices` skill). The image-level SBOM is closer to truth for "what's running in production." Best practice is to generate at build time and attach the SBOM to the artifact as an attestation (mechanics: [Artifact Signing & Provenance](../04-artifact-signing-and-provenance/)).

Then *use* it. `grype` consumes an SBOM directly, so you separate "what's in the artifact" (slow, do once at build) from "what's now known-vulnerable" (fast, re-run continuously as the advisory DB updates):

```bash
# Scan the SBOM, not the filesystem — re-runnable as new CVEs land
grype sbom:sbom.cdx.json

# The 2 a.m. question, answered from a stored SBOM:
grep -i "log4j" sbom.cdx.json
osv-scanner --sbom=sbom.cdx.json
```

This separation is the operational payoff: store the SBOM per release, and when a new CVE drops you re-scan the *stored* SBOMs of every deployed version without rebuilding anything.

---

## Core Concept 3 — Pinning vs ranges, and what hashes really buy

A **version range** (`^1.2.0`, `>=2,<3`, `~=1.4`) delegates the choice of exact version to resolution time. Convenient — you get patches automatically — but it means a *new, unreviewed* release can enter your build the next time you resolve. That is precisely the channel event-stream used.

**Pinning** fixes the exact version. **Hash pinning** goes further: it fixes the exact *content*, so even the same version number can't be swapped for tampered bytes.

The ladder, weakest to strongest:

| Level | Example | What it stops |
|-------|---------|---------------|
| Range | `"lodash": "^4.17.0"` | Nothing — any matching release flows in. |
| Pinned version | `"lodash": "4.17.21"` | Surprise *version* bumps. Not content swaps. |
| Lockfile (version + hash) | `package-lock.json` `integrity` | Content tampering for the locked version. |
| Hash-pinned manifest | `pip --require-hashes`, Go `go.sum` | Content tampering, verified on every install. |
| Vendoring | `vendor/` committed to repo | Registry availability *and* tampering — you own the bytes. |

What `go.sum` actually protects, precisely: it stores a hash of each module's files (`h1:`) and of its `go.mod`. On build, Go fetches the module (via the proxy and, by default, verifies against the **checksum database** `sum.golang.org`), then checks the bytes against `go.sum`. If anyone — the author, the proxy, a MITM — alters the module after the line was written, the hash mismatches and the build **fails**:

```bash
go mod verify        # re-verify the module cache against go.sum
GOFLAGS=-mod=readonly go build ./...   # fail if go.mod/go.sum would change
```

Say it once more because teams get it wrong: **a hash guarantees the bytes are identical to what was approved. It does not guarantee the bytes are good.** A backdoored module with a stable `go.sum` line sails through. Hash pinning defends against *tampering in transit and surprise updates* — not against an upstream that was malicious from the start. That residual risk is what review, scanning, and provenance (next concepts) address.

**Vendoring** trades repo size and noisier diffs for two real wins: your build no longer depends on registry uptime (the left-pad failure mode disappears), and dependency *changes* show up as reviewable diffs in PRs. `go mod vendor`, `npm`'s offline mirror, or `cargo vendor` all support it.

---

## Core Concept 4 — A dependency review workflow that scales

"Be careful" doesn't scale. A real workflow turns dependency changes into reviewable, gated events:

**1. Automated update PRs.** Dependabot or Renovate watch your manifests and open PRs for updates and — higher priority — security advisories. Renovate adds grouping, scheduling, and auto-merge policies (e.g. auto-merge patch-level dev-dependency bumps that pass CI; require human review for anything else).

**2. Scan on every PR, gate the merge.** Run a scanner against the *changed* lockfile and fail on new high-severity findings:

```yaml
# CI step (illustrative)
- run: osv-scanner --lockfile=package-lock.json --fail-on-vuln
```

GitHub's **dependency-review-action** is purpose-built for this: it diffs the PR's dependency changes and flags newly introduced vulnerable or badly-licensed packages *before* merge.

**3. Review what's actually new.** The reviewable unit is the *added or changed* dependency, not the whole tree. For a new direct dependency, a reviewer should glance at: download/usage popularity, recency of maintenance, number of maintainers, presence of install scripts, and the transitive deps it drags in. OpenSSF **Scorecard** automates much of this — it scores a repo on signals like branch protection, signed releases, and fuzzing:

```bash
scorecard --repo=github.com/some/dependency
```

**4. Triage findings, don't drown in them.** Not every CVE is reachable or relevant. Record a decision (fix now / fix by date / not-affected-because-X) — ideally as a **VEX** statement so the "not affected" verdict is machine-readable and survives the next scan. The goal is a *short, justified* list of accepted risks, not an ignored 400-line report.

---

## Core Concept 5 — Private mirrors, allowlists, and dependency confusion

By default your package manager fetches from the public internet and, given a name, will often prefer the highest version it can find *anywhere*. That default is exactly what **dependency confusion** (Birsan, 2021) exploited: publish a public package with your private package's name and a huge version number, and the resolver pulls the attacker's copy into your build.

Three controls, increasingly strict:

- **Scope/namespace your internal packages** so they can't collide with public names (`@yourco/auth` on npm; a private module path in Go) and **explicitly route** those names to your registry. Never let a private name be resolvable from the public registry.
- **Private mirror / proxy** (Artifactory, Nexus, Verdaccio, a Go `GOPROXY`). All installs go through a registry *you* control, which caches upstream packages, can enforce policy, and removes the public registry as a direct runtime dependency. This is also where you can pin which upstream versions are even *visible*.
- **Allowlist.** The proxy serves only an explicitly approved set of packages/versions. Maximum control, real curation cost — appropriate for high-assurance environments.

```bash
# Pin Go's module fetch + checksum verification explicitly
go env -w GOPROXY=https://proxy.yourco.internal,direct
go env -w GOSUMDB=sum.golang.org      # keep checksum DB verification on

# npm: route a scope to your private registry
npm config set @yourco:registry https://npm.yourco.internal
```

The principle: **decide where your dependencies come from, on purpose.** Names alone are not identity; the source is part of the identity.

---

## Core Concept 6 — Where verification fits at consume time

Pinning and scanning answer "is this the right, known-good version?" **Provenance verification** answers a different question: *"was this artifact actually built from the source it claims, by the build system it claims?"* That's the gap SolarWinds drove a truck through — the source was fine, the *build* was subverted.

At the consume side, the middle-tier awareness is:

- **SLSA provenance** is a signed statement describing how an artifact was built (source repo, commit, builder identity). You can *verify* it before you install or admit an artifact.
- **Trusted publishing (OIDC)** lets CI publish to a registry using a short-lived, identity-bound token instead of a long-lived secret — so there's no publish token to steal (the channel Codecov-style attacks abuse). PyPI, npm, and others support it.
- You **verify before you trust**: check the signature/attestation as a gate, not after the fact.

The actual commands — `cosign verify`, `cosign verify-attestation`, SLSA verifier — and the cryptography behind them live in [Artifact Signing & Provenance](../04-artifact-signing-and-provenance/). Here, just internalize the *shape*: at consume time you add a verification gate that rejects artifacts lacking valid, expected provenance, and you prefer publish flows that have no long-lived secret to steal. (See also the `secrets-management` skill.)

---

## Real-World Examples

- **Log4Shell (CVE-2021-44228).** The defining "are we affected, and where?" event. Teams *with* SBOMs grepped for `log4j-core` and had an answer in minutes; teams without spent days manually auditing builds. This single incident is the strongest argument for generating and storing SBOMs.

- **Dependency confusion (Birsan, 2021).** Public packages impersonating private names executed inside Apple, Microsoft, Shopify, and others. The fix is the Concept 5 toolkit: namespacing, explicit routing, and private mirrors.

- **event-stream (2018).** A malicious *transitive* dependency entered via a maintainer handoff and a version range. Hash pinning + a review gate on new dependencies would have surfaced the change as a reviewable event instead of a silent install.

- **Codecov (2021).** Attackers tampered with Codecov's bash uploader script in CI; it exfiltrated environment variables — including secrets — from thousands of customer pipelines. The lessons: protect CI scripts and secrets, and prefer OIDC/short-lived tokens over long-lived ones.

- **SolarWinds (2020).** Malicious code (SUNBURST) was injected during the *build*, so signed, "legitimate" updates shipped a backdoor to ~18,000 organizations. No amount of dependency pinning helps when the build itself is the attacker — which is why provenance and build integrity (senior tier) exist.

---

## Common Mistakes

- **Generating an SBOM and never querying it.** An SBOM nobody scans or stores is compliance theater. The value is the *fast answer* during an incident.
- **Trusting ranges in production builds** while believing the lockfile makes it fine — until someone runs `npm install` and re-resolves.
- **Treating every CVE as a fire drill.** Without triage/VEX, real findings drown in noise and people stop looking.
- **Letting private package names resolve from the public registry.** This is the dependency-confusion door, left open.
- **Storing long-lived publish tokens in CI** when OIDC trusted publishing is available.
- **Generating the SBOM from source only,** missing OS-level packages that the built image actually ships.

---

## Apply it

1. Find a real component where **Supply-Chain Security** affects an interface or dependency.
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

- Which boundary is most affected by Supply-Chain Security?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
