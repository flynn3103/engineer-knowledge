# Registries & Distribution — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Registries & Distribution** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Registries & Distribution

*Immutability, digests, and the rules for pulling a bad release without breaking the world.*

---

## Core Concept 1 — Immutability is the contract

- The single most important property of a good registry: **a published version is immutable.**
- Once `express@4.18.2` exists, those exact bytes are what `4.18.2` means — forever, for everyone.

Why this is non-negotiable:

- **Reproducibility.** A `package-lock.json` or `go.sum` records a version (and hash). If the registry could change the bytes behind that version, the lockfile would be a lie and "works on my machine" would become "works on the machine that downloaded it before it changed."
- **Caching.** Every CI runner, CDN, and mirror caches by coordinate. If bytes could change under a fixed coordinate, caches would serve stale-but-different content with no way to know.
- **Security.** Supply-chain attacks thrive on mutable coordinates. If an attacker can replace the bytes behind a version you already trust, they win silently.

This is why **republishing the same version is forbidden** almost everywhere:

```bash
npm publish        # npm: 403 — "cannot publish over previously published version"
cargo publish      # crates.io: "crate version X.Y.Z already exists"
mvn deploy         # Maven Central: a released version can never be overwritten or deleted
```

- The fix is never "force overwrite." It's **publish a new version**.
- Immutability is a feature, not an obstacle.

## Core Concept 2 — Tags vs digests, in practice

- OCI registries layer a *mutable* naming system (tags) on top of *immutable* content (digests).
- Understanding the split is what separates reliable deployments from flaky ones.
- An image's true identity is its **manifest digest**: `sha256:9b2c...`.
- A **tag** (`1.4.0`, `latest`, `prod`) is just a pointer in a table: tag → digest. You can repoint it any time.

```bash
# Resolve a tag to its current digest
docker buildx imagetools inspect ghcr.io/acme/api:1.4.0
#  Name:      ghcr.io/acme/api:1.4.0
#  Digest:    sha256:9b2c4e...a17

# Deploy by digest so the running thing can never drift
kubectl set image deploy/api api=ghcr.io/acme/api@sha256:9b2c4e...a17
```

> Rule of thumb: **build and promote by tag; deploy and depend by digest.** Tags are for humans choosing what to ship. Digests are for machines guaranteeing what runs.

The same idea exists in language ecosystems via integrity hashes:

```jsonc
// package-lock.json
"node_modules/left-pad": {
  "version": "1.3.0",
  "integrity": "sha512-XI5MPzVNApjAyhQzphX8BkmKsKUxD4LdyK24iZeQGinBN9yTQT3bFlCBy/aVx2HrNcqQGsdot8ghrjyrvMCoEA=="
}
```
```
# go.sum — module + version + hash, verified on every download
github.com/acme/toolkit v0.5.0 h1:abc123...=
```

- If the bytes ever changed, the recorded hash would no longer match and the tool would refuse the download.
- The hash *is* a digest by another name.

## Core Concept 3 — The `latest` trap

- `latest` is not "the newest version." It is a **plain tag with no special meaning**.
- By convention, people repoint it to whatever they consider current — which creates three traps:

1. **It moves.** `docker pull app:latest` today and tomorrow can return different bytes. Caches make it worse — a node may have an old `latest` and never re-pull because the tag name didn't change.
2. **It hides what's running.** `kubectl describe pod` showing `image: app:latest` tells you nothing about *which* build is live. You lose the ability to correlate an incident with a commit.
3. **It defeats rollbacks.** "Roll back to the previous `latest`" is meaningless — the previous bytes may be gone or unidentifiable.

```bash
# Anti-pattern
docker pull myapp:latest
kubectl set image deploy/app app=myapp:latest

# Better — explicit version, pinned by digest for production
kubectl set image deploy/app app=myapp@sha256:9b2c4e...a17
```

- Use `latest` (or no tag) only for throwaway local experiments.
- Production references a specific version, ideally a digest.
- Configure `imagePullPolicy: IfNotPresent` *only* with digests or immutable tags — never with a moving tag, or you'll get inconsistent nodes.

