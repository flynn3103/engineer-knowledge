# Supply-Chain Security — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Supply-Chain Security** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Supply-Chain Security
>
> *The build is the target. Make it reproducible, isolate it, prove what it produced, and verify that proof before you trust anything.*

---

## Core Concept 1 — The build is an attack surface (the SolarWinds lesson)

Restate the chain with the senior emphasis: **source → build → publish → consume.** Most defenses target source (review, signed commits) and consume (pinning, scanning). The *build* is the gap, and it is the most valuable target because:

- Whatever it emits is *automatically* trusted — it gets signed and released as a legitimate artifact.
- It has access to source, secrets, signing keys, and the network simultaneously.
- Its output reaches *every* downstream consumer at once (one compromise → fan-out to thousands).

SolarWinds is the canonical case. Attackers didn't tamper with a dependency or with published source; they implanted SUNBURST *during the build*, so Orion updates were compiled with the backdoor and then *correctly signed* with SolarWinds' own key. Customers verified the signature — it was valid — and installed a backdoor. **Signing a compromised build just gives you an authentic lie.** That's why provenance ("this came from *this* source and *this* builder") matters beyond a bare signature, and why the builder itself must be hardened.

The senior reframing: trust isn't a property of the final artifact alone. It's a property of the *whole production process*, and the build step is where production happens.

---

## Core Concept 2 — Hermetic, isolated, ephemeral builds

If a build can reach the network mid-build, pick up undeclared tools, or run on a long-lived machine that the previous job mutated, then "the same source" can produce *different* outputs — and an attacker has surfaces to persist on. Three properties close those gaps:

**Hermetic.** The build sees only its declared inputs: pinned dependencies (from your mirror/lockfile), a pinned toolchain, no arbitrary network fetches. A build that `curl`s a script mid-run is not hermetic — that's the Codecov failure mode. Tools like Bazel enforce hermeticity by construction; in less strict systems you approximate it by pre-fetching all dependencies, disabling network during the build step, and pinning the toolchain.

```dockerfile
# Approximating hermeticity in a container build:
# 1) resolve+fetch deps in a layer that is cached and reviewable
COPY go.mod go.sum ./
RUN GOFLAGS=-mod=readonly go mod download && go mod verify
# 2) build with no further network access; pinned base image by digest
COPY . .
RUN CGO_ENABLED=0 go build -trimpath -o /app ./cmd/server
```

```dockerfile
# Pin the base image by digest, not a mutable tag (see docker-best-practices)
FROM golang:1.22.3@sha256:<digest> AS build
```

**Reproducible.** Same source → bit-for-bit identical artifact, regardless of when or where. Reproducibility is the ultimate audit: an independent rebuild that yields the same hash *proves* the published artifact corresponds to the published source — it would have caught SolarWinds-style implantation. Achieve it by eliminating nondeterminism: pin everything, strip timestamps/paths (`-trimpath`, `SOURCE_DATE_EPOCH`), and avoid embedding build-host state.

**Ephemeral.** Each build runs on a freshly provisioned runner, destroyed afterward. No persistent runner means no place for an attacker to install a persistent implant that taints future builds. GitHub-hosted runners and ephemeral self-hosted runners both achieve this; long-lived shared runners are a standing risk.

Together: hermetic removes *undeclared inputs*, reproducible *proves* the output, ephemeral removes *persistence*. These are the preconditions that make provenance meaningful — provenance about a non-hermetic build on a persistent runner is a claim you can't fully trust.

---

## Core Concept 3 — Provenance: prove what was built, from what

**Provenance** is signed metadata answering: *what* artifact, built from *what* source (repo + commit), by *what* builder, with *what* inputs. It's the antidote to "authentic lie" — a valid signature says "the holder of this key signed it"; provenance says "this artifact came from commit `abc123` of `github.com/yourco/api`, built by GitHub Actions workflow `release.yml`."

Provenance is emitted as an **attestation** — a signed statement *about* an artifact, wrapped in the in-toto/DSSE envelope. The **SLSA provenance** predicate is the standard schema for build provenance. Generating it: many CI systems and the SLSA GitHub generator produce it automatically; `cosign` can attach attestations to an OCI artifact.

```bash
# Inspect/verify a provenance attestation on a container image
# (full mechanics + key/identity setup live in topic 04)
cosign verify-attestation \
  --type slsaprovenance \
  --certificate-identity-regexp '^https://github.com/yourco/.*' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  ghcr.io/yourco/api@sha256:<digest>
```

