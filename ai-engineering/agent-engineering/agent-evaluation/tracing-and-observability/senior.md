# Tracing and Observability — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Can you design your trace schema and sampling as a budgeted interface — capturing what's needed to debug and monitor without the storage and processing cost of recording everything at full fidelity forever?

---

## Trace schema as a versioned interface

- Treat span attribute names as a public interface other tools (dashboards, alerts, downstream analysis) depend on. Changing `tool.arguments` to `tool.args` silently breaks every query written against the old name.
- Version the schema explicitly when a breaking change is needed, and keep both versions queryable during a migration window rather than a hard cutover that breaks existing dashboards overnight.

## Cardinality control

- A span attribute with unbounded cardinality (e.g., raw user free-text as an indexed field) can blow up the cost and query performance of the trace store. Index on bounded fields (`tool.name`, `error.type`, `model.name`); keep unbounded content (raw prompt text) as an unindexed payload field you can still read but not filter/group by cheaply.

## Cost of full-fidelity capture

- Recording every token of every prompt/response for every run at 100% sampling has a real storage and ingestion cost that scales with traffic. At fleet volume this can rival or exceed the cost of the LLM calls themselves.
- Balance: full fidelity on a tail-sampled subset (errors, high latency, high cost, random baseline sample) instead of full fidelity on 100% of traffic — see [Middle](middle.md) for the sampling mechanics.

## Production monitors built from traces

- **Tool-error rate**: percentage of tool-call spans that returned an error, tracked over time — a sudden jump indicates a dependency degrading before customers necessarily notice.
- **Refusal rate**: percentage of runs where the model declined to help — a spike can indicate a prompt regression or an upstream policy change affecting behavior unexpectedly.
- **Loop-length drift**: average step count per run trending upward over time can indicate the agent is increasingly failing to converge, even if final outcomes still look fine in aggregate.
- Alert on the trend (week-over-week change), not just an absolute threshold, since normal traffic mix shifts can move absolute numbers without anything being wrong.

## Joining traces to business outcomes

- A trace alone tells you what the agent did; joining it to a downstream business signal (did the customer re-contact support about the same order within 24 hours, was the refund reversed by a human) tells you whether what it did actually worked.
- This join requires a stable identifier (order ID, ticket ID) captured on the trace at the time of the run, not reconstructed after the fact from separate systems that may not correlate cleanly.

## Common Mistakes

- **Renaming a span attribute without versioning.** Silently breaks every existing dashboard and alert built against the old name.
- **Indexing high-cardinality raw text fields.** Drives up trace-store cost and query latency without adding filtering value.
- **Alerting on absolute thresholds instead of trend.** Either never fires (threshold too loose for current volume) or fires constantly on normal variance (too tight).
- **No business-outcome join.** You can report what the agent did in exhaustive detail while having no idea whether it actually resolved anything.

## Apply It

1. Document your current span schema as a versioned contract; identify any attribute that's changed silently without a version bump.
2. Identify at least one high-cardinality field currently indexed, and move it to an unindexed payload field.
3. Define one production monitor (tool-error rate, refusal rate, or loop-length drift) with a trend-based alert, not an absolute threshold.
4. Identify the stable ID needed to join a trace to a business outcome, and confirm it's captured on every trace today.

## Verify Your Work

- Span schema changes are versioned, with old and new versions both queryable during migration.
- No unbounded-cardinality field is used as an indexed/groupable attribute.
- At least one production monitor alerts on trend, not a static absolute number.
- Every trace captures the stable ID needed to join it to a downstream business outcome.

## Review Questions

- Why does renaming a span attribute without versioning break more than just one dashboard?
- Why does indexing a high-cardinality field cost more than it's worth for most queries?
- Why is alerting on trend more robust than alerting on a fixed absolute threshold?
