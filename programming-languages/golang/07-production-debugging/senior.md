# Production Debugging — Senior

> **Topic:** [Production Debugging](../README.md)
> **Focus:** Diagnosing goroutine and memory leaks live in production, differential profiling, debugging without stopping the world, and building the diagnostic surface into a service before you need it.

---

## Introduction

At scale, you rarely get to attach a debugger to a production incident — you diagnose from telemetry the service already exposes, or you don't diagnose it at all. Senior-level production debugging is as much about building the right diagnostic surfaces in *before* an incident as it is about using them well *during* one.

---

## Prerequisites

- Comfortable with distributed tracing, flame graph reading, and connection-pool diagnostics (middle level).

---

## Core Concepts

### 1. Diagnosing a goroutine leak live

```bash
curl http://internal:6060/debug/pprof/goroutine?debug=2 > goroutines.txt
grep -c "^goroutine" goroutines.txt          # total count
awk '/^goroutine/{print} ' goroutines.txt | sort | uniq -c | sort -rn | head
```

The dominant, repeated stack trace among thousands of goroutines is almost always the leak's signature — it tells you the exact blocking call (a channel receive, a mutex, a network read) that's never returning, which is the concrete starting point for a fix.

### 2. Differential heap profiling isolates growth, not just size

```bash
go tool pprof -base=heap_t0.pprof heap_t1.pprof
```

Comparing two heap profiles taken minutes or hours apart shows what's actually **growing** between them — far more actionable during a slow leak investigation than a single snapshot, which mixes long-lived legitimate allocations with the actual leak.

### 3. Debugging without stopping the world

Production debugging tools are chosen specifically because they don't require pausing the process: `pprof`'s sampling profiler runs alongside live traffic with low overhead; `strace`/`dtrace`/eBPF-based tools observe syscalls and kernel events without modifying the running binary; a "debug endpoint" exposing internal state (queue depth, cache hit rate, current config) answers questions a debugger would, without needing to attach one.

### 4. On-CPU vs. off-CPU time

A CPU profile shows only time spent *executing* — a goroutine blocked waiting on I/O, a lock, or a channel doesn't show up as "using CPU," even though it's a real source of latency. For genuinely latency-focused (rather than throughput-focused) investigations, an **off-CPU profile** (or a trace showing span wait time) is often more revealing than a CPU profile alone — a request can be slow with 0% CPU usage the entire time, purely from waiting.

### 5. Build diagnostic surfaces in, before you need them

- A `/debug/vars` or custom `/internal/status` endpoint exposing live config, queue depths, cache stats, and build info.
- Feature flags to selectively enable verbose logging or increased trace sampling for a specific request or user, on demand, without a redeploy.
- A "safe to run in production" toolkit documented and rehearsed *before* an incident, not improvised during one.

---

## Worked Example — Diagnosing a Slow Memory Leak With Differential Profiling

A service's memory grew steadily over roughly 6 hours before restarting (via an auto-healing policy) and repeating the cycle. A single heap snapshot showed a large, but not obviously abnormal, set of allocations spread across many call sites. Taking two snapshots two hours apart and diffing them (`pprof -base`) isolated a much smaller set of call sites that were *specifically growing* — narrowing immediately to a cache that was never evicting entries for a specific, rare request shape. The single-snapshot approach had been misleading because it couldn't distinguish "large and stable" from "small but growing without bound."

---

## Pros & Cons

| Technique | Pros | Cons |
|---|---|---|
| Differential heap profiling | Isolates actual growth, not just current size | Requires capturing and retaining profiles over the investigation window |
| Off-CPU / wait-time analysis | Reveals latency invisible to a CPU profile | Requires tracing or specialized tooling (not just `pprof`'s default CPU profile) |
| Pre-built debug endpoints | Instant answers during an incident, no new deploy needed | Requires upfront investment before any specific incident justifies it |

---

## Best Practices

1. Take differential heap profiles (two snapshots over time), not just one, when investigating a leak.
2. Group goroutine-profile dumps by stack trace, not raw count, to find the dominant leaking pattern.
3. Distinguish on-CPU (profiling) from off-CPU/wait-time (tracing) investigations based on whether the symptom is throughput or latency.
4. Invest in debug/status endpoints and toggleable verbose logging before an incident, as standard service scaffolding.

---

## Edge Cases & Pitfalls

- **A single heap snapshot during a slow leak** can be misleading — always prefer a differential comparison over time when the symptom is gradual growth.
- **A CPU profile showing "nothing hot"** during a real latency incident is a strong signal to switch to off-CPU/wait-time analysis rather than concluding "the profile shows no problem."
- **Debug endpoints left unauthenticated on a reachable network** are an information-disclosure risk — the same caution as `pprof` applies to any custom internal-status endpoint.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Relying on a single heap snapshot for a slow-leak investigation | Take differential snapshots over time |
| Only ever profiling CPU when latency (not throughput) is the symptom | Add off-CPU/wait-time analysis via tracing |
| Building diagnostic tooling only after the first major incident forces it | Build debug endpoints and toggleable logging in as standard scaffolding upfront |

---

## Tricky Points

- A goroutine profile's "dominant stack" is dominant by *count*, not necessarily by *impact* — a smaller number of goroutines each holding a large amount of memory can matter more than a large number holding little.
- `pprof`'s CPU profiler samples at a fixed rate (default 100Hz) — extremely short-lived hot functions can be under-sampled and appear less significant than they actually are; cross-check surprising results with a targeted benchmark.

---

## Cheat Sheet

```bash
go tool pprof -base=old.pprof new.pprof        # differential heap analysis
curl .../debug/pprof/goroutine?debug=2 | \
  awk '/^goroutine/' | sort | uniq -c | sort -rn  # dominant leak stack
```

```
Throughput symptom → CPU profile
Latency symptom, low CPU → off-CPU / wait-time / trace analysis
```

---

## Summary

- Differential heap profiling (comparing two snapshots over time) isolates actual leaks far better than a single snapshot.
- Grouping a goroutine-profile dump by stack trace reveals the dominant leaking pattern directly.
- A latency problem with low CPU usage needs off-CPU/wait-time analysis, not a CPU profile.
- Build debug endpoints, toggleable verbose logging, and a documented production-safe toolkit in before an incident forces the question.

---

## Further Reading

- The Go Blog — *Profiling Go Programs*: <https://go.dev/blog/pprof>
- Brendan Gregg — *Off-CPU Analysis*: <https://www.brendangregg.com/offcpuanalysis.html>

---

## Related Topics

- [Goroutines and Concurrency — Senior](../01-goroutines-and-concurrency/senior.md)
- [Go Runtime — Senior](../02-go-runtime/senior.md)

---

## Check your understanding

1. Explain Production Debugging — Senior Level in your own words and name the problem it solves.
2. How would you apply the ideas around Introduction, Prerequisites, Core Concepts in a realistic engineering change?
3. What failure mode or misuse should you look for, and what evidence would reveal it?
4. How would you validate a system-level decision about Production Debugging — Senior Level under uncertainty?
5. What observable result would convince you that the approach improved the system?
