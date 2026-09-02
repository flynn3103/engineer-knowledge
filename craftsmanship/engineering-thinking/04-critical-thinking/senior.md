# Critical Thinking — Senior

**Your question:** How do I run a structured, evidence-based comparison across real architecture options when the team disagrees?

Middle level teaches you to deconstruct one argument and spot one bias. At senior level, you're usually the person accountable for the final recommendation on a decision with real cost to reverse — a data store migration, a service boundary, a build-vs-buy call — and the team is split, sometimes loudly. A gut-feel table with checkmarks ("Option A: good, Option B: bad") looks structured but hides exactly the same bias problems as an unstructured argument, just with a table around them. You need a method that forces the weighting and the evidence to be explicit, so disagreement can be resolved on substance instead of who's more persuasive in the room.

## The method: A weighted trade-off comparison matrix

1. **Name the real options**, including "do nothing" — it's almost always a legitimate option and often gets skipped by default.
2. **List criteria that actually matter for this decision**, not a generic checklist. Pull them from real constraints: latency budget, team's current operational skill, cost ceiling, compliance requirement, migration risk.
3. **Weight each criterion (e.g., 1–5)** based on actual business/technical impact, decided *before* looking at how each option scores — deciding weights after scoring lets people reverse-engineer the weights to favor their preferred option.
4. **Score each option against each criterion using direct evidence** — a measurement, a documented constraint, a cost quote — not a gut feeling. If there's no direct evidence, mark it explicitly as "unverified" rather than guessing a number.
5. **Multiply weight × score, sum per option.** The total is an input to the decision, not the decision itself — a matrix doesn't replace judgment, it makes the judgment's inputs visible and arguable.
6. **Write the sensitivity check:** which single criterion, if its weight or score changed, would flip the recommendation? That's the criterion worth spending the most effort verifying.

### Worked example: choosing a caching layer

**Options:** (A) Redis managed service, (B) self-hosted Redis cluster, (C) in-process cache with no external dependency, (D) do nothing — keep the current uncached DB reads.

**Criteria and weights** (decided before scoring, based on what actually matters to this team):

| Criterion | Weight (1–5) | Why this weight |
|---|---|---|
| P99 read latency under peak load | 5 | Directly tied to an SLA the team is already missing |
| Operational load on the on-call team | 4 | Team is 3 engineers, already stretched |
| Cost at current + projected traffic | 3 | Budget exists but is not unlimited |
| Data consistency risk (stale reads) | 4 | Feature is a pricing display — stale data has real user impact |
| Migration effort / reversibility | 2 | Painful but not catastrophic to redo in 6 months |

**Scoring with evidence** (1–5, higher is better; "u" = unverified, needs a spike before this number is trusted):

| Option | Latency (5) | On-call load (4) | Cost (3) | Consistency risk (4) | Reversibility (2) | Weighted total |
|---|---|---|---|---|---|---|
| A: Managed Redis | 4 (measured: 3ms p99 in spike test) | 4 (vendor handles failover) | 2 (u — quote pending) | 3 (TTL-based, need invalidation design) | 4 (swap-out client lib) | 20+16+6+12+8 = 62 |
| B: Self-hosted Redis | 4 (same latency profile) | 1 (team has zero Redis-ops experience) | 4 (cheaper, but u — no ops-time cost included) | 3 (same as A) | 3 | 20+4+12+12+6 = 54 |
| C: In-process cache | 3 (u — not yet load-tested at peak) | 5 (no new infra) | 5 (free) | 1 (each instance caches independently — inconsistent across replicas, real risk for pricing data) | 5 (trivial to remove) | 15+20+15+4+10 = 64 |
| D: Do nothing | 1 (already missing SLA) | 5 | 5 | 5 (no caching = no staleness) | 5 | 5+20+15+20+10 = 70 |

**What the matrix actually reveals, not just the totals:** D scores highest numerically, but that's because "do nothing" was never actually meeting the latency SLA that motivated this whole comparison — the matrix is only valid if every option is evaluated against the requirement that started the search. This is exactly why step 6 (sensitivity check) matters: latency has the highest weight for a reason, and D fails it outright regardless of its other scores. Re-running with latency treated as a **gate** (must-score ≥ 3) rather than just a weighted factor eliminates D immediately and leaves A vs. C as the real contest — with C's consistency risk (4, weight 4) as the criterion most worth spending a real spike on before deciding, since it's the biggest unresolved swing factor between the two.

**The output of this exercise is not "C wins."** It's: "Latency is a gate, not just a weight — that removes D. Between A and C, the deciding factor is whether in-process cache consistency risk is acceptable for a pricing feature — that needs a one-day spike to answer with data, not a guess." That's a structured recommendation the team can act on or push back on with specifics.

## Detect motivated reasoning and groupthink before they decide for you

A high-stakes technical decision under time pressure is exactly when a team is most likely to converge fast and call it consensus. Watch for these signs:

| Sign | What it looks like | Why it's dangerous |
|---|---|---|
| Dissent gets socially punished | A team member raises a concern and gets met with "we don't have time for this" or eye-rolling rather than a counter-argument | The concern doesn't get resolved, it gets suppressed — it resurfaces after the decision is expensive to reverse |
| The decision was effectively made before the meeting | The "discussion" is really a ratification of a decision two people already agreed on in a hallway conversation | Everyone else's input becomes theater; real objections don't get a real hearing |
| No one can articulate the strongest counterargument | Ask the room "what's the best case *against* this option?" and get silence or a strawman | If the team can't state the opposing case well, they haven't actually understood the trade-off — they've just agreed with each other |
| Uniform enthusiasm with no stated risk | Every voice in the room is positive, no one names a failure mode | Real options always have real risks; total agreement on a nontrivial technical bet is itself a signal to look harder, not a sign of confidence |
| Urgency is used to shut down further evidence-gathering | "We need to decide today" is repeated instead of answered with "the cost of one more day for evidence is X" | Manufactured urgency is one of the most common ways groupthink gets manufactured — check whether the deadline is real or self-imposed |

**Countermeasure: assign an explicit counter-position.** Before the decision meeting, ask one person (rotate this role — see [professional.md](professional.md) for making it durable) to prepare and present the strongest case against the team's leaning option, using real evidence, not a token objection. This isn't about being contrarian for its own sake — it's the only way to guarantee the counterargument gets a real hearing instead of a token nod.

## Make and defend a recommendation under real disagreement

1. **State the recommendation and the matrix that produced it**, including the sensitivity check — show your work, not just the conclusion.
2. **State the strongest reasonable objection yourself**, before someone else has to. This defuses the "you didn't consider X" reflex and shows you've actually stress-tested your own conclusion.
3. **Separate "I disagree with the reasoning" from "I disagree with the decision."** If someone's objection is about a fact (a score, a weight), that's resolvable with more evidence. If it's about values (how much migration risk the team should tolerate), that's a judgment call the team's leader has to own, not a fact to keep researching.
4. **Disagree and commit, correctly.** After genuine debate, once the decision is made: state the decision, the reasoning, and the specific evidence that would cause the team to revisit it. Everyone — including those who argued against it — executes the decision as if it were their own, rather than passively undermining it or saying "I told you so" if it struggles. Disagree-and-commit is not "shut up and comply" — it requires that dissent was genuinely heard and the reasoning was actually shared before commitment, or it's just suppression with better branding.
5. **Set a re-evaluation trigger.** "We'll revisit this if p99 latency exceeds 50ms after the migration" is a real trigger. "We'll revisit if it doesn't work out" is not — it has no observable condition.

## Common mistakes at senior level

| Mistake | Why it hurts | Fix |
|---|---|---|
| Building the matrix after the team has already picked a favorite | Weights and scores get reverse-engineered to justify the preference already held | Set weights and criteria before scoring, ideally before anyone has stated a preferred option out loud |
| Treating the matrix's numeric total as the final answer | Hides the judgment calls (which criteria mattered, how they were weighted) behind a false precision | Present the matrix as an input, and always name the sensitivity check — which score, if wrong, flips the outcome |
| Calling agreement "consensus" without checking whether dissent was suppressed | A decision that looked unanimous can collapse the moment it meets reality, because objections were never actually surfaced | Explicitly ask "what's the strongest case against this?" and require a real answer before treating it as settled |
| Confusing disagree-and-commit with silencing dissent before the decision is made | People stop raising real concerns because they think objecting is pointless | Make clear: full debate happens before the decision; commitment starts only after, and only once objections were genuinely heard |
| Skipping the "do nothing" option | Frames every comparison as "which change should we make" instead of "should we change at all" | Always score the current state as a real option, including its own hidden costs |

## Hands-on exercise

Take a real architecture or tooling decision your team is currently debating, or one that was recently resolved by force of personality rather than evidence.

1. Name every real option, including "do nothing."
2. Write 4-6 criteria that matter for *this* decision specifically, and weight them before scoring anything.
3. Score each option against each criterion, marking any score you don't have direct evidence for as unverified.
4. Run the sensitivity check: which single criterion, if it changed, flips the recommendation?
5. Write the strongest argument against your own leaning recommendation, in one paragraph.
6. Write the re-evaluation trigger: what specific, observable evidence would cause the team to revisit this decision?

## Verify your thinking

- [ ] Were the weights set before anyone scored the options, or after?
- [ ] Can you point to direct evidence for every "high" score, or is it marked unverified?
- [ ] Can you name the single criterion most likely to flip the recommendation if it's wrong?
- [ ] Did anyone genuinely argue the strongest case against the winning option, out loud, with evidence?
- [ ] Is there a specific, observable trigger that would cause this team to revisit the decision?

Continue to [`professional.md`](professional.md).
