# Observability — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run LLM observability as a durable, org-wide operating model — a shared tracing schema, dashboards, on-call runbooks for AI-specific incidents, and cost attribution across teams — so every team's traces are comparable instead of each team inventing its own field names?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Ownership Aligned to Cognitive Load

The predictable failure mode: a central observability team tries to personally instrument, or review the instrumentation of, every team's agent, and becomes a bottleneck the moment more than a handful of teams are shipping LLM features. The split that scales distributes ownership by who has the context to sustain each decision:

| Layer | Owner | Responsibility |
|---|---|---|
| **Shared tracing schema/library** | Platform/observability team | Define and version the common span names and attributes (built on the OpenTelemetry GenAI semantic conventions, not reinvented from scratch) so every team's spans are comparable |
| **Application instrumentation** | The team that owns the service | Instrument their own agent/LLM calls using the shared schema — they know their own tool calls and reasoning steps, the platform team does not |
| **Alerting policy and thresholds** | Platform/observability team, in consultation with each service owner | Define what counts as a refusal-rate spike, a cost spike, or a latency shift worth paging on, and keep thresholds current as traffic patterns change |
| **PII redaction policy and access control** | Security/privacy engineering, enforced in the shared schema/library | Decide what must never be stored raw, own the redaction mechanism, and audit who can read raw trace content |
| **On-call runbooks and incident response** | The team on-call for the affected service, using platform-provided runbook templates | Diagnose and resolve using the shared tooling; the platform team owns the *template*, not every incident |

This keeps each layer within what its owner can sustain: no product team is asked to independently design a redaction policy or a semantic convention, and no central team is asked to understand every service's specific agent logic.

## Core Concept 2 — A Shared Schema, Not a Reinvented One

A shared tracing schema exists so a cross-team dashboard ("median cost per request, by team") is a query, not a data-cleaning project. Building it from scratch is unnecessary: the [OpenTelemetry GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) already define vendor-neutral attribute names — `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.response.finish_reasons` — that several real tools (LangSmith, Langfuse, Arize Phoenix) already speak or map onto. The org-internal work is a thin layer on top: adding organization-specific attributes the public convention doesn't cover, and publishing it as an internal library every team imports rather than a document every team is expected to remember.

```python
# A thin internal wrapper, not a reinvented schema:
from acme_observability import traced_llm_call

@traced_llm_call(team="support-eng", service="support-bot")
def compose_answer(prompt: str) -> str:
    ...
    # the wrapper sets gen_ai.* attributes automatically, plus
    # org-specific ones: team, service, environment, cost_center
```

The paved-road principle from infrastructure standardization applies directly here: the shared library has to be *easier* than instrumenting by hand, or teams route around it, and the "shared" schema quietly forks into as many variants as there are teams.

## Core Concept 3 — Decomposing the Rollout

Mandating "every team adopts the shared schema by end of quarter" produces rushed, unverified adoption. Decompose it instead:

1. **Pilot with one team, on one service** — ideally one already struggling with an unattributed cost or an unexplained quality issue, so the motivation is concrete.
2. **Extract the schema's org-specific attributes from what the pilot actually needed**, rather than designing them by committee beforehand.
3. **Wire alerting as advisory (visible, non-paging) first**, so thresholds can be tuned against real traffic before anyone gets paged on a false positive.
4. **Turn alerting into paging incrementally**, service by service, once each team confirms its thresholds are sane for its own traffic pattern.
5. **Expand team by team**, reusing the same library and schema, and track adoption as a fraction (services instrumented with the shared schema / total LLM-calling services), not a binary migrated-or-not.

Each step stays reversible: a schema attribute that needs to change after the third team adopts it is a version bump to the shared library, not a program failure.

## Core Concept 4 — Dashboards and On-Call Runbooks for AI-Specific Incidents

Standard on-call runbooks (service down, latency SLO breach) don't cover the incident types specific to LLM systems. Three that need their own runbook, because "check the traces" alone isn't a procedure:

- **Refusal-rate spike.** A jump in `finish_reason=content_filter` or refusal-pattern completions. Runbook: pull recent flagged traces, check whether they cluster around a specific input pattern (a prompt-injection attempt, a topic the model now refuses more often after a provider update) or a specific deploy (a system-prompt change that made the model more conservative); escalate to the owning team with the trace sample, not just the aggregate rate.
- **Cost spike.** A jump in `cost_usd` aggregated over a short window. Runbook: check whether it's concentrated in call *volume* (a retry loop firing repeatedly on the same request, or a scheduled job misfiring) or call *shape* (a prompt-injection or adversarial input causing an unexpectedly long tool-call chain, ballooning token counts per request); the fix differs completely depending on which — a volume spike needs a circuit breaker on retries, a shape spike needs an input or tool-call-count guard.
- **Latency percentile shift.** A jump in p95/p99 latency tied to a specific model version or prompt change. Runbook: diff the trace's `model` and prompt-template-version fields between the shifted window and the prior baseline — a shift tied to a specific model string points at the provider; a shift tied to a specific template version points at the app's own last deploy.

