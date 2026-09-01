# Feature Flags & Progressive Delivery — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Feature Flags & Progressive Delivery** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Feature Flags & Progressive Delivery

*At org scale the question isn't "how do I use a flag" but "how do I make ten thousand flag changes a year safe, attributable, and cheap" — and whether you should own the platform that decides.*

---

## Core Concept 1 — Build vs Buy the Flag Platform

Three options, and the answer is usually "buy, or adopt OSS, behind an abstraction."

| Option | Examples | When it fits | Real cost |
|---|---|---|---|
| **Buy (SaaS)** | LaunchDarkly, Split | Fast start, want experimentation + targeting + audit out of the box | Per-seat/MAU pricing scales painfully; data leaves your boundary unless you self-host the relay |
| **Adopt OSS** | Unleash, Flagsmith, GrowthBook | Want control/self-host, lower license cost, decent feature set | You operate it: HA, upgrades, on-call for tier-0 infra |
| **Build** | in-house | Hyperscale or unique requirements SaaS can't meet | You're now maintaining tier-0 infra, SDKs for N languages, a UI, audit, and experimentation stats — usually a mistake |

- **Building from scratch is almost always the wrong call.** Teams underestimate the *long tail*: multi-language SDKs with consistent bucketing, streaming with bounded skew, an audit trail, RBAC, a usable UI, statistically correct experiment analysis, and tier-0 reliability. That's a product, not a sprint.
- The defensible middle path: **adopt a mature OSS or SaaS backend, but put OpenFeature in front of it** so the *decision* is reversible. The build-vs-buy reasoning mirrors the `ci-cd-pipeline-design` skill's "don't build your own CI" instinct — own the policy, rent the engine.

> The honest cost comparison isn't license-fee vs zero. It's license-fee vs (engineers + on-call + opportunity cost) of running tier-0 infra forever. Buy unless your scale or constraints genuinely break the vendor.

---

## Core Concept 2 — OpenFeature as the Vendor-Neutral Layer

- OpenFeature (a CNCF project) standardizes the *evaluation API* so your application code is independent of the backend.
- You write against `OpenFeature.getClient()`; a **provider** adapts that to LaunchDarkly, Unleash, Flagsmith, or a static file.
- Switching vendors becomes swapping a provider at startup, not rewriting every call site.

```go
// Application code is vendor-agnostic. Swap the provider, not the call sites.
openfeature.SetProvider(launchdarkly.NewProvider(sdkKey))   // ← only line that knows the vendor
client := openfeature.NewClient("checkout")

// Everywhere else in the codebase:
useNew := client.Boolean(ctx, "payments.checkout.new-flow", false,
    openfeature.NewEvaluationContext(user.ID, map[string]any{
        "plan": user.Plan, "country": user.Country,
    }))
```

Two professional reasons this matters beyond portability:

- **Cross-cutting hooks.** OpenFeature *hooks* let you attach logging, metrics, and validation to *every* evaluation org-wide — flag-eval latency, default-value-served rate (a leading indicator of a failing backend), and per-flag traffic — without touching app code.
- **Standardized telemetry.** A consistent evaluation event schema across all languages and services means one dashboard for "is the flag system healthy" across the whole org. The mandate becomes "all services use OpenFeature," and the backend choice stays an implementation detail you can revisit.

---

## Core Concept 3 — Flag-Config-as-Production-Risk at Org Scale

The senior insight — a flag change is a production change — becomes an *operational program* at org scale, because flag changes will outnumber deploys by 10–100×, made by PMs, data scientists, and support staff, not just engineers.

What "config is production" looks like as a system:

- **Every flag change is an immutable, attributable event** (who, what, before→after, reason, blast-radius estimate), shipped to the same audit/SIEM pipeline as deploys. When an incident timeline shows "behavior changed, no deploy," this is the first place responders look — and it must answer in seconds.
- **Blast-radius preview is mandatory and accurate.** Before commit, the platform computes "this change affects ~N users / ~M req/s" from real targeting data, not a guess. A surprising number is the cheapest outage prevention there is.
- **High-risk changes are staged like deploys.** A global kill-switch flip goes internal → canary cohort → all, with the same pause-and-observe rhythm as a canary deploy. The platform should make the safe path the easy path.
- **Change freezes apply to flags too.** If you freeze deploys for a sales event, you freeze high-risk flag changes — they carry the same risk. Most orgs forget this and get bitten.

> The org-design failure to avoid: rigorous deploy controls beside a flag UI where anyone flips anything instantly with no review. That asymmetry concentrates all your unreviewed production risk into the channel you watch least.

---

## Core Concept 4 — Org-Wide Governance and Policy-as-Code

Hand-policing flags across forty teams doesn't scale; encode the policy and enforce it at the platform/CI boundary. **Policy-as-code** (e.g. OPA/Rego) turns governance from a wiki page into a gate.

