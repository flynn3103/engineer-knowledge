# Changelogs & Release Notes — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Changelogs & Release Notes** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Changelogs & Release Notes

> *At org scale the question is no longer "how do I write a good entry" but "how do I make hundreds of engineers across dozens of teams produce honest, consistent, compliant change communication — by default, without heroics."*

---

## Core Concept 1 — A Change-Communication Standard as Org Policy

At org scale, the foundational artifact is a written **standard**: the single source of truth that every team's tooling and reviews reference. Without it, each team invents its own conventions and the org's change communication is incoherent — which directly harms integrators, support, and auditors.

A real standard specifies, at minimum:

```markdown
# Change Communication Standard (org-wide)

## Scope & artifacts
- CHANGELOG.md required for every published artifact (lib, service, CLI).
- Release notes required for any user-facing change.
- Migration guide required for any breaking change > one-line fix.

## Format
- Keep a Changelog structure; six groups; ISO dates; newest-first.
- Conventional Commits enforced via commitlint in CI.

## Versioning linkage
- SemVer for libraries; CalVer (YYYY.MM) for the platform.
- Type→bump→section mapping is fixed (see appendix).

## Security
- Security fixes: own group, CVE/GHSA, CVSS, fixed inventory, embargo
  per the Security Disclosure Policy.

## Ownership & review
- Release notes reviewed before ship (gate). Owner per artifact in CODEOWNERS.

## Retention
- Changelogs are append-only history; never rewrite shipped entries.
```

The standard's job is to convert a thousand individual judgment calls into a few decisions made once, centrally. The professional skill is writing a standard that is **prescriptive where consistency matters** (format, security, retention) and **permissive where it doesn't** (entry wording style), so teams comply without friction or resentment.

> **Warning:** a standard nobody can follow easily is shelfware. Pair every "must" with a paved-road tool that makes the "must" automatic — see Core Concept 4.

---

## Core Concept 2 — The Changelog as a Legal and Compliance Artifact

Beyond a contract, the changelog and release record carry **legal and regulatory weight**. Professionals must treat them as evidence.

