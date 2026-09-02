# Evaluation — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run evaluation as a durable, org-wide operating model — shared infrastructure, a documented evidence bar before anything ships, and eval-as-code versioned alongside the system it evaluates — so that trust in a quality claim doesn't depend on which team made it?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

Part of [Evaluation](README.md).

---

## Core Concept 1 — Ownership Aligned to Cognitive Load

The predictable failure mode at org scale: every team hand-rolls its own scoring scripts, its own definition of "faithfulness," and its own ad hoc judge prompt, so a "92% quality score" from one team and an "88%" from another are not comparable numbers at all — they're different measurements wearing the same units. The split that scales distributes ownership by who actually has the context to sustain each decision:

| Layer | Owner | Responsibility |
|---|---|---|
| **Shared eval harness/library** | Central eval-infrastructure team | Build and maintain the common tooling that runs eval sets, calls judges, computes agreement metrics, and stores results in one auditable format — so every team's numbers are comparable by construction, not by convention |
| **Team-specific rubrics and eval-set content** | The team that owns the product surface | The actual questions, criteria, and examples that define quality for their system — they know their users and their failure modes; a central team does not |
| **Deploy-gate policy** | A cross-functional governance group (quality/safety) | What evidence is *required* before a change ships — the minimum bar every team's gate must meet, even though the specific rubric content is team-owned |
| **Judge calibration standards** | Central eval-infrastructure team, in partnership with each team | The methodology (sample size, agreement threshold, recalibration cadence) is standardized centrally; the actual calibration run against each team's rubric is the team's responsibility to execute and record |

This mirrors a familiar organizational split for a reason: the same failure — a central team trying to personally review every team's specifics — happens whenever ownership isn't matched to who holds the relevant context. A central team cannot know every product surface's rubric well enough to write it; a product team cannot be expected to independently reinvent agreement-rate methodology and judge-bias mitigation from scratch.

## Core Concept 2 — Shared Infrastructure as a Paved Road

A shared harness exists to make the comparable, auditable choice the default one, not something every team has to independently rebuild. Concretely, this is the kind of tooling an eval-infrastructure team owns or adopts: an open-source or internal library that standardizes how eval sets are defined, how judges are invoked, and how results are stored (**promptfoo** and **DeepEval** are examples of frameworks built for exactly this — declarative eval-set definitions plus pluggable scorers; **Braintrust**, **LangSmith**, and **Langfuse** offer eval-adjacent dataset and tracing features that connect evaluation results back to the underlying traces).

```yaml
# eval-config.yaml — shared harness format, team fills in specifics
suite: support-bot-faithfulness
owner: support-team
eval_set: evals/support-bot/faithfulness-v3.jsonl   # versioned, see Core Concept 5
judge:
  rubric: rubrics/faithfulness-v2.md
  model: judge-model-v1
  output_schema: score+reasoning+claims
gate:
  metric: faithfulness_score
  threshold: 0.85
  floor: true          # independent hard floor, never blended into an average
calibration:
  last_checked: 2026-07-15
  agreement_within_1pt: 0.91
  recheck_cadence_weeks: 6
```

The point of a shared schema like this is that a governance reviewer, or another team's engineer, can open any team's `eval-config.yaml` and understand what's gated, what threshold applies, and when it was last calibrated — without learning that team's bespoke scoring script first.

## Core Concept 3 — The Evidence Bar Required Before Shipping

A durable program needs a written, minimum evidence requirement — not a norm everyone is assumed to follow, an actual documented gate every team's pipeline must satisfy before a change reaches production:

1. **Offline eval score at or above the team's stated threshold**, run against the current version of the team's eval set.
2. **No drop on any dimension marked as a safety or faithfulness floor**, evaluated independently of the blended score (see [Evaluation — Senior](senior.md), Core Concept 2).
3. **Judge-human calibration checked within the last N weeks** (a reasonable default: 6–8 weeks, or immediately after any rubric or judge-prompt change) — a judge that hasn't been recalibrated recently is treated as unvalidated, regardless of its last known agreement rate.
4. **The eval-set and rubric versions used are recorded against the specific deployed change** — so six months later, "which eval set validated this exact prompt version" has a real, retrievable answer rather than "presumably whatever we were using around then."

A change missing any of these four is not eligible to ship through the standard path — it requires an explicit, logged exception with a named approver, the same discipline as a security or compliance exception in any other engineering process.

## Core Concept 4 — Eval-as-Code, Versioned Alongside the System

