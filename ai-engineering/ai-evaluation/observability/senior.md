# Observability — Senior

<!-- level-focus -->
At senior level, focus on this question:

> A team's support-bot agent starts giving noticeably worse answers starting on a specific day. Using trace evidence alone — not guessing, not re-running the model by hand — how do you find the root cause, and what must a tracing setup guarantee before this kind of diagnosis is even possible?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Anchor Diagnosis to Invariants, Not to a Working Trace View

A middle-level pass gets a trace tree that renders correctly for a healthy run. At senior level, the organizing question changes: **can you trust that every request has a trace, and that trace's fields are complete, right now, for the incident you're investigating** — not "does the tracing dashboard generally work." A trace view that looks fine in a demo is not the same guarantee as a trace view that has never silently dropped a request.

Four invariants a tracing setup must guarantee before trace-based diagnosis is reliable:

| Invariant | What it rules out |
|---|---|
| Every request produces a trace, including ones that error or time out | The incident's causal request is exactly the one missing from the trace store, because tracing was wired only into the success path |
| Trace IDs correlate across every service boundary the request crosses | A gateway, an agent service, and a model-provider proxy each log independently, and nothing ties their records to the same request |
| Cost and token fields are populated on every call, not silently dropped | A provider response that omits usage data (common on some streaming responses) leaves a cost gap that looks like free calls rather than missing data |
| Trace content reflects what was actually sent and received, not a stale or default value | A prompt-template caching bug logs the *intended* template rather than what was actually interpolated and sent |

An invariant-respecting tracing setup has a mechanism enforcing each of these — an alert when trace volume diverges from request volume, a check that usage fields are non-null, a correlation ID that's mandatory at the API gateway — not just a description of best practice.

## Core Concept 2 — Invariant 1: Trace Completeness on the Error Path

The most common gap: tracing is added around the "happy path" model call, and the error-handling branch — a timeout, a retry, an exception — exits before the span closes and gets recorded. This is exactly backwards: the request that errored is disproportionately likely to be the one you need evidence about later.

```python
# Wrong: a span is only recorded on the success path.
@observe()
def call_model(prompt: str):
    response = client.chat.completions.create(...)   # if this raises, no span is ever flushed
    return response

# Right: the span records the outcome either way.
@observe()
def call_model(prompt: str):
    try:
        response = client.chat.completions.create(...)
        return response
    except Exception as e:
        langfuse_context.update_current_observation(level="ERROR", status_message=str(e))
        raise
```

Verify this invariant directly: compare request-volume metrics (from standard APM) against trace-volume metrics for the same window. A gap between the two — more requests than traces — means some fraction of requests, likely concentrated on the error path, are producing no evidence at all.

## Core Concept 3 — Invariant 2: Cross-Boundary Correlation

An agent request commonly crosses an API gateway, an agent orchestration service, and a proxy in front of the model provider. If each layer generates its own trace ID instead of propagating one, "find everything related to this request" becomes impossible — you have three disconnected fragments instead of one trace. The fix is the same one distributed tracing already solved for ordinary microservices: a trace ID generated at the edge (or accepted from an upstream caller) is propagated via a header (commonly `traceparent`, the W3C Trace Context standard used by OpenTelemetry) through every downstream call, and every span at every layer is tagged with it.

The senior-level check isn't "do we have a trace ID" — it's "does the same trace ID actually appear in the gateway's logs, the agent service's spans, and the model-provider proxy's records for the same request, all three, every time." A missing propagation hop anywhere in that chain breaks correlation silently — nothing errors, the trace just doesn't connect.

## Core Concept 4 — Invariant 3: Cost and Token Fields Are Never Silently Dropped

Streaming responses are a specific, common way this invariant breaks: some provider APIs only return final usage/token counts in the last chunk of a streamed response, or in a separate follow-up call, and an instrumentation layer written against the non-streaming response shape simply never captures it. The trace records latency and content correctly, and `cost_usd` sits at zero or null — which, read carelessly, looks like a free call rather than an instrumentation gap. Verify by spot-checking: pick ten recent traces for a streaming endpoint and confirm none show a null or zero cost with a non-trivial completion — a batch of legitimate zero-cost traces is a red flag, not a lucky quarter.