```rego
# OPA policy: reject non-conforming flag definitions at creation/PR time.
package flags

deny[msg] {
  input.type == "release"
  not input.expiresAt
  msg := sprintf("release toggle '%s' must set expiresAt", [input.key])
}

deny[msg] {
  not regex.match(`^[a-z0-9]+\.[a-z0-9-]+\.[a-z0-9-]+$`, input.key)
  msg := sprintf("flag key '%s' must be team.domain.purpose", [input.key])
}

deny[msg] {
  input.riskTier == "high"
  count(input.approvers) < 2          # two-person rule, mechanically enforced
  msg := sprintf("high-risk flag '%s' needs 2 approvers", [input.key])
}

deny[msg] {
  not data.teams[input.owner]         # owner must resolve to a real, active team
  msg := sprintf("flag '%s' has no valid owner", [input.key])
}
```

The governance program around the policy:

- **Naming convention** (`team.domain.purpose`) encodes ownership and type, enforced by policy, so the inventory is self-describing.
- **Ownership** resolves to active teams; orphaned flags (owning team dissolved) are auto-surfaced for reassignment or deletion.
- **RBAC and approvals** scale with risk tier — self-serve for 1% experiments, two-person rule for global kill-switches.
- **Audit + reason strings** are mandatory and immutable; this is your incident-forensics backbone.
- **Lifecycle enforcement** escalates overdue release toggles (ticket → CI warning → failing build) automatically.

This is the same instinct as the broader policy-as-code in [quality gates] and supply-chain work: humans set policy, machines enforce it uniformly.

---

## Core Concept 5 — Experimentation with Statistical Rigor

When flags drive A/B experiments, the flag platform becomes a measurement instrument, and getting the statistics wrong produces *confidently wrong* product decisions — arguably worse than no data. Professional ownership means the platform protects against the classic errors:

- **Stable, hash-based assignment.** A unit (user/account) is bucketed by `hash(unitId + experimentSalt)` so assignment is deterministic, uniform, and independent across concurrent experiments. The per-experiment salt prevents two experiments from systematically overlapping.
- **Sample Ratio Mismatch (SRM) detection.** If you intended 50/50 but observe 53/47 at scale, your assignment or logging is broken and the experiment is invalid — *stop and fix*, don't interpret. The platform should compute SRM automatically and refuse to report a result that fails it.
- **No peeking / proper sequential methods.** Repeatedly checking "is it significant yet?" and stopping at the first green inflates false-positive rate dramatically. Either fix the sample size and horizon in advance, or use sequential testing (always-valid p-values / group sequential designs) that's correct under continuous monitoring.
- **Guardrail metrics.** Even if the primary metric wins, automatically abort if a guardrail (latency, error rate, revenue, churn) regresses past a threshold — a conversion win that tanks latency is not a win.
- **Multiple comparisons.** Twenty metrics at p<0.05 yields ~one false positive by chance. Correct for it or designate a single primary metric up front.

```text
EXPERIMENT VALIDITY CHECKLIST
  assignment deterministic + uniform (hash + per-exp salt)
  SRM check passes (observed split ≈ intended)         → else INVALID, fix don't read
  sample size / horizon fixed in advance, OR sequential test used (no naive peeking)
  guardrail metrics defined + auto-abort on regression
  one primary metric (or multiple-comparison correction)
```

This is product-data territory; the platform's job is to make the *correct* analysis the default and the incorrect one hard. Tie guardrails to the `monitoring-alerting` skill's SLO thinking.

---

## Core Concept 6 — Consistency, Performance, and Cost at Scale

At org scale three engineering concerns dominate the architecture.

- **Consistency across a large fleet.** A flip propagates to thousands of instances over a *window*, not instantly. You bound it with streaming (sub-second) and accept that, during the window, instances disagree. For correctness-sensitive flags, design both values safe simultaneously (expand/contract) — the senior-tier discipline, now a platform-wide contract.
- **Performance on the hot path.** Evaluation must be local, in-process, microsecond-scale — never a per-request RPC. At hyperscale you also avoid every SDK opening a direct upstream connection: a **relay/proxy** (ld-relay, Unleash Edge) terminates one connection to the vendor and fans the ruleset out to thousands of SDKs, cutting upstream load and your dependency on the vendor's edge.

```text
                          ┌─────────────┐  stream ruleset   ┌──────────────────┐
   flag vendor / OSS ───► │ relay/proxy │ ────────────────► │ N service SDKs    │
   (1 upstream conn)      │  (you run)  │   (fan-out)        │ local eval (µs)   │
                          └─────────────┘                   └──────────────────┘
   benefits: 1 upstream dependency, cached LKG at the relay, no per-SDK vendor coupling
```

- **Cost.** SaaS flag vendors typically price on MAU/seats/events. Naive client-side SDK usage that sends every evaluation as an event can produce eye-watering bills and a privacy footprint. Control it: evaluate server-side where possible, sample or aggregate evaluation events, and model the cost curve *before* org-wide rollout — vendor cost at 10M MAU is a budget line, not a footnote, and is itself a build-vs-buy input.

---

## Core Concept 7 — Failure Modes of the Flag System Itself

The flag platform is tier-0: its own failures are outages with no deploy. Design for them explicitly.

