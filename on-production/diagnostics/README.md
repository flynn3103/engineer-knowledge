# Diagnostics & Observability Thinking

> The discipline of reasoning about a running system you cannot step through with a debugger — seeing, attributing, and responding to what's actually happening in production, not what you assumed would happen.

Where the earlier sections in this roadmap sharpen how you reason about a *problem before you write code*, this section sharpens how you reason about a *system after it's shipped*. It covers the original three diagnostic tools (debugging, logging, error handling), the observability pillars that extend them at scale (metrics, tracing), and the production-grade practices — crash reporting, diagnostic endpoints, panic recovery, post-mortem analysis, audit logging, continuous profiling, dynamic instrumentation, and telemetry cost control — that turn "it's broken" into "here's exactly why, and here's the fix."

## Topics

| # | Topic | What you'll learn |
|---|-------|-------------------|
| 01 | [Debugging](01-debugging/junior.md) | Interactive debuggers, post-mortem analysis, core dumps, time-travel debugging, when prints beat breakpoints |
| 02 | [Logging](02-logging/junior.md) | Levels, structured logs, correlation IDs, log volume vs signal, sampling, retention |
| 03 | [Error Handling](03-error-handling/junior.md) | Exceptions vs result types, sentinel errors, error wrapping, stack traces, recovery vs propagation |
| 04 | [Metrics](04-metrics/junior.md) | Counters, gauges, histograms, cardinality, Four Golden Signals / RED / USE, OpenTelemetry Metrics |
| 05 | [Tracing](05-tracing/junior.md) | Spans, context propagation, OpenTelemetry SDK, sampling, tying traces to logs and metrics |
| 06 | [Observability Engineering](06-observability-engineering/junior.md) | Monitoring vs observability, unknown-unknowns, high-cardinality event data, why dashboards aren't enough |
| 07 | [Crash Reporting](07-crash-reporting/junior.md) | Sentry / Crashlytics / Bugsnag flows, symbolication, deduplication, release tagging |
| 08 | [Diagnostic Endpoints](08-diagnostic-endpoints/junior.md) | `/debug/pprof`, JMX, JFR, health / readiness probes, in-process REPLs, runtime config toggles |
| 09 | [Panic & Recovery](09-panic-and-recovery/junior.md) | Invariant violations, unwinding, signals, "let it crash," recover-at-boundary patterns |
| 10 | [Post-Mortem Analysis](10-post-mortem-analysis/junior.md) | Core dumps, heap dumps, thread / goroutine dumps, JFR recordings, offline reproduction |
| 11 | [Audit Logging](11-audit-logging/junior.md) | Security- and compliance-grade logs, tamper-evidence, retention, separation from operational logs |
| 12 | [Continuous Profiling](12-continuous-profiling/junior.md) | Always-on production profiling, flame graphs over time, finding the line burning CPU right now |
| 13 | [Dynamic Instrumentation & eBPF](13-dynamic-instrumentation-and-ebpf/junior.md) | Asking questions of a running system you didn't instrument in advance, safe in-production probes |
| 14 | [Telemetry Cost & Sampling Strategy](14-telemetry-cost-and-sampling-strategy/junior.md) | Balancing signal against observability spend, sampling strategies, cardinality budgets |

## How to use this section

Each topic has five depth levels — **junior → middle → senior → professional** — plus an **interview** Q&A bank and hands-on **tasks**. Topics 01–03 are the tools you reach for first; 04–05 extend them to distributed systems; 06 ties them together; 07–14 are the production-grade practices that separate "I added a log line" from "I can tell you exactly what happened, to whom, and why, six months from now."

---

> Part of the [Engineering Thinking](../) roadmap. It pairs with [Metacognition & Learning](../10-metacognition-and-learning/) — reasoning about your own thinking translates directly into reasoning about a system's behavior under failure.
