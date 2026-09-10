# Critical Thinking — Junior

**Your question:** Is this actually backed by evidence, or is it just a confident-sounding claim?

Design docs, code review comments, and standup updates are full of sentences that sound like facts but are actually opinions wearing a lab coat. "This will be faster." "Users don't care about this." "Everyone agrees this is the right approach." None of these tell you what was measured, who was asked, or what would have to be true for the claim to be false. If you accept sentences like these at face value, you inherit someone else's untested assumption as if it were your own conclusion.

## The method: Split the sentence into claim and evidence

1. **Isolate the claim.** Write it as a single sentence with no evidence attached. "MongoDB will be faster here" is a claim, not a fact.
2. **Ask what evidence is actually offered.** Read the surrounding text literally. Is there a benchmark, a number, a citation — or just the claim repeated in different words?
3. **Name the evidence's source and scope.** "Benchmarked on our staging cluster with our real query patterns" is strong. "Faster in general" with no source is not evidence, it's a restated opinion.
4. **Check if the evidence actually supports the specific claim.** A benchmark showing MongoDB is faster for bulk inserts does not support a claim about read-heavy dashboard queries. Mismatched evidence is one of the most common gaps.
5. **State what's missing.** If there's no evidence, say so directly: "I don't see a benchmark or data behind this — what did we measure?"

## A concrete example

**The claim, in a design doc:** "We should switch the orders table from Postgres to MongoDB — it'll be faster for our use case."

**What's actually written nearby:** "MongoDB is known for being fast and scales horizontally. Lots of high-traffic companies use it."

**Split it apart:**
- Claim: MongoDB will be faster than Postgres *for our orders table and our query patterns*.
- Evidence offered: "MongoDB is known for being fast" (a general reputation claim, not a measurement) and "lots of companies use it" (popularity, not performance for this workload).
- What's missing: No benchmark on our actual queries. No numbers. No comparison of our current Postgres query plans and where they're slow. No mention of what "faster" is even measuring — write latency? Read latency under our access pattern (mostly indexed lookups by `order_id` and range scans by `created_at`)?

**What good evidence would look like:** "We ran our top 5 production queries against a MongoDB replica seeded with a 30-day snapshot of orders. The `created_at` range scan (currently 180ms p95 on Postgres) ran at 340ms p95 on MongoDB without a compound index, and 95ms with one added. Write latency for a single order insert was comparable (12ms vs 14ms)." That's a claim you can act on — it names what was tested, against what baseline, with what result.

**The actual fallacy here:** this is an **appeal to authority / popularity** — "companies like X use it, so it must be right for us" skips the step of checking whether your workload resembles theirs at all.

## Recognize the fallacies you'll see most often

| Fallacy | What it sounds like | Why it's weak |
|---|---|---|
| Appeal to authority | "A senior engineer said we should do it this way." | The person's seniority doesn't make the specific claim about *this* system true — ask for their reasoning, not their title |
| False dichotomy | "Either we rewrite the whole service or we keep shipping bugs forever." | Hides a middle option (incremental refactor, targeted fix) that the two extremes obscure |
| Anecdote as proof | "It worked at my last company, so it'll work here." | One data point, different scale, different team, different constraints — not evidence about this system |
| Appeal to popularity | "Everyone's using microservices now." | Popularity says nothing about whether it fits your team size, traffic, or operational maturity |
| Confusing correlation with cause | "Deploys went out and then errors spiked, so the deploy caused it." | Plausible, but not proven — check what else changed at the same time before concluding |

## Common beginner mistakes

| Mistake | Why it hurts | Fix |
|---|---|---|
| Accepting a claim because it's stated confidently | Confidence is not evidence — a wrong claim stated firmly is still wrong | Ask "what was measured?" regardless of how sure the speaker sounds |
| Treating "no one objected" as agreement | Silence in a meeting often means people didn't have time to think it through, not that they verified it | Ask directly: "does anyone have data that supports or contradicts this?" |
| Attacking the person instead of the claim | Turns a factual disagreement into a social conflict, and the actual claim never gets checked | Restate the claim in neutral terms and ask what would prove or disprove it |
| Assuming the first plausible-sounding reason is the real reason | The first explanation that comes to mind is rarely tested against alternatives | Write down at least one alternative explanation before accepting the first one |

## Hands-on exercise

Find a real design doc, PR description, or code review comment from your own recent work.

1. Pick one sentence that states a claim (a prediction, a comparison, or a "this is better because..." statement).
2. Write the claim alone, stripped of any supporting language.
3. List, separately, every piece of actual evidence offered for it (numbers, benchmarks, named sources — not just confident phrasing).
4. Decide: does the evidence actually support this specific claim, or a related-but-different one?
5. Write one sentence stating what evidence would be needed to make the claim solid.

If you can't find any real evidence in step 3, you've found an unsupported claim — that's the point of the exercise, not a failure of it.

## Verify your thinking

- [ ] Can you write the claim as one sentence, with no evidence mixed in?
- [ ] Can you point to the exact evidence offered, or state plainly that there is none?
- [ ] Does the evidence match the specific claim, or a different, easier-to-support claim?
- [ ] Can you name which fallacy (if any) is doing the persuading instead of the evidence?
- [ ] Could you explain, to someone else, exactly what data would change your mind?

Continue to [`middle.md`](middle.md).
