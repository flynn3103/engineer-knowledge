# Probabilistic Thinking — Middle

**Your question:** How do I build a calibrated estimate — a real range, not a single confident-sounding number — and use it to decide?

Junior level teaches you to attach a base rate and an expected value to a decision. At middle level, the single number you're comparing isn't good enough either — "this will take 6 days" and "this has a 60% chance of success" are both point estimates wearing different clothes. You need a **calibrated range**: a spread of outcomes with real confidence attached, built from evidence, not confidence of delivery.

## Build a calibrated estimate instead of a single number

A calibrated estimate names three things:

1. **A range**, not a point: optimistic, most-likely, and pessimistic outcomes.
2. **A confidence level** attached to the range: "I'm 80% confident the real number falls between X and Y" — not "it'll probably be X."
3. **The assumptions that would move it**: what has to be true for the low end to hold, and what pushes it toward the high end.

### The three-point technique

For a task or bet with a plausible range, estimate:

- **O (optimistic):** best case, everything goes right — roughly a 1-in-10 outcome, not a fantasy
- **M (most likely):** the realistic case given normal friction
- **P (pessimistic):** worst case you'd still call "plausible," not a black-swan disaster — also roughly 1-in-10

A simple weighted estimate (PERT-style): `E = (O + 4M + P) / 6`. The weighting matters less than the discipline of writing down three numbers instead of one — it forces you to name what "everything goes right" and "several things go wrong" actually look like.

### Where the range comes from

Don't invent O, M, and P from imagination. Anchor them the same way you anchor a base rate:

- **Outside view first:** how long did the last 5 similar migrations/features/integrations actually take, end to end? Use that spread as your starting range.
- **Inside view second:** adjust for what's different about *this* case — a new team member, an undocumented dependency, a vendor with a bad track record. Adjustments should be named, not vibes.

## Risk-adjusted expected value

Junior-level EV compares `probability × impact`. At middle level, add the cost of being wrong on top of the average outcome — two bets with the same EV can carry very different risk.

**Scenario:** The team is deciding whether to bet a quarter on migrating the search backend to a new indexing engine, versus incrementally optimizing the current one.

| Option | P(success) | Value if success | Cost if failure | Simple EV | Downside if it fails |
|---|---|---|---|---|---|
| Migrate to new engine | 60% | +$400k/yr in reduced infra cost | 6 wasted engineer-months, delayed roadmap | 0.6 × 400k − 0.4 × (cost of 6 months) ≈ positive | Team loses a quarter, competitor ships first, hard to reverse mid-migration |
| Incrementally optimize current engine | 90% | +$120k/yr in reduced infra cost | 3 wasted engineer-weeks if it doesn't pan out | 0.9 × 120k − 0.1 × (small cost) ≈ positive, smaller | Low — reversible within a sprint |

Simple EV alone might favor the migration. Risk-adjusted thinking asks two more questions:

- **Can we afford the failure case even once?** Losing a full quarter is a bigger deal for a 12-person team than a 200-person org — same probability, different tolerance.
- **Is the bet reversible?** Incremental optimization can be abandoned in a sprint. A half-finished migration is expensive to reverse and expensive to continue. Prefer the option with the cheaper "we were wrong" path when EV is close.

**Decision guidance:** when two options have similar EV, prefer the one with the smaller, more reversible downside — not the one with the larger upside.

## Recognize anchoring instead of reasoning

Watch for a team converging on a number because it was said first, not because anyone computed it.

**Signature:** In a planning meeting, someone says "I think this is about a week." Every following estimate lands suspiciously close to a week — even from people who haven't looked at the code yet. That's anchoring, not agreement.

**How to catch it:**
- Ask each person to write their own O/M/P silently *before* anyone speaks a number out loud.
- Compare the spread. A wide spread means real uncertainty was hiding under false consensus — that's useful information, not a problem to paper over.
- If everyone's numbers cluster suspiciously close to the first number said, ask directly: "Is this based on the reference class, or based on what was said first?"

**Fix:** silent-write estimates, then reveal simultaneously (planning poker does this mechanically). The goal isn't a faster meeting — it's an honest range instead of a socially-agreed one.

## Verification: does the range actually hold?

- **Track it.** When the task finishes, record where the actual outcome landed inside your O–M–P range — not just whether you "were right."
- **Sensitivity check.** Before committing, ask: "Which single input, if wrong, would flip this decision?" If the answer is "the vendor's uptime SLA," go verify that number before betting the quarter on it — that's where evidence has the highest value.
- **Confidence interval, not false precision.** "60-90% likely to ship by end of quarter, assuming the vendor API is stable" is honest. "It'll ship by end of quarter" is not more useful for being shorter — it's just less true.

## Common mistakes at middle level

| Mistake | Why it hurts | Fix |
|---|---|---|
| Giving a range that's really a point estimate with padding ("5 days, maybe 6") | The spread is too narrow to reflect real uncertainty — it's decoration, not a range | Force O and P to each be genuinely plausible ~1-in-10 outcomes, even if they feel uncomfortably wide |
| Building O/M/P purely from imagination | Without a reference class, all three numbers are still just a guess, now with extra steps | Anchor the range in the last 5 similar cases before adjusting for what's different |
| Comparing EV without comparing downside | Two options with equal EV can have wildly different failure costs | Ask "can we absorb the pessimistic case even once?" before choosing the higher-EV option |
| Letting the first spoken number set the room's estimate | The final number reflects social order, not evidence | Silent-write estimates before discussion; reveal together |
| Never checking where actual outcomes landed in past ranges | You can't tell if your estimates are honest or just optimistic-sounding | Track actual vs. estimated range after every bet, even informally |

## Hands-on exercise

Take a real project or feature currently being scoped.

1. Write O, M, and P using the outside view: pull the actual duration/outcome of the last 5 comparable pieces of work.
2. Adjust the range for what's genuinely different about this case, and write down each adjustment as a sentence.
3. Compute the PERT estimate and state your confidence level ("I'm ~70% confident the real number is in this range").
4. Build a risk-adjusted comparison against the alternative (do less, do it differently, or don't do it) — include the downside if you're wrong, not just the EV.
5. Identify the single input most likely to flip the decision, and name what evidence would resolve it fastest.

## Verify your thinking

- [ ] Does your range come from an outside-view reference class, not just imagination?
- [ ] Is your pessimistic case genuinely plausible, not a worst-case fantasy — and genuinely uncomfortable, not padding?
- [ ] Did you compare downside risk, not just expected value, between your options?
- [ ] Can you name the one input that would flip your decision if it turned out different?
- [ ] Did anyone in the room anchor on the first number said, and did you check for that?

Continue to [`senior.md`](senior.md).
