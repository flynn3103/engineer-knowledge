# Agentic Techniques — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you define org-wide standards for which agentic techniques are mandatory at which risk tier, and run a review process that decides — and periodically re-decides — how much autonomy an agent is allowed, without either a rubber-stamp process or a bottleneck that blocks every team on every action?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — A Standard Risk-Tier Framework, Shared Across Teams

The senior-level tiering (reversibility, exposure, blast radius) works for one team designing one gate. At org scale, every team inventing its own tiering vocabulary means a "Tier 2" in one team's system means something entirely different from another's — which makes cross-team risk comparison and audit impossible. A shared framework fixes the vocabulary once:

| Tier | Definition | Mandatory technique |
|---|---|---|
| **Tier 1 — Read-only** | No state change of any kind | None required |
| **Tier 2 — Reversible write** | Changes state, but cheaply and fully reversible (a preference update, a non-final status change) | Mandatory self-check / structural validation before the write executes |
| **Tier 3 — Hard-to-reverse or financial** | Refunds, account changes, anything with real cost to undo | Mandatory human-in-the-loop approval gate + full audit log |
| **Tier 4 — Irreversible or high blast radius** | Production data modification, legally binding communication, actions affecting many records at once | Mandatory HITL gate + dual control (two independent approvers) + rate limiting |

Every team classifies their own actions into this shared framework — the framework doesn't change per team, but the specific classification of "is refunding a subscription Tier 3 or Tier 4 for us" is a judgment product teams make, with security/risk sign-off, because they know their own domain's actual stakes.

## Core Concept 2 — Ownership Split

| Layer | Owner | Responsibility |
|---|---|---|
| **The tier framework itself and its mandatory-technique matrix** | Security/risk governance team | Defines and evolves the tiers and what's mandatory at each, org-wide |
| **Gate infrastructure** (the mechanics of proposing, reviewing, approving/rejecting, timing out) | Platform/AI-infra team | Builds the reusable gate component once, so no team hand-rolls its own approval-queue UI and timeout logic |
| **Action classification into tiers, and the plan/reflect logic itself** | Product teams | Classify their own actions (with security review sign-off for anything landing in Tier 3 or 4), and own the specific reflection checks and plan structure for their domain |
| **Autonomy threshold review** | A joint body — security plus the product team's own data | Neither party unilaterally raises an auto-approve threshold; it requires both the evidence (from the product team's logged approvals) and the sign-off (from the risk owner) |

## Core Concept 3 — The Review Process for a New High-Risk Action

Before a new Tier 3 or Tier 4 agent action goes live, it goes through a defined, lightweight review — not a rubber stamp, not a months-long committee:

1. **Tier classification proposal** from the product team, with their reasoning against the shared framework's definitions.
2. **Security sign-off** on the classification itself — is this genuinely Tier 3, or does its blast radius actually put it in Tier 4?
3. **Confirmation the mandatory technique for that tier is actually implemented** — for Tier 3, does a real gate exist with a real timeout and fallback, not a planned one?
4. **A defined initial autonomy state** — new Tier 3/4 actions launch fully gated (0% auto-approve) by default, per the senior-level "autonomy is earned" principle, now made a hard org rule rather than a team-by-team choice.
5. **A scheduled first review date** (e.g., 60 days post-launch) to evaluate the logged approval/rejection data and decide whether any narrow auto-approve threshold is justified.

## Core Concept 4 — Periodic Autonomy Review, Not a One-Time Decision

An autonomy threshold granted once and never revisited drifts out of sync with reality — the action's risk profile can change (a policy change makes what was a routine refund reason now require case-by-case judgment), or the model backing the agent changes (a model upgrade or prompt change alters its actual error rate in ways the old approval data no longer reflects). A recurring review — quarterly is a reasonable default — re-examines:

```yaml
autonomy_review:
  cadence: quarterly
  per_gated_action_tier_3_plus:
    - current_auto_approve_rate: "% of proposals executed without human review"
    - rejection_rate_on_gated_proposals: "% of human-reviewed proposals rejected"
    - post_hoc_error_rate: "% of auto-approved actions later found incorrect, via audit sampling"
    - decision: "widen / hold / narrow the auto-approve threshold, with written justification"
```

The critical number is `post_hoc_error_rate` on the *auto-approved* population specifically, sampled after the fact — not just the human-reviewed rejection rate, which only tells you about the gated population. An auto-approve threshold can look safe purely because nobody is checking the actions that skipped review; the periodic audit sample is what actually tests that assumption.

## Core Concept 5 — Rollout Decomposition

Rolling out a new risk-tier framework and mandatory-technique matrix across an org with many existing agents surfaces the same rollout risk as any infrastructure standard:

1. **Pilot the framework with one team's existing Tier 3 action**, applying the classification and review process retroactively to see if the framework's definitions actually fit a real case, before mandating it broadly.
2. **Publish the matrix as advisory first**, surfacing which existing agent actions in the fleet are Tier 3/4 but currently ungated, without breaking anything on day one.
3. **Turn the matrix blocking for newly launched actions only**, giving existing ungated high-risk actions a scheduled remediation window instead of an overnight shutoff.
4. **Expand tier classification review team by team**, tracking the fraction of Tier 3/4 actions with a compliant gate in place, not a binary "adopted the framework or not."

## Core Concept 6 — Outcome Measures and Exit Conditions

