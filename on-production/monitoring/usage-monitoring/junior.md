# Usage Monitoring — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Given a few days of raw request logs for one API endpoint, can you correctly count how many distinct customers actually used it — separating real usage from bot traffic and health checks — and use that count to answer a simple "is this feature still used?" question?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Usage Monitoring Answers a Different Question Than Health or Performance

Health monitoring asks "is the system up?" Performance monitoring asks "is it fast?" **Usage monitoring asks "who is actually using this, and how much?"** It's a completely different signal, and it stays true even while the system is perfectly healthy and fast — a feature can pass every health check and every latency budget while almost nobody calls it.

The vocabulary you need at this level:

- **Active user / active actor** — a distinct identity (a logged-in user, an API key, a customer account) that performed a meaningful action inside a time window.
- **DAU / WAU / MAU** — daily / weekly / monthly active actors: the count of distinct actors active within that window.
- **Feature adoption** — the fraction of actors *eligible* to use a feature who actually used it at least once in a window.
- **Request volume** — the raw count of calls. Useful for capacity planning, but **not the same thing as usage** — one actor retrying five times produces five requests and one active actor.

## Core Concept 2 — Define the Actor Before You Write Any Query

Before counting anything, decide what counts as "one user." For a consumer app, that might be a logged-in account. For a B2B API, it's usually the **API key** or **customer/tenant ID**, not the IP address — many employees at one customer share an office network, and a single customer can call from many IPs. Picking the wrong actor unit gives you a number that looks precise and means nothing.

## Core Concept 3 — Not Every Request Is "Usage"

Raw logs are noisy. Before you count distinct actors, filter out traffic that isn't real usage:

- **Health checks and uptime probes** — automated pings that hit an endpoint on a fixed schedule regardless of any human intent.
- **Bots and scrapers** — identifiable by user agent (`Googlebot`, `bingbot`, generic scraping libraries).
- **Retries** — a client that gets a `500` and retries twice produces three requests from one real attempt.
- **Internal service-to-service calls** — unless internal callers are the population you actually care about, they'll inflate a customer-facing usage number.

## Core Concept 4 — A Repeatable Method

1. **Define the actor unit** — user, API key, or tenant.
2. **Define the meaningful action** — which endpoint(s) or events count as "using" the thing you're measuring.
3. **Define the window** — a single day, a rolling 7 days, a rolling 30 days.
4. **Filter out known-noise traffic** — bots, health checks, internal callers, unless explicitly in scope.
5. **Count distinct actors**, never raw requests, as the headline number.
6. **Compare against a threshold or a trend** to answer the actual question you were asked — "is this still used," "did adoption grow," "is this endpoint safe to remove."

## Core Concept 5 — Worked Example: Is `/v1/reports/export` Still Used?

A three-day raw log slice for one endpoint:

```text
day 1
09:01:03  key_A1     /v1/reports/export  200  AcmeClient/2.1
09:01:05  key_A1     /v1/reports/export  500  AcmeClient/2.1
09:01:06  key_A1     /v1/reports/export  200  AcmeClient/2.1   (retry after the 500)
09:15:00  key_B2     /v1/reports/export  200  AcmeClient/1.0
03:00:00  internal   /v1/reports/export  200  healthcheck-probe/1.0
03:00:30  internal   /v1/reports/export  200  healthcheck-probe/1.0
14:22:10  key_C3     /v1/reports/export  200  Mozilla/5.0 (compatible; Googlebot/2.1)

day 2
10:00:00  key_A1     /v1/reports/export  200  AcmeClient/2.1
03:00:00  internal   /v1/reports/export  200  healthcheck-probe/1.0
03:00:30  internal   /v1/reports/export  200  healthcheck-probe/1.0
16:40:00  key_D4     /v1/reports/export  200  AcmeClient/2.0

day 3
03:00:00  internal   /v1/reports/export  200  healthcheck-probe/1.0
03:00:30  internal   /v1/reports/export  200  healthcheck-probe/1.0
11:05:00  key_A1     /v1/reports/export  200  AcmeClient/2.1
```

That's 14 raw log lines. A beginner's mistake is to report "14 requests, this endpoint is busy." Walk it through the method instead:

| Step | Result |
|---|---|
| Actor unit | `api_key` |
| Meaningful action | any `2xx` response on `/v1/reports/export` |
| Window | per day, over 3 days |
| Noise to remove | `internal` (health checks), `key_C3` (Googlebot user agent) |
| Distinct real actors remaining | `key_A1`, `key_B2`, `key_D4` |

The query that produces this, run against a table of raw log rows:

