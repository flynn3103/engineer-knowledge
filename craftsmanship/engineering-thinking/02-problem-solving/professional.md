# Problem-Solving — Professional

**Your question:** How do I build an organization that solves problems well repeatedly, not just this one?

A senior engineer can reduce ambiguity and recover from being stuck on their own initiative. That doesn't scale past one team. At professional level, the job changes: you're no longer just solving problems, you're designing the system that determines whether *everyone else's* problems get routed to the right owner, get solved with a durable fix instead of a one-off patch, and don't get silently re-solved from scratch by someone else six months later because nobody could find out it had already happened.

## Design intake so problems reach the right level of ownership

Without deliberate intake, problems get solved by whoever happens to notice them first — which means trivial problems get escalated to staff engineers, and genuinely ambiguous, cross-team problems get quietly patched by whoever's on-call, at the wrong scope.

**A working intake process answers three questions for every incoming problem:**

1. **Scope:** Does this affect one team's owned system, or does it cross ownership boundaries?
2. **Reversibility:** Can whoever picks this up undo their fix cheaply, or is it a one-way door?
3. **Precedent:** Has this exact problem (or a close variant) been solved before?

| Answer pattern | Route to |
|---|---|
| Single-team scope, reversible | The owning team, no escalation — this is what senior-level individual problem-solving (see [senior.md](senior.md)) is for |
| Cross-team scope, reversible | A named cross-team owner or working group, time-boxed |
| Any scope, irreversible (schema change, public API, compliance-affecting) | Requires the decision-rights process below before work starts |
| Matches existing precedent | Point to the prior solution first — do not let it be re-solved from scratch (see institutional memory, below) |

The point of intake isn't bureaucracy for its own sake — it's making sure a problem's owner has the authority and scope that actually matches the problem, before any plan or spike work begins.

## Turn postmortems into durable process change, not just individual lessons

At middle level, a look-back extracts one personal lesson from a surprise. At professional scale, the equivalent process has to produce a change to *the system*, not just to one person's mental model — because the next person to hit the same surprise won't have read the first person's private lesson.

A postmortem that produces durable change includes:

- **A timeline of what was known, when** — not just what went wrong, but what information was available and unavailable at each decision point.
- **The gap between the plan and reality** — where did the actual work diverge from the plan, and was that divergence caught quickly or only in hindsight?
- **At least one action item that changes a system, not a person.** "Be more careful" is not an action item. "Add a check that blocks this class of mistake" or "add this decision path to the intake table above" is.
- **An owner and a deadline for each action item**, tracked to completion — an action item with no owner is a wish, not a fix.
- **A single number: how many similar problems has this happened for before?** If the answer is more than one, the postmortem isn't fixing a one-off — it's revealing a gap in the intake or ownership design itself.

Avoid "human error" as an endpoint. If a competent engineer following the documented process still produced the bad outcome, the process — not the engineer — is what needs the fix. Ask why the system made the mistake easy and the recovery hard, not just who made it.

## Design decision rights: who decides when there's genuine disagreement

Most problems don't need a decision-rights process — the owning team just decides. It matters specifically for the case intake flagged as cross-team and irreversible, where two reasonable engineers can look at the same evidence and choose differently.

**A working decision-rights design specifies, before disagreement happens (not during it):**

1. **Who has final call** for each class of decision — usually the team that owns the long-term consequences of being wrong, not the team that's loudest or most senior in the room.
2. **What evidence threshold moves the decision**, agreed before anyone has seen the options — so the criteria aren't quietly rewritten by whoever's proposal is winning.
3. **A default if no consensus forms within a set time** — a time-boxed escalation to a named single decision-maker, not an indefinite debate.
4. **A record of what was decided and why**, including the rejected options — so the decision doesn't get silently re-litigated by someone who wasn't in the room.

Push every decision as close to the team living with its consequences as reversibility allows. Reserve the heavier process above for the genuinely irreversible, genuinely cross-team cases — running it on every decision just teaches the organization to route around it.

## Build institutional memory so problems don't get re-solved from scratch

The single most common failure at this level isn't a bad decision — it's a *good* decision, made twice, six months apart, by two people who never knew about each other, because the first solution was never made findable.

Concrete mechanisms, cheapest first:

- **A searchable decision log**, not a folder of unstructured docs — one entry per non-trivial decision, including the problem statement, options considered, the choice, and why. Searchable by the problem, not just by project name.
- **Link the postmortem or decision record from the code or config it produced**, not just from a ticket that will be archived and forgotten.
- **A designated place newcomers are told to search *before* proposing a redesign** — if this doesn't exist, "was this already tried?" becomes tribal knowledge, available only to whoever's been around long enough to remember.
- **Periodic pruning**, not just accumulation — a decision log nobody trusts because it's full of stale, superseded entries is as useless as no log at all. Mark superseded decisions explicitly; don't delete them, since the "why we moved away from X" is itself valuable.

Institutional memory isn't a wiki page — it's whether the *next* person who hits this problem finds the answer before they start solving it from zero.

## Rollout: build the problem-solving system in stages

Don't roll out intake, decision rights, and a decision log all at once against a team that's never had any of them — that's a big, low-evidence bet on process the org hasn't validated it needs.

