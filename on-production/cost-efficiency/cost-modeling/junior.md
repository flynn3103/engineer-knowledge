# Cost Modeling — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Given a small API service's monthly cost breakdown and its request volume, can you calculate a correct cost-per-request and cost-per-user figure and explain what each cost category contributes?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

> **Roadmap:** [Cost Efficiency](../README.md) → Cost Modeling

*A cost model turns a scary total invoice into a number small enough to reason about: what does one request, or one user, actually cost us? Getting that one division right is the whole junior-level skill.*

---

## Core Concept 1 — Vocabulary

- **Unit economics** — the practice of expressing cost (and often revenue) per single unit of work, so costs of wildly different scale become comparable.
- **Cost-per-request** (or cost-per-transaction) — total relevant cost for a period, divided by the number of requests served in that same period.
- **Cost-per-user** — total relevant cost divided by a user-count metric for the same period, usually monthly active users (MAU) or daily active users (DAU).
- **Fixed cost** — cost that doesn't change with volume in the short term (a reserved database instance, a fixed-price SaaS contract).
- **Variable cost** — cost that scales with volume (a pay-per-request third-party API, bandwidth billed per gigabyte).
- **Direct cost** — cost you can attribute to one specific service or feature without guessing.

Cost modeling is *not* capacity planning. Capacity planning uses a cost/usage model to decide how much infrastructure to provision ahead of demand; cost modeling is the prior step of building a trustworthy "what does this cost per unit" number in the first place. You cannot plan capacity sensibly with a unit cost you got wrong.

## Core Concept 2 — A Repeatable Method

For any service, calculating a unit cost is the same five steps every time:

1. **Pick the unit.** Requests, transactions, active users, or jobs processed — whichever matches how the product actually creates value. A payments API cares about cost-per-transaction; a photo-editing API cares about cost-per-request or cost-per-active-user.
2. **Gather every cost input for one period.** Compute, managed database, storage, third-party/managed APIs, bandwidth — for the *same* time window as the volume you'll use in step 3.
3. **Gather the volume for the identical period**, using the definition that matches your intent — usually successful, billable work, not every raw incoming request including retries and bot traffic, unless you deliberately want that broader denominator.
4. **Divide total cost by volume.** That's the unit cost.
5. **Sanity-check it.** Compare against last period's figure and against any known price-per-unit the business charges. A number that jumped 5x from last month with no matching event is a red flag to investigate, not a result to report.

## Core Concept 3 — Worked Example: the PhotoResize API

`PhotoResize` is a small internal API: it accepts an image, resizes it, and returns a URL to the result. Here is one month's cost breakdown (illustrative figures, not a real invoice):

