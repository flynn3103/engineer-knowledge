# Capacity Planning — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Given your service's current peak traffic, its per-instance capacity from a load test, and a simple growth rate, can you calculate how many instances you need and when the current fleet runs out of headroom?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

> **Roadmap:** [Cost Efficiency](../README.md) → Capacity Planning

*Capacity planning starts as arithmetic: how much can we handle, how much are we handling, and when does that gap close. Get the arithmetic right for one service before worrying about a whole system.*

---

## Core Concept 1 — Vocabulary

- **Capacity** — the maximum load a unit (an instance, a pod, a node) can sustain while still meeting its latency and error-rate targets.
- **Utilization** — the fraction of that capacity currently in use.
- **Headroom** — capacity minus current demand: the buffer you have before things degrade.
- **Saturation point** — the load level at which latency spikes or errors start climbing. This is a measured fact from a load test, not a guess from a CPU percentage.
- **Little's Law** — a queueing-theory identity, `L = λ × W`: the average number of requests in a system equals the arrival rate times the average time each request spends in the system. It's a quick sanity check — if you know your arrival rate and target latency, you can back into how much concurrency the system needs to support.

Capacity planning is specifically about sizing infrastructure *ahead of* demand — projecting growth and deciding when and how much to add. It is not about which hardware to buy (that's Hardware-Aware Design) or which cloud levers reduce your bill (that's Cloud Cost Optimization). Those questions come after you know how much capacity you actually need.

## Core Concept 2 — A Repeatable Method

1. **Measure current demand at peak**, not average. Peak is when you'll actually run out.
2. **Find real per-unit capacity by load testing to saturation.** Push a single instance until latency or error rate breaks its target, and record that number.
3. **Pick a headroom target.** A common starting point is to operate at no more than 60–70% of the measured saturation point at peak, so a normal spike or a single lost instance doesn't tip you over.
4. **Project demand forward using a growth rate.** Even a simple percentage-per-month figure, applied consistently, beats no projection at all.
5. **Calculate units needed at each future point**, and find the point where your current fleet's total safe capacity falls below projected peak demand — that's your action date.

## Core Concept 3 — Worked Example: A Checkout API

A checkout service currently measures:

- **Peak traffic:** 350 requests/second, recorded during last week's evening peak. (Average traffic is 200 req/s — always plan against peak, since that's the moment capacity actually gets tested.)
- **Load-test result:** a single instance sustains up to 140 req/s before p99 latency crosses the 300ms SLO and error rate starts rising. That 140 req/s is the saturation point — it came from an actual test, not from "CPU was at 60% so we're fine."
- **Headroom target:** 70% of saturation → safe operating capacity per instance = 140 × 0.7 = 98 req/s, rounded to **100 req/s** for simplicity.
- **Growth rate:** peak traffic has grown roughly 8% month over month over the last two quarters (an illustrative, measured figure for this example, not a universal benchmark).

Instances needed today: `ceil(350 / 100) = 4`. The fleet currently runs 4 instances — exactly at the target, with no slack left for further growth.

Projecting forward:

| Month | Projected peak (req/s) | Instances needed at 100 req/s each |
|---|---|---|
| 0 (now) | 350 | 4 |
| 1 | 378 | 4 |
| 2 | 408 | **5** |
| 3 | 441 | 5 |

The month-2 row is the answer to "when do we run out": somewhere between month 1 and month 2, four instances stop being enough. The action is to add the fifth instance *before* that point, not after an alert fires during it — provisioning, testing, and rolling out a new instance takes real time, and that lead time has to be subtracted from the crossing date, not added after it.

## Core Concept 4 — When a Capacity Calculation Is Done

A junior-level capacity calculation is complete when it states, explicitly:

