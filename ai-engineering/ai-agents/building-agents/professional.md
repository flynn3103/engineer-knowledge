# Building Agents - Professional

A production agent platform combines an RPC gateway, durable workflow engine,
capability executor, model-routing layer, and evaluation/telemetry pipeline.
The model SDK is a replaceable edge dependency, not the architecture.

## Real-system mechanics

**Anthropic Messages API** returns typed content blocks and stop reasons;
clients execute requested tools and send matching result IDs. Streaming clients
must assemble partial events without treating an incomplete JSON argument as
an executable call.

**OpenAI Responses API** represents generated items and tool interactions in a
provider-specific event stream. Adapter tests should preserve item ordering,
correlation IDs, usage, refusal, and truncation states rather than mapping only
the happy path.

**Gemini function calling** similarly exposes declared functions and generated
calls, but schema support and turn representation differ. Capability
negotiation in your adapter prevents silently dropping unsupported constraints.

**LangGraph** provides checkpoints and graph execution; **Temporal** provides
durable replay and activity semantics. They solve overlapping but distinct
problems. A common design runs agent graph logic inside or alongside a durable
workflow boundary rather than assuming either library supplies every control.

## Scale and failure behavior

At 10x, provider rate limits and tool connection pools drive queueing. Use
per-provider and per-tool admission control, tenant fairness, and deadline-aware
scheduling. At 100x, token streaming, trace volume, and checkpoint writes
become material; batch telemetry, tier old payloads, and sample content without
losing counters or error traces.

Hedged model requests can reduce tail latency but double cost and may produce
two tool proposals; use them only before side effects and cancel losers.
Retries require jitter and budgets. Brownouts should disable expensive optional
branches before rejecting core traffic.

## Operations

Measure queue time separately from provider latency, time-to-first-token,
turns, tool calls, token/cost distribution, completion states, retries,
checkpoint lag, policy denials, and evaluation success by runtime version.

Runbooks correlate provider incidents, prompt/model rollouts, tool failures,
and queue saturation. Preserve a sanitized replay bundle containing versions,
events, and external-result references for high-severity incidents.

## Design and operations checklist

- [ ] Internal events preserve provider semantics needed for correctness.
- [ ] Every run and side effect is durable, correlated, and replay-safe.
- [ ] Admission control protects providers, tools, tenants, and total cost.
- [ ] Fallback combinations are evaluated before deployment.
- [ ] Streaming handles partial frames, cancellation, and client reconnects.
- [ ] Telemetry separates queue, model, tool, and orchestration latency.

## Cheat sheet

```text
adapter    = provider wire format <-> internal typed events
runner     = state machine and budgets
executor   = validation, authorization, and tool effects
checkpoint = durable resume boundary
evaluation = behavioral release gate, not only monitoring
```

## Test yourself

1. What information is lost by normalizing all provider stops to `done`?
2. Design fair admission control for three tenants and two model providers.
3. When is a hedged model call safe, and how do you handle its losing result?

## Further reading

- Anthropic Messages and tool-use API documentation
- OpenAI Responses API and function-calling documentation
- Google Gemini function-calling documentation
- LangGraph source and persistence documentation
- Temporal documentation on activities, retries, and durable execution