| Cost category | Monthly cost (USD) | Fixed or variable |
|---|---|---|
| App server compute (always-on pool) | $12,000 | Fixed (sized for peak, doesn't shrink with light traffic) |
| Managed Postgres (job metadata) | $1,800 | Fixed |
| Object storage (resized images) | $1,200 | Variable (scales with stored bytes) |
| Third-party image-processing API | $1,500 | Variable (billed per call) |
| **Total** | **$16,500** | |

Volume for the same month: 33,000,000 successful resize requests, from 45,000 monthly active users.

**Cost-per-request:**

```
$16,500 / 33,000,000 requests = $0.0005 per request
                               = $0.50 per 1,000 requests
```

**Cost-per-user:**

```
$16,500 / 45,000 MAU = $0.3667 per user per month
```

Two things worth noticing in this small example. First, the two "fixed" line items ($13,800 of the $16,500) dominate the bill — meaning cost-per-request will barely move even if volume drops 20%, because most of the cost doesn't scale down with it. Second, breaking the total into categories before dividing lets you say *which* category drives the number: here, compute alone is $12,000 / 33,000,000 ≈ $0.00036 per request, roughly 70% of the total unit cost by itself. A single blended number hides that; the category table doesn't.

## Core Concept 4 — Simple Success Criteria

A junior-level unit-cost figure is trustworthy when all four of these hold:

1. **Matching time windows.** The cost total and the volume total cover exactly the same period — not "this month's bill against last month's traffic count" because that was the easiest number to find.
2. **Complete cost inputs.** Every cost category actually caused by serving this unit is included — not just the line item that happens to live in the same dashboard you were already looking at.
3. **Matching denominator definition.** If the intent is "cost per *successful* request," the denominator must be successful requests, not every request the load balancer saw (including retries, 4xx, and bot traffic), unless that broader definition is what you actually meant.
4. **Sanity-checked, not just computed.** You compared it to the prior period and it makes sense, or you can explain why it changed.

## Real-World Examples

- **The hidden third-party line item.** A junior engineer computes `PhotoResize`'s cost-per-request using only the cloud bill (compute, database, storage) and gets $0.00033 — a suspiciously cheap-looking number. The third-party image-processing API is billed through a separate vendor portal and never makes it into the total, so the real figure, once added, is 50% higher.
- **A fixed cost mistaken for noise.** A cost report shows the same $12,000 compute line every month regardless of traffic, and a first-time reader assumes it must be a mistake — surely a service that handles more requests some months should cost more some months? The fixed/variable distinction from Core Concept 1 explains it: the always-on server pool is sized for peak load, so its cost doesn't move with day-to-day traffic even though total requests do.
- **Revenue and cost get swapped.** Asked for "the cost per request," a junior engineer reports the price the API's customers are billed per call instead of what it costs the team to serve that call. The two numbers can look similar in magnitude and get confused, but one measures spend and the other measures income — mixing them up makes any margin conversation nonsensical.

## Common Mistakes

- **Mismatched time windows.** Pulling this month's cloud bill against last month's request count because the request count was easier to find — the resulting unit cost is meaningless.
- **Omitting an inconvenient cost category.** The third-party image-processing API charge often lands on a separate invoice from the cloud bill and gets left out simply because nobody thought to go find it.
- **Confusing cost with revenue or margin.** "Cost per request" answers what it costs *us*; it is not the price charged to a customer and not profit margin. Mixing these up produces a number that answers the wrong question.
- **Wrong denominator.** Using total incoming requests (including failed and retried ones) when the real question was about successful, billable work — or the reverse, understating true load by only counting successes when the fixed compute pool has to be sized for *all* traffic, including retries.
- **Ignoring idle/baseline cost.** A server pool provisioned for peak traffic still costs money at 3 a.m. when load is light. That baseline cost is real and belongs in the numerator; it doesn't disappear just because it wasn't "caused" by any single request in that quiet hour.
- **Treating a one-time cost as if it recurs.** A one-off data migration fee or an annual reserved-capacity prepayment, if divided evenly across every month without adjustment, will distort the unit cost for the month it happened to land in.

## Apply it

1. Take this cost breakdown for a fictional URL-shortener service, `ShortLink`, for one month: app compute $4,500, managed Redis cache $600, managed Postgres $900, DNS/CDN $400. Total volume: 18,000,000 successful redirect requests, 60,000 MAU.
2. Mark each cost category as fixed or variable, and note which one dominates the total.
3. Calculate cost-per-request and cost-per-user for `ShortLink`, showing your division explicitly (don't just state the final number).
4. Recalculate cost-per-request assuming redirect volume drops 30% next month but every cost category stays the same — write down what changed and why, in one sentence.
5. Write one sentence identifying which cost category you would investigate first if next month's total jumped by $2,000 with no change in traffic.

## Verify your work

- Your cost-per-request and cost-per-user figures are shown with the full division (numerator and denominator both stated), not just a final number.
- You can name, without looking back at the table, which single cost category contributes the most to the total.
- Your answer to the volume-drop question correctly identifies that cost-per-request *rises* when fixed costs stay flat and volume falls — not that it stays the same.
- Your investigation answer names a specific cost category and a specific reason it's the most likely suspect, not "check everything."

## Review questions

- What is the difference between cost-per-request and cost-per-user, and when would you use one instead of the other?
- Why must the cost total and the volume total cover exactly the same time period?
- Why does a service's cost-per-request rise when traffic drops, even though nothing about the service's code changed?
- What is the difference between a fixed cost and a variable cost, and why does that distinction matter when volume changes?