```yaml
program_health:
  tier3_plus_gate_coverage: "Tier 3/4 actions with a compliant HITL gate / total Tier 3/4 actions"
  post_hoc_error_rate_on_auto_approved: "sampled error rate among auto-approved actions, trended quarterly"
  review_turnaround_time: "median days from classification proposal to security sign-off"
  gate_fatigue_signal: "reviewer approval rate on gated items — a rate near 100% with declining review time per item suggests rubber-stamping"
exit_conditions:
  pilot_to_expansion: "pilot action's gate coverage is complete, post_hoc_error_rate_on_auto_approved is at or below the agreed threshold for one full quarter, and classification can proceed without security's direct involvement in routine cases"
  program_maturity: "tier3_plus_gate_coverage > 95%, and post_hoc_error_rate_on_auto_approved stable or improving for two consecutive quarters"
```

`gate_fatigue_signal` matters because a review process that looks healthy on coverage and turnaround can still be failing silently if reviewers are rubber-stamping — the senior-level failure mode, now tracked as an org-level metric rather than something a single team notices anecdotally.

## Core Concept 7 — Cross-Team Contracts and Sustained Delivery

- The shared gate infrastructure publishes a support contract like any internal platform dependency — current version, deprecated behavior still supported, and a date it stops being supported — so teams building on it plan upgrades rather than get surprised.
- A change to the tier framework itself (e.g., splitting Tier 3 into two tiers because financial and legal-exposure actions turned out to need different mandatory techniques) goes through advance notice to every team with actions classified in the affected tier, since it can change what technique is mandatory for actions already in production.
- New agent actions default to the framework from day one — tier classification is part of an action's design review, not a retrofit applied only after an incident makes it clear a gate was missing.
- The periodic review from Core Concept 4 is calendared and owned, not ad hoc — a review that only happens "when someone remembers" reliably doesn't happen.

---

## Real-World Examples

- **A retroactive pilot classification surfaces a tier the team hadn't considered.** A team's existing refund action, treated informally as "needs approval sometimes," gets run through the shared framework for the first time and is classified Tier 4 rather than Tier 3, because the actual blast radius (a batch-refund code path triggered under certain conditions) affects many orders at once — a distinction the team's own informal process had never separated out.
- **A quarterly audit catches an auto-approve threshold that had drifted unsafe.** A narrow auto-approve rule granted after strong initial evidence continues running unchanged for a year; a scheduled post-hoc error-rate sample finds the error rate has crept up after a prompt change altered the agent's behavior in ways nobody re-validated. The threshold is narrowed back pending re-review — exactly the outcome the periodic review process exists to catch, versus a one-time grant that's never revisited.
- **Gate coverage looks complete, but the fatigue signal reveals a rubber-stamp process.** An org reports 98% Tier 3/4 gate coverage, but the gate-fatigue metric shows approval rates near 100% with review times dropping steadily; the next quarter's focus shifts from coverage outreach to redesigning the review queue so high-stakes items are visually and procedurally separated from routine ones.

## Common Mistakes

- **Letting every team define its own risk tiers.** Makes cross-team audit and comparison impossible, and lets a team's own "Tier 3" quietly mean something weaker than another team's.
- **Treating an autonomy threshold as a one-time grant.** Risk profiles and model behavior both drift; a threshold that was safe when granted can become unsafe without anyone noticing unless it's periodically re-audited.
- **Measuring only gate coverage, never post-hoc error rate on the auto-approved population.** High coverage on the gated population tells you nothing about whether the actions that skipped the gate are actually safe.
- **Rolling the framework out as blocking for the entire existing fleet at once.** Forces emergency remediation on teams whose ungated action predates the standard; gate new launches first, remediate existing ones on a scheduled window.
- **No separate signal for reviewer fatigue.** A review process can look fully healthy on coverage and turnaround time while quietly rubber-stamping everything that reaches it.

---

## Apply It

1. Map your org's (or a plausible org's) existing high-stakes agent actions onto the shared four-tier framework, and identify any that are Tier 3/4 but currently ungated.
2. Design the review process from Core Concept 3 concretely: who proposes, who signs off, what the default initial autonomy state is, and when the first scheduled review happens.
3. Define the quarterly autonomy-review metrics from Core Concept 4 for one specific gated action, including how you'd actually sample for post-hoc error rate on the auto-approved population.
4. Draft the exit condition that would justify expanding a pilot team's framework adoption to the rest of the org.
5. Design the gate-fatigue signal specifically — what data would actually reveal reviewers rubber-stamping, distinct from data that just shows the gate exists and is being used.

## Verify Your Work

- The tier mapping uses the shared framework's definitions consistently, not a per-team reinterpretation of what "Tier 3" means.
- The review process names specific roles (who proposes, who signs off), not "the team" as an undifferentiated unit.
- The post-hoc error-rate sampling method is concrete enough to actually execute — a real sampling approach, not "we'll check sometimes."
- The exit condition is falsifiable, with a specific number and duration, not "once we're confident."
- The gate-fatigue signal is distinct from coverage and turnaround metrics, and would actually catch a reviewer rubber-stamping rather than reading carefully.

## Review Questions

- Why does letting every team define its own risk tiers undermine org-wide audit and comparison?
- What does post-hoc error rate on the *auto-approved* population reveal that the rejection rate on gated proposals cannot?
- Why should a new Tier 3/4 action launch fully gated by default, rather than starting with whatever autonomy level the team believes is warranted?
- What's the risk of rolling a new mandatory-technique matrix out as blocking for the entire existing fleet at once?
- How would a gate-fatigue signal differ from a simple gate-coverage metric, and why does an org need both?