## Core Concept 5 — Cross-Component Scenario: The Quality Regression

The support-bot agent's answers get noticeably worse starting at a specific time. Four plausible hypotheses, and what trace evidence would actually confirm or rule out each — rather than reasoning about it in the abstract:

| Hypothesis | Evidence that confirms it | Evidence that rules it out |
|---|---|---|
| **A prompt template changed in the last deploy** | Traces show `prompt.template_version` (or the literal prompt text) changed exactly at the deploy timestamp; the regression's start time matches the deploy to the minute | `template_version` and prompt text are identical in traces from before and after the regression started |
| **The provider silently changed the model behind a floating alias** (e.g., `gpt-4o` resolving to a newer snapshot) | The response's model-version/fingerprint field differs between traces before and after the regression window, while the app's own prompt/template version and deploy history show no relevant change in that window | The fingerprint field is identical across every trace spanning the regression window |
| **Retrieved context degraded** (a RAG knowledge-base ingestion issue) | Traces show the retrieval-tool span's returned documents changed in content, length, or count starting at the regression time, unrelated to any app deploy | Retrieved-context spans are comparable in content and count before and after |
| **Refusal rate increased from a safety-filter change** | Traces flagged with `finish_reason=content_filter` (or matching refusal-text patterns) spike exactly at the regression start | Filter-flagged traces are flat across the whole window |

The evidence-gathering step matters more than guessing: pulling ten traces from immediately before the regression and ten from immediately after, and diffing `prompt.template_version`, the model's fingerprint field, and the retrieved-context span's content, either confirms one hypothesis or rules out several at once — usually before anyone needs to reproduce the bug by hand. This is also the mechanism for the harder question, **is this a model-provider-side regression or an app-side one**: if the model's fingerprint changed and nothing in the app's own deployable artifacts changed in that window, the regression originates upstream of your code, and the fix is pinning to an explicit model version rather than a floating alias — not touching the prompt at all.

## Core Concept 6 — Questions That Expose Weak Assumptions

Before trusting that a tracing setup can actually support this kind of diagnosis, ask:

- "If I compare trace-volume to request-volume for the last hour, do they match — including the error path?" Most teams have only verified this for the success path.
- "Do the same trace ID actually connect across our gateway, agent service, and model-provider proxy logs, or do we only have three separately-tagged fragments?" Surfaces a propagation gap nobody noticed because nothing errors when it's missing.
- "Can I pull ten traces from a streaming endpoint right now and confirm none show a null cost with a non-trivial completion?" An honest check, not an assumption that the same instrumentation logic that works for non-streaming responses also covers streaming ones.
- "If the model provider silently updated the model behind our pinned alias tomorrow, would a trace field tell us, or would we only find out from a user complaint?" Surfaces whether the fingerprint/version field is actually being captured and compared, not just present in the schema.
- "For the last quality regression we diagnosed, did we use trace evidence, or did we end up guessing and testing fixes until one worked?" An honest "we guessed" means the invariants in Core Concept 1 weren't actually being relied on yet.

## Core Concept 7 — Recovery and Evolution

A tracing setup that satisfies these invariants today can silently regress: a new service added to the request path that doesn't propagate the trace ID, a provider API change that moves usage data to a different field, a new failure mode discovered only after an incident where the trace was incomplete. Treat each of these — a correlation gap found during an investigation, a null-cost batch discovered during a spot-check — as a signal the invariant was never actually enforced, not as an unlucky one-off, and add the mechanism (an alert, a schema check) that would catch the next instance automatically rather than relying on the next engineer to notice by hand.

---

## Real-World Examples

