# Versioning & SemVer — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Versioning & SemVer** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Versioning & SemVer
> *Versioning as organizational policy: a governed, machine-enforced version contract spanning hundreds of libraries, services, schemas, and platform APIs — and the migration economics behind every MAJOR.*

---

## Core Concept 1 — A Versioning Policy as a Governed Standard

A written policy that nobody enforces is decoration. A professional version policy is a **standard** — versioned itself, owned by a named group, and binding by default. It answers, unambiguously:

- **What schemes are allowed for what artifact classes** (libraries → SemVer; deploy-only services → CalVer or SHA; contracts → SemVer on the contract). No per-team improvisation.
- **The canonical breaking-change definition**, including the edge cases your org has been bitten by (error messages, enum additions, raised runtime minimums, default changes).
- **The source of truth** for each artifact class (tag-derived vs manifest-derived) and the CI assertion that enforces it.
- **The bump-derivation mechanism**: human-declared via Conventional Commits, machine-derived via API diff, or both with the diff as a floor.
- **The minimum deprecation window per artifact class**, and who may grant exceptions.
- **The exception path** — because there is always one, and undocumented exceptions become the norm.

```yaml
# Excerpt of a machine-readable org version policy (consumed by CI lint)
artifact_classes:
  public_library:
    scheme: semver
    source_of_truth: git_tag
    bump_derivation: [conventional_commits, api_diff_floor]
    min_deprecation_window_days: 180
  internal_service:
    scheme: calver_or_sha
    source_of_truth: build
    min_deprecation_window_days: 0      # no importers; deploy-only
  wire_contract:
    scheme: semver
    compatibility: full
    registry_enforced: true
```

The point of encoding it as data: the policy is then *checkable*, not merely *readable*.

## Core Concept 2 — Enforcing the Contract in the Platform

Policy lives in the pipeline, not in a wiki. The professional move is to make the *correct* versioning behavior the path of least resistance and the incorrect behavior impossible to merge.

**Bump derivation, automated.** Conventional Commits feed a release tool that computes the version and the changelog, removing human bump-choice entirely for the common case.

```bash
# Conventional Commits → release-please / semantic-release derive the bump
feat: add streaming API            → MINOR
fix: handle nil session            → PATCH
feat!: drop Node 16 support        → MAJOR   (the ! marks a breaking change)

# The bot opens a release PR with the computed version + generated changelog.
```

**API-diff as a hard gate.** The derived bump is checked against a machine-computed API diff; a PR that adds a breaking change while declaring `fix:` fails CI.

```bash
# CI step (conceptual): diff the public API, fail if declared bump is too small
declared=$(derive-bump-from-commits)         # e.g. PATCH
required=$(gorelease -base "$(git describe --tags --abbrev=0)" | parse-required-bump)
[ "$declared" -ge "$required" ] || fail "Breaking change requires MAJOR; commit declared $declared"
```

**Policy-as-code for the rules that diffs can't see.** OPA/Conftest enforces structural rules: tag matches manifest, `/v2` import path present for `v2+` Go modules, no floating tags in production manifests, deprecation window present in the removal PR.

```rego
# Conftest/OPA: forbid floating image tags in prod deployments
deny[msg] {
  input.kind == "Deployment"
  endswith(input.spec.template.spec.containers[_].image, ":latest")
  msg := "production images must be pinned to an immutable tag or digest"
}
```

This is the same principle as [Quality Gates](../../testing/) applied to versioning: the standard is enforced by the system, so compliance does not depend on diligence.

## Core Concept 3 — Versioning the Internal Platform: Protos, Schemas, Templates

The highest-leverage versioning in a large org is rarely application code — it is the **shared internal contracts** that every team depends on: the proto/IDL repository, the event schemas, the shared base images, the IaC modules, and the pipeline templates. A breaking change to any of these is a fleveraged break across the whole company.

**The central proto/IDL repository.** One source of truth, with compatibility *enforced at publish*:

```bash
# buf — lint + breaking-change detection for protobuf, run in CI on the proto repo
buf breaking --against '.git#branch=main'
#   user.proto:14:3  Field "1" with name "id" changed type from "string" to "int64".
#   FAIL — breaking change against main
```

The proto repo's policy is typically **additive-only on the main line**; a breaking change requires a new package version (`acme.user.v2`) so `v1` consumers are untouched — the proto equivalent of Go's `/v2`.

**Event schemas via a registry with `FULL` or `BACKWARD` compatibility**, so a producer literally cannot publish a schema that breaks a consumer. Versioning becomes a property the platform guarantees rather than a convention teams follow.

