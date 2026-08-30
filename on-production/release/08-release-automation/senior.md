# Release Automation — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Release Automation** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Release Automation

*Monorepo release graphs, true idempotency and partial-release recovery, and signing in fully automated pipelines without long-lived secrets.*

---

## Core Concept 1 — Monorepo release: fixed vs independent

A monorepo holds many publishable packages. The first decision is **versioning strategy**, and it has deep ripple effects.

**Fixed (lockstep) versioning.** Every package shares one version. When *anything* releases, *everything* bumps to the new version, even untouched packages. Used by Angular, Babel (historically), Jest.

- Pros: trivial mental model ("we're on 7.4.0"); inter-package compatibility is guaranteed because everything ships together; consumers upgrade the whole suite at once.
- Cons: a package with no changes still gets a new version and a confusing "no changes" changelog entry; consumers see churn that isn't real.

**Independent versioning.** Each package versions on its own. `@org/ui` can be at 3.2.0 while `@org/utils` is at 1.9.4. Used by most npm monorepos via changesets.

- Pros: versions carry real meaning; consumers upgrade only what changed; no phantom bumps.
- Cons: you must track a compatibility matrix; a change in a shared package can require coordinated bumps across dependents (the release-graph problem below).

changesets configuration for independent versioning:

```jsonc
// .changeset/config.json
{
  "$schema": "https://unpkg.com/@changesets/config/schema.json",
  "changelog": "@changesets/changelog-github",
  "commit": false,
  "fixed": [],                  // [] = independent. e.g. [["@org/a","@org/b"]] for a fixed group
  "linked": [["@org/eslint-*"]],// linked: bump together only when one of them changes
  "access": "public",
  "baseBranch": "main",
  "updateInternalDependencies": "patch"  // bump dependents when an internal dep changes
}
```

Note `linked` — a middle ground: a group bumps together *only when one of them changes* (unlike `fixed`, which bumps even untouched members). And `updateInternalDependencies: patch` is the lever that propagates a change through the release graph.

> The choice is organizational, not just technical. Fixed suits tightly-coupled suites shipped as a unit; independent suits a platform of loosely-coupled libraries. Most large product monorepos land on independent with a few linked groups.

---

## Core Concept 2 — Affected-package detection and release graphs

In a 40-package monorepo, a PR usually touches two or three packages. Releasing all 40 is wrong: wasted builds, phantom versions, noisy changelogs. You must release **only what changed — plus everything that depends on it.**

This is a two-part problem:

**1. Direct affected detection.** Which packages have file changes since the last release? Tools compute this from git diff against the last release tag, scoped to each package's directory. Nx, Turborepo, and changesets all do a version of this:

```bash
# Nx: list projects affected by the diff between main and HEAD
npx nx show projects --affected --base=origin/main --head=HEAD
```

**2. Transitive propagation through the release graph.** If `@org/core` changed and `@org/ui` depends on `@org/core`, then `@org/ui` must also release (it ships a new `@org/core`). The dependency DAG dictates both *which* packages release and *in what order* — you must publish `@org/core` before `@org/ui` so the dependent can resolve the new version.

```
         @org/utils  (changed)
          /        \
   @org/core      @org/http
        |             |
     @org/ui      @org/client   ← all must release, in topological order
```

changesets handles propagation via `updateInternalDependencies`: when you write a changeset bumping `@org/utils`, it bumps `@org/core`, `@org/ui`, etc., as patches and orders the publish topologically. For non-JS or custom setups, you compute the affected set yourself and feed a topologically-sorted publish list.

> The release graph is why monorepo release tooling is genuinely harder than single-package: correctness requires a graph traversal, not a flag. Get the ordering wrong and a dependent publishes referencing a version that doesn't exist yet.

---

## Core Concept 3 — Idempotency engineered, not hoped

At middle tier idempotency was a principle. At senior tier you *engineer* it, because every step has a different failure-and-retry profile.

Audit each step for "what if this runs twice?":

| Step | Re-run twice → | How to make idempotent |
|------|----------------|------------------------|
| Derive version | same result | pure function of git state — naturally idempotent |
| Tag | second push fails (tag exists) | use as the guard: `git tag` failing = already released → exit 0 |
| Build | same artifacts (if reproducible) | pin toolchain; reproducible builds (see build-systems) |
| Sign | new signature each time | fine — multiple signatures are valid; or skip if signed |
| Publish to npm | **error: cannot republish** | check `npm view pkg@ver` first; skip if exists |
| Publish OCI image | overwrites tag (silent!) | use immutable tags / digest-pinning; check existence |
| Create GitHub Release | error: release exists | upsert: create-or-update by tag |
| Notify | duplicate message | idempotency key, or accept the dup (cheap) |

The pattern: **make the tag the lock.** A tag-driven pipeline where tag creation is the first irreversible act gives you a natural mutex — only one run can create a given tag, and that run owns the release. Everything downstream becomes "is this artifact already there? if so, skip; if not, do it." That conditional makes the entire pipeline safely re-runnable.

