# SLO Ownership — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Can you identify who owns a user-facing SLO and route a breach to the people able to investigate it?

---

## Ownership makes an SLO actionable

An SLO without an owner is only a chart. **SLO ownership** means a named team accepts responsibility for the definition, dashboard, alerts, and response process for a service outcome. It does not mean that team caused every failure. A database or vendor can fail, but the owner remains responsible for making the user impact visible and coordinating the response.

For an order-confirmation SLO, write down four roles:

| Role | Responsibility |
|---|---|
| Product/service team | Defines the user journey and fixes application behavior |
| On-call engineer | Acknowledges alerts and begins triage |
| Dependency owner | Supplies evidence or mitigation for its component |
| Incident commander | Coordinates when impact crosses teams |

## A repeatable handoff

1. Read the SLO page before changing the service.
2. Find the current owning team and on-call route.
3. During a breach, capture the SLI query, start time, affected journey, and recent changes.
4. Page the owner using the documented route; do not guess from repository history.
5. Keep a short timeline and link it in the incident or ticket.

## Example

Checkout confirmations are failing because the payment provider is timing out. The checkout team owns the confirmation SLO and starts rollback/feature controls. The payments team owns the provider adapter and investigates retries. Neither team can declare success merely because its local metric is healthy: the owned outcome is the completed confirmation.

## Common mistakes

- Naming an individual rather than a durable team.
- Treating a platform team as default owner of every downstream SLO.
- Paging a dependency before recording the user-facing symptom and time range.
- Leaving ownership stale after a service transfer.

## Apply it

1. Pick a service and write its user journey in one sentence.
2. Name its owning team, on-call route, and two important dependencies.
3. Draft a five-line breach handoff containing evidence and requested help.

## Verify your work

- A teammate can find the owner and page route without asking you.
- Your handoff distinguishes user impact from a suspected cause.
- The owner is a team with an escalation path, not a single person.

## Review questions

- Why can an SLO owner still be accountable when a dependency fails?
- Which details make an initial breach handoff useful?
- Why is a durable team better than a named individual as owner?
