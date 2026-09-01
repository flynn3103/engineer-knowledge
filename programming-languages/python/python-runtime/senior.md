# Python Runtime — Senior

Choose runtime-sensitive designs from workload evidence.

- CPU-bound Python code does not gain parallel CPU execution from ordinary threads under the traditional GIL build.
- I/O-bound work often benefits from async or threads; compare both with load tests.
- Bound object lifetime in long-running processes; caches need size, expiry, and invalidation rules.
- Treat import time and module-level side effects as startup dependencies.

Create a performance budget for latency, memory, and startup. Review profiles and allocation traces with every significant regression.
