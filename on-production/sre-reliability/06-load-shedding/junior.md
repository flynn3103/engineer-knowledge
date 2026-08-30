# Load Shedding — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Can you reject nonessential work at a clear boundary so a service preserves its most important user requests under overload?

---

## The idea

Load shedding deliberately refuses some work when accepting it would make the whole system fail. A queue, worker pool, database, or dependency has finite capacity. Without a limit, rising latency causes timeouts and retries, which add more load and can collapse the service.

## Pick a boundary and priority

For a storefront, checkout and account login are critical; recommendations and analytics refreshes can be degraded. Shed early at an API gateway or admission queue, where the service can return a fast, explicit response such as `429 Too Many Requests` or a cached result.

| Request class | Policy under overload |
|---|---|
| Checkout | Reserve capacity; reject only as last resort |
| Product search | Limit per client; return cached results |
| Recommendations | Disable or use stale data |
| Batch analytics | Pause |

## Method

1. Define the protected journey and an overload signal such as queue depth.
2. Classify requests using a bounded, trusted attribute.
3. Set a threshold and a deterministic response.
4. Test the decision with synthetic load before an incident.
5. Monitor accepted, rejected, and successful request rates separately.

## Common mistakes

- Letting every client retry immediately after a rejection.
- Shedding at a downstream database after expensive work is already done.
- Using untrusted client-provided priority headers.
- Hiding overload with long waits rather than a clear response.

## Apply it

1. Classify four requests for a service by priority.
2. Choose one overload signal and a threshold.
3. Draft the response and retry guidance for shed requests.

## Verify your work

- Critical traffic remains successful during a controlled overload test.
- Rejections are measured by request class.
- Clients receive a bounded, documented retry behavior.

## Review questions

- Why can accepting every request make availability worse?
- Where is the best point to shed load and why?
- What must clients do differently after a shed response?