- **Change-management compliance (SOC 2 CC8, ISO 27001 A.12.1.2).** Auditors require that production changes are tracked, reviewed, and approved. The changelog + release record + approval trail *is* the evidence. "What changed in production on 2026-05-12 and who approved it?" must be answerable. If your changelog can't reconstruct this, you fail the control.
- **Append-only / immutable history.** Once a version's entries ship, **never rewrite them.** Rewriting shipped history destroys the audit trail and can constitute falsifying records. Corrections go in a *new* entry ("Corrected: the 2.3.0 entry misstated…"), not by editing the old one. This is why mature pipelines protect tags and changelog history.
- **Security-disclosure obligations.** Regulations and contracts increasingly require timely vulnerability disclosure (e.g. customer SLAs, sector regulations, the EU CRA's reporting duties). The Security section's timestamps are the proof of when you disclosed. Disclosing late — or before the patch — has legal consequences.
- **License and dependency provenance.** For some compliance regimes the changelog must note dependency changes that affect licensing or the SBOM. This ties the changelog to [Supply-Chain Security](../supply-chain-security/README.md).
- **Contractual feature commitments.** If a contract promises a feature "by Q3," the dated release note is evidence of delivery. Conversely, announcing a removed feature in the changelog can trigger contractual notice periods.

> **Reframe:** the changelog is not just developer courtesy; it is a **record of corporate action**. Design it with the same integrity controls you'd apply to any audit artifact — immutability, attribution, timestamps, review.

---

## Core Concept 3 — Governance: Ownership, RACI, and Enforcement

A standard without governance decays. Governance answers *who is accountable* and *how compliance is sustained across reorgs and turnover.*

**Ownership model.** Map artifacts to owners explicitly, typically in `CODEOWNERS` plus a RACI:

| Activity | Responsible | Accountable | Consulted | Informed |
|----------|-------------|-------------|-----------|----------|
| Per-PR changelog entry | Author | Eng lead | — | Reviewers |
| Release-notes curation | Release mgr / PM | Product lead | Eng, Support | Marketing |
| Migration guide | Owning team | Eng lead | DevRel, affected teams | Customers |
| Security advisory wording | Security team | CISO/Sec lead | Legal, owning team | All users |
| The standard itself | Platform/RelEng | VP Eng | All teams | Org |

**Enforcement as the load-bearing piece.** Standards are followed only when the easy path enforces them:

- **Commit/PR-title lint** blocks non-conventional commits at CI.
- **A `requires-changelog` check** fails PRs that change behavior without a changelog entry or `skip-changelog` label (and the label itself requires a reason).
- **Release-notes gate** (from senior level) is a required status check on the release PR.
- **Policy-as-code** for the high-stakes invariants: a major bump *must* have a documented breaking change; a `Security` entry *must* have a CVE/advisory link and fixed inventory.

```rego
# policy/changelog.rego (sketch — enforced in CI)
deny[msg] {
  input.version_bump == "major"
  count(input.changelog.breaking) == 0
  msg := "Major version bump with no documented breaking change"
}
deny[msg] {
  some e in input.changelog.security
  not e.advisory_id
  msg := sprintf("Security entry missing advisory id: %v", [e.title])
}
```

**Professional principle:** make compliance the default and non-compliance loud.

- Reviews catch what automation can't — judgment, wording.
- Automation catches what reviews miss under deadline pressure — omissions.
- You need both, layered.

---

## Core Concept 4 — Architecting the Change-Comms Pipeline

The paved road is a pipeline that produces all three artifacts from structured inputs with minimal per-team effort. A reference architecture:

```
[PR merged]
   │  conventional commit + Release-Note: trailer + labels
   ▼
[CI: lint commit/PR-title, requires-changelog check]
   ▼
[Release tool: release-please / changesets]
   │  opens/updates a RELEASE PR:
   │    • auto-generated CHANGELOG (complete, Layer 1)
   │    • draft release notes from Release-Note: trailers (Layer 2 seed)
   │    • computed version bump (policy-checked)
   ▼
[Release-notes GATE: human curation + checklist + policy-as-code]
   ▼
[Merge release PR] → tag → publish → render:
   • CHANGELOG.md committed (append-only)
   • GitHub/GitLab Release created
   • Public changelog page updated (SaaS)
   • Release notes pushed to i18n pipeline (localized surfaces)
   • Security advisory published to OSV/GHSA (if applicable, embargo-gated)
```

Design principles for the pipeline:

- **Single structured source, many renderings.** Engineers add structure once (commit + trailer + label); the pipeline renders CHANGELOG, GitHub Release, public page, app-store notes, and advisory feeds from it. Never ask teams to maintain the same change in five places.
- **Default-exclude noise.** `chore`/`refactor`/`test`/dep-bumps are excluded from user-facing renderings by default; security and `highlight`-tagged entries are promoted automatically.
- **The release PR is the gate's home.** It's where humans curate and where policy-as-code runs — a natural, reviewable chokepoint.
- **i18n as a downstream stage**, working off structured highlight keys (not finished Markdown), so translation never blocks the engineering merge.

This is platform engineering: the central team owns the pipeline and standard; product teams consume it and write only the prose that requires human judgment.

---

## Core Concept 5 — Metrics and the Goodhart Trap

You can't steward what you don't measure, but every changelog metric is gameable. Useful signals, with their failure modes:

| Metric | What it tells you | How it's gamed (Goodhart) |
|--------|-------------------|---------------------------|
| % releases with release notes | Coverage of the gate | Empty/boilerplate notes that pass the check |
| % breaking changes with migration guide | Migration discipline | Stub guides; "see code" |
| Time from security fix → advisory published | Disclosure timeliness | Marking fixes non-security to dodge the clock |
| Support tickets citing "didn't know it changed" | Real-world note quality | Untracked if support doesn't tag them |
| Changelog read/clickthrough (SaaS) | Are notes reaching users | Vanity; clicks ≠ understanding |

Goodhart's law bites hard here: *when a measure becomes a target, it ceases to be a good measure.* "100% of releases have notes" is trivially satisfied by autogenerated noise. The professional response:

- **Measure outcomes, not artifacts.** "Support tickets about surprise changes" and "downstream upgrade time" reflect whether communication *worked*, and are harder to game than "notes exist."
- **Audit a sample qualitatively.** Periodically read a random sample of recent notes against the standard. Numbers tell you coverage; reading tells you quality.
- **Watch the dodge incentives.** The most dangerous gaming is reclassifying security fixes as `fix:` to avoid disclosure timing — monitor for it explicitly.

> See [Engineering Metrics & DORA](../../README.md) — the same Goodhart discipline applies. Treat change-comms metrics as health indicators for a conversation, not as targets to maximize.

---

## Core Concept 6 — Migration Guides as a Managed Program

For platforms with many integrators, breaking changes aren't one-off events — they're a **continuous program** that needs management, not just documentation.

- **Deprecation policy with hard dates.** Publish an org-wide policy: minimum deprecation window, EOL schedule, support tiers. The changelog's `Deprecated` entries and the migration guides execute this policy; the policy makes them predictable.

  ```markdown
  ## Deprecation Policy
  - Deprecated APIs supported for ≥ 2 minor versions and ≥ 6 months.
  - EOL announced in CHANGELOG (Deprecated) + email + runtime warning.
  - Migration guide published at deprecation announcement, not at removal.
  ```

- **Migration guide published at announce-time, not removal-time.** Integrators need the recipe while they still have runway. Shipping the guide alongside the removal is too late.
- **Programmatic migration aids.** For large API surfaces, ship codemods/`jscodeshift` scripts, lint rules, or automated upgraders alongside the guide. "Run `npx @acme/upgrade v3-to-v4`" beats a 40-step manual guide and is what serious platforms (React, Angular, Next.js) provide.
- **Track adoption.** Telemetry on deprecated-API usage tells you whether integrators have actually migrated before you pull the feature — pulling it while 30% still call it is an incident.
- **Coordinate cross-team breaks.** In a monorepo/platform, one team's break can cascade to many internal consumers. The migration program coordinates this (advance notice, consumer sign-off) so a break doesn't surprise internal teams either.

---

## Core Concept 7 — Rollout, Embargo, and Coordinated Disclosure

Publication *timing* is a professional-level control, especially where security and large customers are involved.

- **Security embargo.** An embargoed fix must publish binary + advisory + changelog **simultaneously**, never the changelog first (which hands attackers a roadmap to unpatched users). The pipeline must gate advisory publication on artifact availability. Coordinated disclosure with reporters and downstreams (CERTs, major customers) follows an agreed timeline.
- **Staggered rollout vs changelog timing (SaaS).** With progressive delivery, a feature is at 5% then 50% then 100%. Announcing in the public changelog at 5% confuses the 95% who don't have it; announcing at merge is even earlier. Standard: **announce user-facing changes when they reach general availability**, with a separate early-access channel for beta cohorts. See [Feature Flags & Progressive Delivery](../feature-flags-and-progressive-delivery/README.md) and [Rollback & Roll-Forward](../rollback-and-roll-forward/README.md) — if a rollout is rolled back, the changelog/notes must be retractable too.
- **Pre-announcement for breaking changes.** Major customers and integrators often have contractual notice rights. The changelog's `Deprecated` entry may need to be backed by direct customer notice on a defined timeline.
- **Time-zone and market coordination.** Global products coordinate note publication with regional launches and app-store review latency (Apple/Google review can delay localized notes by days — plan for it).

> The unifying idea: *the change is not "done" when the code merges; it is "done" when the right audiences have been correctly informed at the right time.* Publication timing is part of the release, not an afterthought.

---

## Core Concept 8 — Failure Modes and Organizational Anti-Patterns

The professional value-add is recognizing systemic failures before they compound.

- **The commit-dump changelog.** Fully automated, zero curation; the changelog is an unreadable wall of `chore`/`refactor`. Symptom: nobody reads it; support reconstructs changes from Slack. Fix: add the promotion/curation layer.
- **The phantom changelog.** It exists, passes the coverage metric, but entries are jargon or boilerplate. Symptom: "didn't know it changed" tickets despite "100% notes." Fix: qualitative audit + outcome metrics.
- **The security dodge.** Fixes mislabeled `fix:` to avoid the disclosure clock or the harder Security review. Symptom: CVEs filed by *third parties* before you disclose. Fix: security-fix classification reviewed by the security team; monitor reclassification.
- **The N-dialect org.** Every team's CHANGELOG looks different; integrators can't build tooling against them. Fix: the standard + paved road.
- **The rewritten-history incident.** Someone "cleans up" old changelog entries or force-pushes a tag. Symptom: audit trail broken, possibly a compliance finding. Fix: append-only policy, protected tags, immutable releases.
- **The migration-guide cliff.** Breaking change ships with no guide; integrators stuck. Symptom: support flood, churn. Fix: guide-at-announce-time policy, enforced as a gate for major bumps.
- **The translation-gap leak.** Localized notes lag or are machine-translated; non-English users get wrong migration steps. Fix: i18n stage with human review for high-stakes content; English-first policy with SLA.

---

## Real-World Examples

**An enterprise platform's SOC 2 audit.** The auditor samples ten production changes from the past quarter and asks: what changed, who reviewed it, who approved it, when did it ship? Because every change flowed through the release-PR gate with a generated changelog, CODEOWNERS review, and an immutable tag, the platform answers each in minutes from the changelog + PR + tag. A team that hand-edited CHANGELOG.md ad hoc would have spent days reconstructing and likely caught a finding.

**A framework's major-version program.** A popular framework ships a major version: deprecation warnings landed two minor versions earlier (with changelog `Deprecated` entries), a migration guide and a `npx upgrade` codemod shipped at announce-time, deprecated-API telemetry confirmed <2% usage before removal, and the release note led with "most apps upgrade by running one command." Integrators upgrade smoothly; the break is a non-event because the *program* — not just the changelog — managed it.

**A coordinated security release.** A high-severity vuln across three supported branches. Security, RelEng, and Legal align on a disclosure time. At T-0, patched artifacts for all three branches, the GHSA advisory (with CVSS and the full fixed inventory `4.2.1 / 3.9.7 / 2.14.3`), the changelog Security entries, and customer emails publish simultaneously. No changelog entry leaked beforehand. Downstream scanners pick up the OSV record within the hour and notify every affected consumer.

---

## Common Mistakes

| Mistake | Why it hurts | Fix |
|---------|-------------|-----|
| No written change-comms standard | N inconsistent dialects | Publish a prescriptive-where-it-matters standard |
| Standard with no paved-road tooling | Shelfware; teams ignore it | Pair every "must" with automation |
| Rewriting shipped changelog history | Breaks audit trail; possible compliance finding | Append-only; corrections as new entries |
| Coverage metrics only | Boilerplate passes; quality unknown | Outcome metrics + qualitative sampling |
| Security fix timing not gated | Changelog leaks before patch = 0-day | Embargo gate; simultaneous publish |
| Migration guide at removal-time | Integrators have no runway | Publish at announce-time + codemods |
| Pulling deprecated APIs blind | Breaks active integrators | Gate removal on usage telemetry |

---

## Apply it

1. Define the user or business outcome that **Changelogs & Release Notes** should improve.
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

- Which measurable outcome justifies investing in Changelogs & Release Notes?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
- How does a changelog function as a compliance/audit artifact, and what does that require operationally?
- A high-severity CVE affects three supported branches — how do you coordinate the disclosure across artifacts, advisory, and customers?
- Leadership proposes "100% of releases have release notes" as a target metric — what's your response?
- Can you edit a shipped changelog entry to fix a typo? What should happen instead, and why?
