# Diagnostics & Observability

Use this roadmap to understand, investigate, and improve running systems.

## Topics

- [Debugging](debugging/README.md) — Find the cause with a reproducible case, a clear hypothesis, and evidence—not guesses.
- [Logging](logging/README.md) — Record useful structured events so an operator can explain what the service did.
- [Error Handling](error-handling/README.md) — Represent failures clearly, preserve their cause, and handle them at the right boundary.
- [Metrics](metrics/README.md) — Measure aggregate system behavior with correctly typed, bounded time-series data.
- [Tracing](tracing/README.md) — Follow one request across work boundaries using spans and propagated context.
- [Observability Engineering](observability-engineering/README.md) — Combine telemetry so teams can answer expected and new production questions.
- [Crash Reporting](crash-reporting/README.md) — Capture unhandled failures with release context, grouping, and safe diagnostic detail.
- [Diagnostic Endpoints](diagnostic-endpoints/README.md) — Expose safe, bounded runtime information for operating a live service.
- [Panic & Recovery](panic-and-recovery/README.md) — Treat invariant failures differently from expected errors, and isolate recovery at safe boundaries.
- [Post-Mortem Analysis](post-mortem-analysis/README.md) — Learn from incidents using preserved evidence, a timeline, and corrective actions.
- [Audit Logging](audit-logging/README.md) — Record deliberate actions with integrity and context for security and compliance.
- [Continuous Profiling](continuous-profiling/README.md) — Use low-overhead production profiles to locate CPU, allocation, and blocking regressions over time.
- [Dynamic Instrumentation & eBPF](dynamic-instrumentation-and-ebpf/README.md) — Ask focused questions of a live system without redeploying it, while controlling risk and overhead.
- [Telemetry Cost & Sampling Strategy](telemetry-cost-and-sampling-strategy/README.md) — Control telemetry cost while keeping the data needed to understand important failures.

## How to use the guides

1. Pick the topic closest to the production problem you are solving.
2. Start with your current level: junior, middle, senior, or professional.
3. Apply one checklist item and verify the outcome.
4. Use the final review questions for active recall.

> Part of the [Craftsmanship](../README.md) roadmap.
