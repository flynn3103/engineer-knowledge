# Performance

> Measuring, profiling, and optimising the runtime cost of code — latency, throughput, memory, cache behaviour, contention — and protecting hot paths against regression over the lifetime of a system.

## Topics

| # | Topic | What you'll learn |
|---|-------|-------------------|
| 01 | [Profiling](01-profiling/README.md) | CPU/memory/allocation profiles, flame graphs, pprof/perf/Instruments/async-profiler |
| 02 | [Benchmarking & Microbenchmarks](02-benchmarking-and-microbenchmarks/junior.md) | Avoiding DCE, JIT warm-up, branch-prediction noise; statistical stability |
| 03 | [Latency & Throughput](03-latency-and-throughput/junior.md) | Little's Law, the p99 trap, tail-at-scale, coordinated omission, queueing |
| 04 | [CPU-Bound Optimization](04-cpu-bound-optimization/junior.md) | Profile-first, the memory hierarchy, branch prediction, SIMD, data layout, PGO |
| 05 | [Memory & Allocation Optimization](05-memory-and-allocation-profiling/junior.md) | Allocation rate vs. residency, escape analysis, GC pressure, allocators |
| 06 | [Concurrency & Contention](06-concurrency-and-contention/junior.md) | Amdahl & USL, lock contention, false sharing, cache coherence, scaling curves |
| 07 | [Performance Budgets & Regression Testing](07-performance-budgets-and-regression-testing/junior.md) | Budgets as SLOs, benchstat/Mann-Whitney, change-point detection, CI gates |

## How to use this section

Each topic has four depth levels — **junior → middle → senior → professional** — plus an **interview** Q&A bank. Start at your level and climb.

---

> Part of the [Quality Engineering](../README.md) roadmap.
