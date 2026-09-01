# Efficiency as a Feature — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Can I write a well-scoped efficiency improvement as a backlog item — with a baseline cost, a measurable target, and a way to verify the savings — so it gets prioritized the same way a feature would?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Efficiency Is a Requirement, Not a Cleanup Task

Most new engineers first meet "cost" as something that shows up after the fact: a Slack message from finance, a surprised look at a cloud bill, a "can someone look at why this got expensive" ticket filed weeks after the change that caused it. Treating **efficiency as a feature** means the opposite posture: cost-per-unit-of-work is a property of the system you design for on purpose, the same way you design for correctness or availability, and it gets written down, estimated, and prioritized *before* it becomes an emergency.

This topic is not about how to calculate a cost model or forecast capacity (that's covered elsewhere) — it's about the habit of turning "this is wasteful" into something a team can actually schedule, staff, and finish, the same way a feature request goes from idea to shipped code.

The concrete skill at junior level: write an efficiency improvement as a ticket that a planning meeting can evaluate on the same terms as a feature — what it costs to build, what it saves, and how you'll know it worked.

This matters even for a junior engineer working on one small piece of a system, because the habit of writing cost claims down and checking them is what makes the rest of your career-long relationship with cost trustworthy. An engineer who says "I made it cheaper" and never checks becomes an engineer whose cost claims nobody double-checks, either in the good direction or the bad one.

## Core Concept 2 — Vocabulary

| Term | Meaning |
|---|---|
| **Efficiency backlog item** | A ticket describing a specific, scoped change expected to reduce cost-per-unit, written with the same rigor as a feature ticket (problem, approach, acceptance criteria). |
| **Baseline** | The current, measured cost before the change — a number you can point to, not an impression. |
| **Target** | The cost you expect *after* the change, stated as a number or a percentage reduction. |
| **Savings estimate** | Baseline minus target, multiplied out to a period (per day, per month) so it's comparable to engineering effort. |
| **Owner** | The person or team accountable for the metric moving — not just for writing the code, but for confirming the number actually changed. |
| **Cost-per-unit** | Cost divided by a unit of work the business cares about (per request, per user, per job run) — the number that makes cost comparable across time even as traffic changes. |

The single habit that separates a real efficiency item from a vague intention: **a baseline and a target, both written down before the work starts.** "Make this cheaper" is not a ticket. "Reduce cost-per-request on `GET /search` from $0.004 to $0.0025" is.

## Core Concept 3 — The Method

Writing a good efficiency backlog item follows the same five steps every time:

1. **Measure the baseline.** Pull the actual current cost-per-unit from billing data, a cost dashboard, or a simple calculation (infra cost ÷ requests served over the same window). Write down the number and the window it covers.
2. **Name the change.** One specific, scoped technical action — not "optimize the service," but "add a 5-minute cache in front of the product-catalog read path."
3. **Estimate the target.** State the expected cost-per-unit after the change, and how you got that number (even a rough estimate, labeled as such, is fine at this level).
4. **State how you'll verify it.** Name the exact metric and dashboard you'll check after deployment, and how long you'll wait before calling it done.
5. **Assign an owner.** One name who is responsible for both making the change and confirming the number moved — not "the team," a person.

## Core Concept 4 — Worked Example: A Caching Ticket

**System:** `catalog-api`, a read-heavy service serving product detail pages. Traffic: roughly 2,000,000 requests/day. No caching layer — every request hits the primary database.

**Baseline measurement (from last week's billing + request logs):**

| Metric | Value |
|---|---|
| Requests/day | 2,000,000 |
| Database compute cost/day | $180 |
| Cost per request | $0.00009 |

That number alone looks small — the point of writing it as a ticket is that "small per request" times "2,000,000 requests/day" times "365 days/year" is a real, budget-line number, and it is the number that will get compared against the cost of doing nothing.

**The ticket, as it would actually be written:**

```text
Title: Add read-through cache for product detail lookups

Problem: catalog-api hits the primary database on every product-detail
request. 95% of requests are for the same ~5,000 popular products.

Baseline: $180/day database compute cost, 2,000,000 requests/day
          ($0.00009 per request), measured from last 7 days of billing.

Change:   Add a 5-minute TTL read-through cache (existing Redis cluster,
          no new infrastructure) in front of the product-detail read path.

Target:   Cut database read volume by ~80% (cache hit rate estimate
          based on request-log analysis of repeat product IDs), reducing
          database compute cost to an estimated $45/day
          ($0.0000225 per request) -- illustrative estimate, to be
          confirmed after rollout.

Verify:   Compare database compute cost/day and cache hit-rate metric,
          7 days after rollout, against this baseline. Dashboard:
          "catalog-api cost" in Grafana.

Owner:    Priya (backend, catalog team)
Effort:   ~2 days
```

**After rollout (illustrative before/after):**

| Metric | Before | After (7-day average) |
|---|---|---|
| Cost per request | $0.00009 | $0.000021 |
| Database compute cost/day | $180 | $42 |
| Cache hit rate | n/a | 84% |

The ticket is "done" not when the code merges, but when this table exists and the owner has confirmed the number actually moved — a code change that was never checked against its own baseline is not a verified efficiency win, it's a hope.

## Common Mistakes

- **Writing "optimize the service" as the whole ticket.** Without a named technical change, an estimate, and a baseline, there is nothing to prioritize against — it reads as vague busywork next to a concrete feature ticket, and loses every planning conversation.
- **Skipping the baseline.** Without a "before" number, nobody can tell afterward whether the change actually helped, made things worse, or the difference was just normal traffic variance.
- **No named owner.** A ticket owned by "the team" rarely gets picked up, and even if the code ships, nobody checks whether the number moved.
- **Confusing effort saved with money saved.** "This makes the code cleaner" is a real benefit, but it is not the same claim as "this reduces cost-per-request" — an efficiency ticket needs the cost claim, specifically.
- **Never closing the loop.** Shipping the change and moving on without checking the dashboard a week later means you never actually know if the target was hit — and you lose the evidence you'd need to justify the next efficiency ticket.
- **Treating the estimate as a promise.** A target is a planning estimate, not a guarantee — label it as such, and revise the ticket if the real number that comes back is different.

---

## Apply it

1. Pick one service or endpoint you have access to and find its cost-per-unit — from a billing dashboard, a cost-allocation tag, or a rough calculation (infra cost ÷ requests over the same window).
2. Identify one concrete, scoped change that should reduce that cost (a cache, a smaller instance type, a batched query) — not a vague "optimize" statement.
3. Write it as a ticket with the five parts from Core Concept 3: baseline, change, target, verification plan, and owner.
4. Bring the ticket to a planning conversation (real or simulated) and estimate its effort in the same units you'd use for a feature (story points, days).
5. If you can actually ship it, confirm the real cost-per-unit one week later and update the ticket with the before/after table.

## Verify your work

- The ticket names a specific baseline number, with the measurement window stated.
- The ticket names a specific, scoped technical change — not a general instruction to "optimize."
- The target is stated as a number (or percentage), labeled as an estimate if it hasn't been confirmed yet.
- A single named owner is responsible for both the change and confirming the result.
- If shipped, a before/after table exists showing the real cost-per-unit change, not just "it feels faster."

## Review questions

- Why does an efficiency ticket need a baseline number, not just a description of what to change?
- What is the difference between "this makes the code cleaner" and "this reduces cost-per-request," and why does an efficiency ticket need the second claim specifically?
- Why should an efficiency backlog item have exactly one named owner rather than "the team"?
- What would be missing from a ticket that just said "optimize catalog-api"?
