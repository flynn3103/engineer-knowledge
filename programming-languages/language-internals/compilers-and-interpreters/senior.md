# Compilers and Interpreters — Senior

Compiler correctness includes diagnostics, source maps, debug information, linking, incremental builds, and reproducibility. JITs speculate from profiles and must deoptimize safely when guards fail. A production regression can come from changed inlining, code-cache pressure, warmup, or an optimization blocked by aliasing.

Use optimization remarks, disassembly, profiles, and differential tests. Never infer generated behavior from source aesthetics.

## Test yourself

1. What state must deoptimization reconstruct?
2. Why can inlining increase code size and hurt caches?
3. How would you isolate a compiler-version regression?

Continue to [`professional.md`](professional.md).