### Phase 1: Diagnose before designing
- [ ] Identify concrete pain: which problems are being re-solved, misrouted, or stalling without a decision?
- [ ] Count recurring incidents/problems over the last two quarters — how many hit the same root cause?
- [ ] Interview 3-5 engineers: where did they get stuck waiting on a decision, or discover a problem had already been solved?
- [ ] Write the specific failure this system is meant to fix — not "improve problem-solving" in the abstract (this is the same discipline from [junior.md](junior.md): concrete success criteria before a plan)

### Phase 2: Pilot with one team, one problem class
- [ ] Choose one recurring, well-understood problem class (e.g., "cross-team schema-change requests")
- [ ] Apply the intake routing table to real incoming problems for 4-6 weeks
- [ ] Track: how many problems were routed correctly the first time vs. re-routed?
- [ ] Track: how long did cross-team, irreversible decisions take from raised to decided?

### Phase 3: Add the decision log
- [ ] Require one decision-log entry for every decision routed through the cross-team or irreversible path
- [ ] After 90 days, sample 10 entries — are they specific enough that a newcomer could find and understand the decision without asking the original author?
- [ ] Track: how many times did someone search the log and find a prior answer instead of re-deriving it?

### Phase 4: Expand based on evidence, not optimism
- [ ] Continue only if Phase 2/3 metrics improved (below) — if they didn't, diagnose why before expanding scope
- [ ] Extend intake routing and decision rights to additional problem classes or teams, one at a time
- [ ] Revisit the decision-rights defaults: is the escalation path actually being used, or is everything still resolved informally (a sign it's over-designed) or everything escalating (a sign ownership boundaries are still unclear)?

### Phase 5: Sustain
- [ ] Schedule quarterly pruning of the decision log
- [ ] Re-run the Phase 1 interview periodically — is new pain emerging that the system doesn't cover?
- [ ] Retire any part of the process that isn't producing measurable value; a system nobody trusts gets routed around

## Metrics: what tells you the system is actually working

| Metric | What it reveals | Healthy signal |
|---|---|---|
| Re-routing rate (problems sent to the wrong owner first) | Whether intake scoping questions are working | Trending down after Phase 2 |
| Recurrence rate (same root cause, multiple postmortems) | Whether postmortem action items are producing durable fixes, not just documentation | Trending down over quarters |
| Time from "cross-team decision raised" to "decided" | Whether decision rights and the escalation default are actually functioning | Bounded and predictable, not open-ended |
| Decision-log search-and-reuse count | Whether institutional memory is actually preventing re-solving | Nonzero and growing, not flat at zero |
| Action items closed vs. opened per postmortem cycle | Whether postmortems produce completed fixes or just a growing backlog of good intentions | Closed rate stays close to opened rate |

Watch for a system that looks healthy only because nobody uses it — zero re-routing and zero escalations can mean the process works, or it can mean everyone quietly routes around it. Cross-check metrics against the Phase 1 interviews, repeated periodically, not just the numbers alone.

## Anti-patterns to avoid

| Anti-pattern | Consequence | Prevention |
|---|---|---|
| Intake process routes everything to one senior engineer "to be safe" | That person becomes a bottleneck; trivial problems wait behind irreversible ones | Scope the routing table by reversibility and boundary-crossing, not by default caution |
| Postmortems end at "the engineer should have double-checked" | The same class of mistake recurs, because the system that made it easy is unchanged | Require at least one system-level, ownerless-of-blame action item per postmortem |
| Decision rights exist on paper but everyone still argues informally until someone senior speaks up | The documented process is fiction; real decisions happen off the record and aren't logged | Actually route disputed, irreversible decisions through the documented path — and log the outcome even when it was "obvious" |
| Decision log accumulates but nobody prunes or trusts it | Search returns ten stale, contradictory entries; people stop checking it, defeating its purpose | Schedule pruning; mark superseded decisions explicitly instead of leaving them ambiguous |
| Rolling out the full system (intake + decision rights + log) org-wide before piloting | No evidence it fits how any team actually works; low adoption, high resentment | Pilot on one team and one problem class first; expand only on measured improvement |

## Hands-on exercise

Take a recurring category of problem in your organization — one that gets re-solved, misrouted, or stalls waiting on a decision more than once.

1. **Diagnose:** Write the specific, observed failure (not "we're bad at X") — cite at least two real instances.
2. **Intake:** Sketch a routing table like the one above for this problem class. Where should it land by default?
3. **Decision rights:** If this problem class sometimes requires cross-team, irreversible decisions, who should hold final call, and what's the escalation default if they can't agree?
4. **Memory:** Has this problem class been solved before, somewhere findable? If you don't know, that's itself evidence institutional memory is missing here.
5. **Pilot plan:** Sketch a 4-6 week pilot with one team, and the two or three metrics from the table above you'd track to know if it helped.

If you can't answer step 4 with confidence, start there — a decision log that makes precedent findable is usually the cheapest, highest-leverage piece of this system to build first.

## Verify your thinking

- [ ] Can you route a new incoming problem to an owner using scope and reversibility, without asking "who's free"?
- [ ] Does your postmortem process produce action items that change a system, with an owner and a deadline, rather than "be more careful"?
- [ ] Is there a named decision-maker and a time-boxed default for cross-team decisions where reasonable people disagree?
- [ ] Could a new hire find out whether a given problem has already been solved, without asking a specific tenured person?
- [ ] Are you tracking recurrence rate and re-routing rate, or just assuming the system works because nobody's complaining?
- [ ] Did you pilot this on one team and one problem class before rolling it out broadly?
