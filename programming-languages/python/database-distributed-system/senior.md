# Python Data and Distributed Systems — Senior

Distributed correctness comes from explicit invariants, not reliable-looking code.

- Define consistency needs per workflow.
- Use an outbox or durable workflow when a database write must trigger a message.
- Handle duplicate, delayed, and reordered events.
- Plan migrations for old and new application versions running together.
- Observe connection saturation, slow queries, replication lag, and retry volume.

Design failure paths before adding a new dependency or asynchronous boundary.