**Shared base images, IaC modules, and pipeline templates** must be SemVer'd and pinned by consumers, never floated. A `latest` base image is an un-versioned breaking change waiting to happen; pin to a digest and advance via bot PRs.

```hcl
# Terraform module consumers pin a SemVer range, not "main"
module "vpc" {
  source  = "app.terraform.io/acme/vpc/aws"
  version = "~> 4.2"   # patch + minor of 4.2; never a surprise 5.0
}
```

The governing rule: **a platform contract that thousands depend on may evolve additively without ceremony, but a breaking change is a new versioned namespace plus a migration program — never an in-place edit.**

## Core Concept 4 — Org-Wide Dependency Health and the Diamond at Scale

In a multi-hundred-repo estate, the diamond problem stops being per-build and becomes a *fleet* property. Two capabilities are non-negotiable:

**An estate-wide inventory of who uses what version.** Built from SBOMs and lockfiles, queryable: "which services still run `log4j < 2.17`?" Without this, a CVE is unschedulable.

```bash
# Query the SBOM inventory for a vulnerable transitive version across the fleet
sbom-query 'pkg:maven/org.apache.logging.log4j/log4j-core@<2.17.0'
#   42 services affected; 6 still on 2.14.x
```

**Automated, fleet-wide version advancement.** Renovate/Dependabot open PRs across all repos; the goal is keeping the estate close to the leading edge so the gap to any required upgrade (security or otherwise) is small. A fleet that floats 18 months behind cannot respond to a zero-day in hours.

The diamond at scale also has a **convergence** cost: the more versions of a shared library are live across the fleet, the more compatibility surface the platform team maintains. Professional practice actively *narrows* the spread — campaigns to retire old majors, hard deprecation deadlines, and "version floor" policies ("no service may depend on `auth-lib < 5.0` after Q3").

## Core Concept 5 — The Economics of a MAJOR

A MAJOR version bump is not a number; it is a **bill paid by every consumer**. At org scale this cost is quantifiable, and a professional treats it as a budget to be justified.

```
Cost of a MAJOR ≈ (number of consumers) × (per-consumer migration effort)
               +  platform team support cost during the window
               +  risk cost of consumers who never migrate
```

Implications that drive policy:

- **Breaking changes are amortized by frequency.** Many small, mechanical majors (each migratable with a codemod) are far cheaper in aggregate than one giant manual migration, because per-change effort drops toward zero when you ship the codemod with the release.
- **Ship the migration, not just the break.** A `v2` that includes an automated codemod (`jscodeshift`, `gofmt -r`, `comby`, an OpenRewrite recipe) converts an N-team manual project into an N-team CI run. This is the single biggest lever on MAJOR economics.

```bash
# Ship a codemod alongside the breaking release
npx @acme/migrate-v2 ./src
#   Rewrote 31 call sites: Connect(addr) → NewClient({addr})
```

- **Parallel-run the old major during the window.** `v1` and `v2` coexist (via import path, package namespace, or a compatibility shim) so migration is incremental, not a flag day.
- **A break with no migration plan should not ship.** Policy: a MAJOR PR is blocked until it carries a migration guide, a codemod (where mechanical), and a funded window — turning "I'd like to break this" into "here is the cost and the plan."

This is where the `api-versioning` skill's deprecation and migration strategies become operational policy rather than advice.

## Core Concept 6 — Deprecation Policy and Sunset Governance

Deprecation at org scale needs governance because a deprecation is a *promise* that crosses team boundaries and budget cycles.

- **A central deprecation registry.** Every deprecated symbol/endpoint/schema, its announcement date, its committed sunset date, and its replacement — queryable and reported on. "What sunsets next quarter?" must be answerable.
- **Machine-readable deprecation signals.** For platform APIs, emit `Deprecation` and `Sunset` HTTP headers (RFC 8594) so consumer tooling alerts automatically; for libraries, compiler-visible deprecation annotations that surface in every consumer's build.

```http
HTTP/1.1 200 OK
Deprecation: Sun, 01 Jun 2025 00:00:00 GMT
Sunset: Tue, 01 Dec 2025 00:00:00 GMT
Link: <https://api.acme.com/v2/users>; rel="successor-version"
```

- **Window length scaled to consumer class.** External/partner APIs: often 12+ months and contractually bound. Internal libraries: a quarter or two. Deploy-only services with no importers: effectively zero. The policy states the floor per class.
- **Enforcement at sunset.** When the date arrives, removal proceeds *by default*; an extension requires an explicit, time-boxed exception with an owner. Deprecations that never sunset are how an org accumulates the very legacy it set out to retire.

