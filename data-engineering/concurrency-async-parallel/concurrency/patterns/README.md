# Patterns

> Covers Fan In Fan Out, Pipeline, Producer Consumer, Readers Writers, and Worker Pool.

## Topics

| Topic | What it covers |
|---|---|
| [Fan In Fan Out](fan-in-fan-out/) | Split one stream of work across multiple concurrent workers (fan-out), then merge their results back into one stream (fan-in). The… |
| [Pipeline](pipeline/) | Break a task into sequential stages, each running concurrently on different items — while stage 2 processes item 1, stage 1 is already… |
| [Producer Consumer](producer-consumer/) | One or more producers generate work; one or more consumers process it, through a shared, bounded buffer that coordinates the handoff. The… |
| [Readers Writers](readers-writers/) | Many readers can safely access shared data simultaneously; a writer needs exclusive access. The pattern that generalizes into every… |
| [Worker Pool](worker-pool/) | A fixed set of long-lived workers, each pulling from a shared task queue — reusing threads/processes instead of creating a new one per… |