```bash
# Idempotent npm publish guard
VERSION=$(jq -r .version package.json)
if npm view "${PKG}@${VERSION}" version >/dev/null 2>&1; then
  echo "Already published ${PKG}@${VERSION}; skipping."
else
  npm publish --provenance --access public
fi
```

> Never rely on registries to enforce idempotency for you. npm refuses republish (good), but most OCI registries happily overwrite a mutable tag (dangerous). Pin to digests and check-before-write.

---

## Core Concept 4 — Partial-release recovery

The hardest real failure: the pipeline published the npm package, then the runner died before creating the GitHub Release and notifying. Now `1.5.0` is live and installable but has no release notes and no tag-asset bundle. This is a **partial release**, and recovering requires the pipeline to be *resumable*, not merely *re-runnable*.

Design for it deliberately:

1. **Make every step skip-if-done.** On re-run, each step asks "is my output already present?" The npm step sees `1.5.0` exists → skips. The tag step sees the tag → skips. The GitHub Release step sees no release → creates it. The pipeline self-heals by re-running.

2. **Order by reversibility, hardest-to-undo last.** Publishing to npm is effectively irreversible (no clean unpublish). Creating a GitHub Release is trivially reversible. So publish-to-registry should be as *late* as possible while still preceding the release object — but recognize that *some* step is always "last irreversible," and your recovery story must cover a crash right after it.

3. **Prefer many small idempotent steps over one big script.** A monolithic `release.sh` that does everything can't resume mid-way. Discrete CI steps each with a skip-guard can.

4. **Have a documented manual runbook** for the cases automation can't fix — e.g. a publish that *partially* uploaded a multi-arch image. The runbook says exactly which commands to run to complete or roll back. (Rollback specifics live in [Rollback and Roll-forward](../07-rollback-and-roll-forward/README.md).)

5. **Alert on partial state.** A release that publishes but fails to create the GitHub Release should page someone, because re-running fixes it but only if a human knows to re-run.

> The deep truth: you cannot make a distributed, multi-system release atomic. You *can* make it idempotent + resumable + observable, which is the achievable equivalent. Aim there.

---

## Core Concept 5 — Signing in automated pipelines (OIDC, no long-lived keys)

Automation removes the human who used to hold the signing key. So *where does the key come from* in an unattended pipeline? The wrong answer — a long-lived private key stored as a CI secret — is a catastrophic single point of failure: leak it and an attacker signs malware as you, forever.

The modern answer is **keyless signing via Sigstore**. The CI job proves its identity to Sigstore's Fulcio CA using its **OIDC token** (GitHub Actions mints one automatically). Fulcio issues a *short-lived* certificate (minutes) bound to that identity. cosign signs with an ephemeral key, logs the signature to the Rekor transparency log, and discards the key. There is no long-lived secret to leak.

```yaml
# Keyless cosign signing of a container image in GitHub Actions
permissions:
  contents: read
  packages: write
  id-token: write        # REQUIRED: lets the job mint an OIDC token

jobs:
  sign:
    runs-on: ubuntu-latest
    steps:
      - uses: sigstore/cosign-installer@v3
      - name: Sign image (keyless)
        env:
          COSIGN_EXPERIMENTAL: "1"
        run: |
          cosign sign --yes \
            ghcr.io/myorg/app@${{ env.IMAGE_DIGEST }}
          # identity is the workflow's OIDC token; no key files anywhere
```

Verification later checks the signature *and* that the signer identity matches your expected workflow:

```bash
cosign verify ghcr.io/myorg/app@sha256:... \
  --certificate-identity-regexp '^https://github.com/myorg/.+/.github/workflows/release.yml@.+' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

> Notice the verification pins *which workflow* may have signed. That is the payoff: the signature attests not just "a valid key" but "produced by this org's release workflow." Combined with SLSA provenance, you get a verifiable claim about exactly how the artifact was built. Full detail in [Artifact Signing and Provenance](../04-artifact-signing-and-provenance/README.md) and [Supply-chain Security](../09-supply-chain-security/README.md).

---

## Core Concept 6 — Trusted publishing to registries

The same OIDC mechanism solves the *publish* credential problem. Historically you stored an `NPM_TOKEN` / registry password as a CI secret — a long-lived credential that, leaked, lets anyone publish as you (this is exactly how several supply-chain attacks happened).

**Trusted publishing** (npm, PyPI, RubyGems, and others) replaces the stored token with OIDC. You configure the registry to trust a specific GitHub repo + workflow. At publish time, the workflow presents its OIDC token; the registry verifies it matches the configured trust and issues a short-lived publish grant. No token is stored anywhere.

```yaml
# npm trusted publishing — no NPM_TOKEN anywhere
permissions:
  contents: read
  id-token: write          # enables OIDC for npm provenance + trusted publishing

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          registry-url: https://registry.npmjs.org
      - run: npm ci
      - run: npm publish --provenance --access public
        # --provenance attaches a signed SLSA statement automatically
        # no NODE_AUTH_TOKEN / NPM_TOKEN required with trusted publishing
