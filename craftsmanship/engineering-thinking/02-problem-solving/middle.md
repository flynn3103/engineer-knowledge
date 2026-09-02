# Problem-Solving — Middle

**Your question:** How do I manage several plausible approaches and produce a plan I can safely change my mind about?

At junior level, one clear plan is enough because the problem is usually small and the right approach is usually obvious once you understand the problem. At middle level, the problem is understood but the *approach* isn't — there are two or three plausible ways to solve it, each with real trade-offs, and committing to the wrong one costs real time. The skill here isn't picking correctly on the first try; it's comparing approaches honestly and building a plan that stays cheap to redirect when you learn something new.

## The method: Generate, evaluate, sequence for reversibility, look back

1. **Generate at least two distinct approaches before planning either one in detail.** Committing to the first idea that comes to mind is anchoring — you stop looking as soon as something seems workable, not when something is actually best.
2. **For each approach, write down four things:** cost to build, cost to verify, cost to undo if it's wrong, and what evidence would tell you it's the wrong choice.
3. **Choose using that table, not gut feel.** If your gut still disagrees with the table, that's a signal you're missing a factor — find it and add it, don't override the table silently.
4. **Sequence the chosen approach into steps ordered by reversibility.** Cheap, reversible steps go first; expensive or hard-to-undo steps go last. A wrong turn should surface while it's still cheap to correct.
5. **Execute step by step, checking against reality after each step**, not just against your plan.
6. **Look back after finishing.** Ask what surprised you during execution — not what went as expected. Extract exactly one durable lesson and put it somewhere it will actually be seen again (a doc, a checklist, a test).

## Generate and evaluate: a worked example

**Problem:** A team's admin dashboard runs one query that joins three large tables and takes 4.5 seconds to load, well past the 1-second target. Success criteria: p95 load time under 1 second, no data-freshness regression beyond 5 minutes, shippable in one sprint.

**Two competing approaches — evaluated before either is planned in detail:**

| Approach | Cost to build | Cost to verify | Cost to undo | Evidence it's wrong |
|---|---|---|---|---|
| A: Add a read-through cache in front of the query | ~2 days | Easy — compare cached vs. live results in a diff test | Cheap — remove the cache layer, revert to direct query | Cache hit rate stays low (data changes too often to cache well) |
| B: Denormalize into a precomputed summary table, updated on write | ~5 days | Harder — must verify the summary stays in sync under concurrent writes | Expensive — schema change, migration, and dependent code to unwind | Summary table drifts from source under load, or write path slows down |

**Choice:** Approach A first. It's cheaper to build, cheaper to verify, and cheap to undo if wrong — and the evidence that would prove it wrong (low cache hit rate) is available within a day of shipping it. Approach B is kept as a fallback if A's evidence comes back bad; note that decision and why, so it isn't re-litigated later.

**Why not just pick B because it's the "real" fix?** Because "real fix" is an opinion until you have evidence. A is the cheaper experiment that tells you whether the read pattern is even cacheable — information you need before justifying B's higher cost.

## Sequence the plan for reversibility

Once you've picked approach A, don't build it as one big change. Order the steps so the riskiest, least-reversible parts come last:

1. **Add the cache with a feature flag, defaulting off.** (Reversible in seconds — flip the flag.)
2. **Turn it on for your own account only; compare cached output to live output for a week of your own usage.** (Reversible instantly; no other user affected.)
3. **Turn it on for 5% of traffic; watch cache hit rate and staleness complaints.** (Reversible in minutes; blast radius small.)
4. **If hit rate and freshness hold, ramp to 100%.** (Still reversible via the flag.)
5. **Only after two weeks with no rollback, remove the flag and the old code path.** (This step is the actual irreversible one — put it last, and only after real evidence, not optimism.)

Compare this to planning it as "build the cache, ship it" — a single irreversible step where any wrong assumption (e.g., data changes too fast to cache) is discovered only after full rollout.

## Look back: extract one durable lesson

After the rollout above finishes, the temptation is to close the ticket and move on. Don't — spend five minutes on a look-back before you do:

- **What surprised you?** In this example: cache hit rate was fine, but staleness complaints came from an internal admin who edits and immediately checks the dashboard — a use case the success criteria never mentioned.
- **Extract one lesson, not ten.** Here: "read-through caches for admin views need a short-TTL bypass for the user who just wrote the data." A list of ten minor observations gets read once and forgotten; one sharp lesson is more likely to survive.
- **Put it somewhere it'll be seen again.** A comment in the code near the cache config, a line in the team's design-review checklist, or a fast-follow test — not just a comment in the closed ticket.

This is different from a full retrospective (see [senior.md](senior.md) and [professional.md](professional.md) for team- and org-scale versions) — at this level it's a personal habit, not a process.

## Common mistakes at middle level

| Mistake | Why it hurts | Fix |
|---|---|---|
| Commit to the first approach that seems workable | You never compare it to anything, so you can't know if it's actually the best option available | Generate at least one competing approach before planning either in detail |
| Evaluate approaches only on build cost | The cheapest approach to build can be the most expensive to verify or undo | Score verify-cost and undo-cost explicitly, not just build-cost |
| Order plan steps by convenience instead of reversibility | The riskiest, hardest-to-undo work happens early, so mistakes are expensive to fix | Put reversible, cheap steps first; irreversible steps last, gated on evidence |
| Skip the look-back because the fix "worked" | The same surprise resurfaces on the next similar problem, and nobody remembers it happened before | Spend five minutes after every non-trivial fix on what surprised you |
| Write the look-back lesson only in the closed ticket | Closed tickets are never read again; the lesson dies with the ticket | Put the lesson somewhere still-visible: code comment, checklist, or test |

## Hands-on exercise

Pick a problem you're currently facing that has more than one plausible solution.

1. Write down at least two distinct approaches — don't let yourself stop at one.
2. For each, fill in the four-column table: cost to build, cost to verify, cost to undo, evidence it's wrong.
3. Pick one using the table. If your gut disagrees, name the missing factor and add it to the table.
4. Sequence your chosen approach into steps ordered from most-reversible to least-reversible.
5. Identify the one step in your plan that is genuinely hard to undo. What evidence do you need *before* taking that step?
6. After you finish (or once you've made real progress), write the one thing that surprised you and where you'll record it.

## Verify your thinking

- [ ] Did you generate at least two approaches before planning either in detail?
- [ ] Does your evaluation include cost to undo, not just cost to build?
- [ ] Is your plan ordered so a wrong turn is cheap to discover and fix?
- [ ] Can you name the one step in your plan that's genuinely irreversible, and what gates it?
- [ ] Did you extract exactly one durable lesson, and put it somewhere it will be seen again?

Continue to [`senior.md`](senior.md).
