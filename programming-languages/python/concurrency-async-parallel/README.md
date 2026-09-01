# Python Concurrency, Async, and Parallelism

> Choose concurrency from the workload, then bound tasks, queues, time, and shared state.

```mermaid
flowchart LR
  Work --> IO{mostly waiting?}
  IO -->|async-compatible| Async[asyncio]
  IO -->|blocking I/O| Threads[threads]
  IO -->|CPU work| Processes[processes / native code]
```

Progress through [safe basics](junior.md), [model selection](middle.md), [saturation behavior](senior.md), and [capacity governance](professional.md).
