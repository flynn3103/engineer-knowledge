# Changelogs & Release Notes — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Changelogs & Release Notes** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Changelogs & Release Notes

> *A changelog is an API contract written in prose. At scale it becomes a compliance artifact, a support tool, and a coordination protocol — treat it as load-bearing infrastructure.*

---

## Core Concept 1 — The Changelog as an API Contract

For anything other people build on, the changelog is **the human-readable half of your compatibility contract.** SemVer makes a promise in numbers (`2.x` is backward-compatible with `2.0`); the changelog makes the same promise in prose, and is where the promise is *kept or broken*.

This has hard consequences:

- **A breaking change that isn't in the changelog is a broken contract**, even if you bumped the major version. Downstream maintainers grep changelogs to plan upgrades; an undocumented break is a silent landmine.
- **The changelog is auditable evidence.** "When did behavior X change?" must be answerable from the changelog, not from spelunking git. Support, security, and legal all rely on this.
- **An entry's wording is itself an interface.** "Renamed `getUser` to `fetchUser`" tells an integrator exactly what to change. "Refactored the user module" tells them nothing actionable — and so violates the contract's spirit.

A useful discipline: **for every breaking change, the changelog entry must let a reader fix their code without reading your source.**

```markdown
### Changed
- **BREAKING:** `Client.connect()` is now async and returns a `Promise`.
  Replace `client.connect()` with `await client.connect()`. Synchronous
  callers will receive an unresolved Promise instead of a connection. (#902)
```

That entry is a contract clause: it states what changed, the failure mode if ignored, and the remediation. Compare to "Made connect async" — technically true, contractually useless.

> The senior reframing: review changelog entries for breaking changes with the same rigor as the API change itself. A correct API change with a vague changelog entry is an incomplete change.

---

## Core Concept 2 — Libraries vs SaaS: When "Version" Is Fuzzy

The clean SemVer-and-changelog story assumes discrete, immutable releases that users choose to adopt. **For SaaS, that assumption collapses.**

| | Library / package | SaaS / continuously deployed |
|---|---|---|
| "Version" | Explicit `2.4.0`, immutable | Often a date, a build hash, or nothing user-visible |
| Who adopts | The integrator, on their schedule | Everyone, instantly, whether they want to or not |
| Breaking change | They can pin to the old version | They cannot opt out — you broke them in production |
| Changelog unit | Per release tag | Per deploy, per feature-flag rollout, or per week |

This changes the artifacts:

- **SaaS leans on CalVer or no version at all.** `2026.06` or "the June release" communicates more than `v847`. The changelog becomes a **dated stream** ("Changelog" pages like Stripe's or GitHub's) rather than a tag-anchored file.
- **Because users can't opt out, the release note carries more weight than for a library.** A library user who ignores your note can stay on the old version; a SaaS user who misses your note is broken at next login. So SaaS release notes must be *louder* about behavior changes and *earlier* (announce before, not after).
- **Feature flags decouple "merged" from "released."** A feature behind a flag is in the codebase but not in any user's reality. Your changelog must describe *what users can now do*, which is gated by rollout, not by merge. This is why SaaS changelogs are often written at *flag-100%* time, not merge time. See [Feature Flags & Progressive Delivery](../06-feature-flags-and-progressive-delivery/).

> The principle: **the changelog's unit of change must match the user's unit of adoption.** For libraries that's a version; for SaaS it's a dated rollout. Forcing SaaS into per-tag changelogs produces noise no user reads.

---

## Core Concept 3 — Monorepo Changelogs and Change Propagation

A monorepo publishing many packages defeats the single-`CHANGELOG.md` model. The failures:

1. **Cross-contamination.** A user of `@acme/utils` does not want to read about `@acme/web-ui`. One global changelog buries every package's history in every other's.
2. **Phantom releases.** If a shared `version` bumps everything on every change, `@acme/utils` gets a `2.5.0` release with an empty changelog — eroding trust in the version number.
3. **Dependency-driven bumps.** If `@acme/core` makes a breaking change and `@acme/ui` depends on it, `@acme/ui`'s changelog must record that *its* dependency changed, even though `@acme/ui`'s own code is untouched.

The standard solution is **per-package changelogs with explicit change propagation**, which is exactly what Changesets implements:

```markdown
---
"@acme/core": major
"@acme/ui": patch
---

core: `parse()` now throws on malformed input instead of returning null.
```

At release, `changeset version` writes `@acme/core`'s changelog with the major entry, **and** appends to `@acme/ui`'s changelog:

```markdown
## @acme/[email protected]

### Patch Changes
- Updated dependencies [a1b2c3d]:
  - @acme/[email protected]
```

This makes propagation explicit and auditable: a `@acme/ui` user can see *why* it was re-released even though its source didn't change. The senior skill is **designing the bump-and-propagation policy**: fixed-versioning (everything moves together — simpler, noisier) vs independent versioning (each package on its own — accurate, more bookkeeping), and how transitive dependency bumps cascade.

