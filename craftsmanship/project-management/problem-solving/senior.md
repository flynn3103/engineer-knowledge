# Problem-Solving — Senior

**Your question:** How do I lead work where the requirements themselves are genuinely ambiguous, and how do I recover when I'm stuck?

Middle-level problem-solving assumes the problem is understood and only the approach is uncertain. At senior level, that assumption breaks: sometimes nobody — not you, not the stakeholder, not the org — actually knows what the right outcome looks like yet. Guessing wastes months; stalling for a perfect spec wastes just as much. The senior skill is choosing the cheapest action that converts real ambiguity into real knowledge, staging delivery so no single wrong guess is fatal, and — separately — knowing what to do with yourself when you get stuck mid-problem instead of grinding on the same dead end.

## The method: Reduce ambiguity, stage delivery, recover deliberately

1. **Name what's actually ambiguous.** Not "this is unclear" — specifically: is it the *goal* that's unclear, the *approach*, or the *constraints*? Each needs a different tool.
2. **Pick the cheapest technique that would resolve it**, not the most thorough one. A time-boxed spike, a throwaway prototype, or one sharply-scoped question to a stakeholder — in that rough order of cost.
3. **Stage delivery so the problem can be specified further as you learn**, instead of committing to a full build against a spec you don't trust yet.
4. **When you get stuck on a specific sub-problem, diagnose the kind of stuck before choosing a recovery technique.** Different flavors of stuck need different fixes; applying the wrong one wastes the time it was supposed to save.

## Reducing genuine ambiguity

Three techniques, cheapest first, each answering a different question:

| Technique | Answers | Cost | When to use |
|---|---|---|---|
| One sharply-scoped clarifying question | "What does the stakeholder actually mean by X?" | Minutes to a day (waiting on a reply) | The ambiguity is in stated intent, and one specific person can resolve it — ask instead of guessing or building around it |
| Time-boxed spike (fixed time, e.g. 2 days, throwaway code allowed) | "Is this technically feasible, and roughly how hard?" | Days | The ambiguity is in feasibility or rough sizing, not in what "done" means |
| Throwaway prototype shown to real users or stakeholders | "Does this actually solve the problem, and did we understand the problem at all?" | Days to a couple weeks | The ambiguity is in the goal itself — nobody can describe success until they see something concrete to react to |

The failure mode at this level isn't picking the wrong technique — it's skipping straight to a full build because asking feels slow, or stalling in "further discovery" past the point where the next unit of information is worth its cost. Both are avoidable: **before starting any of these, write down what decision the answer will actually change.** If the answer wouldn't change what you build next, you don't need it yet.

**Example — a genuinely ambiguous initiative:** "Improve onboarding conversion" arrives with no agreed metric, no owner of the onboarding flow end-to-end (it touches signup, three feature teams, and support), and two different stakeholders who each assume a different definition of "converted."

- Ambiguity in goal: what does "converted" mean? → One sharply-scoped question to the stakeholders, together in the same room, forcing them to agree on one number (e.g., "activated" = completed setup within 7 days). Cost: one 30-minute meeting. Without it, two teams would optimize for different, possibly conflicting metrics.
- Ambiguity in feasibility: can setup completion time actually be reduced without a major rewrite? → A 2-day spike prototyping one shortened flow against a copy of production data. Cost: 2 days, throwaway code.
- Ambiguity in whether the fix actually helps: does a shorter flow really change behavior, or do users drop off for an unrelated reason? → A throwaway prototype shown to 10 real users in a moderated session, before writing production code. Cost: 3-4 days including recruiting.

Only after these three answers exist does a full plan (in the middle-level sense — compare approaches, sequence for reversibility) get written.

## Staging delivery when the problem can't be fully specified up front

When ambiguity can't be fully resolved before you start — common when the unknown is "will users actually behave the way we predict" — contain the risk with staged delivery instead of waiting for certainty or betting everything on one guess:

1. **Ship the smallest version that produces real signal**, not the smallest version of the final feature. These aren't the same: a shortened onboarding flow behind a flag, shown to 2% of new signups, produces signal; a polished-but-unlaunched design doc does not.
2. **Define, before shipping, what signal would make you stop, continue, or change direction.** For the onboarding example: if 7-day activation doesn't move within two weeks at 2% traffic, stop and re-examine the goal-ambiguity question, not the implementation.
3. **Keep each stage cheap to unwind** — a flag, a percentage rollout, a reversible schema change — so a wrong guess at this stage costs days, not a quarter.
4. **Re-specify the problem as evidence arrives.** Staged delivery isn't just risk containment, it's also how you finish resolving the ambiguity that a spike or prototype couldn't fully settle — production behavior at scale reveals things a 10-user session doesn't.

