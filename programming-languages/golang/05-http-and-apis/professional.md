# HTTP and APIs — Professional

> **Topic:** [HTTP and APIs](../README.md)
> **Focus:** API governance across teams, deprecation policy enforcement, resilience-pattern standardization (timeouts, retries, circuit breakers) fleet-wide, and leading the response to an availability incident.

---

## Introduction

At professional level, the concern shifts from "does this API handle load correctly" to "do all our APIs handle load correctly, consistently, and can we prove it before an incident forces the question." This means governance, shared libraries, and incident leadership.

---

## Core Concepts

### 1. Resilience patterns belong in a shared library, not reinvented per team

Timeouts, retry-with-backoff, circuit breakers, and load shedding are exactly the kind of cross-cutting concern that should live in one well-tested internal package, imported everywhere, rather than each team implementing (and subtly getting wrong) their own version. A single bug fix or tuning improvement in the shared library then benefits every service simultaneously.

### 2. API deprecation needs an enforced timeline, not just a changelog entry

Announcing a deprecated API version in a changelog is necessary but not sufficient. A professional-level process includes: a `Deprecation` and `Sunset` HTTP header (per RFC 8594) on responses from the old version, monitoring which clients are still calling it, direct outreach to remaining callers before the sunset date, and only then removing it — with the deprecation timeline itself documented and consistently enforced across every public API, not decided ad hoc per team.

### 3. Cross-team consistency in timeout/retry defaults prevents cascading failures

If Team A's service retries 3 times with no backoff against Team B's already-struggling service, Team A can be the reason Team B's incident gets worse. Fleet-wide conventions — a shared library's defaults for backoff, jitter, and retry caps — reduce the chance that one team's local resilience decision becomes another team's outage amplifier.

### 4. Leading an availability incident is a distinct skill from fixing the bug

During a live incident, the senior/professional engineer's job often shifts to: establishing what's actually failing (via dashboards, not guessing), deciding whether to shed load / open a circuit breaker / roll back, communicating status to stakeholders, and only then diagnosing root cause — in that order. Diagnosing root cause first, while the system continues degrading, is a common and costly mistake under pressure.

### 5. Postmortems for availability incidents should audit resilience-pattern usage

Beyond "what broke," a thorough postmortem for a cascading-failure-style incident should ask: did every service in the chain have a reasonable timeout? Was there a circuit breaker, and did it trip appropriately? Was load shedding in place? Gaps found here become concrete, trackable action items — often "adopt the shared resilience library at call site X" rather than a one-off patch.

---

## Code Examples

### Example 1 — A `Deprecation`/`Sunset` header

```go
w.Header().Set("Deprecation", "true")
w.Header().Set("Sunset", "Sat, 01 Aug 2026 00:00:00 GMT")
w.Header().Set("Link", `<https://docs.company.com/api/v2>; rel="successor-version"`)
```

### Example 2 — Shared resilience defaults

```go
// company.com/pkg/resilience
func DefaultClient() *http.Client {
    return &http.Client{
        Timeout: 5 * time.Second,
        Transport: &http.Transport{MaxIdleConnsPerHost: 20, IdleConnTimeout: 90 * time.Second},
    }
}
func DefaultRetryPolicy() RetryPolicy {
    return RetryPolicy{MaxAttempts: 3, BaseBackoff: 100 * time.Millisecond, Jitter: true}
}
```

---

## Pros & Cons

| Approach | Pros | Cons |
|---|---|---|
| Shared resilience library | Consistency, single point of improvement | Requires adoption discipline; a bug affects everyone |
| Enforced deprecation headers + monitoring | Predictable, low-surprise API evolution | Requires tooling to track caller adoption |
| Incident-response order (stabilize, then diagnose) | Minimizes damage during active incidents | Requires training/drills; instinct under pressure often skips to root-cause first |

---

## Best Practices

1. Publish and mandate a shared resilience library for timeouts, retries, circuit breakers, and load shedding.
2. Enforce API deprecation with `Deprecation`/`Sunset` headers and caller-adoption monitoring, not just changelog announcements.
3. Train the incident-response order explicitly: stabilize (shed load, open breakers, roll back) before deep root-cause diagnosis.
4. Audit resilience-pattern coverage as a standing postmortem question for every availability incident.

---

## Edge Cases & Pitfalls

- **A shared resilience library adopted inconsistently** (some services on v1 defaults, some on v2) can itself become a source of confusing, inconsistent behavior — track adoption as deliberately as the library's development.
- **Deprecation headers that are technically present but never checked by any client tooling** provide a false sense of a completed process — verify client teams actually have monitoring/alerting on them.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Every team implementing its own retry/circuit-breaker logic | Adopt a shared, mandated resilience library |
| Deprecating an API via changelog only | Add enforced headers, monitor caller adoption, direct outreach before sunset |
| Diagnosing root cause before stabilizing during an active incident | Train and drill the stabilize-first incident response order |

---

## Cheat Sheet

```
Fleet resilience checklist:
  [ ] Shared library for timeouts/retries/circuit breakers, adopted org-wide
  [ ] Deprecation + Sunset headers on retiring API versions, with adoption monitoring
  [ ] Incident response order: stabilize (shed/breaker/rollback) -> then root-cause
  [ ] Postmortems explicitly audit resilience-pattern coverage
```

---

## Summary

- Resilience patterns (timeouts, retries, circuit breakers, load shedding) belong in a shared, mandated internal library — not reinvented per team.
- API deprecation needs enforced headers and adoption monitoring, not just a changelog entry.
- During an availability incident, stabilize first (shed load, trip breakers, roll back), then diagnose root cause.
- Postmortems should explicitly audit resilience-pattern coverage across the failure chain, producing concrete adoption action items.

---

## Further Reading

- RFC 8594 — *The Sunset HTTP Header Field*: <https://www.rfc-editor.org/rfc/rfc8594>
- Google SRE Book — *Managing Incidents*: <https://sre.google/sre-book/managing-incidents/>

---

## Related Topics

- [Error Handling — Professional](../04-error-handling/professional.md)
- [Production Debugging — Professional](../07-production-debugging/professional.md)

---

## Check your understanding

1. Explain HTTP and APIs — Professional Level in your own words and name the problem it solves.
2. How would you apply the ideas around Introduction, Core Concepts, Code Examples in a realistic engineering change?
3. What failure mode or misuse should you look for, and what evidence would reveal it?
4. How would you introduce and govern HTTP and APIs — Professional Level across teams through reversible, measurable increments?
5. What observable result would convince you that the approach improved the system?