---

## Core Concept 4 — Breaking Changes, Deprecations, and Migration Guides

Breaking changes are where the three artifacts must work in concert. A well-run breaking change has a **lifecycle**, and each stage produces a different artifact:

1. **Announce (deprecation).** Long before removal, the changelog's `Deprecated` group and a runtime warning announce intent.

   ```markdown
   ### Deprecated
   - `Client.connectSync()` is deprecated and will be removed in v4.0.
     Use the async `connect()`. (deprecated since 3.6.0) (#880)
   ```

2. **Remove (the break).** The `Removed`/`Changed` group records it, the major version bumps, and **the migration guide carries the remediation.**

3. **Migration guide** — a standalone, step-by-step document, not a changelog bullet. The changelog says *what* broke; the migration guide says *how to fix every break*, in order, with before/after code.

   ```markdown
   # Migrating from v3 to v4

   ## 1. Async connect (required)
   `connectSync()` is removed. Replace:
   ```diff
   - const conn = client.connectSync();
   + const conn = await client.connect();
   ```
   ## 2. camelCase response keys (required)
   …
   ## 3. Dropped Node 16 support (required if on Node 16)
   …
   ```

The senior judgment is **what goes where**. A common failure is stuffing migration steps into changelog bullets (unreadable, unmaintainable) or omitting the migration guide and expecting users to reconstruct it from `Removed` entries (impossible for non-trivial upgrades). Rule: **if a breaking change requires more than a one-line fix, it needs a migration-guide section, and the changelog entry links to it.**

> Track the **deprecation window** as policy. "Deprecated for at least one minor version and one quarter before removal" is a promise; the changelog's "deprecated since 3.6.0 / removed in 4.0.0" trail is the proof you kept it.

---

## Core Concept 5 — Security Advisories in the Changelog

Security fixes are the highest-stakes changelog entries. They are read by attackers (to find unpatched targets) and by defenders (to prioritize patching), and they are increasingly a **compliance artifact**.

Principles:

- **Always a `Security` group, never buried in `Fixed`.** Defenders scan for it; burying a fix delays patching across your user base.
- **Link the advisory, not just the bug.** Reference the CVE / GHSA and include severity (CVSS):

  ```markdown
  ### Security
  - Fixed a prototype-pollution vulnerability in config parsing
    (CVE-2026-22000, GHSA-xxxx-yyyy-zzzz, CVSS 8.1 High). All users on
    3.x should upgrade to 3.7.2 or 2.x users to 2.9.5. (#945)
  ```