```sql
SELECT
  DATE(ts) AS day,
  COUNT(DISTINCT api_key) AS active_customers
FROM request_logs
WHERE endpoint = '/v1/reports/export'
  AND status < 400
  AND api_key <> 'internal'
  AND user_agent NOT ILIKE '%bot%'
  AND user_agent NOT ILIKE '%healthcheck%'
GROUP BY DATE(ts)
ORDER BY day;
```

| day | active_customers |
|---|---|
| day 1 | 2 (`key_A1`, `key_B2`) |
| day 2 | 2 (`key_A1`, `key_D4`) |
| day 3 | 1 (`key_A1`) |

Three distinct real customers used the endpoint across the three days, one of them (`key_A1`) every single day. The retry on day 1 didn't add a phantom second user. The bot and the two daily health-check pings never appear in the count. If a team's deprecation rule of thumb were "no distinct customer calls in 30 consecutive days," this endpoint is clearly still in active use and is not a deprecation candidate — the raw "14 requests" number would never have told you that on its own.

## Core Concept 6 — Turning a Usage Count Into a Deprecation Threshold

A raw daily count answers "how many customers called this today." A deprecation decision needs a rolling view over a longer window, compared against a simple, explicit threshold agreed on before you run the query — not chosen after looking at the number, which invites picking whichever threshold happens to support the answer you already wanted.

```sql
-- Rolling 30-day distinct-customer count, evaluated as of any given day.
SELECT
  COUNT(DISTINCT api_key) AS distinct_customers_last_30_days
FROM request_logs
WHERE endpoint = '/v1/reports/export'
  AND status < 400
  AND api_key <> 'internal'
  AND user_agent NOT ILIKE '%bot%'
  AND user_agent NOT ILIKE '%healthcheck%'
  AND ts >= CURRENT_DATE - INTERVAL '30 days';
```

A simple beginner-level rule of thumb: agree on a threshold such as "fewer than one distinct real customer in the trailing 30 days" *before* running the query, write that threshold down alongside the actor unit and filters from Core Concept 4, and only then check the number against it. In the worked example, the rolling 30-day count would return at least 3 (`key_A1`, `key_B2`, `key_D4`), clearly above any "effectively zero" threshold — so the endpoint fails the deprecation test and stays.

## Success Criteria

A junior-level usage check is done correctly when all of the following hold:

- The actor unit, window, and exclusion filters were written down *before* the query ran, not adjusted afterward to match an expected answer.
- The query's distinct-actor count for each day matches a manual, line-by-line recount of the raw log.
- No health-check or bot-identified row contributes to the final count.
- A single retried request contributes exactly one active actor, not one per attempt.
- The resulting number is compared against an explicit, pre-agreed threshold to answer the actual question asked ("still used," "safe to deprecate," "adopted"), rather than left as a number with no decision attached.

## Common Mistakes

1. **Counting requests instead of distinct actors.** A single customer retrying a failed call three times is not three users.
2. **Not filtering health checks and bots.** Synthetic traffic looks identical to real usage in a raw log unless you explicitly exclude it by identity or user agent.
3. **Confusing "enabled" with "used."** A feature flag being turned on for a customer says nothing about whether that customer ever called the feature.
4. **Using IP address as the actor unit for a B2B API.** Office NAT and shared VPNs make one customer look like many, or many customers look like one.
5. **Picking a window too short for the traffic pattern.** A single day of "no calls" for a feature that customers use monthly does not mean the feature is unused.
6. **Not writing the actor + window + filter definition down before running the query.** Different people re-deriving "the same" metric with different unstated assumptions will get different numbers and argue about which one is right.

## Apply it

1. Take (or construct) a raw request log for one endpoint spanning at least three days, including at least one retry, one health-check-style caller, and one bot-like user agent.
2. Write down, explicitly, your actor unit, the meaningful action, and the window before running any query.
3. Write a query (or a short script) that counts distinct actors per day after filtering out the noise you identified.
4. Manually recount the distinct real actors by reading the raw log line by line, and confirm your query's output matches your manual count exactly.
5. Using your daily counts, answer a single concrete question: "would this endpoint be a safe candidate for deprecation under a rule of 'no real customer calls in the last 30 days'?"

## Verify your work

- Your query's distinct-actor count for each day matches a manual line-by-line recount of the raw log.
- The health-check caller and the bot-like user agent do not appear anywhere in your final counted numbers.
- The retried request contributes exactly one active actor for that day, not two or three.
- You can state, in one sentence, why your chosen actor unit (not IP, not raw request) is the right one for this scenario.

## Review questions

- Why is counting distinct active actors different from counting raw requests, and why does that difference matter for a deprecation decision?
- What kinds of traffic should usually be excluded before you count "usage," and why do they look like real usage in a raw log?
- Why does the choice of actor unit (user, API key, IP address) change the answer to "how many customers used this feature"?
- What is wrong with concluding a feature is unused from a single day with zero calls?
