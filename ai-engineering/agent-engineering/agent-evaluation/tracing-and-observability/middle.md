# Tracing and Observability — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Can you instrument a multi-step agent so a teammate can read the run tree and understand what happened, without you walking them through it?

---

## Parent/child spans

- A multi-step agent's spans nest: a top-level "agent run" span is the parent; each model call, tool call, or sub-agent invocation is a child span. A sub-agent invoked from within a step gets its own nested children.
- This nesting is what lets a viewer collapse/expand a run tree instead of reading a flat list and reconstructing order and nesting manually.

## Naming conventions and semantic conventions

- Use consistent attribute names across every span of the same kind (`tool.name`, `tool.arguments`, `llm.model`, `llm.input_tokens`) — a mix of `toolName` in one place and `tool_name` in another breaks any tooling built to query across spans.
- OpenTelemetry's GenAI semantic conventions define a standard attribute set for LLM and agent spans — adopting them means existing OTel-compatible viewers and alerting can work on your traces without custom parsing.

## Sampling: head vs. tail

- **Head sampling**: decide whether to record a trace at the start of the run (e.g., record 10% of all runs at random). Cheap, but you might not capture the run that later turns out to matter.
- **Tail sampling**: decide after the run completes, based on what happened (e.g., always keep traces that errored or exceeded a latency threshold, sample the rest). Costs more to hold the data until the decision, but guarantees you keep the runs you actually need to debug.
- Default to tail sampling anchored on failure/high-latency/high-cost — those are exactly the runs you'll want to inspect later.

## PII redaction and retention

- Traces often contain customer PII (names, order details, payment info) inside prompts and tool results. Redact or tokenize known PII fields before storage, and set an explicit retention window — don't keep full-fidelity traces indefinitely by default.
- Redaction needs to happen consistently at ingestion, not as an afterthought applied inconsistently by whoever queries the data later.

## Attaching feedback and eval scores back onto spans

- When an eval run or a human reviewer scores a specific run, write that score back onto the trace (as an attribute on the top-level span), so you can later query "show me every trace scored below 3" directly instead of cross-referencing two separate systems.
- Same for user feedback (thumbs up/down) — attach it to the trace it applies to at ingestion time, not in a separate table with no link back.

## Instrumenting retries visibly

- A retried step should appear in the trace as a retry (e.g., an attempt-number attribute on the span, or explicit "attempt 1 failed, attempt 2 succeeded" child spans) — not as if the second attempt were the only attempt that happened, which hides that the step was flaky at all.

## Common Mistakes

- **Inconsistent attribute naming across span kinds.** Breaks any query or dashboard that expects one consistent schema.
- **Head-sampling only, with no override for failures.** The 1% of runs you sampled almost never includes the specific failing run you need to debug.
- **No PII redaction before storage.** Creates a compliance liability and often violates data-handling policy the moment traces include real customer data.
- **Retries invisible in the trace.** Makes a flaky step look successful on the first try, hiding a reliability problem from anyone reading the trace later.

## Apply It

1. Instrument one multi-step agent with parent/child spans using one consistent attribute naming scheme.
2. Set a tail-sampling rule: always keep traces with an error or latency above a stated threshold.
3. Add PII redaction for at least the fields you know are sensitive, and set an explicit retention window.
4. Confirm a retried step shows up distinctly in the trace, not silently merged into one span.

## Verify Your Work

- Span attribute names are consistent across every span of the same kind.
- Failed or slow runs are guaranteed to be kept regardless of the sampling rate applied to normal runs.
- No known PII field reaches storage unredacted.
- A retried step is visibly distinguishable from a first-attempt success in the trace.

## Review Questions

- Why does tail sampling anchored on failure catch more useful traces than random head sampling?
- What breaks when two span kinds use inconsistent attribute names?
- Why does hiding a retry inside one span hide a real reliability signal?