- **State the fixed inventory.** Which versions received the backported fix? Operators on `2.x` need to know `2.9.5` is safe, not just `3.7.2`. This is also what populates vulnerability databases (OSV, GitHub's advisory DB) that downstream scanners consume.
- **Coordinate disclosure timing.** The Security entry must not land *before* the fix is published — that's a zero-day handed to attackers. Embargoed fixes ship the binary and the advisory simultaneously. This couples changelog publication to your disclosure process. See [Supply-Chain Security](../09-supply-chain-security/).
- **The changelog feeds machines now.** Tools like Dependabot/Renovate and SBOM scanners read your advisory metadata to auto-flag downstream. A precise, machine-parseable Security entry protects every downstream user automatically; a vague one protects no one.

---

## Core Concept 6 — The Curation-vs-Automation Tension at Scale

At small scale you can hand-write everything. At scale (hundreds of merges/week) you must automate — and automation's "every commit is noise" failure becomes acute.

The senior resolution is a **two-layer pipeline with a promotion step**:

1. **Layer 1 — automated, complete.** Every change produces a structured record (conventional commit, changeset, or labeled PR). A tool renders the exhaustive CHANGELOG. This layer optimizes for *completeness and auditability*; readability is secondary.

2. **Layer 2 — curated, narrative.** A human (release manager / PM / tech writer) reads Layer 1 and **promotes** the handful of user-impacting changes into the release notes, adding the "why," the screenshots, the migration links. This layer optimizes for *the reader's time*.

The promotion step is the whole game. Design it explicitly:

- **Mark promotable entries at authoring time.** A `release-note: ...` trailer or a `highlight` PR label lets authors flag what deserves the spotlight, so the curator isn't reverse-engineering importance from commit messages.

  ```
  feat(reports): add scheduled CSV exports

  Release-Note: You can now schedule recurring CSV exports from any report.
  ```

- **Default to silence for noise.** `chore`, `refactor`, `test`, dependency bumps (except security) should be *excludable by default* and explicitly includable. The failure mode is the inverse: defaulting to include and asking humans to suppress noise — they won't, and the changelog rots into a commit dump.

> The senior insight: automation doesn't remove the human; it *relocates* them from transcription to curation. If your process has no promotion step, you've automated the changelog and abandoned the release notes — the artifact users actually read.

---

## Core Concept 7 — Release Notes Review as a Release Gate

For anything with meaningful blast radius, **release notes are reviewed before the release ships**, as a required gate — not written afterward.

Why a gate and not a courtesy:

- **It's the last chance to catch an undocumented breaking change.** If reviewers can't map a `2.0.0` bump to a documented break, something is wrong — either the version or the changelog.
- **It catches security-disclosure timing errors** before the note goes public.
- **It catches "this needs a migration guide and there isn't one."**
- **It catches wording that leaks internal jargon or, worse, confidential roadmap.**

Concretely, the gate is a checklist enforced in the release PR (the release-please / changesets release PR is the natural home):

```markdown
## Release Notes Review (required)
- [ ] Every major/minor bump maps to a documented user-facing change
- [ ] All breaking changes have a migration-guide section + link
- [ ] Security entries: advisory linked, fixed inventory stated, embargo respected
- [ ] Highlights written for users (not commit messages)
- [ ] No internal jargon / no unreleased roadmap leaked
- [ ] Deprecations state since-version and removal-version
```

This makes release notes a **quality gate** alongside tests and coverage. See Quality Gates for the gate-design patterns this reuses, and [Release Automation](../08-release-automation/) for wiring it into the pipeline.

---

## Core Concept 8 — Internationalization of Release Notes

For consumer-facing products in multiple markets, release notes are localized — and this introduces real failure modes.

- **CHANGELOG stays in English (or one canonical language).** It's a developer/contributor artifact; localizing it multiplies maintenance for no benefit.
- **Release notes are localized**, because they're user-facing. App-store release notes (Apple/Google) are localized per locale and are a common surface.
- **Translation lags the release.** If the English note ships and translations arrive days later, non-English users see stale or English-only notes. Decide policy: block the release on all translations (slow), or ship English-first with translations following (fast, but inconsistent).
- **Don't machine-translate breaking-change instructions blindly.** A mistranslated migration step is worse than none. High-stakes content (security, migration) needs human review per locale.
- **Keep highlights short and translatable.** Idioms, puns ("squashed some bugs"), and dense jargon translate poorly. This is a concrete reason release notes should be plain and benefit-focused — it's also what survives translation.

> Architecturally: separate the *content* (a structured set of highlights with keys) from the *rendering* per locale, so translators work against keys, not against a finished Markdown blob. This is the same docs-as-code pattern covered in the code-craft `documentation` material.

---

## Real-World Examples

**A library's breaking release.** A widely-depended-on HTTP client ships `v4.0.0`. The maintainers: (1) deprecated the sync API in `3.6.0` with a runtime warning and a `Deprecated` changelog entry; (2) published a v3→v4 migration guide two weeks before v4; (3) the v4 changelog's `Removed`/`Changed` entries each link the relevant migration section; (4) backported the security fix that motivated part of the change to `3.7.2` for users not ready to migrate. Downstream maintainers upgrade smoothly because every break was announced, documented, and remediated.

**A SaaS continuous-deployment changelog.** A product deploys 30×/day. There's no per-deploy version users see. Instead, a public "Changelog" page is updated when a feature reaches 100% rollout, written by the PM from a `Release-Note:` trailer the engineer added. Internal CHANGELOG (auto-generated from commits) exists for engineers and incident response; the public page is the curated story. The two artifacts have different update cadences and different authors — by design.

**A monorepo security cascade.** A vuln in `@acme/core`'s parser. The fix ships `@acme/[email protected]` with a full advisory in its `Security` section. Changesets propagates patch bumps to the 14 packages depending on `core`, each changelog noting the dependency update. Downstream SBOM scanners pick up the OSV advisory and flag every consumer automatically.

---

## Common Mistakes

| Mistake | Why it hurts | Fix |
|---------|-------------|-----|
| Major bump with vague break entry | Contract technically broken; integrators surprised | Entry = what broke + failure mode + fix |
| Forcing SaaS into per-tag changelogs | Noise no user reads | Dated rollout stream, written at flag-100% |
| One global changelog in a monorepo | Cross-contamination, phantom releases | Per-package changelogs + explicit propagation |
| Migration steps stuffed into changelog bullets | Unreadable, unmaintained | Standalone migration guide, linked from entries |
| Security fix in `Fixed` without advisory/inventory | Defenders miss it; scanners can't act | `Security` group + CVE/GHSA + CVSS + fixed versions |
| Release notes written after shipping | No gate, breaks ship undocumented | Notes review as a required release gate |
| Localizing the CHANGELOG | Maintenance explosion, no benefit | Localize only user-facing release notes |

---

## Apply it

1. State the system invariant that **Changelogs & Release Notes** must protect.
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

- Which invariant must remain true when Changelogs & Release Notes fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