## Core Concept 7 — Versioning, Compliance, and Supply Chain

Versions are the keys that tie everything else in the release contract together — provenance, SBOMs, vulnerability response, and reproducibility.

- **Immutable version → immutable artifact.** A published version must never be re-pointed. Re-tagging `1.4.1` to new content invalidates every cached SBOM, signature, and provenance attestation. Registries should enforce immutability; floating tags (`latest`, `v1`) are convenience aliases over immutable digests, never the artifact identity itself.
- **Versions index the SBOM.** Vulnerability management is "which *versions* are affected," so the version string must precisely and immutably identify the build it names. This is why pinning to a digest (`@sha256:...`) beats pinning to a tag for security-critical deployments.
- **Yanking, not deleting.** When a published version is found dangerous (a leaked secret, a critical bug), the supply-chain-safe operation is to *yank* (mark unusable for new resolutions while leaving existing pins working), as crates.io and npm support — not to delete and break every lockfile referencing it.

See [Artifact Signing & Provenance](../04-artifact-signing-and-provenance/) and [Supply Chain Security](../09-supply-chain-security/) for the attestation machinery these version guarantees underpin.

## Core Concept 8 — Choosing Schemes Across a Heterogeneous Estate

A real org runs many artifact classes at once; the policy assigns each the scheme whose semantics match its consumers' question.

| Artifact class | Scheme | Why |
| --- | --- | --- |
| Public SDK / library | SemVer | Integrators need a compatibility signal. |
| Internal shared library | SemVer + API-diff CI | Same need, machine-enforced. |
| Proto / IDL package | SemVer on package, additive main, `vN` namespace for breaks | Wire compat across all consumers. |
| Deploy-only microservice | CalVer or `<date>-<sha>` | No importers; only "how new / which commit" matters. |
| End-user app / mobile | CalVer or marketing version | Users care about recency, not API compat. |
| Container base image | SemVer, pinned by digest downstream | Reproducibility + controlled advancement. |
| IaC / pipeline template | SemVer | Consumers pin ranges; breaks must signal. |

The error to avoid is **monoculture by mandate** — forcing SemVer onto deploy-only services produces meaningless `3.0.0` bumps, while forcing CalVer onto libraries strips the compatibility signal integrators need. The policy's sophistication is in matching scheme to artifact class, then enforcing *that* mapping uniformly.

## Real-World Examples

- **Buf-governed proto monorepo.** A company centralizes all protos, runs `buf breaking` in CI against `main`, and mandates `vN`-namespaced packages for breaking changes. Result: a producer team *cannot* merge a wire-breaking change to a live package; breaking evolution is forced into a new, opt-in namespace with a migration. The version contract is enforced by the platform, not trusted to reviewers.
- **Codemod-shipped MAJOR.** A framework team ships `v3` with breaking renames *and* an OpenRewrite recipe. Across 120 internal services, the upgrade is a Renovate PR plus a recipe run; what would have been a multi-quarter manual migration becomes a two-week fleet campaign. The MAJOR's economics were transformed by shipping the migration with the break.
- **Fleet vulnerability response via SBOM + version inventory.** A critical CVE drops in a transitive dependency. Because the org maintains an SBOM-indexed inventory keyed by version and keeps the fleet near the leading edge via Renovate, the affected set is identified in minutes and patched across hundreds of services within the SLA — a capability that only exists because versions are immutable and inventoried.

## Common Mistakes

- **A policy doc with no enforcement.** Without CI/policy-as-code, every team's interpretation drifts.
- **Forcing one scheme across all artifact classes** — meaningless majors for services, lost signal for libraries.
- **Shipping a MAJOR without a codemod or migration plan.** You have exported the cost to every consumer and made the upgrade optional in practice.
- **In-place breaking changes to shared protos/schemas/base images** rather than a new versioned namespace.
- **Floating tags in production** (`:latest`, `v1`) — non-reproducible, unsignable, un-rollback-able.
- **Deprecations with no sunset date or owner** — they accumulate into the legacy you meant to retire.
- **No fleet version inventory** — turning every CVE into an unschedulable scramble.
- **Deleting (not yanking) a bad published version** — breaking every existing lockfile that pins it.

---

## Apply it

1. Define the user or business outcome that **Versioning & SemVer** should improve.
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

- Which measurable outcome justifies investing in Versioning & SemVer?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
