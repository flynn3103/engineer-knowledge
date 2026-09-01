# Evaluation and Execution Models — Middle

Bytecode VMs trade portability for dispatch overhead. AOT compilers pay work before execution; JITs use runtime profiles after warmup. Exceptions and effects constrain reordering. Async execution suspends at defined points and resumes through a scheduler.

Compare startup, steady-state throughput, memory, and tail latency on one representative program.

## Test yourself

1. Why can lazy evaluation retain memory?
2. What does an async suspension preserve?
3. Why is warmup part of a JIT benchmark?

Continue to [`senior.md`](senior.md).
