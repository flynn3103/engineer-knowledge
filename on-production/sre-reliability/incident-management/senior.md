# Incident Management — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Can you shape incident architecture that contains blast radius, supports recovery, and remains effective as systems and responders change?

---

## Design for command under uncertainty

Incident process is part of system architecture. Define severity from user impact, not pager volume; define who may change traffic, disable features, or communicate externally. Preserve evidence with deploy markers, immutable logs, and decision records while enabling quick rollback.

## Cross-component scenario

A bad configuration propagates through a shared service mesh. The incident commander freezes configuration rollout, isolates affected tenants, and assigns one workstream to restore safe defaults while another checks control-plane state. The recovery invariant is that tenant isolation must not block emergency authentication. Test this before the outage, not during it.

## Trade-offs

A centralized command structure improves coordination in broad incidents but can slow local recovery. A federated model scales with independent domains but risks conflicting mitigations. Use a clear threshold for central command and allow local teams pre-authorized reversible actions.

## Evidence and evolution

Analyze time-to-detect, time-to-mitigate, repeated command handoffs, and mitigation reversals. Run simulations involving personnel changes and partial observability. Improve templates from actual cognitive failures rather than copying industry rituals.

## Apply it

1. Define pre-authorized actions and escalation thresholds for one platform.
2. Tabletop a configuration blast-radius event.
3. Identify evidence that must remain available during recovery.

## Verify your work

- Roles and authority are clear without the usual lead present.
- A mitigation does not violate a protected system invariant.
- Exercises expose and improve command latency.

## Review questions

- Why is severity based on impact rather than alert count?
- What is the value of pre-authorized reversible action?
- Which evidence is easily lost during recovery?
