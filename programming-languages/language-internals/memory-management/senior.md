# Memory Management — Senior

Under load, unbounded queues and caches defeat any collector. Pinned objects fragment moving heaps; finalizers delay reclamation; off-heap buffers hide from heap limits. Set memory budgets with backpressure and capture heap, native, mmap, and cgroup evidence.

## Test yourself

1. Why does a stable heap not prove stable RSS?
2. How does pinning affect compaction?
3. Which limit stops admission before OOM?

Continue to [`professional.md`](professional.md).