Eval sets and judge prompts live in version control next to the prompts and code they evaluate — not in a shared spreadsheet, not in someone's local notebook. This buys two specific things:

- **A breaking eval-set change is reviewed like a breaking API change.** Removing examples, loosening a threshold, or rewriting a rubric's definition changes what "passing" means; routing that through the same pull-request review as a production code change means a rubric can't be quietly softened to make a stuck deploy pass.
- **Traceability**: for any deployed prompt or model version, the exact eval-set version and judge-prompt version that validated it before shipping is recoverable from version history, the same way a deployed binary's commit SHA is recoverable. This is what makes Core Concept 3's fourth requirement actually auditable rather than a claim nobody can check.

```text
repo/
  prompts/
    support-bot/
      v12/prompt.txt
  evals/
    support-bot/
      faithfulness-v3.jsonl     # eval set, versioned
      rubrics/faithfulness-v2.md
  deploy-manifest.yaml           # records: prompt v12 shipped, validated by
                                  #   faithfulness-v3.jsonl + rubric v2,
                                  #   calibration checked 2026-07-15
```

## Core Concept 5 — Decomposing the Rollout

Mandating "every team adopts the shared harness and the four-point evidence bar by end of quarter" produces the same theater any top-down infra mandate produces — rushed, unverified adoption to hit a deadline. Decompose it instead:

1. **Pilot with one team** whose current evaluation process is informal or inconsistent, so the improvement is concrete and measurable, not speculative.
2. **Build the harness's actual shape from what the pilot needs**, not from a spec written in a vacuum — the pilot reveals which fields the shared config format actually needs and which are premature.
3. **Roll the evidence-bar requirement out as advisory first** — reported on every deploy, blocking none — so teams can see how many of their current changes would fail the bar before it has teeth.
4. **Turn it blocking for new changes only**, not retroactively for whatever's already in production, so a backlog of unvalidated existing prompts doesn't halt current work; give existing systems a scheduled window to backfill evidence.
5. **Expand team by team**, tracking adoption as a fraction, and treat each new team's onboarding as a chance to refine the harness rather than a rerun of the same fixed process.

## Core Concept 6 — Outcome Measures

```yaml
# Program health dashboard, reviewed quarterly
metrics:
  evidence_coverage: "% of shipped prompt/model changes with recorded eval evidence / total shipped changes"
  calibration_freshness: "% of active judges with calibration checked within the required N-week window"
  judge_human_agreement: "agreement-within-1pt rate, tracked over time, per judge/rubric — not just at launch"
  eval_set_staleness: "median age (in shipped changes, not just calendar time) since an eval set last had a new example added"
exit_conditions:
  pilot_to_expansion: "pilot team's evidence_coverage reaches 100% for two consecutive weeks, and the harness runs without the eval-infra team's direct involvement"
  program_maturity: "evidence_coverage > 90% org-wide, and judge_human_agreement stable or improving for two consecutive quarters"
```

`judge_human_agreement`, tracked as a trend rather than a one-time launch number, matters most: a program can report high `evidence_coverage` — every team dutifully runs its gate — while the judges behind those gates have quietly drifted out of calibration, making the "evidence" decorative rather than real. Coverage proves the paved road is being used; agreement trend proves it's still measuring what it claims to measure.

## Core Concept 7 — Cross-Team Contract and the Risk of Eval-Set Staleness at Scale

A shared eval set is only a genuine quality bar as long as it keeps being refreshed. This is Goodhart's law at governance scale: the moment an eval set stops changing, engineers under deadline pressure start (even unintentionally) tuning prompts specifically to pass *that* fixed set rather than to generalize — a set nobody refreshes becomes something teams learn to game rather than a real measurement, exactly as a public benchmark a model was tuned against stops measuring genuine capability. The same applies to a team's own eval set: if it's never updated with new production examples, especially the failing ones surfaced by online monitoring (see [Evaluation — Senior](senior.md), Core Concept 4's feedback loop), passing it stops correlating with being good and starts correlating with being familiar.

The cross-team contract that keeps this from quietly happening:

- Every shared or team-owned eval set has a **named owner** responsible for refreshing it, not an assumption that "someone" will notice it's gone stale.
- **A held-out portion of every eval set is never used for prompt tuning** — only for final gate checks — so a change that's been iterated against the visible portion still has to pass a set it was never directly optimized against.
- **New failing examples from online monitoring get added on a defined cadence** (not "eventually, if someone remembers"), closing the loop the senior level identified as a mechanism, not just an intention.
- Accountability follows ownership: if a shipped change caused real user harm that an eval set should have caught, and the set was known to be stale (last refreshed long before the incident, or never received the failing examples from a prior similar incident), that's the eval-set owner's action item; if the harness itself produced an incorrect verdict due to an infrastructure bug, that's the eval-infrastructure team's.

