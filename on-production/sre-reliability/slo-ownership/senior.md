# SLO Ownership — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Can you design ownership contracts that survive service evolution, shared platforms, and conflicting reliability priorities?

---

## Define boundaries and obligations

Ownership is an interface, not a hierarchy. A service owner publishes the outcome, SLI semantics, operating limits, on-call route, dependency expectations, and deprecation plan. A platform owner publishes capacity and support contracts rather than taking ownership of every application outcome.

## Evolving-system scenario

A monolith is split into checkout and fulfillment. During migration, retain one journey owner and explicit component owners; dual-write or asynchronous handoff must state which team owns reconciliation and customer communication. Prevent a gap where each new service is healthy but orders disappear between them.

## Trade-offs

Central ownership makes consistent standards easy but creates queues and weak product context. Fully local ownership reduces handoffs but can fragment measurement. Favor a central reliability enablement function with product teams accountable for their own user outcomes.

## Evidence

Audit pages after reorganizations; measure page-routing success, time to engage a dependency, and unresolved incident handoffs. Treat repeated ambiguity as an architecture signal, not a documentation typo.

## Apply it

1. Write a contract for a shared platform and one consumer service.
2. Identify a handoff invariant in a planned service split.
3. Review a past incident for ownership ambiguity.

## Verify your work

- Contracts name scope, support boundary, and escalation expectations.
- Migration plans preserve a journey owner until the new path is proven.
- Handoff metrics expose repeated ambiguity.

## Review questions

- Why is ownership an interface rather than a title?
- What gap can a service split introduce?
- When does central ownership become harmful?
