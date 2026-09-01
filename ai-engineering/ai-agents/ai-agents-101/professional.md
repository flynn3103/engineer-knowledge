# AI Agents 101 — Professional

This level is general systems-engineering knowledge about building
request/response loops around a nondeterministic, latency-heavy remote call
— the same class of problem as building a reliable RPC client, a job
scheduler, or a saga orchestrator. Everything here transfers whether the
"model" is an LLM, a human-in-the-loop reviewer, or any other slow, fallible
step in a pipeline.

## Under the hood: how real agent runtimes structure the loop

Look at how three different systems implement the same loop from middle.md,
just with more engineering around it.

**Claude Code's tool-execution model**: the CLI agent runs tools in a
supervisor process, not inline in the model-call thread. Each tool
invocation is a separate subprocess/call with its own timeout and permission
check (read/write/network), so a hung tool can't block cancellation of the
whole run. Tool results are streamed back into context incrementally rather
than batched, which bounds worst-case memory for long tool outputs.

**LangGraph's executor**: models the agent as an explicit state machine
(nodes = steps, edges = transitions) rather than an implicit `while` loop.
This makes the "loop" a directed graph you can statically analyze —
you can prove there's no path back to a node without a decrementing counter,
which is exactly the halting-problem-adjacent guarantee an ad-hoc `while`
loop can't give you.

**OpenAI's Assistants/Responses API**: pushes the loop server-side —
the *server* holds the run state machine (`queued → in_progress →
requires_action → completed`), and your client polls or streams status. This
trades client-side control (you can't intercept mid-loop as easily) for not
having to re-implement retry/persistence logic yourself.

## Scale and failure behavior

At low volume (a few loops/minute), a naive `while` loop with no batching
is fine — the LLM call itself dominates latency (200ms–5s).

At scale (thousands of concurrent agent runs), what breaks first is usually
**not** the model API — it's:

- **Tool-call fan-out concurrency limits**: if each step can trigger 5
  parallel tool calls, and you have 1,000 concurrent agents, that's 5,000
  simultaneous downstream calls hitting your database/APIs — a classic
  thundering-herd, the same failure mode as an unbounded goroutine/thread
  pool. Bound it with a semaphore per downstream dependency, not per agent.
- **Context-window growth**: unbounded conversation history means token
  count — and therefore cost and latency — grows with the number of loop
  iterations. This is the same "unbounded queue growth" problem as an
  in-memory message queue with no backpressure; the fix is the same
  (truncate/summarize = drop-oldest or compact, exactly like a ring buffer).
- **Retry storms**: naive per-agent retry-with-backoff on tool failure, at
  scale, produces synchronized retry waves if backoff isn't jittered — the
  same bug class as the classic AWS "thundering herd" reconnect storms.

## Production operability

- **Dashboard metrics**: loop-iteration count distribution (p50/p99),
  tool-call error rate by tool name, tokens-in/tokens-out per run, and
  "stuck" rate (runs hitting max_steps).
- **Runbook entry**: "agent runs spiking to max_steps" → check for a tool
  returning malformed/ambiguous results, or a system-prompt regression that
  makes the model second-guess a correct answer.
- **Postmortem shape**: "Agent X issued 400 duplicate refunds" → root cause
  is almost always a missing idempotency key on the tool call, not a model
  reasoning failure — treat every tool as if it will be called twice.
- **Design review question a staff engineer asks**: "What happens if this
  tool call succeeds on the server but the response is lost before the
  model sees it?" (classic at-least-once vs. exactly-once problem — the
  model will likely retry, so every tool with side effects needs an
  idempotency key.)

## Design/ops checklist

- [ ] Every tool with a side effect (write, send, delete) is idempotent or
      keyed so a retried call is safe
- [ ] Concurrency to each downstream dependency is bounded independently of
      total agent concurrency
- [ ] Context history has an explicit truncation/summarization strategy
      before it's needed, not after a cost incident
- [ ] Retries use jittered backoff, not fixed intervals
- [ ] Loop termination is provable (state machine or decrementing counter),
      not "should stop eventually"

## Cheat sheet

```
agent loop  = while(not done): call_model() -> execute_tools() -> append_results()
failure modes = infinite loop | poisoned context | injected instructions | retry storm | duplicate side effects
mitigation    = step cap + repeat detection | structured errors | untrusted-data framing | jittered backoff | idempotency keys
```

## Test yourself (staff-level)

1. A support-bot agent's refund tool has no idempotency key. Under what
   exact conditions does a user get double-refunded, and where would you
   add the fix?
2. You're seeing synchronized latency spikes every 30s across 10,000
   concurrent agent runs. What's your first hypothesis and how do you
   confirm it?
3. Design a review question you'd ask about a new agent that can call a
   `delete_file` tool — what three things must be true before you approve
   it for production?

## Further reading

- Anthropic, ["Building Effective Agents"](https://www.anthropic.com/research/building-effective-agents)
- Anthropic, [Tool use documentation](https://docs.anthropic.com/en/docs/tool-use)
- Classic distributed-systems reading on idempotency and at-least-once
  delivery (any saga-pattern / outbox-pattern writeup) — the same
  guarantees apply directly to tool calls with side effects.
