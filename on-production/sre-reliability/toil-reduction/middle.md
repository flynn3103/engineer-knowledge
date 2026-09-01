# Toil Reduction — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Can you redesign a recurring operational workflow with safe interfaces, observability, and an exception path?

---

## Automate the decision boundary

Do not start with a script. First define the interface: input, validation, decision, action, audit record, and exception path. A queue-remediation tool might accept a queue ID, refuse unknown queues, require a low-watermark check, apply one scaling action, and emit an event linked to the incident.

## Make it testable

Separate policy from provider calls. Unit-test rules such as “never scale more than 20% in one run”; integration-test a sandbox provider; run dry-runs in production before enabling mutation. Use idempotency keys so repeated alerts do not repeat the action.

## Adoption scenario

Support engineers spend 40 minutes daily restarting a consumer after a transient credential refresh error. A tool can restart only after it confirms the error signature, no active deployment, and a healthy upstream. It creates a ticket after two failed attempts. The first rollout runs in observe-only mode and compares recommendations with human decisions.

## Under- and over-automation

Manual copy/paste after a known alert is under-automation. An autonomous system that changes database capacity based on a noisy single metric is over-automation. Escalate ambiguous or high-blast-radius decisions to humans.

## Apply it

1. Specify an automation interface for one recurring task.
2. List policy unit tests and one sandbox integration test.
3. Design an exception record a human can action.

## Verify your work

- Repeated triggers produce at most one intended change.
- Dry-run recommendations agree with sampled human decisions.
- Failures preserve enough context for a responder to continue safely.

## Review questions

- Why separate policy from provider calls?
- What makes an operation idempotent?
- When should automation defer to a human?
