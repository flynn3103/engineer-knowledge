# Memory Management — Junior

Stack-like storage follows call lifetime; heap storage supports dynamic lifetime. References can keep objects alive. Manual freeing risks leaks and use-after-free; managed runtimes reclaim unreachable objects; ownership systems prove lifetime constraints.

## Test yourself

1. What keeps an object reachable?
2. Why is stack versus heap not purely a source decision?
3. What is a leak in a GC language?

Continue to [`middle.md`](middle.md).
