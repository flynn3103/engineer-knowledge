# Changelogs & Release Notes — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Changelogs & Release Notes** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Changelogs & Release Notes

> *The format is easy. The hard part is the policy: who writes entries, when, in what tense, and whether a machine should do it for you.*

---

## Core Concept 1 — Conventional Commits as a Source of Truth

**Conventional Commits** is a lightweight spec that makes commit messages machine-readable. The structure:

```
<type>[optional scope][!]: <description>

[optional body]

[optional footer(s)]
```

Real examples:

```
feat(auth): add TOTP-based multi-factor authentication

fix(parser): handle config files with a UTF-8 BOM

docs: clarify the retry-policy section in the README

feat(api)!: return camelCase keys in all responses

BREAKING CHANGE: response keys changed from snake_case to camelCase.
Clients parsing snake_case fields must update.
```

The common types:

| Type | Meaning |
|------|---------|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation only |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `perf` | A performance improvement |
| `test` | Adding/correcting tests |
| `build` / `ci` | Build system or CI changes |
| `chore` | Maintenance not affecting source/tests |

Two ways to signal a **breaking change**: a `!` after the type/scope (`feat(api)!:`) **or** a `BREAKING CHANGE:` footer. Either one forces a major version bump.

> **Payoff:** once commits follow this format, a tool can read `git log`, classify every commit, decide the version bump, and render the changelog — with zero manual editing.
> **Cost:** discipline. Every contributor must write structured messages, usually enforced by a commit-lint hook in CI.

---

## Core Concept 2 — Mapping Commit Type to SemVer and Changelog Section

Conventional Commits is valuable precisely because it defines two mappings: commit type → **version bump**, and commit type → **changelog section**.

| Commit | SemVer bump | Keep a Changelog group |
|--------|-------------|------------------------|
| `fix:` | PATCH (`1.4.2 → 1.4.3`) | Fixed |
| `feat:` | MINOR (`1.4.2 → 1.5.0`) | Added |
| `feat!:` / `BREAKING CHANGE:` | MAJOR (`1.4.2 → 2.0.0`) | Changed / Removed |
| `perf:` | PATCH (often) | Changed |
| `docs:`, `chore:`, `ci:`, `test:` | none | usually omitted |

This is the engine behind tools like semantic-release. Given a range of commits since the last tag:

```
$ git log v1.4.2..HEAD --oneline
a1b2c3d feat(reports): add CSV export
d4e5f6a fix(auth): prevent focus loss on validation error
9z8y7x6 chore: bump dev dependencies
```

The tool reasons: one `feat` (highest non-breaking) → **MINOR bump → 1.5.0**. It then renders:

```markdown
## [1.5.0] - 2026-06-20

### Added
- **reports:** add CSV export (a1b2c3d)

### Fixed
- **auth:** prevent focus loss on validation error (d4e5f6a)
```

The `chore` commit is dropped from the changelog — it's noise to a reader. **This is the first place you see the curation problem leak in: the tool's idea of "noise" must match yours.** A `chore: upgrade lodash to patch CVE-...` arguably belongs in Security, but a naive type-only rule hides it.

---

## Core Concept 3 — Automated Generation: The Tool Landscape

Four tools dominate. They differ mainly in *what they read* and *how much of the release they automate*.

**git-cliff** — a fast, configurable changelog generator (TOML config) from git history. It generates the changelog and nothing else; you control versioning and publishing.

```bash
# Generate the full changelog from conventional commits
git cliff --output CHANGELOG.md

# Just the unreleased section, for a release PR
git cliff --unreleased --tag v1.5.0
```

**semantic-release** — fully automated. On every push to the release branch, it analyzes commits, computes the next version, generates the changelog, tags, and publishes to the registry — all in CI, no human in the loop.

```jsonc
// .releaserc.json
{
  "branches": ["main"],
  "plugins": [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    "@semantic-release/changelog",
    "@semantic-release/npm",
    "@semantic-release/github"
  ]
}
```

**release-please** (Google) — the "release PR" model. It watches your default branch and opens/updates a PR that accumulates the changelog and version bump. Merging that PR cuts the release. This inserts a human review point: you can edit the generated notes before they ship.

```yaml
# .github/workflows/release-please.yml
- uses: googleapis/release-please-action@v4
  with:
    release-type: node
```

**Changesets** — the monorepo favorite. Authors don't rely on commit messages; they add an intent file per change:

```bash
$ npx changeset
# prompts: which packages? what bump (patch/minor/major)? summary?
```

```markdown
---
"@acme/ui": minor
"@acme/core": patch
---

Add a `<DatePicker>` component and fix a tree-shaking regression in core.
```

At release time, `changeset version` consumes these files, bumps each package, and writes per-package changelogs. The intent file *is* the human-written changelog entry — automation handles only the bookkeeping.

> Rule of thumb:
> - **git-cliff** — you want a generator and keep control.
> - **semantic-release** — fully hands-off single-package CI.
> - **release-please** — generated-but-reviewable.
> - **changesets** — monorepos, or you want authors to write prose.

---

## Core Concept 4 — PR Labels and Merge Titles as Inputs

Not every team adopts conventional commits. Two other structured sources are common:

**PR labels.** Tag each PR with a label (`type: feature`, `type: bugfix`, `breaking`, `skip-changelog`). A tool — GitHub's built-in *automatically generated release notes*, or `release-drafter` — groups merged PRs by label into a draft note.

