# Agent Architectures - Professional

An agent architecture is a distributed workflow runtime whose transition
function may consult a probabilistic service. Durable execution principles
still apply: replay, idempotency, state versioning, leases, and compensation.

## Real-system mechanics

**LangGraph** models applications as stateful graphs and checkpoints state
between supersteps. Its execution model draws from **Pregel**, where nodes
process state and propagate updates in synchronized rounds. This makes loops,
interrupts, and resumability explicit.

**Temporal** records workflow event history and deterministically replays
workflow code after worker failure. Activities perform nondeterministic I/O
and may execute more than once, so they require idempotency. Model calls belong
in activities, not replayed workflow decision code.

**ReAct** interleaves reasoning-oriented model outputs and actions, improving
adaptation to observations but coupling control flow to generated text. Typed
tool calls and explicit state reduce parser and replay ambiguity.

**Ray** supplies distributed tasks and actors for fan-out workloads. It solves
scheduling and resource placement, not semantic coordination; an unbounded
agent planner can still overwhelm a Ray cluster with branches.

## Scale and failure behavior

At 10x, model latency hides orchestration overhead but tool pools and checkpoint
writes begin to queue. At 100x, fan-out multiplies calls, hot workflow keys
serialize state updates, and event histories become expensive to replay.
Continue-as-new or compact histories while preserving audit references.

Use leases for step ownership, fencing tokens to reject stale workers, and
compare-and-swap state versions. A worker that resumes after a network pause
must not overwrite a newer result. Queue fairness should prevent long research
graphs from starving short interactive tasks.

## Operations

Measure graph starts/completions, terminal states, node latency/error/retries,
fan-out width, critical-path latency, checkpoint bytes, replay duration,
budget exhaustion, compensation failures, and stale-worker rejections.

Postmortems should reconstruct the exact accepted plan, state transitions,
external effects, and model/tool versions. Generated narrative is supporting
evidence, not the authoritative execution log.

## Design and operations checklist

- [ ] Deterministic transitions are separated from model and network I/O.
- [ ] Plans and state transitions are durable and versioned.
- [ ] Activities are idempotent; irreversible actions have approval boundaries.
- [ ] Fan-out, depth, retries, tokens, and wall time have hard budgets.
- [ ] Leases use fencing so stale workers cannot commit.
- [ ] Partial failure and compensation are observable terminal paths.

## Cheat sheet

```text
workflow       = code selects next step
agent          = model may select next step
checkpoint     = durable state for resume/replay
activity       = nondeterministic external operation
fencing token  = rejects commits from stale owners
compensation   = explicit response to a committed partial effect
```

## Test yourself

1. Why should a Temporal workflow not invoke a model directly during replay?
2. Design fencing for two workers racing to complete the same graph node.
3. How would you bound and schedule a tree-search workload fairly?

## Further reading

- Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models"
- Malewicz et al., "Pregel: A System for Large-Scale Graph Processing"
- Temporal documentation, "Workflow Execution" and durable execution
- LangGraph source and persistence documentation
- Moritz et al., "Ray: A Distributed Framework for Emerging AI Applications"