This is the same reversible-plan discipline from [middle.md](middle.md), applied to a problem where even the *goal*, not just the approach, is still being discovered.

## Recover when stuck: five techniques and when each applies

Getting stuck is different from facing ambiguity — ambiguity is not knowing the goal or constraints; being stuck is having a clear-enough problem but no forward progress on solving it. Misdiagnosing which one you're facing wastes the recovery attempt.

| Technique | What it does | When it applies | When it doesn't |
|---|---|---|---|
| Change representation (draw it, write pseudocode instead of code, model it as a graph/table/state machine) | Exposes structure your current mental model is hiding | You keep re-deriving the same fact by hand, or the problem "feels" more complex than it should | The blocker is missing information, not missing structure — a new diagram won't produce data you don't have |
| Work backward from the goal | Reveals which of your current steps are actually necessary | You have a clear end-state but the forward path keeps branching into options you can't compare | The end-state itself is the ambiguous part — work backward from an unclear goal and you're just guessing in reverse |
| Simplify to a smaller version of the same problem | Isolates whether the difficulty is inherent or incidental | You're stuck on a general case; solve it for n=1 or a single record first, then generalize | The small version is trivial in a way the real problem isn't (e.g., concurrency bugs vanish at n=1) — solving it won't tell you anything |
| Explain it to someone else (including a rubber duck) | Forces you to make implicit assumptions explicit, often surfacing the gap mid-sentence | You can't articulate *why* you're stuck, only that you are | You already understand the blocker clearly and just lack the information or access to resolve it |
| Take a deliberate break | Lets you stop reinforcing an unproductive line of thought | You notice you're re-trying variations of the same failed idea (thrashing), not making new progress | You're making steady incremental progress — a break here just costs time |

The common thread: **each technique targets a specific kind of stuck.** Before reaching for one, name what's actually blocking you — missing structure, missing information, unclear necessity, an implicit false assumption, or thrashing — and pick accordingly, instead of cycling through all five hoping one works.

## Common mistakes at senior level

| Mistake | Why it hurts | Fix |
|---|---|---|
| Jump straight to a full build when the goal is ambiguous | Weeks of work optimized for a definition of success that turns out to be wrong | Resolve goal-ambiguity with the cheapest technique (usually a clarifying question) before planning delivery |
| Stall in "more discovery" past the point of useful new information | The team loses momentum and stakeholders lose confidence, without the extra discovery actually changing the plan | Before each round of discovery, write what decision the answer would change; stop when nothing would change |
| Treat every stuck moment the same way (usually: push harder) | Wastes time reapplying effort to a blocker that needs a different kind of unblocking | Diagnose the kind of stuck first; match it to the technique in the table above |
| Ship a staged rollout without predefined stop/continue signal | Ambiguous results get rationalized into "let's just ship it," defeating the point of staging | Write the stop/continue/change-direction thresholds before the first stage ships |
| Confuse feasibility (a spike) with desirability (a prototype with real users) | A technically-working spike gets treated as proof users want it, when no user ever saw it | Match the technique to the actual unknown — feasibility and desirability are different questions |

## Hands-on exercise

Take an ambiguous initiative you're currently leading or advising on.

1. Name the specific kind of ambiguity: goal, approach, or constraints. (There may be more than one — list each separately.)
2. For each, pick the cheapest technique from the table that would resolve it, and write what decision the answer would change.
3. Sketch a staged delivery plan: what's the smallest shippable stage that produces real signal, and what stop/continue thresholds gate the next stage?
4. Recall a recent moment you were stuck on part of this problem (or a related one). Which of the five recovery techniques would have matched that specific kind of stuck? Would the technique you actually used have been the right match?
5. Identify the one decision in this initiative that is hardest to reverse. What has to be true before you're willing to make it?

## Verify your thinking

- [ ] Can you name specifically what's ambiguous — goal, approach, or constraints — rather than just "this is unclear"?
- [ ] For each ambiguity, can you state what decision the resolving evidence would change?
- [ ] Does your staged plan have a predefined stop/continue signal, written before the first stage ships?
- [ ] Can you diagnose which of the five kinds of "stuck" you're in before picking a recovery technique?
- [ ] Have you separated "is this feasible" from "do people actually want this" as different questions needing different evidence?

Continue to [`professional.md`](professional.md).
