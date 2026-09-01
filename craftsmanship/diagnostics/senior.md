# Diagnostics — Senior

During incidents, mitigate impact, preserve evidence, and maintain a shared timeline. Separate facts, hypotheses, decisions, and actions. Use dynamic instrumentation or eBPF only with access controls, overhead limits, and a precise question.

Design telemetry for degraded dependencies, retries, queue growth, partial results, cancellation, and recovery. Audit logs serve accountability and need tamper resistance, retention policy, actor identity, and access review; they are not ordinary debug logs.

Control telemetry cost through semantic conventions, aggregation, tiered retention, adaptive sampling, and budgets per service. Dropping all successful events can hide the comparison needed to explain failure.

## Test yourself

1. Which action mitigates impact without destroying evidence?
2. How does an audit log differ from a debug log?
3. What is the risk of sampling only errors?
4. Which telemetry proves successful recovery?

Continue to [`professional.md`](professional.md).
