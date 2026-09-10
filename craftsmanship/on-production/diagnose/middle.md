# Debug-Thinking — Middle

**Your question:** How do I find a bug when it isn't in one obvious function — when the evidence is scattered across a call chain, multiple commits, or multiple services?

Junior level teaches you to hypothesize and test inside one function you can see end to end. At middle level, the failure crosses a boundary: it started somewhere in the last 40 commits, or it happens somewhere between a request entering your service and a response leaving it, and you can't just read the whole thing top to bottom and spot it.

## Bisect the failure surface, not just the code

**Bisection is binary search applied to "where is the bug," not "what is the bug."** Cut the space that could contain the fault in half, check which half still reproduces the failure, and repeat. This works at multiple granularities:

- **Bisect commit history:** the bug wasn't there 3 weeks ago and is there now. Instead of reading every commit, check the middle commit of the range. Still broken → bug is in the first half. Works → bug is in the second half. Repeat. (`git bisect` automates exactly this loop.)
- **Bisect a call chain:** a request fails somewhere between the API gateway and the database. Add one checkpoint (log line, trace span) at the midpoint of the chain. If the data is already wrong there, the bug is upstream of that point; if it's still correct, the bug is downstream.
- **Bisect a data pipeline:** a batch job produces wrong output. Instead of reading the whole transform, dump the intermediate state halfway through and check if it's already wrong there.

Each bisection step should cut the remaining search space roughly in half. A search that only eliminates one possibility per step is not bisection — it's linear search, and it doesn't scale past a handful of candidates.

## Correlate signals instead of trusting one source

At this level, no single signal tells the whole story. A user bug report says "checkout failed." The application log shows a 200 response. The payment provider's dashboard shows a declined charge. These aren't contradictory — they're describing different points in the same chain, and the bug is in the gap between what the log says and what actually happened.

**How to correlate:**

1. **Line up signals by a shared key.** A request ID, user ID, or timestamp that appears in more than one source lets you confirm you're looking at the same event across systems.
2. **Trust the most specific signal over the most convenient one.** "The log says success" is convenient; "the payment provider shows declined" is specific to the actual failure. When they conflict, the gap between them *is* the bug — here, the app never checked the payment provider's actual response code.
3. **Note what's missing, not just what's present.** If a request has upstream logs but no downstream logs, the request likely never reached downstream — that absence is evidence, not a gap to ignore.

## Prioritize competing hypotheses

At junior level there's usually one plausible hypothesis. At middle level, several signals can each suggest a different cause. Prioritize by:

1. **Explanatory power first.** Which hypothesis explains *all* the observed symptoms, not just some of them? A hypothesis that explains 3 of 4 symptoms and requires "a second, unrelated bug" for the fourth is usually wrong.
2. **Cost to test second.** Among hypotheses with similar explanatory power, test the cheapest one first (a log line beats a new deployment).
3. **Recency and blast radius third.** A hypothesis tied to a change deployed an hour before the first report is more likely than one tied to code that hasn't changed in a year — but don't let recency override explanatory power; "it's probably the last deploy" without checking the actual diff is a guess, not a hypothesis.

## Recognize cross-boundary bug patterns

| Pattern | Signature | Where to look |
|---|---|---|
| Race condition | Fails only under concurrency or load; not reproducible by running the same steps alone, locally, slowly | Anything read-then-written without a lock, transaction, or atomic operation |
| Cache invalidation | Stale data after an update; correct data appears after a delay or restart | Where the cache is written vs. where the source of truth is written — are they updated together? |
| N+1 query / hidden fan-out | Fine with small data, slow or timing out with real data | A loop that calls out to a database or service once per item instead of once total |
| Timezone / DST | Off-by-one-hour, wrong day near midnight, breaks only around a DST transition | Anywhere a timestamp crosses a timezone boundary without an explicit zone |
| Partial failure treated as success | Downstream shows failure, upstream logged success | Whether the calling code actually checks the *result* of a downstream call, not just that the call didn't throw |
| Version skew | Fails intermittently after a partial deploy, works again once fully rolled out | Whether two communicating services or a service-and-client pair can be running different versions simultaneously |

## A concrete example

**Symptom:** Checkout succeeds for most users, but ~2% of orders are marked "paid" while the payment provider shows them as declined.

**Bisect the chain:** Checkpoint at three points — order-service log, payment-service log, payment provider's own dashboard. Pull 10 known-bad order IDs and check all three.

**Correlate:** All 10 orders show `200 OK` in the order-service log. All 10 show a `declined` status in the payment provider's dashboard. The payment-service log for these 10 shows the provider's response was received — but the *specific field* the order-service checks (`status == "success"`) is missing from the older provider API version still used by 2% of traffic (a canary still on the old client library).

**Prioritize:** This hypothesis explains all three symptoms (success recorded, decline actually happened, only a minority of traffic affected) — it beats a "random flakiness" hypothesis, which explains the rate but not the systematic direction (always fails toward false-success, never false-decline).

**Fix:** The order-service should fail closed (treat missing/unrecognized status as failure, not success) instead of failing open.

**Verify:** Re-run the 10 known-bad order IDs' request payloads against a test environment pinned to the old client library version; confirm they now correctly mark as failed.

## Verification: unit-level and integrated-flow

- **Unit-level:** the specific function or boundary you bisected to now behaves correctly in isolation (re-run the middle.md junior-level check on that one component).
- **Integrated-flow:** the full chain, end to end, with the original reproduction steps, produces the expected result — a component-level fix that doesn't verify at the full-chain level hasn't actually confirmed the user-facing symptom is gone.

## Common mistakes at middle level

| Mistake | Fix |
|---|---|
| Reading logs from only one system when the bug spans a boundary | Correlate by request ID/timestamp across every system the request touched |
| Bisecting linearly (checking commits one at a time from newest) instead of binary search | Always check the midpoint of the remaining range, not the next item in a list |
| Picking the hypothesis that's easiest to believe instead of the one that explains the most evidence | Score each hypothesis against every symptom, not just the loudest one |
| Treating "no error was thrown" as "it succeeded" | Check the actual return value or downstream state, not just the absence of an exception |
| Fixing at the point you noticed the bug instead of the point it was introduced | Trace back to where the two systems' understanding of reality diverged |

## Hands-on exercise

Take a bug (real or constructed) that involves at least two components or a range of commits.

1. Identify the smallest number of checkpoints needed to bisect the failure surface in half, then half again.
2. Pull the evidence from each checkpoint and line it up by a shared key (request ID, timestamp, user ID).
3. Write two competing hypotheses. For each, list which symptoms it explains and which it doesn't.
4. Pick the hypothesis with the most explanatory power, and design the cheapest test that would confirm or refute it.
5. After fixing, verify at both the unit level (the specific boundary) and the integrated-flow level (the original symptom, end to end).

## Verify your thinking

- [ ] Did you cut the search space roughly in half at each bisection step, not just eliminate one candidate at a time?
- [ ] Did you correlate evidence from every system the request touched, using a shared key?
- [ ] Does your chosen hypothesis explain *all* the observed symptoms, not just the most obvious one?
- [ ] Did you verify at both the unit level and the full end-to-end flow?
- [ ] Can you point to the exact moment two systems' understanding of the world diverged?

Continue to [`senior.md`](senior.md).
