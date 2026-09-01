# Registries & Distribution — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Registries & Distribution** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Registries & Distribution

*Governance, trusted publishing, provenance programs, and cost at fleet scale — making the whole org's distribution trustworthy, affordable, and auditable.*

---

## Core Concept 1 — Distribution as an org-wide platform

- A platform team owns "how artifacts are published and consumed here" so product teams don't each reinvent it.
- The platform provides:

- **One blessed path to publish** (a reusable CI workflow) that signs, attaches provenance + SBOM, publishes by digest, and records the release.
- **One blessed path to consume** (proxies/mirrors with scanning, resolver config that blocks dependency confusion, admission policy in clusters).
- **Golden defaults**: immutable release tags, retention by tag class, OIDC publishing, least-privilege scopes — on by default, hard to misconfigure.
- **Paved road, not a cage**: teams that need an exception go through a documented process, but the default is secure and cheap.

> The platform principle: make the secure, cheap, reproducible path the *easiest* path. If doing it right requires every engineer to remember ten steps, it won't happen at scale. Encode the steps once; everyone inherits them.

## Core Concept 2 — Trusted publishing and the death of long-lived tokens

- Long-lived publish tokens are the worst credential class in distribution: broadly scoped (publish under your name), rarely rotated, and catastrophic if leaked — and they leak (CI logs, env dumps, committed `.npmrc`).
- **Trusted publishing** eliminates them.

The mechanism:

- Your CI provider (GitHub Actions, GitLab) issues a short-lived **OIDC** token asserting "this run is from repo X, workflow Y, branch Z."
- The registry is configured to *trust* that specific claim and mints a short-lived publish credential — no secret stored anywhere.

```yaml
# PyPI trusted publishing — no API token anywhere
permissions:
  id-token: write          # allow OIDC token issuance
jobs:
  publish:
    steps:
      - uses: pypa/gh-action-pypi-publish@release/v1   # authenticates via OIDC
```
```yaml
# npm provenance + (with org policy) OIDC-based publishing
- run: npm publish --provenance --access public
  env:
    NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}   # or, increasingly, OIDC trusted publishing
```

- PyPI and npm both support trusted publishing.
- Container registries support the analogous pattern via cloud workload identity (GitHub OIDC → ECR/GHCR/Artifactory) so no static cloud keys live in CI.

**Rollout as a program:**

1. Inventory every place a long-lived publish token exists.
2. Enable trusted publishing per package/registry.
3. Revoke the old tokens.
4. Add a policy check that *fails CI* if a publish step uses a static token.

Trusted publishing also strengthens provenance: because the registry verified the OIDC claim, the "published from repo X / workflow Y" statement is trustworthy by construction.

## Core Concept 3 — Provenance and SBOM as a program

- One artifact with provenance is a demo.
- Provenance *as a program* means every artifact, automatically, carries verifiable answers to "where did this come from?" and "what's inside it?"

- **Provenance (SLSA / in-toto)** — a signed attestation: this digest was built from this commit, by this builder, with these inputs. Stored alongside the artifact in the registry (as an OCI referrer / attestation).
- **SBOM (SPDX / CycloneDX)** — the dependency inventory, generated at build, attached to the artifact, queryable when the next Log4Shell-class CVE drops: "which of our 4,000 deployed images contain the vulnerable library?"

```bash
# Generate + attach an SBOM and provenance to an image (cosign + syft style)
syft ghcr.io/acme/api@sha256:9b2c... -o spdx-json > sbom.json
cosign attest --predicate sbom.json --type spdxjson ghcr.io/acme/api@sha256:9b2c...
cosign verify-attestation --type slsaprovenance ghcr.io/acme/api@sha256:9b2c...
```

- The registry becomes the **system of record** for trust metadata: artifact + signature + provenance + SBOM, all addressed by the same digest.
- The professional deliverable is the *pipeline* that produces this for every artifact and the *query capability* to answer audit and incident questions in minutes.
- Depth lives in [Artifact Signing & Provenance](../artifact-signing-and-provenance/professional.md) and [Supply-Chain Security](../supply-chain-security/professional.md).

## Core Concept 4 — Policy: only admitted artifacts run

