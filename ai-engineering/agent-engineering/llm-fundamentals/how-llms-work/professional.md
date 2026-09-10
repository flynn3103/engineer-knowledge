# How LLMs Work — Professional

<!-- level-focus -->
At professional level, focus on this question:

> Can you set a model policy — approved families, pinning discipline, upgrade evaluation — that keeps many teams from each re-learning the same drift lessons?

---

## Why a policy, not just advice

- Without a shared policy, every team independently discovers silent upgrades, cutoff surprises, and lock-in — each with a production incident as the tuition.
- The policy's job is to make the good habits from [Senior](senior.md) the default: pinning, version recording, eval-gated upgrades.

## Approved model families

- Maintain a short list of approved families with a named owner and the reason each is approved (capability, cost tier, residency, license).
- Approve **families and their intended use**, not specific hype-cycle versions — e.g., "a frontier Claude-class model for hard reasoning tasks; a small fast class for extraction; GLM/open-weight for residency-sensitive or self-hosted workloads."
- Adding a family requires a stated need no approved family meets — prevents approval sprawl.

## Pinning and upgrade rules

- Default: pin to dated snapshots in all production code.
- Upgrades are events, not drift: new snapshots get evaluated against each affected team's golden set before becoming the new default (see [Agent Evaluation](../../agent-evaluation/evaluation-fundamentals/)).
- Record in the policy who approves an upgrade and what evidence they need — a pass on the golden set plus no cost/latency regression is a defensible bar.

## Vendor concentration risk

- If every team runs on one provider, that provider's outage, price change, or policy change is an org-wide incident.
- Mitigations, in increasing cost: an abstraction layer (see [Senior](senior.md)), a tested fallback model in a second family, and for the most critical paths, a second provider actively used by at least one team.
- Decide explicitly how much concentration risk you're accepting — "we have a fallback nobody has tested" is not a mitigation.

## Keeping the policy alive

- Review quarterly: are the approved families still justified? Are teams pinning? Did any incident reveal a gap?
- Track one org-level metric — e.g., "percentage of production calls on pinned snapshots" — so policy adherence is visible, not aspirational.

## Common Mistakes

- **A policy that's a wiki page with no owner and no metric.** Drifts into fiction within months.
- **Approving models by name and version.** Forces a policy edit every release cycle; approve families and use-cases instead.
- **Treating the abstraction layer as the mitigation.** Untested fallbacks and unreviewed upgrades defeat it — the policy must require testing and evaluation, not just the capability to switch.
- **No exception path.** Teams with a genuine need route around the policy; give them a fast, documented exception process instead.

## Apply It

1. Write the approved-families list with owners and one-line justifications; define the bar for adding a family.
2. Set the pinning default and the upgrade-evidence bar; name who approves.
3. Pick the concentration metric (e.g., % production calls pinned, % testable fallback coverage) and put it on a dashboard.
4. Schedule the quarterly policy review.

## Verify Your Work

- Approved families have named owners and justification lines.
- Upgrade approval requires golden-set evidence, per the written bar.
- A concentration/adherence metric is tracked and visible.
- The policy has a review cadence and an exception path.

## Review Questions

- Why approve families and use-cases rather than specific model versions?
- What evidence should gate a model upgrade, and who owns that decision?
- Why is an untested fallback not a real mitigation for vendor concentration?
