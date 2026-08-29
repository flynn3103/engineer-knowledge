# Release Automation — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Release Automation** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Release Automation

*The full pipeline shape, the conventional-commit contract that drives it, and a clear map of which tool fits which language and team.*

---

## Core Concept 1 — The full pipeline, step by step

A complete release pipeline is a chain of steps where the output of each feeds the next. Knowing what each does — and how it fails — is the core skill of this tier.

```
┌──────────────────────────────────────────────────────────────┐
│ TRIGGER:  push to main   OR   push of a tag   OR   manual run  │
└──────────────────────────────────────────────────────────────┘
        │
        ▼
1. DERIVE VERSION      read commits since last tag → compute next SemVer
        │             failure: no releasable commits → exit cleanly (not an error)
        ▼
2. GENERATE CHANGELOG  group commits by type into release notes
        │             failure: malformed commits → ugly notes
        ▼
3. TAG                 create annotated git tag vX.Y.Z, push it
        │             failure: tag already exists → STOP (idempotency guard)
        ▼
4. BUILD ARTIFACTS     compile / package for all targets
        │             failure: build error → release aborts, nothing published
        ▼
5. SIGN + ATTEST       cosign signature + SLSA provenance
        │             see ../04-artifact-signing-and-provenance/
        ▼
6. PUBLISH             upload to npm / OCI registry / package index
        │             failure mid-publish → PARTIAL RELEASE (the hard case)
        ▼
7. CREATE RELEASE      GitHub/GitLab Release with notes + assets
        │
        ▼
8. NOTIFY              Slack / email / status page update
```

Three design principles run through every step:

- **Idempotent.** Re-running the pipeline must not double-publish. The tag-exists check at step 3 and the version-exists check at step 6 are the guards.
- **Observable.** Each step emits clear logs; a failed release tells you exactly which step and why.
- **Fail-closed early.** Cheap, reversible steps (version, build) come before expensive, irreversible ones (publish). You want failures *before* anything reaches users.

The ordering is not arbitrary: you compute and build everything *before* you publish anything, so a build failure never leaves a half-released version in the wild.

---

## Core Concept 2 — Conventional commits as a contract

Conventional Commits is not a style preference — it is a **machine-readable contract** between developers and the release tool. The developer's promise: "I will describe each change's type accurately." The tool's promise: "I will compute the correct version and a complete changelog." Break the first promise and both break.

The grammar:

```
<type>[(scope)][!]: <description>

[body]

[footer(s)]   ← e.g. "BREAKING CHANGE: ...", "Refs: #123"
```

Mapping to behavior:

| Commit | Bump | Changelog section |
|--------|------|-------------------|
| `feat: ...` | MINOR | Features |
| `fix: ...` | PATCH | Bug Fixes |
| `perf: ...` | PATCH | Performance |
| `feat!: ...` or `BREAKING CHANGE:` footer | MAJOR | ⚠ BREAKING |
| `refactor:`, `chore:`, `docs:`, `test:`, `ci:`, `style:` | none | (hidden by default) |

**The discipline cost is real and worth naming.** Every developer must learn the format. PRs get nitpicked over commit types. New hires get it wrong. Some teams resent it. The payoff: versions and changelogs that are *always correct* and *never hand-maintained*, plus a commit history that reads like documentation. For most teams shipping frequently, the trade is decidedly worth it.

**Squash-merge as the source of truth.** Many teams squash-merge PRs. In that model, individual commits inside the PR don't matter — only the **squash commit title** does, and that's usually the PR title. So the contract shifts: the *PR title* must be a conventional commit. Enforce it with a PR-title linter rather than per-commit linting. This is often easier to adopt than asking everyone to write every commit perfectly.

---

## Core Concept 3 — Enforcing the contract with commitlint