- Generating trust metadata is worthless if nothing checks it.
- The enforcement point is **admission control** in your runtime: an image runs only if it is signed by an approved key, has acceptable provenance (e.g. SLSA level ≥ N), comes from an allowed registry, and passes scan policy.

```yaml
# Sigstore policy-controller (cluster policy): admit only verified images
apiVersion: policy.sigstore.dev/v1beta1
kind: ClusterImagePolicy
spec:
  images:
    - glob: "ghcr.io/acme/**"
  authorities:
    - keyless:
        identities:
          - issuer: https://token.actions.githubusercontent.com
            subjectRegExp: "https://github.com/acme/.*"
```

Policy spectrum (roll out gradually):

1. **Audit/warn** — log violations, admit anyway.
2. **Enforce in staging.**
3. **Enforce in production.**

- Going straight to hard-enforce org-wide breaks deploys and burns trust in the program.
- The professional move is staged rollout with clear dashboards of what *would* be blocked before it *is*.

> The principle: the registry holds the evidence; the admission gate is the judge. No evidence or failing evidence → no run. This closes the loop from "we sign things" to "unsigned things cannot reach production."

## Core Concept 5 — Cost governance at scale

- At fleet scale, registry cost is real and usually un-owned: storage grows monotonically, cross-region/cross-cloud egress spikes on every scale event, and nobody's budget is debited.
- Levers:

- **Retention by tag class, automated.** CI-scratch and PR tags expire in days; release tags persist. This alone often cuts storage by an order of magnitude.
- **Dedup-aware accounting.** OCI layers are shared; report *unique* storage per team, not summed image sizes, or you'll chase phantom costs.
- **Egress reduction.** Regional pull-through caches and CDN-fronted immutable blobs turn N cross-region pulls into one fetch + local serves — frequently the single biggest line item.
- **Showback / chargeback.** Attribute storage and egress to teams via labels. Visibility creates the incentive; teams clean up what they're billed for.
- **Right-size images.** Smaller base images (distroless, multi-stage builds — see the `docker-best-practices` skill) cut storage, egress, *and* pull latency simultaneously. A 1.2 GB image vs a 120 MB one is 10× the bill and 10× the cold-start pull.

```bash
# Surface the cost drivers
# - unique storage per repo (dedup-aware) → chargeback report
# - top egress repos by region → target for regional caching
# - largest images → target for base-image slimming
```

> Cost governance is not penny-pinching; it's making the cheap path the default (slim images, aggressive scratch retention, regional caches) and the expensive path visible (showback) so it self-corrects.

## Core Concept 6 — Immutability, retention, and compliance as policy-as-code

- Ad-hoc retention rules and per-repo settings drift and create gaps.
- Express them as **reviewed, versioned policy-as-code**:

- **Immutable release tags** enforced registry-wide: a `v*` tag, once pushed, can never be repointed (configurable in ECR, Artifactory, GHCR). This makes "deploy by tag" almost as safe as digest and kills tag-mutation attacks.
- **Retention rules in IaC**: lifecycle policies defined in Terraform, reviewed in PRs, applied uniformly — not clicked into a console where they silently differ across 200 repos.
- **Compliance retention**: regulated artifacts (the actual deployed releases, their SBOMs, provenance) may need to be retained for *years* for audit. Encode "release artifacts: retain N years; scratch: 7 days" as policy, and make deletion of compliance-class artifacts require an explicit, audited exception.

```hcl
# Terraform: ECR repo with immutable tags + lifecycle policy as code
resource "aws_ecr_repository" "api" {
  name                 = "api"
  image_tag_mutability = "IMMUTABLE"      # release tags can never be repointed
}
resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name
  policy     = file("${path.module}/lifecycle.json")   # reviewed in PRs
}
```

> Policy-as-code turns "we have a retention policy" (a wiki page nobody enforces) into "retention is enforced identically on every repo and changes go through review." That is what auditors — and incident responders — actually need.

## Core Concept 7 — Incident response for a bad or poisoned release

- When a release is bad — regression, leaked secret, or actively malicious — execute a rehearsed playbook, not improvisation.
- The right action depends on registry semantics ([middle.md](middle.md)) and *whether the bytes are dangerous*.