- **Fail-static, never fail-closed-to-error.** If the backend is unreachable, SDKs serve **last-known-good** values from in-memory + on-disk cache. A flag-service outage must *not* flip every flag to its default (that's a mass behavior change) and must *not* throw. Persist LKG so even a cold start during the outage has values.
- **The default-served-rate alarm.** Instrument the fraction of evaluations returning the hardcoded default. A spike means the backend is failing for some fleet — a leading indicator that fires before users notice.
- **A bad ruleset push is a mass outage.** A malformed or wrong ruleset propagating to every SDK can break everything at once — the platform's own "Knight Capital." Mitigate with schema validation on publish, staged ruleset rollout (canary the *config push* itself), and a fast rollback of the ruleset.
- **Bound the blast radius of a bad flag change.** Blast-radius preview + staged high-risk changes + auto-rollback on guardrail breach. Apply `circuit-breaker-pattern` thinking: the relay/SDK should shed the upstream and run on cache rather than block requests waiting for a sick backend.
- **Don't make the flag system a hard dependency for starting up.** If a service can't boot without reaching the flag backend, you've coupled your cold-start availability to tier-0 infra. Bootstrap from a local file; refresh from the backend after.

> A flag platform that *fails open to defaults* is more dangerous than one that's simply down, because it silently changes behavior everywhere at once. Fail-static is the only acceptable mode.

---

## Core Concept 8 — The Org-Wide Flag-Debt Program

Flag debt at one team is a chore; across the org it's a measured program with budgets and owners.

- **Inventory reconciliation as a job.** Continuously diff the platform's flags against code references (linters/static analysis emitting flag keys). Platform-only flags = dead config to remove; code-only flags = unmanaged, must be registered. Surface both per team.
- **Org health metrics.** Track total live release toggles, median flag age, and overdue-flag count *per team*, on a dashboard leaders see. A rising trend is an early signal the cleanup loop is broken.
- **Enforced expiry with escalating teeth.** Overdue release toggle → auto-ticket → CI warning → failing build. Kill-switches/permission flags are explicitly exempt but must be *declared* long-lived (so the inventory distinguishes "intentionally permanent" from "forgotten").
- **Cleanup includes dead-code deletion.** Retiring a flag removes the branch *and* the now-unreachable code it guarded. A retired flag with surviving dead code is the Knight Capital condition; the program treats dead-code removal as part of "done."
- **Automation where possible.** Tools (e.g. PRs that strip a single flag's branches) make cleanup cheap enough that it actually happens. Cheap cleanup is the only cleanup that survives contact with deadlines.

---

## Real-World Examples

- **Vendor migration in a quarter, not a year.** An org on OpenFeature swaps SaaS vendors by writing one new provider and rolling it out service-by-service behind the same API. App teams change nothing. Without OpenFeature this would have been a multi-team rewrite of every call site.
- **The default-served-rate save.** A vendor regional outage starts; the default-served-rate dashboard spikes for one cluster minutes before any user-facing alert. Because SDKs fail-static on LKG, no behavior actually changes, and the team fails over the relay calmly.
- **SRM catches a broken experiment.** A "winning" pricing experiment shows a 51/49 split against an intended 50/50; the platform's SRM check marks it invalid. Investigation finds a logging bug double-counting one cohort. The wrong decision — ship the losing price — is averted.
- **Bad ruleset push, contained.** A targeting edit accidentally enables a heavy feature for all users. Because config pushes are staged (canary cohort first) and guardrails watch latency, propagation halts at the canary and auto-rolls-back the *config*, not just the code.

---

## Common Mistakes

- **Building the platform.** Underestimating multi-language SDKs, streaming, audit, experiment stats, and tier-0 ops. Buy or adopt OSS unless scale truly breaks the vendor.
- **Fail-open to defaults.** A flag-service outage that flips everything to defaults is a silent mass behavior change — worse than an explicit failure. Fail-static on LKG.
- **No vendor abstraction.** Coding directly against a vendor SDK everywhere makes migration a rewrite and locks in pricing. Mandate OpenFeature.
- **Treating flag changes as outside change management.** No audit, no blast-radius preview, no freeze — concentrating unreviewed prod risk in the least-watched channel.
- **Peeking at experiments.** Stopping at the first significant result without sequential methods inflates false positives into confident wrong decisions.
- **Ignoring cost and privacy.** Client-side per-evaluation events at scale produce huge bills and data exposure; model cost before org rollout.
- **Cleanup that leaves dead code.** Retiring the flag but not the guarded code recreates the Knight Capital loaded gun.

---

## Apply it

1. Define the user or business outcome that **Feature Flags & Progressive Delivery** should improve.
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

- Which measurable outcome justifies investing in Feature Flags & Progressive Delivery?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
- How would you decide whether to build or buy a feature-flag platform for a 300-engineer org?
- What does it take to trust the result of an A/B experiment run through your flag platform?
- The flag vendor has a regional outage — what should happen to your services, and what should you have designed?
- A targeting rule edit accidentally enables a feature for 100% of users instead of 5% — how should the platform have prevented it, and how do you respond?
- Design how a high-blast-radius flag change should flow end-to-end through your system — what are the components and checks?