A contract nobody enforces is a suggestion. [commitlint](https://commitlint.js.org/) validates commit messages against the Conventional Commits spec and rejects bad ones.

`commitlint.config.js`:

```js
module.exports = {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "type-enum": [2, "always", [
      "feat", "fix", "perf", "refactor",
      "docs", "test", "ci", "chore", "build", "revert",
    ]],
    "subject-case": [2, "never", ["upper-case", "pascal-case"]],
    "header-max-length": [2, "always", 100],
  },
};
```

Run it locally via a git hook (using husky):

```bash
npx husky init
echo 'npx --no -- commitlint --edit "$1"' > .husky/commit-msg
```

And — more importantly, because local hooks can be bypassed — enforce it in CI on the PR title:

```yaml
# .github/workflows/pr-lint.yml
name: PR Title Lint
on:
  pull_request:
    types: [opened, edited, synchronize]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: amannn/action-semantic-pull-request@v5
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

> Make the CI check a **required status check** (branch protection) so a non-conforming title literally cannot merge. Local hooks improve the developer experience; the CI gate is what actually guarantees the contract. See Quality Gates for required-check design.

---

## Core Concept 4 — The release-PR model (release-please)

`semantic-release` releases on *every* qualifying merge. Some teams want releases to be deliberate — a human decides *when* to cut, even though *what* goes in is still automatic. That is the **release-PR model**, exemplified by Google's [release-please](https://github.com/googleapis/release-please).

How it works:

1. You merge feature PRs to `main` with conventional commits. Nothing is released yet.
2. release-please opens (and keeps updating) a **"chore: release 1.4.0"** PR that accumulates the computed version bump and the generated changelog.
3. When you're ready to ship, you **merge the release PR**. *That* merge tags, builds, and publishes.

```yaml
# .github/workflows/release-please.yml
name: release-please
on:
  push:
    branches: [main]
permissions:
  contents: write
  pull-requests: write
jobs:
  release-please:
    runs-on: ubuntu-latest
    steps:
      - uses: googleapis/release-please-action@v4
        id: release
        with:
          release-type: node
      # Only build + publish AFTER the release PR is merged:
      - uses: actions/checkout@v4
        if: ${{ steps.release.outputs.release_created }}
      - run: npm ci && npm publish
        if: ${{ steps.release.outputs.release_created }}
```

The release PR is a genuinely nice artifact: a reviewable, mergeable preview of exactly what the next version and changelog will be. It gives you an approval point and an audit trail without forcing humans to compute versions. The trade-off versus semantic-release: releases are less continuous (they happen when someone merges the PR, not automatically).

---

## Core Concept 5 — Choosing a tool

There is no universal best tool. Match the tool to your language and your release cadence.

| Tool | Ecosystem | Model | Best for |
|------|-----------|-------|----------|
| **semantic-release** | JS/npm (any via plugins) | Fully automatic on merge | Single package, continuous release, no human gate |
| **release-please** | Multi-language | Release PR (human merges) | Teams wanting an approval point + audit trail |
| **changesets** | JS monorepo | Human-authored intent files | Monorepos, multi-package, deliberate version intent |
| **goreleaser** | Go | Tag-driven | Go binaries: cross-compile, archive, Homebrew, sign |
| **cargo-release** | Rust | Command-driven | Rust crates published to crates.io |
| **Maven Release Plugin / Gradle** | JVM | Plugin-driven | Java/Kotlin artifacts to Maven Central |
| **Raw GitHub Actions** | Any | Hand-built | Custom flows the above can't express |

**changesets** deserves a closer look because it inverts the model. Instead of inferring intent from commits, contributors *declare* it by adding a markdown "changeset" file in their PR:

```markdown
---
"@myorg/ui": minor
"@myorg/utils": patch
---

Add `<Tooltip>` component and fix focus-trap edge case in `<Modal>`.
```

This file says: bump `@myorg/ui` a minor, `@myorg/utils` a patch, with this note. At release time, `changeset version` consumes all such files, bumps each package independently, and writes per-package changelogs. The explicit intent is a feature: in a monorepo where one PR touches several packages, commit-message inference is too coarse — a human stating "this PR is a minor for X, a patch for Y" is clearer and reviewable.

> Decision shortcut: **Go → goreleaser. Rust → cargo-release. JVM → Maven/Gradle. JS single package → semantic-release. JS/any monorepo → changesets. Want a human approval gate → release-please.**

---

## Core Concept 6 — Idempotency and tag-driven triggers

The scariest release bug is the **double publish** or the **partial release**. Idempotency is the property that protects you.

**Tag-driven triggers** are the cleanest way to get idempotency. The release runs only when a tag is pushed, and the tag *is* the version. A tag can only exist once, so the release for that version can only be initiated once:

```yaml
on:
  push:
    tags: ["v*"]
```

Compare with push-to-main triggers (semantic-release), which need an *internal* guard: before publishing, the tool checks whether that version already exists on the registry and on the git tags. If it does, it exits cleanly. Both approaches achieve idempotency; tag-driven makes it structural rather than logical.

**The "release is just CI" model and its limits.** It is liberating to treat a release as just another CI job. But the model has limits that distinguish a release from a normal build:

- A normal CI job is *fully* idempotent — rerun it freely. A release publishes *side effects to the outside world* (npm, a registry, a GitHub Release) that can't always be cleanly undone.
- npm forbids republishing a version (and unpublish is heavily restricted). Container registries may allow overwriting a tag — which is its own danger.
- A failure *between* publishing to the registry and creating the GitHub Release leaves a **partial release**: the package is live but undocumented. Recovery means re-running only the remaining steps, which requires the pipeline to be resumable, not just rerunnable.

So: design every step to be idempotent, order irreversible steps last, and have a documented recovery for partial releases (covered at senior tier).

---

## Real-World Examples

**A React component library on npm.** Team uses changesets. Every PR that changes a component includes a changeset file describing the bump. The CI opens a "Version Packages" PR; merging it bumps versions, writes per-package changelogs, and publishes to npm. Contributors love that the changelog is written in plain English by whoever made the change, not auto-generated from terse commits.

**A Go microservice.** Tag-driven goreleaser. `git tag v3.2.0 && git push --tags` triggers a build of multi-arch container images, signs them with cosign, generates SBOM and provenance, pushes to the org's OCI registry via OIDC (no stored credentials), and cuts a GitHub Release. Four minutes, fully reproducible.

**A platform team's API server.** release-please. Engineers merge `feat:`/`fix:` PRs all week. A standing release PR shows the accumulating 2.5.0 changelog. On Tuesday's release window, the on-call merges the release PR; that triggers the build, sign, publish, and deploy. The approval point satisfies the change-management policy.

---

## Common Mistakes

- **No enforcement.** Adopting Conventional Commits as a "guideline" without commitlint and a required PR-title check. It decays within weeks.
- **Wrong tool for the topology.** Using semantic-release in a monorepo and fighting it forever. Reach for changesets.
- **Overwriting tags or registry versions.** Treating a release like a rerunnable build. Some registries let you; you'll regret it (consumers cached the old bits).
- **Irreversible step too early.** Publishing before all artifacts are built, so a later build failure leaves a partial release.
- **Ignoring squash-merge reality.** Linting individual commits while squash-merging — only the PR title survives. Lint the title.
- **No dry run in CI.** Every tool supports a snapshot/no-publish mode; run it on PRs to catch config errors before they reach `main`.

---

## Apply it

1. Find a real component where **Release Automation** affects an interface or dependency.
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

- Which boundary is most affected by Release Automation?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
