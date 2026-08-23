# Production Debugging — Interview Prep

> **Topic:** [Production Debugging](../README.md)

---

## Conceptual / Foundational

**Q: What is `net/http/pprof`, and how do you use it safely?**
A: A package that, when blank-imported, registers live profiling endpoints (`/debug/pprof/...`) on an HTTP server. It should be exposed only on an internal/localhost-only port, never publicly — it can leak implementation detail and its captures cost CPU/memory.

**Q: Difference between a CPU profile and a heap profile?**
A: A CPU profile samples which functions are executing on-CPU over a time window (for "why is this slow/high-CPU"); a heap profile snapshots current memory allocations by call site (for "why is this using so much memory").

**Q: How do you read a flame graph?**
A: Width represents time/samples; height represents call-stack depth. Wide bars, at any depth, indicate where time is being spent — that's what to investigate, not necessarily the deepest part of the stack.

## Tricky / Trap Questions

**Q: A CPU profile during a latency incident shows nothing unusually hot. What does that tell you?**
A: The bottleneck is likely off-CPU (waiting on I/O, a lock, a channel, or a downstream call) rather than compute-bound — switch to distributed tracing or off-CPU/wait-time analysis instead of continuing to profile CPU.

**Q: Why is a single heap snapshot sometimes misleading when investigating a suspected memory leak?**
A: It mixes large-but-stable legitimate allocations with a smaller, actually-growing leak — a differential comparison between two snapshots taken over time isolates what's actually growing.

**Q: A goroutine profile shows 10,000 goroutines. How do you find the actual problem quickly?**
A: Group the dump by identical stack trace (not raw count) — the dominant repeated stack is almost always the leak's signature, pointing directly at the blocking call that never returns.

## System / Design Scenarios

**Q: Design the diagnostic surface you'd want on every service in a fleet, before any specific incident happens.**
A: A consistent internal debug port exposing `pprof` and a status endpoint (queue depths, cache stats, build info), structured logs with a shared request/trace ID schema, distributed tracing with a shared backend, and standard latency/error/saturation dashboards — the same shape across every service so any on-call engineer knows where to look.

**Q: Walk through diagnosing a service with rising P99 latency but flat average CPU usage.**
A: Check connection-pool wait metrics (`db.Stats()`) and goroutine counts first — a queuing/concurrency-limit problem produces exactly this signature. If pools look fine, pull a trace to find which span is accumulating wait time, then decide between a CPU profile (if genuinely compute-bound) or off-CPU analysis (if waiting).

## Behavioral / Experience

**Q: Walk me through the last production incident you debugged, from detection to resolution.**
A: (Tailor to experience — strong answers follow a phase structure: detection signal, triage/impact assessment, mitigation taken to stop the bleeding, then root-cause diagnosis with specific tools named, and the structural fix that followed.)

---

## Cheat Sheet

```
pprof CPU     → on-CPU time, sampled; good for compute-bound slowness
pprof heap    → current allocations by call site; diff two snapshots for leaks
goroutine?debug=2 → group by stack trace to find leak signature
Flame graph   → width = time; wide bars at any depth = investigate
Latency + low CPU → check pool/queue metrics and traces (off-CPU), not just CPU profile
Incident order → Detect -> Triage -> Mitigate -> Resolve -> Postmortem
```

---

## Related Topics

- [Junior](junior.md) · [Middle](middle.md) · [Senior](senior.md) · [Professional](professional.md) · [Tasks](tasks.md)
