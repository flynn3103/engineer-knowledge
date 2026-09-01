# Artifact Signing & Provenance — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Artifact Signing & Provenance** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Artifact Signing & Provenance

*From "I signed an image" to a real workflow: keyless signing in CI, attestations, and admission policies that reject anything unproven.*

---

## Core Concept 1 — Inside Sigstore: Fulcio and Rekor

Keyless signing has two pillars.

- **Fulcio** — a certificate authority that does not deal in long-lived keys:
  - cosign generates an *ephemeral* key pair in memory and presents your OIDC identity token.
  - Fulcio returns an X.509 certificate that is valid for roughly 10 minutes and embeds your identity (email, or for CI, the workflow URL) in the certificate's SAN extension.
  - cosign signs with the ephemeral private key, then throws it away. There is no key to leak, rotate, or revoke.
- **Rekor** — an append-only **transparency log**. Every signature and attestation is recorded with a timestamp and the signing certificate. This gives two things:
  1. **Non-repudiation** — there is a public, tamper-evident record that identity X signed digest D at time T.
  2. **Timestamping** — because the cert lived only minutes, you need proof the signature was made *while the cert was valid*. Rekor's countersignature provides that, so verification still works long after the cert expired.

```bash
# Inspect what was logged for an image
cosign tree registry.example.com/app@sha256:5d41402abc...
# shows signatures and attestations attached to the digest
```

- Chain of trust: *I trust the OIDC issuer to identify the signer → Fulcio to bind that identity into a cert → Rekor to prove the signature happened in-window.*

---

## Core Concept 2 — Signing from CI with workload identity

- In production the signer is a pipeline, not a person.
- GitHub Actions can mint an OIDC token that *is* the build's identity — no secret stored anywhere.

```yaml
# .github/workflows/release.yml
name: release
on:
  push:
    tags: ['v*']

permissions:
  id-token: write        # REQUIRED: lets the job request an OIDC token
  packages: write        # push to GHCR
  contents: read

jobs:
  build-sign:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: sigstore/cosign-installer@v3

      - name: Build & push
        id: build
        run: |
          IMAGE=ghcr.io/acme/app
          docker build -t $IMAGE:${GITHUB_REF_NAME} .
          docker push $IMAGE:${GITHUB_REF_NAME}
          DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' $IMAGE:${GITHUB_REF_NAME})
          echo "digest=$DIGEST" >> "$GITHUB_OUTPUT"

      - name: Sign (keyless, identity = this workflow)
        env:
          COSIGN_EXPERIMENTAL: "1"
        run: cosign sign --yes ${{ steps.build.outputs.digest }}
```

- The resulting certificate's identity is not a person — it is the workflow, e.g. `https://github.com/acme/app/.github/workflows/release.yml@refs/tags/v1.4.0`.
- That string is what consumers will later *require*. It pins not just "acme signed this" but "acme's *release* workflow, from a tag, signed this." A leaked developer laptop cannot reproduce it.

---

## Core Concept 3 — Signed vs provenance: attestations

- A plain signature answers: *did the holder of identity X vouch for digest D?* It says nothing about *how* D came to exist.
- An **attestation** is a signed statement *about* the artifact. It uses the **in-toto** envelope: a `subject` (which artifact, by digest) plus a typed `predicate` (the claim). Common predicate types:
  - **SLSA provenance** — what built this and from where.
  - **SBOM** — the software bill of materials (dependencies).
  - **Vulnerability scan** — results at build time.

```bash
# Attach an SBOM as a signed attestation
cosign attest --yes \
  --predicate sbom.spdx.json \
  --type spdxjson \
  registry.example.com/app@sha256:5d41402abc...
```

- The distinction to internalize:
  - **Signed** = integrity + a voucher. "These bytes weren't changed and X stands behind them."
  - **Provenance/attestation** = a verifiable build story. "This came from commit `abc123` of `acme/app`, built by GitHub Actions workflow `release.yml`, with these parameters."
- You want both because a signature alone cannot tell a malicious-but-authentic build from a clean one — provenance lets a verifier insist the artifact came from an *expected source and builder*.

---

## Core Concept 4 — SLSA provenance in practice

- SLSA provenance is a standardized predicate describing the build.
- The cleanest way to produce trustworthy provenance is to let the **build platform** generate it, so the values are not self-asserted by the thing being built. The SLSA project ships reusable GitHub Actions generators:

```yaml
# Use the SLSA generator to build + emit provenance for a container
jobs:
  provenance:
    permissions:
      id-token: write
      packages: write
      actions: read
    uses: slsa-framework/slsa-github-generator/.github/workflows/generator_container_slsa3.yml@v2.0.0
    with:
      image: ghcr.io/acme/app
      digest: ${{ needs.build.outputs.digest }}
```

- The provenance predicate (abbreviated) records:

```json
{
  "buildType": "https://github.com/slsa-framework/...",
  "builder": { "id": "https://github.com/acme/app/.github/workflows/release.yml@refs/tags/v1.4.0" },
  "invocation": {
    "configSource": {
      "uri": "git+https://github.com/acme/app@refs/tags/v1.4.0",
      "digest": { "sha1": "abc123..." }
    }
  }
}
```

- Now a verifier can demand: this image must have provenance whose **source repo** is `acme/app` and whose **builder** is our trusted workflow. That defeats "attacker pushed a lookalike image" because the attacker cannot produce provenance signed by *your* builder pointing at *your* source.

---

## Core Concept 5 — Verifying signatures and attestations

Verification escalates from "is it signed" to "is it signed *and* does its provenance match what I require."

```bash
# 1. Verify the signature, pinning the CI identity
cosign verify \
  --certificate-identity-regexp='^https://github.com/acme/app/' \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
  ghcr.io/acme/app@sha256:5d41402abc... | jq .

# 2. Verify a SLSA provenance attestation exists and matches
cosign verify-attestation \
  --type slsaprovenance \
  --certificate-identity-regexp='^https://github.com/acme/app/' \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
  ghcr.io/acme/app@sha256:5d41402abc...
```

- For artifacts built with the SLSA generator, `slsa-verifier` checks the provenance against expected source and builder in one step:

```bash
slsa-verifier verify-image ghcr.io/acme/app@sha256:5d41402abc... \
  --source-uri github.com/acme/app \
  --source-tag v1.4.0
```

- Note how every verify command states **expectations** (identity, issuer, source, tag). Verification with no expectations is theater; the security comes from what you *require*.

---

## Core Concept 6 — Enforcing at admission

- Manual verification does not scale. You push enforcement to the place where artifacts are *used*.
- In Kubernetes, Sigstore's **policy-controller** (or **Kyverno**) rejects pods whose images do not meet policy.

```yaml
# Sigstore policy-controller: only admit images signed by our release workflow
apiVersion: policy.sigstore.dev/v1beta1
kind: ClusterImagePolicy
metadata:
  name: require-acme-signature
spec:
  images:
    - glob: "ghcr.io/acme/**"
  authorities:
    - keyless:
        url: https://fulcio.sigstore.dev
        identities:
          - issuer: https://token.actions.githubusercontent.com
            subjectRegExp: "^https://github.com/acme/app/.github/workflows/release.yml@.*$"
```

- A pod referencing an unsigned or wrong-identity image is denied before it ever runs.
- Beyond container platforms, the same principle shows up across ecosystems: `npm audit signatures` checks installed packages' Sigstore signatures, and **Maven Central requires PGP-signed artifacts** for publication.

> Rollout wisdom: deploy in **warn/audit mode first**, watch what *would* be blocked, fix the gaps, then flip to **enforce**. Turning on hard enforcement blind will block legitimate deploys and erode trust in the control. More on sequencing at the Senior level.

---

## Real-World Examples

- **GitHub Actions + npm provenance.** Publishing with `--provenance` generates Sigstore-backed SLSA provenance; the npm registry shows a "provenance" badge and `npm audit signatures` verifies it.
- **Kubernetes with Kyverno.** Many platform teams run a Kyverno `verifyImages` rule requiring a specific keyless identity, in audit mode for weeks before enforcing.
- **Distroless / Chainguard images.** Shipped with cosign signatures and SBOM attestations consumers can verify.
- **Tekton Chains.** Automatically signs and emits provenance for artifacts built in Tekton pipelines.

---

## Common Mistakes

- **`cosign verify` without identity flags.** Accepts any Sigstore signer, including an attacker's. Always pin identity *and* issuer.
- **Confusing signed with provenance.** A signed image can still be a malicious authentic build; require provenance pinned to source + builder.
- **Self-asserted provenance.** Provenance generated *by the build artifact itself* is only as trustworthy as the artifact. Prefer builder-generated (SLSA generator, Tekton Chains).
- **Forgetting `id-token: write`.** Without it the CI job cannot get an OIDC token and keyless signing fails.
- **Enforcing on day one.** Hard-blocking before measuring breaks legitimate workloads. Audit first.
- **Pinning identity by tag only.** `subjectRegExp` should constrain the workflow path, not just the org, or any workflow in the org can sign.

---

## Apply it

1. Find a real component where **Artifact Signing & Provenance** affects an interface or dependency.
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

- Which boundary is most affected by Artifact Signing & Provenance?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
- Walk through keyless signing with cosign — what roles do Fulcio and Rekor play?
- How do you sign an artifact from CI without storing a long-lived secret?
- What's the difference between `cosign sign` and `cosign attest`?
- What does `permissions: id-token: write` enable in a GitHub Actions workflow?
- What does an in-toto attestation contain?
- Why is builder-generated provenance more trustworthy than provenance the build script writes about itself?