Each runbook's first step is the same pattern from `senior.md`: pull trace evidence and diff it against a known-good baseline, rather than reasoning from the aggregate metric alone.

## Core Concept 5 — What to Log, and What Never to Log

The volume/sampling trade-off from `middle.md` has a second, non-negotiable dimension: content sensitivity. A support-bot transcript can contain a customer's address, a partial card number, or an account PIN typed directly into the prompt — and once that's stored raw in a trace store, it inherits whatever access control and retention policy the trace store has, which is usually looser than the systems that were designed to hold PII in the first place.

| Do | Don't |
|---|---|
| Redact known PII patterns (card numbers, SSNs, email addresses) before the span is written, using a redaction step in the shared instrumentation library | Store raw completions containing customer PII with the same access control as aggregate cost/latency metrics |
| Set a shorter retention window for raw prompt/completion content (for example, 30 days) than for aggregated metrics (which can reasonably live for a year or more) | Retain full raw completions indefinitely by default because nobody set a retention policy |
| Field-level access control: engineers debugging latency don't need read access to raw prompt text; an incident responder investigating a specific reported issue does, with an audit trail | Give every engineer with dashboard access blanket read access to every raw completion in the trace store |
| Sample raw-content capture at a rate that scales with traffic, keeping structured metadata (tokens, cost, latency, `finish_reason`) at 100% always | Choose between "log everything forever" and "log nothing" as if those were the only two options |

The redaction step belongs in the shared instrumentation library from Core Concept 2, not as a policy document teams are expected to remember to apply — the same paved-road logic: the safe choice has to be the default, automatic one.

## Core Concept 6 — Cost Attribution Across Teams

