# Artifact Signing & Provenance — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Artifact Signing & Provenance** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Artifact Signing & Provenance

*SLSA levels as an attack-defeat ladder, reproducible builds as a trust primitive, and a clear-eyed threat model of what signing does and does not buy you.*

---

## Core Concept 1 — SLSA Build levels as defeated-attack ladder

SLSA's value is that each level is defined by the *attacks it forecloses*. Reason about it as a ladder, not a score.

- **Build L1 — provenance exists, build is scripted.**
  - The build runs from a script (no manual `docker build` on a laptop) and emits provenance describing how.
  - Defeats: *"nobody knows how this was built."*
  - Does **not** stop tampering — the provenance can be forged because nothing authoritative signs it.
- **Build L2 — provenance is signed by a hosted build service.**
  - A hosted, version-controlled build platform generates and *signs* provenance, tied to a builder identity.
  - Defeats: *forged provenance* and *"I built it on my machine and lied about it."*
  - Does **not** stop a build that is itself influenced by the thing being built (a malicious `Makefile`, a poisoned dependency executing at build time).
- **Build L3 — hardened, isolated builder; non-falsifiable provenance.**
  - The builder runs each build in isolation so one build cannot influence another or forge another's provenance; secret material used to sign provenance is inaccessible to user-defined build steps.
  - Defeats: *cross-build contamination*, *provenance forgery by the build itself*, *exfiltration of the provenance-signing key by build code.*
  - This is the level where provenance becomes genuinely *non-falsifiable by the user*.

```bash
# Verify you actually received L3-grade, builder-signed provenance
slsa-verifier verify-image ghcr.io/acme/app@sha256:5d41402abc... \
  --source-uri github.com/acme/app \
  --builder-id "https://github.com/slsa-framework/slsa-github-generator/.github/workflows/generator_container_slsa3.yml@refs/tags/v2.0.0"
```

- What *no* Build level addresses: a compromised **source repo** (the commit itself is malicious) and a malicious **dependency** pulled in legitimately. Those are different threat surfaces — see Supply-Chain Security.

---

## Core Concept 2 — The threat model: what signing does NOT protect against

State the boundary explicitly. Signing + provenance defeats:

- A compromised **registry/CDN/mirror** swapping bytes (integrity).
- An attacker **publishing a lookalike** artifact under your namespace (origin, via pinned identity).
- **Forged build metadata** (at L2/L3).

It does **not** defeat:

| Threat | Why signing misses it |
|--------|-----------------------|
| Malicious-but-authentic build | The harmful artifact is signed correctly by your real workflow. Authentic ≠ safe. |
| Compromised source commit | Provenance faithfully records the source — including the attacker's commit. |
| Poisoned dependency | The dep is genuinely part of the declared build; provenance vouches for it. |
| Compromised builder (full takeover) | If the builder is owned, it signs whatever the attacker wants, truthfully. |
| Trusted insider with signing identity | They are, by definition, an allowed signer. |
| A *bug* you shipped | Signing has no opinion on correctness. |

- The SolarWinds attack is the canonical illustration: the *build system* was subverted, so malicious updates were *correctly signed* and passed every signature check downstream. The defense there is not "more signatures" — it is **L3 builder hardening, reproducible builds, and source controls**, narrowing how the build can be subverted in the first place.
- Senior takeaway: present signing as **one layer**. It collapses the "transport and storage" attack surface to near zero and makes provenance auditable, but the *source → build* surface needs separate controls.

---

## Core Concept 3 — Reproducible builds as a trust primitive

