# Artifact Signing & Provenance — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Artifact Signing & Provenance** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Artifact Signing & Provenance

*Org-wide root-of-trust strategy, key/identity lifecycle, a staged enforcement rollout that doesn't break delivery, and the regulatory drivers behind all of it.*

---

## Core Concept 1 — Choosing a signing strategy for the whole org

There is no single right answer; there is a decision with explicit trade-offs.

- **Keyless (Sigstore public good).**
  - Benefits: no keys to manage; identity-bound; transparency by default; free.
  - Costs: dependency on external Sigstore availability and OIDC; public Rekor reveals *that* you released (metadata exposure); requires trusting the public trust root.
- **Self-hosted Sigstore (private Fulcio/Rekor).**
  - Benefits: same model, internal control; works air-gapped; no public metadata leak.
  - Costs: you now operate a CA and a transparency log — real SRE burden, your own root-of-trust to protect.
- **Long-lived keys in KMS/HSM.**
  - Benefits: familiar; works offline; fine for a small set of high-value, infrequently-rotated release keys (e.g. an OS distro's master key).
  - Costs: the very key-management failure modes Sigstore was built to avoid — rotation, custody, the "who can sign" sprawl. GPG-era pain (lost keys, unverified web-of-trust) is the cautionary history.
- A common professional pattern is **hybrid**: keyless (public or private) for the high-volume CI-built artifacts, plus a small number of **KMS-backed keys** for a few sensitive boundaries (e.g. the policy that admits third-party software, signed by a platform-team key).
- Pin **identities, not key files**, wherever possible — an identity (`release.yml@tag` from the org's IdP) is far harder to misuse than a portable secret.
- Decision drivers to write down: air-gap requirement, metadata-exposure tolerance, regulatory scope, team maturity, and acceptable external dependencies.

---

## Core Concept 2 — Root of trust and key/identity lifecycle

Whatever the strategy, define the **root of trust** explicitly and govern its lifecycle.

- **For keyless:** the roots are Fulcio's CA, Rekor's key, and your OIDC issuer. Sigstore rotates these via **TUF**; your responsibility is to pin and refresh the TUF root reliably across all verifiers, and to *constrain accepted identities* tightly.
- **For self-hosted/KMS:** you own the root. Apply standard high-assurance custody:
  - Root key in an **HSM**, offline, with **M-of-N** quorum to use (no single human can sign with it).
  - The root signs only **intermediate/signing identities**, rarely; day-to-day signing uses short-lived or scoped keys.
  - **Rotation is pre-planned**: publish the new root, allow an overlap window where both are trusted, then retire the old. Never a flag-day swap.

```bash
# KMS-backed signing (no private key on the box)
cosign sign --key awskms:///alias/release-signing IMG@sha256:...
cosign verify --key awskms:///alias/release-signing IMG@sha256:...

# Refresh the (public or mirrored) Sigstore trust root everywhere verification runs
cosign initialize --mirror https://tuf-mirror.internal --root root.json
```

- **Identity strategy** is the higher-leverage half. Maintain a governed registry of "who may sign what":

| Artifact class | Required signer identity | Required provenance |
|----------------|--------------------------|---------------------|
| First-party services | `…/release.yml@refs/tags/*` via org IdP | SLSA source = our repo, builder = our generator |
| Internal base images | platform-team workflow identity | SLSA L3 |
| Vetted third-party | platform-team *attestation* identity | re-attested "approved" predicate |

- This table *is* your acceptance policy. Changes to it go through review like any production change.

---

## Core Concept 3 — Staged enforcement rollout

The fastest way to discredit a signing program is to switch on hard enforcement and block legitimate deploys. Sequence it.

- **Phase 0 — Sign everything (no enforcement).** Turn on signing + provenance in every pipeline. Nothing is blocked. Goal: achieve *coverage* and find pipelines that cannot yet sign.
- **Phase 1 — Observe (audit mode).** Deploy admission policy in `Audit`/`warn`. Emit metrics: how many workloads *would* be blocked, and why (unsigned, wrong identity, missing provenance). This is your gap list.
- **Phase 2 — Enforce on a beachhead.** Flip `Enforce` for one low-risk namespace/cluster or one mature team. Keep escape hatches and watch closely.
- **Phase 3 — Expand by ring.** Roll enforcement outward ring by ring (dev → staging → prod; team by team), each ring gated on a clean audit signal from the previous.
- **Phase 4 — Tighten requirements.** Only after signature enforcement is stable do you add *provenance* requirements, then *source/builder* constraints. Each is its own audit→enforce cycle.

```yaml
# The single most important rollout lever lives in policy:
spec:
  validationFailureAction: Audit    # Phase 1
  # validationFailureAction: Enforce  # Phase 2+, ring by ring
```

- Treat enforcement like a feature flag rollout (see Feature Flags & Progressive Delivery): measurable, reversible, ringed. The **quality-gates** topic covers the gate-design discipline this mirrors.

---

## Core Concept 4 — Break-glass and incident response

- Enforcement *will* eventually block a legitimate, urgent deploy — a critical hotfix when Sigstore is degraded, or a pipeline gap during an incident.
- A program without a sanctioned bypass invites unsanctioned ones (disable the controller cluster-wide), which is far worse.
- Design break-glass to be **possible, narrow, loud, and audited**:
  - **Possible:** a documented procedure (e.g. an exception annotation/label admitted only by a separate, tightly-scoped policy, or a temporary policy carve-out via PR).
  - **Narrow:** scoped to one image digest / one namespace / a time-boxed window, never "disable verification."
  - **Loud:** firing an alert and creating a ticket automatically; visible to security in real time.
  - **Audited:** who invoked it, for what digest, when, why, and an expiry. Reviewed post-incident.

```yaml
# Example: a narrowly-scoped exception, itself reviewed and time-boxed
metadata:
  annotations:
    policy.acme.io/break-glass: "INC-4821"     # ticket ref, alerts on use
    policy.acme.io/break-glass-expires: "2026-06-23T06:00:00Z"
```

- Tie this to the **rollback** plan: if you cannot verify a roll-forward fix in time, rolling back to a *previously verified* digest is often the safer break-glass than admitting an unverified image. See Rollback & Roll-Forward. The **secrets-management** discipline applies to any KMS bypass credentials.

---

## Core Concept 5 — Operational cost and the burden ledger

Sell and run the program with honest numbers. The recurring burdens:

- **Pipeline changes** across every repo (one-time, but broad) — `id-token` perms, signing steps, provenance generators.
- **Verification infrastructure** — admission controllers, their availability, latency budget at admission, and TUF-root/Rekor mirroring.
- **Availability coupling** — verification now depends on Sigstore/OIDC/registry. Budget for caching and a fail stance, or you have added a new outage class.
- **Policy maintenance** — the acceptance registry evolves with every new repo/builder; it needs owners and review.
- **Reproducibility engineering** — if you pursue it, real toolchain work and ongoing drift control.
- **Cognitive load** on developers when a deploy is blocked — invest in *clear failure messages* ("blocked: image not signed by an approved identity; see runbook X").

- The payoffs to weigh against this: closed transport/storage attack surface, auditable provenance for compliance, faster incident forensics (Rekor shows exactly what shipped), and a precondition for several regulatory regimes.
- Make the trade explicit; do not let it be discovered as surprise toil.

---

## Core Concept 6 — Regulatory drivers: EO 14028, SSDF, and attestations

Much of this work is funded by compliance, and a professional should map controls to mandates.

- **Executive Order 14028 (2021)** directed US federal agencies to require secure software practices from suppliers, catalyzing SBOMs and provenance.
- **NIST SSDF (SP 800-218)** is the framework EO 14028 points to; its practices include producing and verifying provenance, protecting build environments, and archiving artifacts and their attestations.
- **CISA Secure Software Development Attestation Form** asks vendors to *attest* (literally) that they follow SSDF practices — produced provenance, hardened builds, etc.
- **SLSA** is the de facto technical yardstick procurement and auditors reference for "build integrity level."

- Practically, this means your signing/provenance program should be able to **produce evidence**: "every prod artifact in scope has a SLSA L3 provenance attestation, signed by an approved builder identity, recorded in Rekor, retained for N years."
- Design the attestation store and retention to answer auditor questions directly, and align your control descriptions to SSDF practice IDs so the mapping is mechanical, not narrative.

---

## Core Concept 7 — Metrics, audit, and proving the program works

Instrument the program as a product. Useful indicators:

| Metric | Why it matters |
|--------|----------------|
| Signing coverage (% artifacts signed) | Phase-0 progress; gaps = blind spots. |
| Provenance coverage (% with SLSA L3) | Maturity beyond bare signatures. |
| Audit-mode block rate & reasons | The gap list before you enforce. |
| Enforcement violations (post-cutover) | Should trend to ~zero; spikes = a real attempt or a broken pipeline. |
| Break-glass invocations | Each is a story; rising count = a policy or availability problem. |
| Verification availability / p99 latency | Have you added an outage/latency class? |

```bash
# Spot-audit: prove a running prod digest is signed + attested by an approved identity
DIGEST=ghcr.io/acme/app@sha256:5d41402abc...
cosign verify --certificate-identity-regexp='^https://github.com/acme/' \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com "$DIGEST"
cosign verify-attestation --type slsaprovenance \
  --certificate-identity-regexp='^https://github.com/acme/' \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com "$DIGEST"

# Query the transparency log for everything an identity ever signed (forensics)
rekor-cli search --email release@acme.io
```

- These numbers drive the rollout (when to enforce the next ring), justify the spend, and produce the audit evidence in Concept 6. A signing program you cannot measure is one you cannot defend in a review or an incident.

---

## Real-World Examples

- **Kubernetes & CNCF projects.** Org-wide cosign signing + SLSA provenance with published verification instructions; a template for a large multi-repo program.
- **Major OS distributions.** Long-lived HSM-protected master keys with quorum and planned rotation — the KMS/HSM end of the spectrum.
- **US federal software procurement.** Vendors submitting CISA attestation forms mapped to SSDF, with SLSA provenance as evidence.
- **Large enterprises adopting Kyverno/policy-controller.** Multi-quarter audit→enforce rollouts ringed by environment, with documented break-glass.
- **Internal Sigstore deployments.** Banks/regulated orgs running private Fulcio/Rekor to avoid public metadata exposure and external dependencies.

---

## Common Mistakes

- **Flag-day enforcement.** Turning on `Enforce` org-wide blocks legitimate deploys and burns trust. Ring it.
- **No break-glass.** Leads to ad-hoc, unaudited bypasses (disabling the controller) — worse than the original risk.
- **Unbounded identity policy.** Accepting "any identity from our org" lets any workflow sign release artifacts. Constrain to specific workflows.
- **Ignoring availability coupling.** Verification depending on un-cached Sigstore/OIDC becomes a new outage source.
- **Treating it as a tooling project, not a program.** No owners for the acceptance registry, no metrics, no retention → it rots.
- **Mistaking attestation paperwork for security.** A signed SSDF form over a weak build process is compliance theater; pair attestation with real L3/reproducibility.
- **Reinventing GPG key sprawl.** Long-lived portable keys per team recreate exactly the failures keyless was meant to fix.

---

## Apply it

1. Define the user or business outcome that **Artifact Signing & Provenance** should improve.
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

- Which measurable outcome justifies investing in Artifact Signing & Provenance?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
- Design an admission gate so a Kubernetes cluster only runs images your release pipeline produced.
- Enforcement just blocked an urgent prod hotfix because Sigstore was degraded — what do you do, and how do you prevent a repeat?
- A vendor ships an image you can't require your own identity for — how do you bring it under your trust model?
- Leadership wants signing enforced org-wide by next week — how do you push back constructively?
- Name two regulatory drivers behind artifact signing and provenance work.