---

## Real-World Examples

- **A pilot's evidence gap justifies expansion.** A team known for shipping prompt changes with no consistent evaluation becomes the harness pilot; running its first month of changes retroactively through the four-point evidence bar shows a third would have failed the calibration-freshness requirement alone — a concrete, specific number that justifies expanding the program rather than a mandate imposed with no demonstrated need.
- **Coverage looks strong, agreement quietly erodes.** An org reaches 90% evidence-coverage across teams, but a quarterly review of `judge_human_agreement` shows three teams' judges have drifted below the 85% threshold for two consecutive checks without anyone noticing, because nothing was tracking the trend, only whether a calibration check happened at all — the next quarter's investment shifts from coverage outreach to enforcing the agreement-trend metric itself.
- **A held-out set catches a subtly overfit prompt.** A team iterates a prompt against their visible eval set for weeks, reaching a near-perfect score, but the held-out portion — never used for tuning — shows a real regression the visible portion missed, because the visible set had quietly become the target rather than the measurement.

## Common Mistakes

- **Centralizing rubric-writing in the eval-infrastructure team.** That team cannot know every product surface's failure modes well enough to write its rubrics, and becomes a bottleneck the same way a central reviewer of every team's Dockerfile would.
- **Mandating full adoption before piloting.** Skips the step where the harness's actual required shape is discovered from a real team's needs instead of guessed at.
- **Turning the evidence bar blocking for the entire existing fleet of prompts at once.** Breaks many teams' ability to ship over gaps that predate the policy and were never anyone's fault to have fixed in the moment.
- **Measuring only evidence coverage, never calibration freshness or the agreement trend.** High coverage with quietly stale judges looks like program success on a dashboard while the underlying "evidence" has stopped meaning what it claims to.
- **Letting an eval set go unrefreshed indefinitely.** Turns a genuine quality bar into something teams learn to pass without actually being good, exactly as an unrefreshed public benchmark stops measuring real generalization.
- **No held-out portion of the eval set.** Every example is visible during tuning, so a prompt can be iterated straight at the metric rather than at real quality, and nothing catches the difference.

## Apply it

1. Draft the four-point evidence bar from Core Concept 3 as a literal checklist your org (or a hypothetical one) would require before a prompt or model change ships, naming a concrete threshold and recalibration cadence.
2. Design the ownership split from Core Concept 1 for your context: name who would own the shared harness, who owns rubric content per team, and who owns the gate policy itself.
3. Write the outcome-measure YAML from Core Concept 6 with real numerator/denominator definitions for your context, and state the specific exit condition that would justify expanding a pilot beyond one team.
4. Identify one eval set (real or hypothetical) that has gone unrefreshed, and design the held-out-portion and refresh-cadence mechanism that would prevent it from being gamed going forward.
5. Write a one-paragraph cross-team contract stating who is accountable when a shipped change causes harm an eval set should have caught, distinguishing a stale-eval-set failure from a harness-infrastructure failure.

## Verify your work

- The evidence bar is a literal checklist with concrete thresholds and a stated recalibration cadence, not a general aspiration to "evaluate well."
- The ownership split names a specific owner for each layer (harness, rubric content, gate policy), with no layer left implicitly "everyone's responsibility."
- The outcome measures have real numerators and denominators, and at least one (agreement trend or eval-set staleness) is tracked over time, not just as a point-in-time snapshot.
- The held-out-portion mechanism is concrete enough that someone could audit whether a given eval set actually has one, not just claims to.
- The accountability contract distinguishes a stale-eval-set failure from an infrastructure failure, with a different owner for each.

## Review questions

- Why does centralizing rubric-writing in a single eval-infrastructure team tend to fail as the number of product teams grows?
- What does a stalled or declining judge-human agreement trend reveal that a high evidence-coverage number alone does not?
- Why can turning an evidence-bar requirement blocking for an entire existing fleet of prompts at once cause more harm than gating only new changes first?
- How does a held-out portion of an eval set protect against the same failure mode as an org gaming a public benchmark?
- What specifically makes "which eval-set version validated this deployed prompt version" answerable six months later, and why does that matter?