- A signature says "*I* built these bytes." A **reproducible build** says "*anyone* can rebuild the same bytes from the same source and check." That is qualitatively stronger: it converts trust in *you* into independently verifiable fact.
- A build is reproducible when identical sources plus a recorded environment yield **bit-for-bit identical output**. The enemy is non-determinism. Usual sources and fixes:
  - **Embedded timestamps** → honor `SOURCE_DATE_EPOCH`.
  - **Absolute build paths** baked into binaries → strip/remap (`-ffile-prefix-map`, Go's `-trimpath`).
  - **Non-deterministic ordering** (map iteration, parallel output, archive member order) → sort; use deterministic archivers.
  - **Locale / timezone / hostname / `umask`** leaking in → pin in the build environment.
  - **Unpinned dependencies** → lockfiles + content-addressed fetches.

```bash
# Go: trim paths and pin the build timestamp
export SOURCE_DATE_EPOCH=$(git log -1 --format=%ct)
go build -trimpath -buildvcs=false -o app ./cmd/app
sha256sum app   # should match an independent rebuild on the same toolchain
```

```bash
# Reproducibility check: build twice, compare digests
sha256sum app && (cd /tmp/clean && go build -trimpath -o app2 ./cmd/app && sha256sum app2)
# diffoscope shows WHAT differs if they don't match
diffoscope app app2
```

- Reproducibility lets a verifier rebuild and compare, turning "trust the publisher" into "verify the publisher." It is the trust primitive behind Debian's reproducible-builds effort and a strong complement to SLSA: provenance says *how* it was built; reproducibility lets you *check the claim*.

---

## Core Concept 4 — Hardened, isolated builders

Build L3 demands a builder where:

- Each build is **isolated** — no shared mutable state, no ability to read or tamper with another build.
- The **provenance-signing material is unreachable** from user build steps. If `make` could read the signing key, malicious build code could mint false provenance.
- The build definition is **version-controlled and immutable** for a given run.

- Practical realizations: GitHub Actions reusable workflows used via the SLSA generator (the signing happens in a context the job's own steps cannot touch), Google Cloud Build with provenance, Tekton Chains with isolated task pods.
- The common thread: **separation between "code under build" and "the authority that signs the provenance."**
- Pair this with **hermetic builds** — no network during the build, all inputs pinned and content-addressed — so the build cannot pull in unrecorded, mutable inputs. Hermeticity is what makes provenance *complete*; isolation is what makes it *trustworthy*.

---

## Core Concept 5 — Verification policy as code

At scale, verification rules live in version control and are enforced by an engine, not by tribal command-line knowledge. Kyverno expresses rich policy:

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-signed-and-attested
spec:
  validationFailureAction: Audit   # flip to Enforce after a soak period
  webhookTimeoutSeconds: 30
  rules:
    - name: verify-acme
      match:
        any:
          - resources: { kinds: [Pod] }
      verifyImages:
        - imageReferences: ["ghcr.io/acme/**"]
          failurePolicy: Fail
          attestors:
            - entries:
                - keyless:
                    subject: "https://github.com/acme/app/.github/workflows/release.yml@*"
                    issuer: "https://token.actions.githubusercontent.com"
                    rekor:
                      url: https://rekor.sigstore.dev
          attestations:               # require SLSA provenance too, not just a signature
            - type: https://slsa.dev/provenance/v1
              attestors:
                - entries:
                    - keyless:
                        subject: "https://github.com/acme/app/.github/workflows/release.yml@*"
                        issuer: "https://token.actions.githubusercontent.com"
              conditions:
                - all:
                    - key: "{{ regex_match('^github.com/acme/app$', '{{ buildDefinition.externalParameters.source.uri }}') }}"
                      operator: Equals
                      value: true
```

- Policy-as-code gives you review, diff, rollout staging (`Audit` → `Enforce`), and a single source of truth.
- Treat the policy repo like any other production code: PRs, tests against known-good and known-bad images, and a break-glass path (see Professional level and the **quality-gates** topic).

---

## Core Concept 6 — Trust roots and revocation under keyless

Keyless removes per-publisher keys but does not remove *trust roots*. A verifier ultimately trusts:

- **Fulcio's root CA** — to mean its certificates are legitimately identity-bound.
- **Rekor's key** — to mean log entries are authentic.
- The **OIDC issuer** — to mean an identity assertion is real.

- Sigstore distributes and rotates these via **TUF (The Update Framework)**, which provides secure, rotatable, replay-resistant root distribution. `cosign initialize` fetches/refreshes the TUF root; air-gapped or high-assurance orgs may run their **own Sigstore stack** (private Fulcio/Rekor) and pin their own root.

```bash
# Refresh the trust root (public good instance)
cosign initialize

# Or pin a private/own trust root bundle
cosign verify --trusted-root=trusted_root.json ...
```

- **Revocation** works differently than with long-lived keys. There is no "revoke this key" because the key lived minutes. Instead you respond by **tightening verification policy**: if a workflow or identity is compromised, you stop *accepting* its signatures (narrow the allowed identity/issuer, or cut off a time window using Rekor timestamps).
- The Rekor log is also how you *audit* what a compromised identity signed and when. This is a different operational mindset — you manage *acceptance policy*, not key lifecycles.

---

## Core Concept 7 — Designing the verification gate under constraints

Real gates run under constraints: latency budgets, registry availability, air-gap, false-positive tolerance.

- **Availability of Sigstore services.** Verification touches Rekor/Fulcio roots. Cache the TUF root, consider an internal Rekor mirror, and decide your **fail-open vs fail-closed** stance per environment (fail-closed in prod; perhaps fail-open with alerting in a low-risk dev cluster).
- **Latency at admission.** Image verification adds time to pod admission. Pre-verify in the pipeline and **resolve tags to digests at deploy**, so admission verifies a digest you already proved, not a re-resolved tag.
- **Air-gapped environments.** Mirror signatures and attestations alongside images; run a private Sigstore or pre-verify at import and re-sign with an internal identity.
- **Third-party images.** You often *cannot* require *your* identity. Strategy: re-verify the vendor's signature at import, then **re-attest with your own identity** ("we vetted this"), and have prod require *your* attestation. This gives a uniform internal trust root.
- **Gradual tightening.** Start by requiring a signature; add provenance; then add source/builder constraints. Each step is a separate, measurable rollout.

The senior skill is choosing *where in the lifecycle* verification happens (build, import, admission, runtime) and *what to require at each*, balancing assurance against availability and operational cost.

---

## Real-World Examples

- **SolarWinds (2020).** Subverted build pipeline produced correctly-signed malicious updates — the textbook case for L3 + reproducible builds over "just sign it."
- **Debian Reproducible Builds.** A large-scale effort proving the published binaries match the source, independently of the maintainers.
- **Chainguard / Wolfi.** Images shipped with SLSA provenance and SBOM attestations, built on hardened builders.
- **Kubernetes project signing.** Release artifacts are cosign-signed and provenance-attested; consumers can verify with `slsa-verifier`.
- **Go module checksum database.** A transparency-log model (`sum.golang.org`) ensuring everyone sees the same module bytes — provenance thinking applied to dependencies.

---

## Common Mistakes

- **Selling signing as "now we are secure."** It is one layer; name the residual threats (malicious-but-authentic, compromised source/builder, insiders).
- **Requiring provenance but not constraining its contents.** Demand the *source URI* and *builder ID*, not merely "some provenance exists."
- **Ignoring builder isolation.** L1/L2 provenance from a builder where build steps can reach the signing key is forgeable.
- **Assuming reproducibility for free.** Timestamps, paths, and ordering silently break it; you must engineer determinism and *test* it (build twice, diffoscope).
- **No fail-open/fail-closed decision.** Treating Sigstore availability as guaranteed makes verification a new outage source.
- **Forgetting revocation is policy, not keys.** When an identity is compromised, you tighten acceptance and audit Rekor — there is no key to revoke.

---

## Apply it

1. State the system invariant that **Artifact Signing & Provenance** must protect.
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

- Which invariant must remain true when Artifact Signing & Provenance fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
- How do SLSA Build levels L1, L2, and L3 differ in the attacks each one defeats?
- A registry is fully compromised — what does signing protect against, and what does it not?
- Why are reproducible builds a stronger trust primitive than signing alone?
- How does revocation work under keyless signing, since there's no long-lived key to revoke?
- What does Rekor provide that a bare signature does not?