Once a shared model budget is spread across many teams, `team` and `service` tags on every span (from Core Concept 2's wrapper) turn an aggregate bill into a breakdown:

```sql
SELECT team, service, SUM(cost_usd) AS monthly_cost
FROM traces
WHERE timestamp >= '2026-08-01'
GROUP BY team, service
ORDER BY monthly_cost DESC;
```

This only works if every team's spans are actually tagged — a team that skips the `team`/`service` attributes (or instruments outside the shared library) becomes invisible in the breakdown, and its cost gets misattributed to "unknown" or silently absorbed into whichever team's dashboard happens to query broadly. Enforcing the tag at the schema/library level (a required field, not an optional convention) is what makes attribution reliable enough to actually back a budget conversation between teams.

## Core Concept 7 — Outcome Measures and Exit Conditions

```yaml
# Program health dashboard, reviewed quarterly.
metrics:
  trace_completeness: "production LLM calls with a complete trace / total production LLM calls"
  schema_adoption: "services instrumented with the shared schema / total LLM-calling services"
  cost_attribution_coverage: "cost_usd tagged with team+service / total cost_usd across the org"
  cost_spike_ttr: "median time from a cost-spike alert firing to root cause identified"
  refusal_spike_ttr: "median time from a refusal-rate alert firing to root cause identified"
exit_conditions:
  pilot_to_expansion: "pilot service reaches >99% trace_completeness, alerting is tuned to a false-positive rate the on-call team accepts, and the platform team can evolve the schema without the pilot team's direct involvement"
  program_maturity: "schema_adoption > 80% of active LLM-calling services, and cost_spike_ttr trending down for two consecutive quarters"
```

`trace_completeness` and the two time-to-root-cause measures matter more than adoption alone: an org can have high schema adoption on paper while an incident still takes hours to diagnose, if alerting thresholds are miscalibrated or runbooks are unused. Adoption is a leading indicator that the paved road exists; time-to-root-cause is the outcome measure that proves it actually pays off during a real incident.

## Core Concept 8 — Cross-Team Contracts and Governance

Once many teams build on a shared schema, it needs the same discipline as an internal API:

- Every schema version publishes a **support window**: which version is current, which are deprecated but still accepted, and the date a version stops being accepted by the ingestion pipeline.
- A **breaking change to the schema** — renaming an attribute, changing a field's type, removing one a team already queries on — goes through advance notice to known consumers and a deprecation window, exactly like a breaking API change, because for a team with a dashboard built on the old field name, it functionally is one.
- **Accountability follows the contract**: if cost attribution breaks because the platform team shipped a breaking schema change without notice, that's the platform team's action item; if it breaks because a team instrumented outside the shared library and skipped the required `team` tag, that's the consuming team's.
- As agent systems grow more autonomous — longer tool-call chains, more decision points per run — the schema's coverage of *why* a run took a given path (not just what it cost) becomes more load-bearing; teams building more complex agent architectures should expect the shared schema to need periodic extension, not treat it as finished. (See [Agent Architectures](../../ai-agent/agent-architectures/README.md) for how architectural choices there shape what a trace needs to capture.)

## Core Concept 9 — Sustained Delivery, Not a Static Rollout

Getting every team onto the shared schema once is not the end state:

- **A deprecation cadence tied to actual breaking-change need**, not a fixed calendar — most schema evolution should be additive (new optional attributes) and require no consumer action; breaking changes are rare and deliberate.
- **New teams onboard onto the shared schema by default**, via the instrumentation library being the standard starting point for any new LLM-calling service, not a retrofit applied after an incident reveals the team never adopted it.
- **A program-level retrospective every couple of quarters** against the Core Concept 7 measures, asking explicitly: is time-to-root-cause actually falling, and if not, is the bottleneck alerting calibration, runbook quality, or a schema gap that doesn't capture what an incident actually needed?

---

## Real-World Examples

- **A pilot's concrete win funds expansion.** A team with an unattributed, growing model bill becomes the pilot for shared cost tagging; within a month the breakdown shows a scheduled batch job, not live traffic, driving 40% of the cost — a finding the team could act on immediately, giving the platform team a specific result to justify expanding rather than a mandate with no proven payoff.
- **A redaction default catches what a policy document would have missed.** A support-bot trace store is found, during a routine audit, to contain full customer messages including account numbers typed directly into the chat — the redaction step existed as a documented policy but wasn't enforced in the instrumentation library, so teams instrumenting by hand skipped it. Moving redaction into the shared library's default path (rather than an opt-in step) closes the gap for every current and future consumer at once.
- **Adoption looks strong, time-to-root-cause doesn't move.** An org reaches 85% schema adoption, but a recent cost-spike incident still took most of a day to diagnose, because the alerting threshold was still the pilot team's original, untuned value and nobody had revisited it as traffic patterns shifted. The next quarter's investment moves from adoption outreach to a per-service threshold review.

## Common Mistakes

- **Centralizing instrumentation review in one platform team.** Cannot scale past a handful of teams; the review queue becomes the bottleneck to shipping.
- **Designing the schema from scratch instead of building on the OpenTelemetry GenAI conventions.** Reinvents attribute names the ecosystem's tools already understand, and makes future tool migrations harder than they need to be.
- **Treating redaction as a policy document instead of a default in the shared library.** Any team instrumenting by hand, intentionally or not, bypasses a policy that isn't enforced in code.
- **Measuring schema adoption without measuring time-to-root-cause.** High adoption with slow incident diagnosis looks like program success on a dashboard while delivering little of the actual operational benefit the program exists for.
- **Shipping a breaking schema change without a deprecation window.** Breaks every downstream dashboard and query built on the old field name simultaneously, with no notice.
- **Leaving cost attribution optional.** A team that skips the required `team`/`service` tags becomes invisible in the cost breakdown, undermining the entire point of attributing a shared budget.

---

## Apply it

1. Inventory which services across your org make LLM calls, and which of them are instrumented with a consistent schema versus ad hoc, freehand fields.
2. Design the org-specific extension to the OpenTelemetry GenAI conventions your shared schema needs (team, service, cost center, redaction status), and pilot it on one service with a known cost or quality visibility gap.
3. Draft one on-call runbook (refusal-rate spike, cost spike, or latency shift) following the pattern in Core Concept 4: what trace fields to pull first, what they distinguish, and who to escalate to.
4. Write the redaction rule for your most sensitive service's trace content, and confirm it's enforced in the instrumentation library's default path, not as an opt-in step.
5. Define `trace_completeness` and one time-to-root-cause measure for your pilot service, with a concrete numerator and denominator, and the exit condition that would justify expanding beyond the pilot.

## Verify your work

- The inventory names specific unstructured or freehand-instrumented services, not a general impression that "some services probably aren't standardized."
- The pilot's schema extension is built on top of the OpenTelemetry GenAI conventions, not a parallel reinvention of the same fields.
- The runbook specifies exact trace fields to pull and what each possible value distinguishes, not just "investigate the traces."
- The redaction rule is enforced in code in the shared library's default path, verified by checking that a raw PII string cannot reach the trace store through the standard instrumentation call.
- Both outcome measures are specific and falsifiable (a rate or duration with a clear numerator and denominator), not a vague statement like "better visibility."

## Review questions

- Why does centralizing every team's instrumentation review in one platform team tend to fail as the number of LLM-calling services grows?
- Why build the shared schema on top of the OpenTelemetry GenAI semantic conventions rather than defining org-specific attribute names from scratch?
- What does a slow time-to-root-cause reveal about an observability program that high schema adoption alone does not?
- Why does redaction belong in the shared instrumentation library's default path rather than in a policy document teams are expected to follow?
- What breaks for a consuming team when the shared schema changes a field's name or type without a deprecation window?

---

*Part of [Observability](README.md) → [AI Evaluation](../README.md). See also [Testing](../testing/README.md) and [Evaluation](../evaluation/README.md) for how the same traces feed regression suites and quality measurement at scale.*