## Core Concept 4 — Yank, deprecate, unpublish: not the same thing

- When a release is bad — a regression, a leaked secret, a vulnerable dependency — you need to pull it back.
- The mechanism differs sharply by ecosystem.
- **Picking the wrong one either breaks everyone or fails to protect anyone.**

**Yank (crates.io, PyPI).** A yank is *soft*:

- The version stays downloadable, so **existing builds and lockfiles keep working**.
- It can no longer be *newly selected* by a resolver.

```bash
cargo yank --version 1.2.3          # can't be added as a new dependency
cargo yank --version 1.2.3 --undo   # reverse it
```
- PyPI's equivalent is **PEP 592 yank**: a yanked release is ignored by resolvers *unless* a pin requests it exactly (`==1.2.3`).
- This is the right tool for "this version is broken, stop new adoption, don't break existing users."

**Deprecate (npm).** Deprecation is *advisory*:

- The package still installs, but every install prints your warning.
- Nothing breaks.

```bash
npm deprecate mypkg@"<1.2.4" "Has a memory leak; upgrade to 1.2.4+"
npm deprecate mypkg "Whole package unmaintained; use @scope/new-pkg"
```

**Unpublish (npm) — the dangerous one.** Unpublish actually *removes* the bytes.

- This is the [left-pad incident](https://en.wikipedia.org/wiki/Npm_left-pad_incident) of March 2016: a single developer unpublished `left-pad`, an 11-line package, and broke thousands of builds worldwide because everyone's installs suddenly 404'd.
- npm responded by **heavily restricting unpublish**: you can only fully unpublish within **72 hours** of publishing, and only if nothing depends on it; older versions require contacting support and meeting strict criteria.
- The lesson: deletion breaks the immutability contract that other people's builds rely on, so registries make it nearly impossible.

**Maven Central — immutable, period.**

- You *cannot* delete or overwrite a released artifact on Maven Central.
- A bad release is fixed only by publishing a new version (e.g. `1.2.4`) and, if needed, marking the old one deprecated in docs.
- There is no yank, no unpublish.

| Mechanism | Existing builds | New adoption | Bytes removed? | Use when |
|-----------|-----------------|--------------|----------------|----------|
| **Yank** (crates/PyPI) | keep working | blocked | no | broken/insecure version, don't break current users |
| **Deprecate** (npm) | keep working (warned) | allowed (warned) | no | discouraged but not dangerous |
| **Unpublish** (npm, <72h) | break (404) | blocked | yes | mistaken publish, caught fast, nothing depends on it |
| **New version only** (Maven) | keep working | should move | never | the only option on immutable registries |

> Decision rule for a *security* incident: **yank/deprecate the bad version, publish a fixed one immediately, and only unpublish if the bytes themselves are dangerous and you're inside the window.** Removing bytes that others depend on turns your incident into everyone's incident.

## Core Concept 5 — Publish mechanics with provenance and 2FA

Real publishing in a team adds three things on top of the bare command:

- **Two-factor auth**
- **Scoped packages/namespaces**
- **Provenance**

**npm with provenance and 2FA:**
```bash
# Scoped package: name is @acme/widgets, owned by the acme org's namespace
npm publish --access public --provenance   # provenance requires a supported CI (e.g. GitHub Actions w/ OIDC)
```
- `--provenance` makes npm attach a signed statement linking the tarball to the exact GitHub repo, commit, and workflow that built it — visible as a "published via" badge.
- 2FA (or an automation token with 2FA policy) gates who may publish at all.

**PyPI with trusted publishing (OIDC):** instead of a long-lived `twine` token, configure a *trusted publisher* so CI authenticates via short-lived OIDC and uploads with no stored secret:
```yaml
# GitHub Actions
- uses: pypa/gh-action-pypi-publish@release/v1   # no password — uses OIDC trusted publishing
```

**Maven Central staging → release:**

- `mvn deploy` uploads to a *staging* repository (a temporary, private holding area).
- You then **close** the staging repo (Sonatype runs validation: signatures, POM completeness, javadoc/sources) and **release** it, which promotes it to Central.
- This two-phase flow exists precisely because Central is immutable — staging is your last chance to catch a bad artifact before it becomes permanent.

These all connect to signing — see [Artifact Signing & Provenance](../artifact-signing-and-provenance/middle.md). Provenance answers "where did this come from"; signing answers "prove it wasn't tampered with."

## Core Concept 6 — Retention, untagged layers, and garbage collection

- Registries fill up: every CI run pushes new image tags, old layers pile up, and storage bills climb.
- Two cleanup concepts matter: untagged manifests and retention policies.

**Untagged manifests.**

- When you repoint a tag (e.g. push a new `1.4.0`... which you shouldn't, but `latest` you do), the old manifest may become *untagged* — no tag references it, but it's still stored.
- Untagged manifests and their layers are GC candidates.

**Retention policies.** Most registries let you auto-delete by rule. Example GHCR / generic patterns:

- Keep the last *N* versions per repo.
- Delete untagged manifests older than *X* days.
- **Never** auto-delete tags matching a release pattern (e.g. `v*` or semver) — those are referenced by deployments.

```bash
# Example: delete untagged ECR images older than 14 days, keep all release tags
aws ecr put-lifecycle-policy --repository-name api --lifecycle-policy-text '{
  "rules": [{
    "rulePriority": 1,
    "selection": {"tagStatus": "untagged", "countType": "sinceImagePushed",
                  "countUnit": "days", "countNumber": 14},
    "action": {"type": "expire"}
  }]
}'
```

> The classic mistake: a retention rule that deletes "old" images by age, sweeping away an LTS release that production still pins by digest. **Protect release tags explicitly; only auto-expire untagged or CI-scratch tags.** See the `caching-strategies` skill for how cached pulls interact with deletion.

## Real-World Examples

**Example 1 — Bad version, contained correctly.** `acme-client 2.4.0` leaks a token in its build output. The team: (1) `npm deprecate acme-client@2.4.0 "Security: upgrade to 2.4.1"`, (2) publishes `2.4.1` immediately, (3) rotates the leaked token. They do *not* unpublish — existing pinned users keep working, and the warning steers everyone forward.

**Example 2 — Deploy drift from `latest`.** A team deployed `app:latest`. Three nodes had a 2-day-old `latest` cached and never re-pulled; two had the new one. Half the fleet ran old code. Fix: deploy `app@sha256:...` and the inconsistency became impossible.

**Example 3 — Maven, no take-backs.** A library is released to Central with a broken `pom.xml` dependency. It cannot be deleted. The maintainer ships `3.1.1` with the fix, marks `3.1.0` deprecated in the README and a GitHub release note, and moves on — there is no other option.

## Common Mistakes

- **Trying to "fix" a released version in place.** Immutable registries reject it; mutable ones that allow it corrupt everyone's caches. Always ship a new version.
- **Unpublishing to "fix" a bug.** It breaks downstream builds (the left-pad lesson). Deprecate or yank, then publish a fix.
- **Confusing yank with delete.** Yank keeps existing builds working *on purpose*. If you delete instead, you turn a quiet fix into an outage.
- **Deploying mutable tags to production.** `latest` and even moving release tags cause node drift. Pin digests.
- **Retention rules that don't exempt release tags.** Age-based cleanup can delete an image production still runs.
- **Long-lived publish tokens.** Use trusted publishing / OIDC where available so there's no secret to leak.

---

## Apply it

1. Find a real component where **Registries & Distribution** affects an interface or dependency.
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

- Which boundary is most affected by Registries & Distribution?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
- How do you deploy so you're certain exactly which bytes are running?
- How does trusted publishing work, and why is it safer than a long-lived publish token?
- What's the difference between provenance and an SBOM, and where do they live?
- Explain the difference between yank, deprecate, and unpublish.
- What happened in the left-pad incident, and what did it change?
- Can you delete a release from Maven Central? What do you do instead?