The key senior insight is *what to assert in policy*, not how the crypto works (that's [topic 04](../artifact-signing-and-provenance/README.md)): you want provenance that ties the artifact to an **expected source repo**, an **expected builder identity**, and ideally an **expected workflow** — so a build produced by anything *other* than your sanctioned pipeline fails verification, even if it's signed.

---

## Core Concept 4 — Verifying at consume time, as a gate

Provenance you generate but never check is decoration. The control is **verify-before-trust**, enforced as a *gate* that blocks anything failing verification:

- **At deploy/admission.** A Kubernetes admission controller (Sigstore policy-controller, Kyverno, or OPA/Gatekeeper) rejects images that lack a valid signature *and* provenance from your expected identity. Mechanics in [topic 04](../artifact-signing-and-provenance/README.md); the senior decision is *where the gate lives and what it asserts*.
- **At install (deps).** Verify package signatures/attestations before consuming. PyPI, npm, and others increasingly support signed attestations via **trusted publishing**.
- **In CI, before promote.** A pipeline step that runs `cosign verify-attestation` and refuses to promote build → staging → prod unless provenance matches policy.

```bash
# Gate example: refuse to promote unless provenance verifies
cosign verify-attestation --type slsaprovenance \
  --certificate-identity-regexp '^https://github.com/yourco/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  "$IMAGE" || { echo "provenance verification failed"; exit 1; }
```

The design principle: **the gate must be on the critical path and fail closed.** A verification step that logs a warning and proceeds is theater. The verifier must reject (a) unsigned artifacts, (b) artifacts signed by the wrong identity, and (c) artifacts whose provenance points at the wrong source or builder.

---

## Core Concept 5 — SLSA levels under real constraints

**SLSA** grades build integrity. The mechanics of achieving each level via signing/provenance tooling live in [topic 04](../artifact-signing-and-provenance/README.md); here's the senior decision framework — *what each level buys and what it costs*:

| Level | Roughly means | Buys you | Realistic cost |
|-------|---------------|----------|----------------|
| **L1** | Provenance exists, even if unsigned | Basic transparency; you can see how things were built | Cheap — wire your CI to emit provenance |
| **L2** | Signed provenance from a hosted build service | Tamper-evidence; provenance tied to a builder | Moderate — managed signing / OIDC keyless |
| **L3** | Hardened, isolated builder; provenance non-forgeable by build steps | Resistance to a *compromised build step* forging its own provenance | Higher — hermetic/ephemeral builders, isolation |

The senior judgment is **not** "get everyone to L3." It's: *which artifacts warrant which level?* Your internet-facing, widely-distributed release artifact deserves L3-class assurance; an internal cron job's image may be fine at L1–L2. Spend the isolation budget where the blast radius is largest. Under constraints — limited platform support, a build system that can't yet be made hermetic, a team mid-migration — a defensible plan is: L1 everywhere now, L2 on released artifacts this quarter, L3 on the crown-jewel artifacts next, with the gap explicitly tracked as risk. SLSA is a ladder to climb deliberately, not a binary to fail.

---

## Core Concept 6 — Protecting the build system and its secrets

The build holds source, secrets, *and* signing keys at once — so hardening the builder is non-negotiable. The senior checklist:

- **Two-person review on anything that reaches the build.** Require PR review (the two-person rule) on source *and* on the CI/release configuration itself. A pipeline definition that one person can edit and run is a one-person path to a signed malicious release.
- **Least privilege for the runner.** The build needs read on source and write on the artifact registry — rarely more. Scope tokens to exactly that. Don't hand the build broad cloud admin.
- **Short-lived, identity-bound secrets (OIDC).** Replace long-lived publish tokens and cloud keys with OIDC: the runner exchanges a workflow identity for a short-lived credential at job time. There's no long-lived secret to steal, which is the direct countermeasure to the Codecov pattern. (See the `secrets-management` skill.)
- **Pin your CI actions/steps by digest.** A third-party GitHub Action referenced by mutable tag (`@v4`) can be re-pointed at malicious code; pin by commit SHA. Your CI config is *also* a dependency graph.
- **Isolate the signing key.** Signing should happen in the hardened build or a dedicated signer, with keys in an HSM/KMS or keyless (Fulcio/Sigstore). The build step should be able to *request* a signature, not exfiltrate a key. (Encryption and key-management fundamentals: the `encryption-basics` skill; mechanics in [topic 04](../artifact-signing-and-provenance/README.md).)
- **Audit and monitor the pipeline.** Log who triggered what, with which inputs; alert on out-of-band builds (a release produced outside the sanctioned workflow should page someone).

The throughline: treat the CI/CD system as **production infrastructure with production-grade access controls** — because in a supply-chain sense, it *is* production.

---

## Core Concept 7 — SSDF, EO 14028, in-toto: the framework map

You'll be asked to align with frameworks. Senior-level: know what each *is for* so you can map controls, not recite acronyms.

- **NIST SSDF (SP 800-218)** — Secure Software Development Framework. A practice catalog grouped into Prepare the Organization, Protect the Software, Produce Well-Secured Software, Respond to Vulnerabilities. It's the "what good looks like" checklist that procurement and auditors map against.
- **Executive Order 14028 (2021)** — drove U.S. federal requirements that software vendors attest to secure development (per SSDF) and provide SBOMs. If you sell to the U.S. government, this is *why* SBOMs and attestations became contractual, not optional.
- **OpenSSF Scorecard** — automated scoring of a repo's security posture (branch protection, signed releases, pinned deps, fuzzing, etc.). Useful both to *measure your own* repos and to *evaluate dependencies*.
- **in-toto** — the framework for attesting *each step* of the chain cryptographically; SLSA provenance is expressed as in-toto attestations. It's the substrate under "prove every link," not a competitor to SLSA.

The map: **SSDF/EO 14028 = the policy "what," SLSA = the build-integrity grading, in-toto = the attestation substrate, Scorecard = the measurement.** They compose; they don't compete.

---

## Core Concept 8 — Sequencing a rollout you can defend

A senior doesn't boil the ocean. Sequence by leverage and blast radius:

1. **Foundation (weeks):** lockfiles enforced, scanning gated in CI, Dependabot/Renovate on, SBOMs generated and stored per release. (Mostly middle-tier, but make it *enforced*, not optional.)
2. **Build integrity (a quarter):** pin base images and CI actions by digest, move runners to ephemeral, adopt OIDC for publish/cloud (kill long-lived tokens), require two-person review on release config.
3. **Provenance (a quarter):** emit SLSA provenance, then add a **fail-closed verification gate** at promote/admission for released artifacts.
4. **Maturity (ongoing):** push crown-jewel artifacts toward L3 (hermetic builds), aim for reproducibility on critical artifacts, formalize SSDF mapping and Scorecard targets, and stand up the incident-response muscle (the professional tier).

At each step, the test is: *does this measurably reduce blast radius, and can I keep shipping?* Controls that block delivery get bypassed; controls that fail closed *and* stay fast survive.

---

## Real-World Examples

- **SolarWinds (2020).** Build-time implantation → validly signed backdoored updates → ~18,000 orgs. The case for hermetic/isolated builds, provenance beyond signatures, and reproducibility as an independent check. A signature alone would (and did) verify successfully.

- **Codecov (2021).** A tampered CI uploader script exfiltrated secrets from thousands of pipelines. The case for hermetic builds (no mid-build script fetch), OIDC short-lived secrets (nothing long-lived to steal), and least-privilege runners.

- **xz/liblzma (2024).** A social-engineered maintainer planted a backdoor *in release tarballs* that differed from the git source — a build/release-artifact discrepancy. Reproducible builds and provenance tying the artifact to reviewed source are exactly the controls that catch "the tarball doesn't match the repo."

- **Dependency confusion (2021).** Resolution preferring a public impostor over a private package. Mitigated by namespacing + private mirrors (middle tier) and verified by provenance at consume time.

- **PyPI / npm trusted publishing (OIDC) rollout.** The ecosystem's move to short-lived, identity-bound publish credentials is the standardized fix for the long-lived-token theft pattern that Codecov-style attacks exploit.

---

## Common Mistakes

- **Signing without provenance,** then believing a valid signature means a trustworthy artifact (the SolarWinds trap).
- **Generating provenance but never verifying it** — or verifying it in a step that fails open.
- **Long-lived runners and long-lived tokens** in CI, when ephemeral runners + OIDC eliminate whole attack classes.
- **Pinning deps but not CI actions/base images,** leaving a mutable `@v4` action or `:latest` base as the unpinned door.
- **Letting one person edit and run the release pipeline** — the two-person rule applies to *config*, not just app code.
- **Chasing SLSA L3 everywhere** instead of targeting the high-blast-radius artifacts and tracking the rest as risk.
- **Treating SSDF/EO 14028 as paperwork** rather than mapping real controls to it.

---

## Apply it

1. State the system invariant that **Supply-Chain Security** must protect.
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

- Which invariant must remain true when Supply-Chain Security fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
