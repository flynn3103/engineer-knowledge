# Testing — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run AI-feature testing as a durable, org-wide operating model — a required minimum before any prompt or model change ships, and a governance process for flaky non-deterministic tests — so every team ships tested changes without a central team gatekeeping every prompt edit?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Ownership Aligned to Who Can Actually Sustain It

The predictable failure mode: a central AI-platform or QA team tries to personally review every team's prompt change for test coverage, becomes the bottleneck the moment more than a few teams ship AI features, and the review queue grows faster than it clears. The split that scales assigns each layer to whoever has the standing context to maintain it:

| Layer | Owner | Responsibility |
|---|---|---|
| **Shared golden-set tooling and CI harness** | Platform / eval-infrastructure team | Build and maintain the framework that runs property checks against a model backend, reports pass rate, and wires into CI — so no team hand-rolls its own harness |
| **Each team's specific golden-set content** | The team that owns the feature | The actual input cases and property checks for their prompt or agent — because they know their traffic, their edge cases, their past incidents |
| **Flake policy and quarantine process** | A shared QA / eval governance group | Defines the flake budget, the quarantine workflow, and the statistical pass-rate policy for threshold-based assertions, applied consistently across teams |
| **Required-gate policy and its rollout** | The same governance group, with platform team execution | Decides what's mandatory before a change ships, and sequences the rollout so it doesn't break every team's velocity on day one |

This split keeps each owner within what they can actually sustain: no product team is asked to build or maintain a testing harness from scratch, and no central team is asked to know every team's traffic well enough to write their golden-set cases for them.

## Core Concept 2 — The Required Minimum Before a Change Ships

A durable gate needs to be specific and mechanically checkable, not a vague "make sure it's tested":

- **Golden-set pass rate at or above a defined threshold** (for example, 95% of cases passing their property checks against the production-grade model run) before a prompt or model change is eligible to ship.
- **Tool-call schema tests green** — every tool the workflow can invoke has passing schema-validity tests, with no exceptions, because a malformed tool call has a real side effect on the other end.
- **No regression in a tracked quality metric** beyond an agreed tolerance, measured against the team's [evaluation](../evaluation/README.md) pipeline — testing's pass/fail gate and evaluation's quality measurement are different systems answering different questions, and this is the one point where the gate explicitly depends on the other's output.
- **An explicit waiver path, not a silent bypass**, for the rare case a team needs to ship below threshold — a named owner signs off, the reason is recorded, and a follow-up ticket exists to bring the metric back above threshold on a deadline.

A gate without a waiver path gets bypassed informally the first time it blocks something urgent, which quietly turns it into a suggestion. A gate with an unlimited, unrecorded waiver path is the same thing with extra steps.

## Core Concept 3 — Flake Governance: A Budget, Not a Shrug

`senior.md` establishes that a flaky test either gets redesigned as a structural check or gets a documented statistical pass-rate policy — never silently ignored. At the org level, that needs process backing it, or it decays into exactly the ignored-noise outcome it's meant to prevent:

