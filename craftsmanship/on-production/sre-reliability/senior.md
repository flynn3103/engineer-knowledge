# SRE and Reliability — Senior

## Own SLOs across dependencies and regions

A service's reliability is bounded by its dependencies — you cannot offer a 99.99% SLO on top of a dependency that only commits to 99.9%. Senior-level SLO ownership means:

- **Tracing SLO composition** across every dependency in the critical path, not just your own service's numbers.
- **Owning regional failure** explicitly — what happens to your SLO when an entire region is degraded, and whether failover is automatic, tested, and within budget.
- **Tracking the recovery backlog** — work queued up during an incident (retried jobs, delayed writes) that must drain without itself causing a second incident.

## Separate incident roles

A live incident needs distinct roles so diagnosis and coordination don't block each other:

| Role | Owns | Does not do |
|---|---|---|
| **Incident commander** | Coordination, status communication, go/no-go on mitigation actions | Doesn't personally debug — stays focused on decisions and communication |
| **Technical investigator(s)** | Forming and testing hypotheses (see [Debug-Thinking — Senior](../../engineering-thinking/08-debug-thinking/senior.md)) | Doesn't own external communication — stays focused on diagnosis |
| **Scribe** | A shared, timestamped timeline of facts, hypotheses, decisions, and actions | Doesn't editorialize — records what happened, not who's at fault |

**Preserve evidence while mitigating.** A rollback or restart that erases the only copy of the evidence you needed (a crashed process's core dump, an in-memory queue's state) trades a faster mitigation for a harder root-cause investigation — know which trade-off you're making before you act, not after.

## Design telemetry for degraded state, not just healthy state

Most telemetry is designed to show a system working. Senior-level telemetry also has to show a system *failing partially*:

- **Retries** — are they visible as a distinct signal, or do they look identical to first attempts in your metrics?
- **Queue growth** — is depth-over-time visible before the queue is already full?
- **Partial results** — when a request degrades gracefully (see [middle.md](middle.md)), is that logged distinctly from a full success?
- **Cancellation and recovery** — can you see a request that was cancelled mid-flight, and confirm when a degraded dependency actually recovers, not just when its health check turns green?

## Client-side crash reports

Server-side telemetry doesn't cover crashes on a device you don't control. Crash reporting (tools like Sentry, Crashlytics, or a custom uploader) needs:

- **Symbolicated stack traces** — a raw memory address is useless; the crash report pipeline must map addresses back to source lines using the build's debug symbols.
- **Grouping and deduplication** — thousands of crash reports from the same root cause should collapse into one issue, not flood a queue with duplicates that hide how many distinct problems actually exist.
- **Crash-free rate as the user-facing SLI** — "% of sessions with zero crashes" is closer to actual user experience than a raw crash count, which conflates a rare crash affecting many users with a frequent crash affecting few.

## Audit logs are not debug logs

An audit log answers "who did what, when" for accountability and compliance — a fundamentally different job from a debug log's "what happened, technically." Audit logs need:

- **Actor identity** — not just a service name, the actual user or system that initiated the action.
- **Tamper resistance** — an audit log a compromised process could quietly edit isn't evidence of anything.
- **A defined retention policy** and **periodic access review** — who can read audit logs is itself a fact worth auditing.

Don't let debug and audit logging share infrastructure casually — a debug log rotated out after 7 days for cost reasons is fine; an audit log rotated out after 7 days may violate a compliance requirement nobody checked.

## Use dynamic instrumentation deliberately

Tools like eBPF let you observe a running system (syscalls, network, scheduling) without redeploying — powerful, and risky if used casually. Only attach dynamic instrumentation with:

- **A precise question** — "why is this process's CPU usage spiking" not "let's see what's going on."
- **Access controls** — dynamic instrumentation typically requires elevated privileges; scope who can attach it and to what.
- **Overhead limits** — some instrumentation has real performance cost; know the budget before attaching it to a production system under load.

## Run blameless postmortems that produce durable fixes

A postmortem's job is to **improve defenses, detection, response, and recovery** — not to assign blame. Concretely:

- Separate **facts** (what the timeline shows happened), **hypotheses** (what might explain it), **decisions** (what was chosen and why), and **actions** (what will change) — mixing these makes a postmortem unreadable six months later.
- Track **recurring failure patterns** across postmortems, not just each incident in isolation — a failure mode that recurs under a new trigger every quarter means the fix keeps patching the symptom.
- Track **action-item completion**, not just action-item creation — an unfinished postmortem action is a risk someone is silently carrying.
- Be explicit about **who can accept reliability risk** — a "we'll fix it later" decision needs an accountable owner, not silent agreement.

## Test yourself

1. How do shared dependencies limit the SLO you can honestly offer, regardless of your own service's numbers?
2. Which mitigation actions destroy evidence you might need for root-cause diagnosis, and how do you decide the trade-off in the moment?
3. What specifically makes an audit log different from a debug log, beyond "it's for compliance"?
4. Why is crash-free session rate a better user-facing SLI than a raw crash count?
5. What makes a postmortem action durable instead of a promise that quietly expires?

Continue to [`professional.md`](professional.md).