1. **Contain.** Stop new adoption: yank (crates/PyPI), deprecate (npm), or pull the tag from rotation. Update admission policy to deny the bad digest immediately — admission control is your fastest org-wide kill switch.
2. **Roll forward / back.** Ship a fixed version *now* (immutable registries leave you no other choice; mutable ones still shouldn't overwrite). Deploys pinned by digest roll back deterministically — see [Rollback & Roll-Forward](../rollback-and-roll-forward/professional.md).
3. **Decide on deletion.** Only unpublish/delete if the bytes themselves are dangerous *and* you're inside the window (npm 72h). Remember left-pad: deleting bytes others depend on turns your incident into everyone's.
4. **Rotate.** Leaked secret → rotate it; compromised publish credential → revoke (trusted publishing minimizes this surface).
5. **Trace blast radius with the SBOM/provenance program.** "Which deployed images contain the bad artifact?" must be a query, not an archaeology project.
6. **Postmortem → policy.** Feed the gap back into policy-as-code so the class of incident can't recur.

> Professional reality: the registry's *immutability* is your friend in an incident (the good versions are still exactly there to roll back to) and the *deletion* lever is the one you almost never pull. Containment is yank + admission-deny + ship-a-fix, not delete.

## Core Concept 8 — Rollout strategy and migration

Introducing these controls into a live org is itself the hard part — break deploys and the program loses credibility:

- **Sequence:** observability first (inventory tokens, images, egress, what *would* fail policy) → trusted publishing (no breakage, removes credentials) → provenance/SBOM generation (additive) → admission in *audit* mode → enforce in staging → enforce in production.
- **Migrate registries carefully.** Moving from Docker Hub to GHCR/ECR, or consolidating onto Artifactory, means dual-publishing during transition, repointing consumers, and preserving digests (re-pushing an image to a new registry yields the *same* manifest digest if bytes are identical — pins survive if you keep the digest).
- **Measure adoption.** Track % of artifacts signed, % with SBOMs, % of publishes via trusted publishing, % of clusters enforcing admission. A program without metrics stalls — see [Engineering Metrics & DORA](../../engineering-metrics-and-dora/) for framing.
- **Communicate deprecations.** Old publish paths and registries get sunset dates, warnings, and migration guides — you're applying the same yank/deprecate discipline to your *own* internal tooling.

## Real-World Examples

**Example 1 — Killing static tokens.** A platform team finds 140 long-lived publish tokens across repos. They enable PyPI/npm trusted publishing and cloud OIDC for container pushes, migrate per package, revoke all 140, and add a CI lint that fails any publish step using a static token. Credential-leak risk for publishing drops to near zero.

**Example 2 — CVE blast-radius query.** A critical CVE lands in a popular logging library. Because every image carries an attached SBOM, the security team queries the registry's attestations and identifies the 312 affected deployed digests in 20 minutes, then drives targeted rebuilds — instead of weeks of guesswork.

**Example 3 — Staged admission rollout.** Admission policy runs in audit mode for a month; dashboards show 6% of deploys *would* be blocked (unsigned legacy images). Teams fix those, then the policy flips to enforce in staging, then production — with zero surprise outages because nothing newly broke at flip time.

## Common Mistakes

- **Long-lived publish tokens left in place.** The single highest-value credential to eliminate via trusted publishing.
- **Generating provenance/SBOM but never verifying.** Evidence with no judge changes nothing — wire admission control.
- **Hard-enforcing admission org-wide on day one.** Breaks deploys, kills the program's credibility. Stage it (audit → staging → prod).
- **Un-owned registry cost.** Without retention-as-code and showback, storage and egress grow unbounded.
- **Console-clicked retention/immutability.** Drifts across repos; un-auditable. Use IaC.
- **No rehearsed bad-release playbook.** Improvising yank-vs-delete during an incident causes left-pad-class self-harm.
- **Deleting compliance-class artifacts.** You may lose the exact bytes an audit or rollback needs.

---

## Apply it

1. Define the user or business outcome that **Registries & Distribution** should improve.
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

- Which measurable outcome justifies investing in Registries & Distribution?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
- A teammate wants to "fix a typo" in a version that's already published — what do you say?
- What is dependency confusion, and how do you defend against it at org scale?
- A published library version leaks an API token in its build output — walk through your incident response.
- An auditor asks which deployed services contain a specific vulnerable dependency — how fast can you answer, and what determines that?