- **A fingerprint diff ends a "which team broke this" argument.** A quality regression is initially blamed on a recent prompt change; comparing the model's version/fingerprint field across traces before and after shows it changed at the same moment, with no corresponding app deploy — the provider had rolled out a new model snapshot behind the pinned alias, and the fix was pinning to an explicit dated model version instead of reverting a prompt change that was never the cause.
- **A trace/request volume gap surfaces a silent tracing hole.** A team assumes their tracing coverage is complete because the dashboard "looks full"; comparing trace count to request count for the same hour shows a 6% gap, entirely concentrated in timeout errors — the error-handling branch never flushed a span, exactly the pattern in Core Concept 2.
- **A null-cost batch turns out to be a real instrumentation gap, not a lucky day.** A cost dashboard shows a cluster of zero-cost traces on a streaming endpoint; spot-checking confirms the completions are real and non-trivial — the usage data was arriving in the final stream chunk, which the instrumentation wasn't reading.

## Common Mistakes

- **Trusting that a tracing dashboard "looks complete" without comparing trace volume to request volume.** A dashboard that renders fine for the traces it has says nothing about the traces it's missing.
- **Diagnosing a quality regression by re-running the prompt by hand instead of diffing trace evidence.** Manual reproduction can fail to reproduce a provider-side change at all, and wastes time a trace diff would have resolved in minutes.
- **Assuming a pinned model alias can't silently change.** A floating alias (`gpt-4o` rather than a dated snapshot) is, by definition, not pinned — treat the fingerprint/version field in the trace as the actual source of truth, not the string in your own configuration.
- **Treating a null or zero cost field as "a free call" instead of investigating it as a possible instrumentation gap.** Especially common on streaming responses where usage data arrives in a different place than the instrumentation expects.
- **Never testing cross-boundary correlation directly.** Assuming trace IDs propagate correctly across every service in the request path without ever confirming the same ID appears in all of them for one real request.

---

## Apply it

1. For a traced service you run (or the agent from `middle.md`), compare trace volume to request volume for the same time window, using your APM tool's request count and your tracing tool's trace count. Note any gap and which paths (success, error, timeout) it concentrates in.
2. Pick one real request and confirm its trace ID appears, unbroken, in every service layer it passes through — not just the layer closest to the model call.
3. If the service uses streaming responses, pull ten recent traces and confirm every one has a non-null, non-zero cost for a non-trivial completion.
4. Using the hypothesis table in Core Concept 5 as a template, pick a real or simulated quality regression and identify which trace fields you would diff to confirm or rule out each hypothesis, before writing any code to investigate further.
5. Run the five weak-assumption questions from Core Concept 6 against your own tracing setup and write down which one exposed the shakiest assumption.

## Verify your work

- You have a concrete number (not an impression) for how closely trace volume matches request volume, including the error path.
- You have confirmed, for at least one real request, that the same trace ID connects every service layer it crossed.
- You can state definitively whether your streaming endpoints ever produce null-cost traces with real completions, based on an actual spot-check.
- You can name, for a real or simulated quality regression, which specific trace field distinguishes a provider-side cause from an app-side one.
- At least one weak-assumption question surfaced a real, previously unverified gap in your own tracing setup, not a hypothetical one.

## Review questions

- Why is comparing trace volume to request volume a stronger check than confirming the tracing dashboard "looks complete"?
- What specifically breaks if a trace ID isn't propagated across every service boundary a request crosses, and why does nothing visibly error when this happens?
- What trace evidence distinguishes a provider-side model regression from an app-side prompt regression, and why is diffing that evidence more reliable than manually reproducing the issue?
- Why can a null or zero cost field on a streaming response be a bug rather than a genuinely free call, and how would you tell the difference?

---

*Continue to [`professional.md`](professional.md). The regression this level diagnoses from traces is exactly the kind a golden-set regression suite should catch before it ships — see [Testing](../testing/README.md) — and the quality signal you're tracing here is what [Evaluation — Senior](../evaluation/senior.md) measures systematically over time rather than one incident at a time. Part of [Observability](README.md) → [AI Evaluation](../README.md).*
