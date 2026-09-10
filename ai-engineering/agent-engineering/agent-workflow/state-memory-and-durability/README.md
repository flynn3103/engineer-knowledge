# State, Memory, and Durability

> A workflow that only works when nothing goes wrong isn't production-ready. This subtopic is about what survives a crash, a restart, or a multi-day pause — and what it costs to guarantee that.

```mermaid
flowchart LR
    J["Junior: locate the state"] --> M["Middle: decide what persists"]
    M --> S["Senior: checkpoint and resume"]
    S --> P["Professional: version live workflows"]
```

## Levels

| Level | Guide | You are done when |
|---|---|---|
| Junior | [Locate where state lives](junior.md) | You can point to exactly what state a workflow run has, and what's ephemeral vs. persisted. |
| Middle | [Decide what persists, and why](middle.md) | You can decide what must survive across sessions, and how it gets retrieved back into context. |
| Senior | [Checkpoint, resume, and compensate](senior.md) | You can design a resumable workflow with idempotent retries and a rollback plan for a partially completed run. |
| Professional | [Version workflows already in flight](professional.md) | You can migrate a running workflow's code or schema without corrupting in-progress runs. |

## Practice rule

Before calling a workflow "resumable," kill it mid-run on purpose and try to resume it. If you can't answer exactly what state it needs to pick back up correctly, it isn't resumable — it's untested.

## Related

- [Workflow Fundamentals](../workflow-fundamentals/) — the steps whose state this subtopic persists and resumes.
- [Reliability and Recovery](../reliability-and-recovery/) — the retry and rollback logic that depends on the durability model here.
- [Scaling Workflows](../scaling-workflows/) — durability at fleet scale, where checkpointing itself becomes a cost and throughput concern.