1. **Peak demand**, with the date/window it was measured.
2. **Per-unit saturation point**, from an actual load test, not an inferred CPU or memory percentage.
3. **The headroom target used**, and why that number (not just "we picked 70%" with no reasoning — usually it's "our slowest safe rollout takes N days, so we need enough buffer to survive that long even under growth").
4. **The growth rate and its source window** — the last quarter, the last year, whatever data it came from.
5. **The date the current fleet crosses the headroom target** — the number that turns this from a spreadsheet exercise into an action item.

If any of these five is missing, the calculation isn't ready to hand to someone making a provisioning decision.

## Core Concept 5 — Using Little's Law as a Sanity Check

Little's Law is a useful second check on a capacity number, especially for anything with in-flight concurrency rather than simple stateless request handling. Take a worker pool that processes background jobs: if jobs arrive at `λ = 20 jobs/second` and each job takes an average `W = 0.5 seconds` to process, Little's Law says the average number of jobs in the system at any moment is `L = λ × W = 20 × 0.5 = 10`.

That number, 10, is the concurrency the worker pool needs to support without a growing backlog — if the pool only has 6 concurrent workers, jobs queue up faster than they drain, and the queue grows without bound even though no single job is slow. This is a different failure signature than the request-per-second saturation point from Core Concept 3: instead of individual requests slowing down, you get an ever-growing backlog that eventually exhausts memory or hits a queue-depth limit. Little's Law won't tell you the saturation point itself, but it will tell you, from just an arrival rate and an average processing time, roughly how much concurrency to provision for — a fast check before you even run a load test.

---

## Real-World Examples

- **The average-traffic trap.** A team sizes a fleet for 200 req/s because that's what the dashboard shows "most of the time," and the service falls over every evening at the 350 req/s peak — a pattern that was visible in the same dashboard's own peak column the whole time, just never used as the sizing input.
- **A stale saturation number.** A team's load test found 140 req/s per instance six months ago. Since then, a new fraud-check call was added synchronously to every checkout request. Nobody reran the load test, so the capacity plan still assumes 140 req/s per instance when the real number, under the new code path, is closer to 90 — and the fleet quietly runs with far less headroom than anyone believes it has.
- **Backlog instead of slow responses.** A background job worker pool looks fine on CPU and per-job latency graphs, but its queue depth climbs steadily over a week. Applying Little's Law reveals the pool's concurrency was sized for the old arrival rate, not the new one — the symptom is a growing queue, not a slow individual job, which is why it went unnoticed on latency dashboards alone.

## Common Mistakes

- **Sizing to average traffic instead of peak.** A fleet sized for 200 req/s average looks fine on a dashboard right up until the 350 req/s peak hits and falls over.
- **Guessing saturation from a CPU percentage.** CPU utilization is a proxy, not the thing that actually breaks. A load test that pushes real traffic until latency or errors degrade gives you a number you can trust; "CPU was at 55%" does not tell you where the real ceiling is.
- **Running with zero headroom.** Sizing exactly to today's peak means any traffic spike, or the loss of a single instance, immediately pushes you past saturation — there's no room to absorb the unexpected.
- **Treating compounding growth as if it were linear (or the reverse).** Applying an 8%-per-month rate as if it were a flat +8-req/s-per-month addition understates future demand more each month; the gap compounds just like the growth does.
- **Reusing a stale saturation number after a code or dependency change.** A new library, an added synchronous call, or a schema change can silently lower per-instance capacity. The load test needs to be rerun, not assumed permanent.

## Apply it

1. Pick one service you can measure (a real one, or the checkout example above) and record its actual peak requests/second over the last week, not the average.
2. Run — or find the results of — a load test on a single instance that pushes traffic until latency or error rate breaks the service's stated target, and record that saturation number.
3. Choose a headroom target (state a percentage and your reason for it) and compute the safe per-instance capacity.
4. Using a growth rate you can defend (even a rough one, labeled as an estimate), project peak demand for the next three months and compute instances needed each month.
5. State the exact month or date your current fleet's capacity falls below the projected peak — that's the number you'd hand to whoever provisions new instances.

## Verify your work

- Your peak number came from a real measurement window, not "roughly what it usually does."
- Your saturation number came from an actual load test result (a specific latency or error-rate threshold being crossed), not an inferred CPU percentage.
- Your headroom target is stated as a number with a stated reason, not left implicit.
- Someone reading only your final table can tell exactly which month requires action, without needing you to explain it further.

## Review questions

- Why should a capacity calculation use peak traffic instead of average traffic?
- Why is a load-test-derived saturation point more trustworthy than a CPU-utilization guess?
- What does a headroom target protect against that sizing exactly to today's peak does not?
- What happens to a capacity projection if a compounding growth rate is mistakenly treated as linear?
