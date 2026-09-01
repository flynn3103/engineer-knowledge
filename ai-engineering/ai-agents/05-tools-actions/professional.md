# Tools and Actions - Professional

Tool execution is a capability-oriented RPC subsystem with a nondeterministic
planner as one client. Design it with the same rigor as a public API and job
runner.

## Real-system mechanics

**Anthropic tool use** represents requests as typed `tool_use` blocks and
correlates responses through `tool_use_id`. Multiple blocks can appear in one
turn, so executors must define concurrency and result ordering explicitly.

**OpenAI function calling and Structured Outputs** can constrain arguments to
a JSON Schema. This reduces parse failures but does not authorize the call or
guarantee that arguments reflect user intent.

**Stripe's idempotency layer** stores the first result for a client key and
returns it for repeats. Its request-parameter comparison is the right model
for side-effecting agent tools: duplicate delivery must not duplicate effect.

**gVisor** interposes a user-space application kernel, while **Firecracker**
runs workloads in microVMs. Both provide stronger isolation for hostile code
than a language-level timeout, with different startup, compatibility, and
operational costs.

## Scale and failure behavior

At 10x load, unbounded parallel tool calls saturate downstream connection
pools before model serving fails. Apply per-tool bulkheads, queue limits, and
deadlines propagated from the parent agent run. At 100x, large tool outputs
inflate context, object storage, and trace pipelines; cap bytes at ingress and
store large artifacts out-of-band with a scoped reference.

Retries amplify incidents. Combine exponential backoff with jitter, a retry
budget, and circuit breakers. Never retry a side effect unless its idempotency
contract is proven. Cancellation should stop queued work and signal running
work, while acknowledging that remote work may already have committed.

## Operations

Dashboard calls, latency, errors, denials, retries, output bytes, sandbox
violations, and duplicate-key hits by tool and tenant. Trace model decision,
validated arguments, policy decision, executor attempt, and normalized result
under one correlation ID, with secrets redacted before storage.

A design review should ask: what authority does this tool grant; how is the
principal bound to the call; can it be repeated; what is the commit point;
and how do operators determine whether an ambiguous call took effect?

## Design and operations checklist

- [ ] Schemas are narrow, versioned, and reject unknown fields.
- [ ] Authorization and confirmation happen outside the model.
- [ ] Side effects have durable idempotency and status lookup.
- [ ] Each tool has deadlines, concurrency limits, and output limits.
- [ ] Hostile computation has kernel-level isolation and no ambient secrets.
- [ ] Traces correlate proposals, policy, execution, and result safely.

## Cheat sheet

```text
schema       = what arguments are well formed
authorization= who may perform the action
idempotency  = whether replay duplicates the effect
sandbox      = what compromised code can reach
bulkhead     = how one tool avoids exhausting the system
```

## Test yourself

1. A payment commits but the executor times out. Describe the safe recovery path.
2. When would Firecracker's isolation justify its overhead over a process sandbox?
3. Design backpressure for one slow tool shared by 20,000 agent runs.

## Further reading

- Anthropic documentation, "Tool use with Claude"
- OpenAI documentation, "Function calling" and "Structured Outputs"
- Stripe documentation, "Idempotent requests"
- Agache et al., "Firecracker: Lightweight Virtualization for Serverless Applications"
- gVisor architecture and security documentation
