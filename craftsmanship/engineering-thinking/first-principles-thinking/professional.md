# First-Principles Thinking — Professional

**Your question:** How do I institutionalize assumption-challenging without paying its cost on every single decision?

Senior level taught you to classify constraints and choose analogy vs. first principles for one redesign. At professional/staff level, you can't personally trace every decision's "why" chain, and you shouldn't want to — most decisions in an organization are low-stakes, reversible, and well-precedented, and re-deriving them from scratch is pure waste. The job now is designing a *practice*: a way for the organization to apply deep assumption-tracing exactly where it pays for itself, skip it everywhere else, and know — with evidence, not vibes — whether the policy is working.

## The method: Tiered assumption-review

Not every decision deserves a why-chain. Build a rubric that sorts decisions into tiers, and attach a review requirement to each tier — not to every decision uniformly.

**Tier a decision by:**
- **Blast radius** — how many teams, systems, or customers does it touch if wrong?
- **Reversibility** — can it be undone in hours, or does it require a migration measured in months?
- **Precedent depth** — has this exact combination of constraints been faced and resolved before, inside or outside the org?
- **Cost of being wrong** — silent data loss and compliance breaches cost more than a slow page.

| Tier | Profile | Review requirement |
|---|---|---|
| **Low** | Small blast radius, cheap to reverse, well-precedented | No why-chain required. Pattern library / precedent is the default. Document the choice, not the reasoning behind every constraint. |
| **Medium** | Touches one team's system, reversible in weeks, mostly precedented with one or two open questions | Lightweight why-chain: name the constraints that are genuinely novel; everything else can cite precedent directly. |
| **High** | Crosses team boundaries, expensive or slow to reverse, sets a pattern others will copy, touches compliance or a signed contract | Full why-chain required in the design doc: every governing constraint classified (see senior.md's four buckets), evidence cited, analogy vs. first-principles decision stated explicitly per piece. |

The tiering itself is the lever. Get it right, and expensive assumption-tracing happens on the handful of decisions where it matters, while the other 90% of decisions move at precedent speed.

## Build the why-chain requirement into design review

For high-tier decisions, require the design doc or RFC to include a section that a reviewer can actually check, not just a paragraph asserting rigor:

```
Constraint classification:
  - [Constraint]: [physical / regulatory / contractual / organizational habit]
    Evidence: [measurement, document, or log query that supports this]
    Blank-slate test result: [would this hold if we rebuilt today?]

Decomposition:
  - [Piece of the design]: [analogy — cite precedent] or [first principles — state why no precedent fits]

Reversibility:
  - If this decision is wrong, what does undoing it cost, and who decides to undo it?
```

A reviewer's job is not to re-derive the whole design from scratch — it's to spot-check: is a claimed "genuine constraint" actually genuine? Is a claimed "no precedent fits" actually true, or is there a precedent the author didn't look for? This keeps the review cost bounded even though the decision is consequential.

## The real cost of first-principles thinking

Teach this explicitly, because unmanaged enthusiasm for "question everything" is itself a failure mode:

- **It's slow.** Tracing a why-chain to bedrock, gathering evidence, and deriving a solution from fundamentals takes real engineering time that a precedent-based decision doesn't.
- **Re-deriving solved problems is waste, not rigor.** If the org has already verified that a message queue, an auth pattern, or a retry strategy works under these exact constraints, redoing that verification produces the same answer at a real cost and zero new information.
- **It doesn't scale to every decision.** An organization that requires a why-chain for every choice grinds to a halt; the practice only pays for itself on the decisions where being wrong is expensive.

**When precedent is the right tool:**
- The problem is well-precedented and the constraints have already been checked to match.
- The decision is cheap to reverse if it turns out to be wrong.
- Someone specific already paid the verification cost, and that verification is still current.

**When precedent is a trap:**
- The precedent was set under constraints that have since changed (different scale, different regulatory environment, different team).
- Nobody currently on the team can explain the original justification — it's been copied forward past the point anyone remembers why.
- Precedent is being used to avoid an uncomfortable but necessary redesign, not because the constraints genuinely still match.

## Rollout: phased introduction of tiered review

**Phase 1 — Frame**
- [ ] Write the tiering rubric (blast radius, reversibility, precedent depth, cost of being wrong) as a one-page document.
- [ ] Identify 5-10 recent decisions across tiers as calibration examples, so reviewers have a shared reference.

**Phase 2 — Build the template**
- [ ] Add the constraint-classification, decomposition, and reversibility sections to the design-doc/RFC template for high-tier decisions only.
- [ ] Write down explicitly what does *not* require this template (low- and medium-tier decisions), so teams don't over-apply it out of caution.

**Phase 3 — Pilot**
- [ ] Run the tiered template on 5-10 real upcoming high-tier decisions.
- [ ] Track how long each review took, and whether the why-chain actually changed the outcome versus confirming the original proposal.

**Phase 4 — Measure**
- [ ] Compare decision cycle time for tiered vs. non-tiered reviews.
- [ ] Count how many high-tier decisions later turned out to rest on an assumption that didn't hold (a post-mortem finding, not a guess).
- [ ] Survey reviewers: did the why-chain make a wrong constraint visible before implementation, or only after?

**Phase 5 — Institutionalize or adjust**
- [ ] If the why-chain caught real issues at an acceptable time cost, make it mandatory for the high tier org-wide.
- [ ] If low- or medium-tier decisions are drifting into the high-tier template "just to be safe," tighten the tiering rubric — that drift is the practice failing, not succeeding.
- [ ] Revisit the tier of any constraint that was classified "genuine" more than a year ago — regulations, contracts, and infrastructure limits change; a stale classification becomes exactly the kind of inherited assumption this whole practice exists to catch.

## Metrics that show the policy is working

| Metric | What it tells you |
|---|---|
| % of high-tier RFCs with a completed why-chain section | Whether the process is actually being followed, not just documented |
| Cycle time: high-tier decisions with why-chain vs. without (historical baseline) | The real cost of the practice, in time — needed to judge whether it's worth keeping |
| Count of post-mortems citing "assumption not checked" as a root cause, before vs. after rollout | Whether the practice is catching what it's meant to catch |
| Count of low/medium-tier decisions escalated to the full template | Whether the tiering rubric is calibrated, or whether fear is driving over-application |
| Time between a constraint's classification and its next review | Whether "genuine constraints" are being revisited as circumstances change, or frozen forever |

## Anti-patterns to avoid

| Anti-pattern | Consequence | Prevention |
|---|---|---|
| **Interrogating every decision** — no tiering, why-chain demanded everywhere | Organization grinds to a halt; engineers route around the process | Tier decisions; make low-tier explicitly exempt, in writing |
| **First-principles theater** — a design doc invokes "we questioned our assumptions" without any evidence cited | Looks rigorous, changes nothing; a wrong constraint sails through review | Require the why-chain to cite specific evidence (measurement, document, log), not assertions |
| **Skipping the why-chain on a genuinely consequential migration** because it "feels similar to last time" | The one time the constraints actually differ is exactly when this fails silently | Apply the tiering rubric before the decision, not from memory of how the last one went |
| **Single-holder "why" knowledge** — one senior engineer is the only person who can explain why a constraint is genuine | Bus-factor risk; the constraint becomes unquestionable folklore the moment that person leaves | Require the why-chain to be written down, not held in one person's head |
| **No expiry on constraint classifications** — "genuine constraint" decided once, never revisited | A constraint that was real in 2022 quietly becomes the next inherited assumption nobody re-checks | Set a revisit cadence for high-tier constraints, especially regulatory and contractual ones |

## Hands-on exercise

Design a tiered assumption-review policy for your own team or org.

1. Write the tiering rubric: what makes a decision low, medium, or high tier, in terms your team can apply without you in the room?
2. Pick 3 recent real decisions and tier them. Would each have gotten the review it actually needed under your rubric?
3. Draft the why-chain template section you'd add to your design-doc process for the high tier only.
4. Name 2 metrics you'd track to know whether the policy is working within two quarters.
5. Name one existing "genuine constraint" in your system that hasn't been revisited in over a year, and schedule that revisit.

## Verify your thinking

- [ ] Can you state your tiering rubric in terms a teammate could apply without asking you first?
- [ ] Does your why-chain template require cited evidence, not just a statement that assumptions were "considered"?
- [ ] Have you named what does *not* require the full practice, as clearly as what does?
- [ ] Do you have a metric that would tell you if the policy is catching real issues, versus just adding process?
- [ ] Do your genuine constraints have a revisit cadence, or were they classified once and frozen?
