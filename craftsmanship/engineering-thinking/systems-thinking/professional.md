# Systems Thinking — Professional

**Your question:** How do I design incentive structures and metrics across an organization without the system gaming them?

Senior level redesigns a technical boundary or policy. Professional level designs the *incentive* boundary — the metrics teams are measured on, the ownership lines between them, and the shared dependencies that put unrelated systems at correlated risk. Every metric you attach to a team's performance becomes part of the system, and the system will optimize for the metric, not the intent behind it.

## Goodhart's law in practice

Named for economist Charles Goodhart, popularized as: *when a measure becomes a target, it ceases to be a good measure.* Once people know a number is being watched and rewarded, they optimize the number — and the number stops tracking the thing it was meant to represent.

This isn't a hypothetical — it's a predictable pattern with recognizable shapes:

| Metric made a target | How it gets gamed | What actually happened to the goal |
|---|---|---|
| Incidents closed per week | Large incidents get split into several small "resolved" tickets; ambiguous ones get closed early and reopened later (off this week's count) | Apparent resolution rate rises; real time-to-recovery is unchanged or worse |
| Deployment frequency | Trivial no-op commits and config touch-ups ship to inflate the count | The metric no longer distinguishes teams shipping value from teams shipping noise |
| Average first-response time | Support sends an automated "we're looking into it" reply immediately, then resolution drags | First-response time looks great; resolution time — the thing users actually feel — gets worse |
| Uptime / SLO percentage | "Down" gets redefined narrowly (only full outage counts, degraded-but-serving doesn't) | The number stays green while users experience real, uncounted pain |
| Lines of code reviewed | Reviewers rubber-stamp large diffs to keep throughput numbers up | Review quality drops exactly where it matters most — large, risky changes |

**The defense is not "pick a better single metric."** Any single metric that becomes a target will eventually be gamed, because the people closest to it have the most information and the most incentive to make the number move. The defense is pairing every target metric with a **guardrail metric** that would catch the gaming:

- Deployment frequency **+** change-failure rate **+** mean time to restore (the DORA framing) — you can't inflate deploy count without the failure-rate guardrail exposing it.
- Incidents closed **+** reopen rate within 30 days — closing prematurely shows up as a reopen spike.
- First-response time **+** resolution time — a fast auto-reply doesn't help the pair move together.
- Uptime **+** an independently defined "degraded" state tracked separately, owned by someone other than the team being measured on uptime.

### Worked example: a metric that moved without the outcome moving

**Target set:** a platform team is measured on "median time to first response" on internal tooling tickets, with a goal of 4 hours.

**What happens over one quarter:** median first-response time drops from 4 hours to 25 minutes. Leadership treats this as a clear win.

**What the guardrail would have shown, had one existed:** median time-to-*resolution* rose from 2 days to 6 days over the same quarter. The team started auto-replying "we've received this and are triaging" within minutes of every ticket, which satisfied the measured metric without changing when anyone actually looked at the underlying problem — the fast reply was true, but it wasn't the outcome the metric was meant to represent.

**Fix applied:** the target metric stayed (fast acknowledgment is genuinely useful to requesters), but a resolution-time guardrail was added to the same dashboard, owned by the requesting teams rather than the platform team itself, so the two numbers are reviewed together instead of the target being reported alone.

## Design incentive structures so local optimization doesn't damage the global system

A team optimizing its own metric in isolation can quietly damage a system it shares with others. This is the organizational version of the reinforcing loops from earlier levels — except the "component" is a team, and the "load" is metric pressure.

**Signs local optimization is damaging the whole:**
- A team's dashboard is green while a shared dependency (database, connection pool, on-call rotation, shared library) creeps toward saturation because every team individually stayed under *their own* threshold.
- Two teams sharing a resource each have headroom on paper, but neither accounts for the other's peak — combined, they exceed capacity.
- A platform team is measured on ticket-response time, so it says yes to every customization request; six months later no two teams' setups are consistent, and the platform's maintenance cost has exploded.

**Design principles:**
1. **Measure teams primarily on what they actually control.** A team can't be held accountable for a shared dependency's overall health if three other teams also write to it — that ownership has to sit somewhere explicit, not implicitly with whoever measures loudest.
2. **Give shared dependencies an explicit owner with their own guardrail metric**, reviewed across all consuming teams together, not per-team. If four teams share a connection pool, one team (often a platform team) owns pool-saturation as a metric no individual consuming team's dashboard reflects.
3. **Review metrics for teams that share a dependency together, not in isolation.** A quarterly review that only ever looks at one team's numbers will never surface a slow-building tragedy-of-the-commons problem in the resource they all touch.
4. **Prefer metrics that can't be satisfied by shifting cost onto another team.** "Tickets closed" can be satisfied by pushing work to whichever team picks up the reopened ticket. "Tickets closed and not reopened by any team within 30 days" can't.

## Manage systemic risk across a portfolio of systems

Individual systems can each look healthy while the portfolio carries concentrated, correlated risk that no single team's dashboard shows.

### Find correlated failure risk

- **Shared infrastructure:** the same base image, the same auth provider, the same cloud region, the same message broker — a failure in any of these takes down every system built on it simultaneously, not one at a time.
- **Shared people:** the same handful of engineers are the only ones who understand a critical system, or the same on-call rotation covers too many services to page effectively during a wide incident.
- **Shared timing:** batch jobs, cron schedules, or cache expirations that were set up independently but happen to cluster at the same hour, creating a self-inflicted correlated spike.

### Map blast radius, not just direct callers

For each shared dependency, list every system that goes down *together* if it fails — not just the systems that call it directly, but the systems those systems support. A shared authentication service's failure doesn't just break the services that call it; it breaks every user-facing flow behind them, which is usually a much longer list than the dependency graph on a whiteboard suggests.

### Decide diversification deliberately, and record the decision

Diversifying away from a shared dependency (multi-region, multiple providers, isolated pools per critical path) has a real, ongoing cost. Sometimes that cost is worth it; sometimes concentration is the right call for now. The failure mode isn't "we chose to concentrate risk" — it's choosing it *by default*, without anyone deciding on purpose or writing down why, so nobody revisits it as the blast radius grows.

**Track a concentration metric:** for each shared dependency, how many independent systems depend on it, and what's the combined user or revenue impact if it fails at once? Review this list on a cadence — the same way you'd review any other risk register — not only after an incident exposes it.

### Worked example: mapping a blast radius

**Shared dependency:** a single regional identity provider used for authentication.

**Direct callers:** 6 services list it as a direct dependency in their service catalog — a number any team could find in five minutes.

**Actual blast radius, traced one hop further:** those 6 services sit behind 22 user-facing flows (checkout, account settings, support tooling, internal admin consoles, a partner-facing API, and a mobile app's session refresh). None of those 22 flows appear in the identity provider's own dependency list, because the catalog only tracks direct callers.

**Combined impact if it fails:** the 6 direct callers estimate their own individual impact as "medium" in isolation. Traced together, a regional identity-provider outage stops checkout, blocks all new support tickets, and locks internal engineers out of the admin console needed to mitigate the incident — a severity none of the 6 individual risk assessments captured on its own.

**Action taken from the mapping:** the identity provider gets a named owning team with an explicit availability guardrail reviewed by representatives of all 6 consuming teams together, and the admin console gets a documented break-glass path that doesn't depend on the same provider — closing the worst part of the blast radius (losing the tool needed to respond to the outage during the outage).

This is the pattern: the number that matters is never the direct-caller count — it's what those callers are the last line in front of.

## Rollout: phased incentive and metrics design

### Phase 1: Frame
- [ ] Write the actual outcome you want in one sentence (not the metric — the outcome).
- [ ] List who is affected by the metric being proposed: the team being measured, and every team that shares a dependency with them.
- [ ] Name the failure mode you're most worried about if this metric gets gamed.

### Phase 2: Map incentive and dependency structure
- [ ] Draw which teams share which dependencies (databases, pools, on-call rotations, platforms).
- [ ] For each shared dependency, name its owner. If there isn't one, that's the first gap to close.
- [ ] Identify existing metrics that could already be gamed and check history — has the number moved without the underlying outcome moving?

### Phase 3: Design the metric pair
- [ ] Pick the target metric (what you want to encourage).
- [ ] Pick a guardrail metric that would move if the target is gamed.
- [ ] Confirm the guardrail is owned or visible to someone other than the team optimizing the target.

### Phase 4: Pilot with one team or unit
- [ ] Run the metric pair with one team for a fixed period before rolling out further.
- [ ] Watch for early gaming signals (a target metric moving faster than the guardrail can plausibly explain).
- [ ] Set an explicit review date — don't let a pilot metric become permanent by default.

### Phase 5: Instrument for gaming signals
- [ ] Track the target and guardrail together on the same dashboard, not separately.
- [ ] Alert on divergence: target improving while the guardrail stays flat or worsens.
- [ ] Review qualitatively, not just numerically — ask the team what behavior changed, not only what the dashboard shows.

### Phase 6: Expand based on evidence
- [ ] Roll out only if the guardrail held during the pilot.
- [ ] If gaming appeared, redesign the pair before expanding — don't expand a metric you already know can be gamed and hope for the best at scale.
- [ ] Revisit the concentration/blast-radius map at least once a quarter, since the dependency graph shifts as systems evolve.

## Anti-patterns to avoid

| Anti-pattern | Consequence | Prevention |
|---|---|---|
| A single target metric with no guardrail | The metric gets gamed and stops tracking the real outcome, often silently | Always pair a target with a guardrail owned by someone with different incentives |
| Measuring a team on a shared resource it doesn't fully control | Team either can't hit the target through no fault of its own, or games it by pushing cost onto another team | Give shared dependencies an explicit owner and a cross-team review |
| Copying another org's incentive structure without adapting it | Optimizes for the other org's local conditions, not yours — can reward the wrong behavior here | Design the guardrail from your own failure modes, not from a template |
| Reviewing metrics only during postmortems | Gaming is discovered only after real damage, not before | Put target/guardrail pairs on a standing dashboard reviewed on a cadence, not only after incidents |
| Concentrating on shared infrastructure by default, without a decision | Blast radius grows quietly until one failure takes out many systems at once | Track a concentration metric per shared dependency and review it like any other risk |
| Treating a pilot metric as permanent without a review date | A metric that made sense for one team's context spreads unexamined | Set an explicit review date before rollout and honor it |

## Hands-on exercise

Take one metric currently used to evaluate your team, or one you're about to propose for another team.

1. State the outcome the metric is meant to represent, in one sentence.
2. Describe the easiest way someone could move the number without improving the outcome — be concrete.
3. Propose a guardrail metric that would catch that specific gaming behavior, and name who should own it.
4. List every other team that shares a dependency affected by this metric, and check whether their incentives point the same direction or in conflict.
5. Identify one shared dependency behind this metric and estimate its blast radius: if it fails, what else goes down at the same time?

If step 2 is hard to answer, you likely haven't found the real gaming vector yet — ask someone who'd be measured by the metric how they'd hit the number on a bad week.

## Verify your thinking

- [ ] Can you name the specific way a target metric could be gamed, in concrete terms, not just "people might cheat"?
- [ ] Does every target metric you're proposing have a guardrail owned by someone with different incentives?
- [ ] Can you name the owner of every shared dependency your metric touches?
- [ ] Have you mapped the blast radius of at least one shared dependency behind this system, not just its direct callers?
- [ ] Is there a review date set for any new metric, so it doesn't become permanent by default?