- **A documented flake budget** — for example, a test that fails more than 10% of its runs over a trailing 30-day window is automatically flagged for quarantine review, rather than staying in the suite indefinitely at whatever rate it happens to fail.
- **A quarantine process, not a delete-and-forget.** A flagged test moves to a non-blocking status (still runs, still reports, doesn't block merge) and gets a ticket with an assigned owner and a deadline — commonly 14 days — to either fix the underlying cause, redesign it as a pass-rate-over-N policy, or delete it as no longer meaningful.
- **Statistical pass-rate-over-N-runs as the default for borderline LLM-as-judge assertions**, org-wide, not something each team reinvents differently — a shared default (for example, 4-of-5 runs must clear threshold) means teams aren't each independently guessing at how much variance to tolerate.
- **An owner accountable for every quarantined test.** A quarantined test with no owner is indistinguishable from a deleted one that still burns CI minutes — it stops meaning anything and nobody is answerable for that.

## Core Concept 4 — Decomposing the Rollout

Mandating "every team's golden-set gate is required starting next quarter" produces the same rushed, unverified compliance any top-down infrastructure mandate produces. Decompose it instead:

1. **Pilot on one team, one feature** — ideally one that's already had a real regression reach production, so the motivation is concrete and the win is measurable.
2. **Build the shared harness from what the pilot actually needed**, not from a spec written in advance — the pilot reveals which property-check types, which CI hooks, and which reporting format teams actually use.
3. **Run the gate as advisory (non-blocking) first**, across a wider set of teams, to see how many changes would currently fail it — this surfaces the real size of the gap without breaking anyone's merge on day one of the policy existing.
4. **Turn the gate blocking for new prompt/agent changes only**, not retroactively for every feature already in production — existing features get a scheduled remediation window to build their golden set, not an overnight requirement.
5. **Expand team by team**, tracking adoption as a fraction, not a binary migrated/not-migrated status.

Each step stays reversible: if the shared harness needs a new property-check type after the third team adopts it, that's an addition, not a redesign, because nothing downstream assumed the first version was final.

## Core Concept 5 — Migration and Governance Risks

Rolling this out across an org with existing, ungated AI features surfaces risk a single pilot doesn't show:

- **Legacy features with no golden set at all.** Features shipped before the gate existed often have no representative input set and no property checks — discovery starts with an inventory of which features have zero test coverage of this kind, not with asking teams to self-report.
- **Model-version drift with no test watching for it.** A provider updating a model behind an alias a team references by name (rather than a pinned snapshot) can silently change behavior with no code change to trigger a re-test — the nightly golden-set run against the production model (`senior.md`, Core Concept 3) is the mechanism that would catch this, and a feature with no nightly run has no defense against it at all.
- **A blocking gate turned on for the whole existing fleet at once.** Breaks many teams' merges simultaneously over gaps that predate the policy and were never that day's engineer's decision to fix — gate new changes first, remediate the existing fleet on a scheduled window, exactly as in Core Concept 4.
- **Compliance-sensitive banned-pattern checks owned inconsistently.** A property check for PII, regulated financial language, or medical-advice boundaries needs a single, org-reviewed definition reused across teams' golden sets, not each team writing its own version of "no PII" independently and inconsistently.

## Core Concept 6 — Outcome Measures and Exit Conditions

```yaml
# Program health dashboard, reviewed quarterly.
metrics:
  gate_coverage: "% of prompt/agent changes that went through the golden-set gate before shipping"
  golden_set_coverage: "features with an owned, currently-passing golden set / total shipped AI features"
  quarantine_dwell_time: "median days a flaky test spends quarantined before being fixed or deleted"
  gate_bypass_rate: "% of shipped changes that used the waiver path instead of clearing the gate"
exit_conditions:
  pilot_to_expansion: "pilot feature clears the gate at >= 95% pass rate, and the platform team can run the harness against a new team's feature without that team building tooling from scratch"
  program_maturity: "gate_coverage > 90% of active features, and quarantine_dwell_time trending down for two consecutive quarters"
```

`quarantine_dwell_time` is the number that most directly proves the flake-governance process is real rather than theater: a program can report a large flake budget and a documented quarantine process while tests actually sit quarantined for months with no owner acting on them. High `gate_coverage` on its own can also mislead — a change that technically went through the gate but used the waiver path every time has coverage without an actual quality bar. Track `gate_bypass_rate` alongside `gate_coverage` so a rising waiver rate shows up as a signal, not a footnote.

## Core Concept 7 — The Cross-Team Contract

Once many teams ship against a shared gate, "tested" has to mean the same specific thing everywhere, formalized the way an internal API contract is formalized:

- A written definition of "tested" that lists exactly what's required — golden-set pass rate, tool-call schema tests, quality-metric non-regression — so no team is guessing at what's expected or discovers a missing requirement only when a release is blocked.
- The waiver path (Core Concept 2) is a real process with a named approver, not an informal "ask in Slack," and every waiver is logged and visible to the governance group.
- A breaking change to the shared harness — a new required property-check type, a change to how pass rate is computed — goes through advance notice to consuming teams, the same as a breaking API change, because for a team relying on the old behavior, it functionally is one.
- Accountability follows ownership: if a regression ships because a team's golden set didn't cover the input that broke, that's the owning team's gap to close; if it ships because the shared harness itself reported a false pass, that's the platform team's.

## Real-World Examples

- **A pilot's concrete regression funds the harness build.** A feature that shipped a disclaimer-dropping regression becomes the pilot; building its golden set around that exact past incident gives the platform team a demonstrated catch to point to when proposing the gate for other teams, instead of a policy imposed with no evidence it works.
- **Advisory-first rollout avoids a fleet-wide break.** Running the gate as non-blocking across ten teams for a month shows three of them would currently fail outright — each gets a scheduled remediation window before the gate turns blocking for their new changes, instead of every merge in those three teams failing the day the policy goes live.
- **Coverage looks strong, quarantine dwell time doesn't move.** An org reaches 90% gate coverage, but a review shows several flaky tests have sat quarantined for over two months with no assigned owner — the next quarter's investment shifts from expanding coverage to enforcing the quarantine deadline that already exists on paper.

## Common Mistakes

- **Centralizing golden-set content ownership in one platform team.** That team cannot sustain writing test cases for every other team's specific traffic and edge cases — the queue becomes the actual bottleneck.
- **Mandating the gate as blocking for the entire existing fleet on day one.** Breaks many teams simultaneously over gaps that predate the policy; gate new changes first, remediate on a schedule.
- **Measuring gate coverage without also measuring the waiver bypass rate.** A change that always uses the waiver path counts as "gated" on a dashboard while clearing no actual quality bar.
- **A quarantine process with no owner or deadline attached to each entry.** A quarantined test with nobody accountable for it is functionally deleted, just still consuming CI time.
- **Letting each team invent its own definition of a banned-pattern check for compliance-sensitive content.** Produces inconsistent, unreviewed coverage for exactly the checks that most need to be consistent.
- **Treating a shared harness change as internal refactoring instead of a breaking-change notice to consumers.** Silently changes what "gate passed" means for every team relying on it.

---

## Apply it

1. Inventory the AI features you have visibility into and identify which ones have zero golden-set coverage today.
2. Design the required-minimum gate (Core Concept 2) for one feature, including its waiver path and who the named approver is.
3. Write the flake budget and quarantine process (Core Concept 3) as a short policy document: the threshold that triggers quarantine, the deadline for resolution, and who owns unassigned quarantined tests by default.
4. Define the four outcome measures from Core Concept 6 for your org, with real current numbers if you can get them, even rough ones.
5. Draft the cross-team contract's one-paragraph definition of "tested" — the exact list of what's required before a prompt or agent change ships.

## Verify your work

- The inventory names specific features with no coverage, not a general impression that "some features are probably untested."
- The gate's waiver path has a named approver and a required follow-up deadline, not an open-ended exception.
- The quarantine policy specifies a concrete threshold and a concrete deadline, not "review flaky tests periodically."
- Each outcome measure is a rate or duration with a clear numerator and denominator, not a vague statement like "better test coverage."
- The "tested" definition is specific enough that two different teams reading it would agree on whether a given change qualifies.

## Review questions

- Why does centralizing golden-set content ownership in one platform team tend to fail as the number of teams grows?
- What does a rising gate-bypass rate reveal that gate-coverage alone does not?
- Why can turning a golden-set gate blocking for the entire existing fleet at once cause more harm than gating only new changes first?
- What turns a flake budget and quarantine process into something real, rather than a documented policy nobody enforces?
- Why does a shared golden-set harness change need the same advance-notice discipline as a breaking API change?

---

*Part of [Testing](README.md) → [AI Evaluation](../README.md).*
