# SLO Ownership — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Can you establish ownership boundaries for a journey spanning several services and make escalation testable?

---

## Own outcomes, document dependencies

An order journey can involve web, checkout, payment, inventory, and notification services. Give each team an owned service SLO, then define a journey SLO owned by the product team closest to the user promise. Dependency owners publish their own objectives and support route; they do not silently inherit an upstream product outcome.

## A practical ownership record

| Field | Example |
|---|---|
| Outcome | Customer receives an order confirmation |
| Owner | Checkout team |
| On-call | `checkout-primary` |
| Dependencies | Payments API, inventory reservation |
| Escalation | Incident commander after 10 minutes of unresolved impact |
| Review cadence | Monthly and after material architecture change |

## Change scenario

Inventory moves to a new team. Before cutover, update the ownership record, page routes, runbook, dashboards, and dependency contract. Run a game-day handoff: simulate inventory timeouts and confirm checkout owns customer communication while inventory owns its mitigation. A repository transfer alone is not ownership transfer.

## Signals of poor boundaries

- Alerts go to a platform queue with no service responder.
- Two teams both believe the other owns the journey.
- An SLO page names a former team or has no escalation route.
- A downstream dependency is blamed before an upstream user impact is established.

## Apply it

1. Draw a two-service journey and assign outcome versus component ownership.
2. Write an escalation trigger and expected first response from each owner.
3. Rehearse a dependency-timeout handoff with a teammate.

## Verify your work

- An alert reaches a current on-call route in a test.
- The ownership page remains accurate after a team transfer.
- Each team can state what evidence it owes the other during an incident.

## Review questions

- Why should journey ownership differ from component ownership?
- What changes must accompany a service transfer?
- How can an escalation exercise reveal an ownership gap?
