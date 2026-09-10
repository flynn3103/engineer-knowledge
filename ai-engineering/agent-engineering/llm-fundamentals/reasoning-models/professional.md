# Reasoning Models — Professional

<!-- level-focus -->
At professional level, focus on this question:

> Can you decide which product surfaces may use reasoning models, govern the spend, and measure whether deliberation actually improves outcomes?

---

## Surfaces, not vibes

- Decide per product surface — not per team or per engineer — where reasoning models are allowed:
  - **Allowed**: background analysis, planning stages of workflows, internal hard-problem tools — places where seconds-to-minutes of latency and multiplied token cost buy real quality.
  - **Restricted**: user-facing chat, real-time paths, high-volume cheap tasks — where the multiplier lands on every request and users feel it.
- Publish the allowed list with the rationale; anything outside it needs an exception with measured justification.

## Cost governance

- Reasoning spend is the most elastic line in an LLM budget — effort dials and task choices move it 5–10× without any code architecture change.
- Track **reasoning tokens as a separate cost category** in dashboards (alongside input/output — see [Cost and Performance](../../agent-evaluation/cost-and-performance/)), attributed per surface.
- Set per-surface budgets with alerting on trend; a new "high effort everywhere" habit shows up as a slope, not a spike.

## Measure whether it pays

- The only justification for deliberation cost is better outcomes. Measure the delta:
  - Run the surface's eval set (see [Datasets and Graders](../../agent-evaluation/datasets-and-graders/)) on standard vs. reasoning configurations — quality delta, cost delta, latency delta, side by side.
  - For user-facing surfaces, pair eval deltas with online signals: escalation rate, human edit distance, task completion (see [Online eval](../../agent-evaluation/datasets-and-graders/senior.md)).
- Retire reasoning where the measured quality delta doesn't cover its cost delta — this happens more often than teams expect, because "feels smarter" rarely survives contact with a labeled eval set.

## Model and vendor governance

- Reasoning behavior varies sharply across model families and snapshots — more than standard generation. The org model policy (see [How LLMs Work — Professional](../how-llms-work/professional.md)) should name which families are approved *for reasoning paths* specifically.
- Effort-dial semantics are not standardized across vendors: "high" means different budgets on different families. Document per-family mappings rather than assuming a portable setting.

## Common Mistakes

- **Per-engineer model choice.** Reasoning adoption spreads by enthusiasm; governance by surface list contains it.
- **Reasoning tokens invisible in cost reporting.** Hidden inside "output tokens," the fastest-growing cost category can't be seen, attributed, or governed.
- **Justifying with "feels smarter."** Without a measured quality delta, deliberation cost is untethered spend.
- **Assuming effort settings transfer across model families.** A "medium" on one vendor can be another vendor's "high" in both tokens and latency.

## Apply It

1. Write the allowed/restricted surface list for reasoning models, with rationale and an exception path.
2. Split reasoning tokens into their own cost category, attributed per surface, with trend alerting.
3. Run the standard-vs-reasoning bake-off on one currently-reasoning surface; make the keep/retire call from measured deltas.
4. Document per-family effort-dial mappings in the model policy.

## Verify Your Work

- Every reasoning usage maps to an approved surface, or holds a documented exception.
- Reasoning-token cost is visible per surface and trended.
- Each surface's reasoning usage has a measured quality-vs-cost justification on file.

## Review Questions

- Why is "allowed surface list" the right unit of governance rather than team-level choice?
- What measurement retires a reasoning deployment, and why does "feels smarter" not count?
- Why do effort-dial semantics need per-family documentation?
