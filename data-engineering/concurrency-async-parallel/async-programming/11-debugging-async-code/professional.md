# Debugging Async Code - Professional

> Production async debugging reconstructs causality from continuation state,
> scheduler behavior, resource queues, and distributed traces.

## Runtime mechanisms

**CPython asyncio** tasks retain coroutine frames and expose `get_stack()`;
debug mode records slow callbacks and creation provenance. `faulthandler` gives
thread stacks but must be combined with task inspection. An event-loop callback
blocked in native code may appear only in the thread artifact.

**Tokio Console** instruments task spawn, poll, wake, and resource state through
`tracing`. Poll duration and scheduled/idle duration reveal tasks that monopolize
workers or are repeatedly woken without progress. Instrumentation changes cost
and timing, so use sampling and reproduce under representative load.

**.NET** async state machines can be inspected with Visual Studio Parallel
Stacks, `dotnet-dump`, EventPipe, and `dotnet-trace`. Runtime counters expose
ThreadPool queue length and starvation. `Activity` carries distributed trace
context across awaits, while exception dispatch preserves logical stacks better
than manual throw patterns.

**Java async ecosystems** combine JFR, async-profiler, virtual-thread dumps, and
framework-specific Reactor debugging. Reactor assembly tracing improves causal
stacks but can be expensive; checkpoint operators add targeted provenance.

## Wait-for graphs and causality

Model tasks and resources as a graph: task -> awaited lock/future/pool slot;
resource -> owning or completing task. A cycle is evidence of deadlock. A long
acyclic chain ending at a remote future indicates dependency latency; many tasks
ending at a bounded executor indicate queueing or starvation.

At 100x task count, full stack capture and one span per tiny continuation can
consume more CPU and memory than application work. Retain aggregates, exemplars,
oldest-task samples, and event-triggered detailed dumps.

## Incident runbook

1. Freeze or snapshot evidence before restart: task dump, thread dump, profile,
   runtime counters, and trace exemplars.
2. Classify tasks as runnable, waiting on I/O, waiting on synchronization,
   queued for an executor, or cancelled but not terminated.
3. Build the terminal wait resource for the oldest and highest-fan-in tasks.
4. Compare scheduler delay with dependency service time.
5. Reproduce the suspected ordering with barriers and fault injection.

## Design and ops checklist

- Give every long-lived task an owner, operation name, and creation provenance.
- Propagate deadlines, cancellation causes, and trace context across spawns.
- Dashboard loop lag, runnable queue, task age, pool queueing, and outcomes.
- Keep metric labels bounded; put request identity in traces or logs.
- Provide a safe on-demand task-dump endpoint with access controls.
- Test diagnostics at scale and quantify their overhead.
- Preserve multiple concurrent failures rather than logging only the first.
- Include async evidence capture in shutdown-hang and latency runbooks.

```text
ASYNC DEBUGGING CHEAT SHEET
thread stack   what an OS thread executes now
task stack     where suspended logical work waits
trace          why work exists and which dependency it reached
runtime metric whether scheduling or queues delay progress
wait graph     cycle = deadlock; terminal queue/dependency = bottleneck
```

## Test yourself

1. Ten thousand tasks wait while CPU is low. How do you distinguish a healthy
   downstream wait from executor starvation?
2. Design bounded observability for one million short-lived tasks per minute.
3. Which artifacts must be captured before restarting a hung async service?
4. How can instrumentation create or hide the race being investigated?

## Further reading

- CPython `asyncio` developer documentation and `Lib/asyncio/tasks.py`.
- Tokio Console documentation and `tokio-rs/console` source.
- .NET diagnostics documentation for EventPipe, `dotnet-counters`, and dumps.
- OpenTelemetry specification, context propagation and span links.
- Project Reactor reference, debugging and `checkpoint()`.
