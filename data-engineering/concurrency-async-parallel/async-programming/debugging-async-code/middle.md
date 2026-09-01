# Debugging Async Code - Middle

> Make task ownership and causal context visible before an incident.

```python
async def load_partition(run_id, key):
    task = asyncio.current_task()
    task.set_name(f"load:{run_id}:{key}")
    async with tracer.start_as_current_span("object_store.get"):
        return await client.get_object(key)
```

At runtime, inspect all tasks and their stacks:

```python
for task in asyncio.all_tasks():
    print(task.get_name(), task.done(), task.get_stack())
```

Propagate context with task-local facilities such as Python `contextvars`,
.NET `Activity`, or tracing spans. Include low-cardinality operation names in
metrics and high-cardinality run IDs in traces/logs, not metric labels.

| Question | Evidence |
|---|---|
| What is waiting? | task dump and await target |
| Why was it started? | parent span/task ownership |
| What resource is slow? | dependency span and pool metrics |
| Was it cancelled? | cancellation cause and deadline |

Enable debug modes in staging and targeted production windows; creation-stack
tracking and slow-callback diagnostics can have measurable overhead.

## Test yourself

1. Why should run IDs not become metric labels?
2. What does a named task add beyond a thread name?
3. Which evidence links a waiting task to its downstream dependency?

Continue to [`senior.md`](senior.md).