```yaml
# .github/release.yml  (GitHub native)
changelog:
  categories:
    - title: Breaking Changes 🛠
      labels: [breaking]
    - title: New Features 🎉
      labels: [feature, enhancement]
    - title: Bug Fixes 🐛
      labels: [bug, fix]
    - title: Other
      labels: ["*"]
  exclude:
    labels: [skip-changelog, dependencies]
```

**Merge / squash titles.** Teams that squash-merge make the squash commit title the unit of record. If the squash title follows Conventional Commits (many repos enforce a PR-title linter), you get the commit-based pipeline for free — without requiring every intermediate commit to be clean.

```
Squash PR title:  feat(reports): add CSV export (#318)
→ becomes the single commit on main → feeds the generator
```

> The deeper point: automation needs *some* structured input. The only open question is *where* you make humans add it — commits, PR titles, labels, or intent files. Pick the one with the least friction for your team and enforce it in CI.

---

## Core Concept 5 — Automation vs Hand-Curation: The Trade-off

This is the central judgment call. Both extremes fail.

**Pure automation (every commit → an entry):**

- ✅ Nothing is forgotten; the changelog is exhaustive and always up to date.
- ✅ Consistent format; no merge conflicts on `CHANGELOG.md`.
- ❌ **Every commit is noise.** Readers drown in `fix: typo`, `refactor: rename variable`, `chore: bump deps`. The signal — the two changes that actually matter to a user — is buried.
- ❌ Entries read like commit messages, because they *are* commit messages. No narrative, no "why."

**Pure hand-curation:**

- ✅ A readable, prioritized story; highlights first; the "why" explained.
- ❌ Slow, easily skipped, prone to omissions and merge conflicts.

**The mature answer is layered:**

| Artifact | Approach |
|----------|----------|
| CHANGELOG (developers) | **Automated** from commits/PRs — completeness matters most. |
| Release notes (users) | **Curated** — a human picks 3–5 highlights and writes the narrative. |
| Migration guide | **Hand-written** — automation can't generate a safe upgrade recipe. |

So the generated changelog feeds the curator: the human reads the auto-generated list and *promotes* the important entries into the release notes, adding context. release-please and changesets are popular precisely because they leave a review step where this curation happens.

> Heuristic: **automate the complete record, curate the story.** If your "release notes" are just the raw generated changelog, you've automated the wrong artifact.

---

## Core Concept 6 — Release Notes Done Well

Release notes are not a changelog with a nicer header. They follow different rules.

1. **Lead with impact, not inventory.** Open with the one or two things a user will notice.
2. **Group by user value, not by code area.** "Faster dashboards," "New export options" — not "changes to the reporting module."
3. **Explain the *why* for behavior changes.** Users tolerate change when they understand the reason.
4. **Surface anything requiring action prominently** — breaking changes, deprecations, required migrations — and link the migration guide.
5. **Link out** to the full changelog for the completionists.

```markdown
# v3.2.0 — Cleaner logs and YAML config

**Highlights**
- 🧹 The default log level is now `info`. Your logs will be much quieter
  out of the box (set `--log-level=debug` to restore the old behavior).
- 📝 You can now write configuration in YAML as well as JSON.

**Action needed**
- `--verbose` is deprecated and will be removed in v4. Replace it with
  `--log-level=debug`. See the [v3 → v4 migration guide](…).

[Full changelog →](CHANGELOG.md#320---2026-06-15)
```

---

## Real-World Examples

**A semantic-release pipeline.** A team merges PRs to `main` all week. CI runs semantic-release on each merge: it sees three `fix:` commits since the last release, bumps `2.3.1 → 2.3.2`, generates the changelog section, tags `v2.3.2`, publishes to npm, and creates a GitHub Release — all without a human. Downside they later hit: a marketing-worthy feature shipped with the bland auto-generated note "feat: add sharing." They added a `release-please`-style review step so a human could rewrite the headline before publish.

**A monorepo with changesets.** A 40-package repo. Every PR that changes published behavior must include a changeset file (CI fails otherwise). At release, `changeset version` bumps only the affected packages and writes each one's `CHANGELOG.md`. A package with no changesets since its last release simply isn't re-released — solving the "everything bumps when one thing changes" monorepo problem.

---

## Common Mistakes

| Mistake | Why it hurts | Fix |
|---------|-------------|-----|
| Shipping the raw generated changelog as "release notes" | Users get noise, not highlights | Curate a separate notes artifact |
| Adopting conventional commits without CI enforcement | Drift; some commits unparseable | Add commitlint / PR-title lint |
| Hiding security `chore:` bumps from the changelog | Operators miss patches | Tag security-relevant deps explicitly |
| Hand-editing `CHANGELOG.md` in every PR | Constant merge conflicts | Generate, or use per-PR intent files |
| One global changelog in a monorepo | Users of package A see package B's churn | Per-package changelogs (changesets) |
| Squash-merging with junk titles | Junk becomes the unit of record | Lint PR/squash titles |

---

## Apply it

1. Find a real component where **Changelogs & Release Notes** affects an interface or dependency.
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

- Which boundary is most affected by Changelogs & Release Notes?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
- How does Conventional Commits drive both the version bump and the changelog section?
- Compare git-cliff, semantic-release, release-please, and Changesets — when would you pick each?
- What goes wrong if you auto-generate the changelog from every single commit?
- What makes a breaking-change changelog entry actionable rather than just accurate?
- Which tool would you reach for in a monorepo, and why?
- Your team merges 50 PRs a week and `CHANGELOG.md` edits keep causing merge conflicts — how would you redesign the process?
