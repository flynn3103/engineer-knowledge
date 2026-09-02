# Metacognition and Learning — Senior

**Your question:** Am I systematically over- or under-confident, and do I actually know the boundary of what I know before a high-stakes call?

At senior level, your calls carry other people's plans. An estimate other teams schedule around, an architecture judgment others build on, an on-call decision that determines whether an incident gets worse — being locally right most of the time isn't enough anymore. You need to know *how much to trust your own read*, and you need to know it before the decision, not after the postmortem.

## The method: calibrate your confidence against outcomes

**Calibration** means your stated confidence matches your actual accuracy: things you're 80% confident about should turn out right roughly 80% of the time. Most engineers have never checked whether that's true for them — they know whether they're "usually right," but not whether their 90%-confidence calls and their 60%-confidence calls are actually different in reliability.

### How to apply it

1. **Before a decision or estimate, write down** the prediction, a stated confidence level (a number, even a rough one — "70%," not "pretty sure"), and the assumptions and evidence behind it.
2. **After the outcome arrives, score it** on two separate axes: was the prediction right, and was the confidence level *justified given what was known at the time* — not just justified in hindsight.
3. **Track this over time** in a simple log. Look for patterns by category, not just an overall average: consistently overconfident on estimates? Underconfident on system-design calls? Overconfident specifically on "this should be a quick fix"?
4. **Adjust your default number for that category**, not just your general gut feeling. Calibration is usually domain-specific, not a single global trait.

### A concrete example

A senior engineer logs estimate, stated confidence, and actual outcome for every non-trivial task across 12 sprints.

| Task category | Stated confidence | Actual accuracy | Verdict |
|---|---|---|---|
| Small, isolated bug fix (<1 day) | 85% | 88% right | Well calibrated |
| Feature within an owned service | 75% | 70% right | Roughly calibrated |
| Migration touching a shared library | 80% | 40% right | Chronically overconfident |
| Work in an unfamiliar part of the codebase | 60% | 65% right | Slightly underconfident |

The useful finding isn't "I'm bad at estimating" — the small-fix and owned-service numbers are fine. It's specific: confidence on cross-team migrations is badly miscalibrated, probably because those estimates don't account for coordination and review latency the engineer doesn't directly control. That's a fixable, named bias — "widen my estimate range specifically when a shared library or another team's review is in the critical path" — not a vague resolution to "estimate better."

## Map the boundary of your own knowledge before a high-stakes call

Before a decision where being wrong is expensive, write down four things explicitly:

- **What I know directly** — tested, verified, or observed firsthand.
- **What I'm inferring from adjacent experience** — pattern-matched from a similar situation, not verified in this specific case.
- **What I don't know and haven't verified.**
- **Who or what could verify the unknowns** — a specialist, another team, a test you could run first.

The point of the exercise is the third line. Most engineers can list what they know; naming what they *don't* know, specifically, before committing is the harder and more valuable habit.

### A concrete example

**Decision:** whether to fail over to the backup region during a partial outage in the primary region.

- **Know directly:** the failover runbook, tested twice in staging drills; the on-call engineer has executed it once before, successfully, six months ago.
- **Inferred, not verified here:** database replication lag during failover will behave like it did in the last similar incident — reasonable, but that incident was under different load conditions.
- **Don't know:** whether the notification service, added two months ago, has ever been through a failover. It wasn't part of either staging drill.
- **Who could verify:** the team that owns the notification service could confirm its failover behavior in under 10 minutes if paged now.

Writing this down turns a vague "I think this will be fine" into a specific action: page the notification-service team before committing to failover, rather than discovering the gap live. The unknown that mattered here was findable in the ten minutes before the decision — it just had to be named first.

## Signals of miscalibration

| Signal | What it suggests | Response |
|---|---|---|
| High-confidence claims come out wrong more often than the stated confidence implies | Overconfidence | Widen the uncertainty range for that category; seek disconfirming evidence before committing |
| Low-confidence claims come out right more often than the stated confidence implies | Underconfidence, excess hedging | Trust your read more on that category, while still checking |
| The same task category keeps surprising you | Your model of that specific domain is wrong, not a general skill gap | Rebuild the mental model deliberately — study why the estimates diverge, don't just nudge the number |
| You feel equally confident about things you've verified and things you're guessing at | You're not distinguishing evidence quality from gut feeling | Explicitly separate "I checked this" from "this is my best guess" in every decision record |

## Common mistakes at senior level

| Mistake | Why it hurts | Fix |
|---|---|---|
| Treating "I've done this before" as calibrated confidence without checking the actual track record | Past success in a different context doesn't guarantee accurate confidence here | Keep a real log of predictions versus outcomes; check it before trusting the feeling |
| Only reviewing decisions that went wrong | Survivorship bias in your calibration data — you never learn what earned your correct high-confidence calls | Log predictions before the outcome is known; review both hits and misses |
| Conflating outcome with process quality | A good decision can have a bad outcome from bad luck, and vice versa; conflating them corrupts your calibration signal | Score the decision against the evidence available at the time, separately from the eventual result |
| Presenting an inferred assumption as a known fact under pressure | Downstream people build on it as if verified, and the error compounds silently | Explicitly flag "this is inferred, not verified" in the decision record |
| Skipping the unknowns map because the deadline is tight | Exactly when a hidden unknown is most expensive if it turns out to matter | The boundary map takes ten minutes; the incident it prevents costs hours |

## Hands-on exercise

1. Pull your last 10–15 estimates or predictions — sprint estimates, on-call risk calls, "this fix should hold" guesses — or start logging them now if you don't have a record.
2. For each: what did you predict, what confidence did you state (or would you have stated), what actually happened.
3. Group by task category. Where is your confidence well calibrated? Where does it diverge?
4. Before your next high-stakes technical decision, write the boundary map: know directly / inferred / unknown / who could verify.
5. After the decision, check: did an "unknown" you named turn out to matter? Did you miss one you should have named?

## Verify your thinking

- [ ] Do you have an actual log of past predictions versus outcomes, not just a general impression of your accuracy?
- [ ] Can you name one task category where you're overconfident and one where you're underconfident?
- [ ] Before your last high-stakes call, did you write down what you don't know, not just what you do?
- [ ] Can you separate "I verified this" from "I'm inferring this from a similar case" in your own reasoning?
- [ ] Did you score a past decision by its process and evidence, separately from whether the outcome was good or bad?

Continue to [`professional.md`](professional.md).
