# First-Principles Thinking — Junior

**Your question:** Is this actually a hard constraint, or just an inherited assumption nobody has questioned?

Codebases are full of small rules nobody currently defends: "we paginate at 20," "retries are capped at 3," "usernames are max 32 characters." Some of these are real constraints — a database limit, a contract, a law. Most are inherited: someone chose a number once, it worked, and it was copied forward until it looked load-bearing. Confusing the two means you either break something real by "simplifying" it, or you spend effort protecting a rule that was never actually required.

## The method: Trace it to bedrock

1. **State the rule as it stands today**, in one sentence, with the actual number or behavior. Not "we limit uploads" — "uploads are rejected above 5MB."
2. **Ask "why" and write down the answer.** Then ask "why" about *that* answer. Keep going until you hit one of two floors:
   - A **verifiable fact**: a measured limit, a law, a contract clause, a number you can check right now.
   - An **inherited assumption**: "that's what we did last time," "someone chose this," "it matched a system that no longer exists."
3. **Classify the floor you landed on.**
   - Genuine constraint: still true if you rebuilt the system from scratch today, independent of who's asking.
   - Inherited assumption: exists because of precedent or convenience, and nobody currently on the team can defend it from a fact.
4. **If it's inherited, look for the real fact underneath it.** The rule was probably protecting *something* once — find out what, and check if that something is still true, still relevant, or still true at the same value.
5. **Decide, and write down why.** Keep the rule (now for a real, current reason), change it (freed from a stale constraint), or leave it for now and say explicitly "not worth the churn today."

## A concrete example

**Rule as it stands:** the order-history API returns 20 items per page.

**Ask why (round 1):** "That's the default our other list endpoints use." Not a fact yet — that's just consistency with another inherited choice.

**Ask why (round 2):** Git blame on the endpoint points to a three-year-old PR whose description says "match the admin panel's table default." Follow that: the admin panel's default of 20 dates to 2014, when its table rendered as static HTML with no scrolling or virtualization — 20 rows was chosen because that's what fit above the fold on a 1024×768 monitor without the page growing too tall.

**Floor reached:** an inherited assumption. The admin panel that justified "20" no longer exists in that form, and the order-history API isn't even the admin panel — it's a JSON endpoint consumed by a mobile app.

**Find the real fact underneath:** what actually constrains page size today?
- Backend: order history is indexed by `(user_id, created_at)`; a query for 100 rows costs about the same as a query for 20 — no meaningful backend constraint at this scale.
- Mobile client: the app requests pages to fill an infinite-scroll list and currently pages every ~4 seconds of scrolling on a fast connection; each round trip costs ~120ms on 3G, and users have filed complaints about pagination lag on slow networks.
- Real, current constraint: fewer round trips is better on slow networks, and the client can comfortably hold 50 rows in memory for the scroll view.

**Decision:** raise the default to 50, matching the actual current constraint (network round-trip cost on mobile), and drop the "matches the admin panel" justification because that system no longer governs this decision. Written down: "Changed order-history page size from 20 → 50. Old value copied from a 2014 admin-panel UI limit that no longer applies to this endpoint. New value chosen to reduce round trips on 3G; backend query cost is flat across this range."

## Recognize the signals

**Signals you're looking at an inherited assumption, not a constraint:**
- The reason given is "we've always done it this way."
- Nobody currently on the team can restate the reason as a fact, only as precedent.
- The value was copied from a blog post, a different company's system, or a tutorial.
- Changing it "feels risky," but no one can name what specifically would break.
- The commit or ticket that introduced it references a system that no longer exists.

**Signals you're looking at a genuine constraint:**
- A law, contract, or SLA explicitly requires this value.
- You can measure the limit right now (e.g., your load balancer rejects payloads over 10MB — try it).
- Removing or changing it reproduces a failure in a test, today, on the current system.

## Common beginner mistakes

| Mistake | Why it hurts | Fix |
|---|---|---|
| Treating "we've always done it this way" as a real reason | You accept a stale limit as if it were physics, and design around it unnecessarily | Ask "why" until you hit a verifiable fact, a name, or a date — not a feeling |
| Re-litigating every convention, all the time | Slows down trivial decisions and wears out your teammates' patience | Reserve assumption-tracing for decisions with real cost — see the exercise below for how to pick one |
| Stopping at the first "why" answer | The first answer is almost always another inherited assumption, not the root | Keep asking why until the answer can't be traced any further back, or becomes a fact |
| Confusing "hard to change" with "cannot change" | A merely inconvenient convention gets frozen as if it were a hard limit | Hard-to-change is a cost, not a constraint — track them separately |
| Removing a rule without checking what it protected | The old-looking rule may be a real safeguard wearing a dusty coat | Trace it first; write down what you checked before you remove anything |

## Hands-on exercise

Pick one small existing rule in your own code — a pagination limit, a retry count, a timeout value, a cache TTL, a field-length limit.

1. Write the rule as it stands today, in one sentence, with the actual number.
2. Find its origin: git blame, a comment, a doc, or ask a teammate who was there.
3. Ask "why" at least three times, writing down each answer as you go.
4. Classify the final answer: genuine constraint (name what makes it genuine) or inherited assumption.
5. If it's inherited, name the real, current fact that should determine the value instead — with a number if you can get one.
6. Decide: keep it, change it, or "not worth the churn right now" — and write one sentence saying which and why.

## Verify your thinking

- [ ] Can you state the rule you examined as one sentence with a concrete number or behavior?
- [ ] Did you ask "why" more than once, instead of stopping at the first answer?
- [ ] Can you name whether the floor you reached is a verifiable fact or an inherited assumption — and say what makes it one or the other?
- [ ] If it was inherited, did you find the real, current fact that should actually decide the value?
- [ ] Did you write down your decision and the reason, so the next person doesn't have to redo this trace?

Continue to [`middle.md`](middle.md).
