# Incident Management — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Can you run a contained incident workflow across application and dependency teams while keeping investigation and mitigation separate?

---

## Roles reduce cognitive load

For a sustained incident, separate command from execution. The incident commander prioritizes impact and decisions; an operations lead coordinates tasks; investigators gather evidence; a communications lead updates stakeholders. One person may hold several roles initially, but explicitly split them as scope grows.

## Decision log

Record each material decision as: time, decision, owner, evidence, expected effect, and reversal condition. This prevents repeated debate and makes a rollback safe. For example: “10:28 UTC, pause canary; owner IC; checkout 5xx 14%; expect queue drain within 10 min; resume only after 30 min below 1%.”

## Cross-component scenario

A database connection limit causes API timeouts and client retries. The application team caps retries and sheds report traffic; the database team increases connections only after checking memory headroom. The commander measures the user journey, not merely open connections. Parallel actions must have dependencies stated so one mitigation does not defeat another.

## Improve incrementally

Practice with a low-risk simulation. Start with a channel template, severity rubric, and status cadence. Add incident automation only after responders agree it creates the right record; a bot cannot replace command judgment.

## Apply it

1. Assign four incident roles for a three-team outage.
2. Write two decision-log entries, including reversal conditions.
3. Create a status update for technical and nontechnical audiences.

## Verify your work

- Tasks have an owner and do not conflict with active mitigations.
- A new responder can understand current impact from the decision log.
- Status updates distinguish current impact, mitigation, and next update time.

## Review questions

- Why should command and investigation be separated?
- What makes a mitigation decision reversible?
- How does a decision log help a changing incident team?