```

`--provenance` is a bonus: npm records *which workflow run* built and published the package, visible on the package page, giving consumers a verifiable build origin.

> This is the single highest-leverage hardening you can apply to an automated release: eliminate the long-lived publish token. It removes the most-attacked secret in the ecosystem. The `secrets-management` and `ci-cd-pipeline-design` skills both reinforce this principle — prefer ephemeral, federated identity over stored secrets everywhere.

---

## Core Concept 7 — Prereleases, channels, and backports

Real release automation isn't one stream. You ship `latest` from `main`, betas from `next`, and patch the previous major from a maintenance branch.

**Channels / dist-tags.** A channel is a named pointer consumers subscribe to. `npm install pkg` gets `latest`; `npm install pkg@next` gets the beta. Map branches to channels:

```js
// release.config.js — multi-channel semantic-release
module.exports = {
  branches: [
    "main",                                   // → latest
    { name: "next", prerelease: true },       // 2.0.0-next.1 → @next
    { name: "beta", prerelease: true },
    { name: "1.x", range: "1.x", channel: "1.x" }, // maintenance: backport fixes here
  ],
};
```

**Backports / maintenance releases.** When you're on 2.x but a customer on 1.x needs a security fix, you cherry-pick the `fix:` onto the `1.x` branch; the pipeline computes `1.7.4`, publishes it to the `1.x` channel, and `latest` stays at 2.x. This requires the tool to scope version computation to the branch's range, which the config above expresses.

> Channel design connects directly to [Release Branching and Trains](../03-release-branching-and-trains/README.md): your branch model *is* your channel model. Decide them together.

---

## Core Concept 8 — Observability of the release pipeline

You cannot operate what you cannot see. A senior-owned release pipeline emits signals like any other production system.

- **Per-step status and timing.** Which step ran, how long, pass/fail. Surfaces slow steps and flaky ones.
- **Release events as metrics.** Emit a metric on every release: version, duration, success/failure, packages released. Feed your DORA dashboards (see [Engineering Metrics and DORA](../../engineering-metrics-and-dora/)).
- **Partial-state alerts.** A page when a release reaches a partial state (published-but-no-release-object) so a human triggers recovery.
- **Audit log.** Who/what triggered the release, what identity signed it, what was published. For governed environments this is mandatory (expanded at professional tier).

```yaml
- name: Emit release metric
  if: always()
  run: |
    curl -s -X POST "$METRICS_URL/release" \
      -d "version=${VERSION}&status=${{ job.status }}&duration=${SECONDS}&repo=${{ github.repository }}"
```

> Treat "time from merge to published release" and "release failure rate" as first-class metrics. They are leading indicators of delivery health and map cleanly onto DORA's lead-time and change-failure-rate.

---

## Real-World Examples

**A 50-package design-system monorepo.** Independent versioning via changesets with three linked groups. A PR touching `@org/tokens` triggers, through the release graph, coordinated patch releases of the 12 components that consume tokens — published in topological order, each with its own changelog. The 38 untouched packages stay put. CI runs the affected build only.

**A fintech with strict supply-chain requirements.** Every release is signed keyless via Sigstore, carries SLSA Level 3 provenance, and publishes to a private OCI registry via OIDC. Zero long-lived signing keys or registry tokens exist anywhere. A monthly audit verifies every published artifact's signer identity matches the org's release workflow regex.

**A library that crashed mid-release.** The runner died after npm publish but before the GitHub Release. PagerDuty fired on the partial-state alert. The on-call simply re-ran the workflow; the npm step skipped (version exists), the release-object step created the missing release, notify fired. Total recovery: one click, because every step was skip-if-done.

---

## Common Mistakes

- **Releasing the whole monorepo on every change.** No affected detection → phantom versions, wasted builds, noisy changelogs.
- **Wrong publish order in a release graph.** A dependent published before its dependency exists; consumers can't resolve it.
- **A monolithic release script.** Can't resume after a partial failure; one crash means manual surgery.
- **Long-lived signing keys or publish tokens in CI secrets.** The catastrophic single point of failure that keyless signing and trusted publishing exist to eliminate.
- **Mutable OCI tags overwritten silently.** Two releases "succeed," consumers get different bits under the same tag. Pin to digests.
- **No partial-state alerting.** Self-healing re-run is useless if nobody knows a release is half-done.
- **Channels bolted on later.** Branch model and channel model designed separately, producing contradictions (a `1.x` fix accidentally tagged `latest`).

---

## Apply it

1. State the system invariant that **Release Automation** must protect.
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

- Which invariant must remain true when Release Automation fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
