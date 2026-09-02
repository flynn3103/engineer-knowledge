# Scientific and Hypothesis-Driven Thinking — Junior

**Your question:** What's my falsifiable hypothesis for whether this change actually helps, and how do I check it cheaply?

"This should make it faster" is not a hypothesis — no observation could ever prove it wrong, because it names no number, no direction, and no mechanism. "Adding an index on `orders.user_id` will cut `GET /orders` p95 latency from ~420ms to under 150ms, because the query planner is currently doing a full table scan" is falsifiable: run the test, and either the latency drops below 150ms or it doesn't.

## The method: state it, predict it, measure it

1. **Write the current belief in one plain sentence.** "I think this will help" — capture it honestly before dressing it up.
2. **Name the mechanism.** Why would this change produce the effect? If you can't say *why*, you don't understand the change well enough to test it yet.
3. **Attach a specific, measurable prediction.** A number, a threshold, or a clear direction — something a measurement could contradict.
4. **Design the cheapest check that could contradict it.** Not the most thorough test — the cheapest one that still gives a real answer.
5. **Measure the baseline before you change anything.** Without a "before," an "after" number means nothing.
6. **Make the change, measure again, and compare to the prediction — not to your feeling.**

## A concrete example

**Belief:** "Adding an index on `orders.user_id` will make the orders page faster."

**Rewritten as a falsifiable hypothesis:** `EXPLAIN` on the current query shows a full table scan on a 2M-row table. Adding a B-tree index on `orders.user_id` will let the planner use an index scan instead, reducing `GET /orders?user_id=X` p95 latency from ~420ms to under 150ms.

**Cheapest check:** Replay 500 real production requests for this endpoint against a staging replica, once before the index and once after, and record p95 latency both times. No load-testing framework, no new dashboards — just `EXPLAIN` and a stopwatch-grade timer around the replay.

**Baseline (before):** p95 = 418ms. `EXPLAIN` confirms `Seq Scan on orders`.

**After the change:** p95 = 310ms. `EXPLAIN` confirms `Index Scan using orders_user_id_idx`.

**Result vs. prediction:** The hypothesis predicted under 150ms; the actual result was 310ms. The index helped (mechanism confirmed — the scan type changed) but the prediction was still wrong. That's useful: it tells you the index wasn't the whole story, and something else is contributing to the remaining latency (worth its own hypothesis later), instead of declaring victory because "it got faster."

## Recognize a real hypothesis vs. a vague claim

| Vague claim (not falsifiable) | Falsifiable hypothesis |
|---|---|
| "This should help." | "This will reduce p95 latency by at least 40%." |
| "The new library feels snappier." | "The new library will render the list in under 100ms for 1,000 rows, down from ~280ms." |
| "Caching will fix it." | "Caching the config lookup will drop DB queries per request from 12 to 1, because the config rarely changes." |
| "It's probably the network." | "If it's the network, error rate should track packet loss, not request volume." |

A claim only counts as falsifiable if you can describe, right now, the specific measurement result that would prove it wrong.

## Common beginner mistakes

| Mistake | Why it hurts | Fix |
|---|---|---|
| Judging "it feels faster" instead of measuring | Subjective impressions are unreliable and not repeatable | Always take a number before and after, using the same method both times |
| Writing a prediction with no number or threshold ("this will help") | Nothing could ever prove it wrong, so it teaches you nothing | Attach a specific number, percentage, or direction to every prediction |
| Skipping the baseline measurement | You can't tell whether anything actually changed | Measure current behavior first, before touching any code |
| Changing several things at once (index + query rewrite + caching) | You can't tell which change caused the result | Change one thing, measure, then change the next thing |
| Declaring success because the result "improved," ignoring the actual prediction | You stop investigating real gaps between prediction and reality | Compare the measured result to the number you predicted, not to your prior mood |

## Hands-on exercise

Take a change you're about to make (or one you made recently without measuring it):

1. Write the current belief about it in one sentence, exactly as you'd say it out loud to a teammate.
2. Rewrite it as a falsifiable hypothesis: mechanism + specific number or direction.
3. Write down the cheapest measurement that could contradict it.
4. Measure the baseline before making the change.
5. Make the change and measure again.
6. Compare the actual result to your prediction — not to whether it "feels" better. Write one sentence on what you'd test next if the prediction was wrong.

## Verify your thinking

- [ ] Can you state a specific number or direction that, if observed, would prove your hypothesis wrong?
- [ ] Did you measure a baseline before making any change?
- [ ] Did you change exactly one thing before re-measuring?
- [ ] Can you name the mechanism — *why* you expect this change to produce this effect?
- [ ] Did you compare the actual result to your prediction, not just to how it felt?

Continue to [`middle.md`](middle.md).
