# Tracing and Observability — Professional

<!-- level-focus -->
At professional level, focus on this question:

> Can you make trace quality a measured, owned property of the organization's agent infrastructure — instead of something each team implements to its own inconsistent standard?

---

## One trace standard org-wide

- Publish one required schema (attribute names, span structure, correlation ID format) every team's agent must emit, built on top of an existing open standard (OpenTelemetry GenAI conventions) rather than an internal one-off.
- A shared standard is what lets a single incident-response or cost-analysis tool work across every team's agents, instead of needing a custom adapter per team.

## Ingest and storage budget

- Set an explicit budget (cost per month, or cost as a percentage of total LLM spend) for trace ingestion and storage, and design sampling/retention policy to fit inside it rather than an unbounded "capture everything" default that silently grows into a significant cost line.

## Compliance: residency, retention, deletion

- Traces containing customer data are subject to the same data-residency and retention rules as any other customer data store — a trace pipeline that ships raw prompts to a US-based vendor by default can violate a data-residency requirement (e.g., GDPR) for EU customer data.
- Deletion requests (a customer invoking their right to be forgotten) need a defined path to purge or redact their data from traces too, not just from the primary application database — traces are often a store people forget is customer data.

## Vendor neutrality vs. lock-in

- Building directly against one vendor's proprietary trace format makes migrating away from that vendor expensive later. Building on an open standard (OTel) with a vendor as the *backend*, not the *format*, keeps that option open.
- Trade-off: a proprietary vendor's tooling may offer features (better UI, faster queries) an open-standard-only approach doesn't — evaluate the lock-in cost explicitly rather than defaulting to whichever tool is easiest to integrate first.

## Self-serve tooling

- Provide a shared library/SDK that any team can drop in to get correct instrumentation (correct span nesting, correct attribute names, redaction applied) by default, rather than every team hand-rolling their own instrumentation and inevitably diverging from the standard.
- Without self-serve tooling, "one trace standard" stays a document nobody actually follows consistently.

## Common Mistakes

- **A trace standard that exists only as a wiki page.** Without an enforced SDK or CI check, teams drift from it within a few months.
- **No ingest/storage budget.** Trace volume grows with traffic silently until someone notices the bill.
- **Treating trace data as exempt from data-residency and deletion policy.** It isn't — it's still customer data, often overlooked because it lives in an "engineering" system rather than the primary application database.
- **Betting entirely on one vendor's proprietary format.** Makes a future migration a multi-quarter rewrite instead of a backend swap.

## Apply It

1. Publish (or find and adopt) one org-wide trace schema built on an open standard, with a named owner.
2. Set an explicit ingest/storage budget for trace data and confirm current spend against it.
3. Confirm a deletion request can actually purge a customer's data from the trace store, and identify the gap if it can't yet.
4. Build or adopt a shared instrumentation SDK so new agents get the standard by default.

## Verify Your Work

- The trace schema is enforced by tooling (SDK, CI check), not just documented.
- Trace ingestion has an explicit budget and current spend is measured against it.
- A concrete deletion path exists for customer data inside traces.
- New agents onboard onto tracing via a shared SDK, not custom one-off code.

## Review Questions

- Why does a trace standard that's only documentation tend to drift within months?
- Why are traces subject to the same data-residency and deletion rules as the primary application database?
- What's the trade-off between a vendor-proprietary trace format and one built on an open standard?
