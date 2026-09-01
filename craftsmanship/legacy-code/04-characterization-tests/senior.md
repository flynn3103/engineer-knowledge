# Characterization Tests — Senior

At system boundaries, characterization tests are risk controls. They preserve contracts while you learn where legacy behavior is intentional, accidental, or relied upon by unknown consumers.

## Characterize the contract surface

Prioritize behavior with a large blast radius:

- API status codes, payload fields, ordering, and defaults.
- Persistence formats and migration behavior.
- Queue messages, retry rules, idempotency, and timeouts.
- Security and authorization decisions.

Use a layered test strategy. Unit tests clarify local decisions; contract tests pin a boundary; a few end-to-end probes verify wiring. Do not try to capture the whole system in slow end-to-end tests.

## Make uncertainty visible

Label tests that capture questionable behavior: `test_currently_accepts_blank_customer_id`. Pair them with an issue, decision, or acceptance criterion before changing the behavior. This prevents a refactor from silently becoming a product decision.

## Control the data

Use representative production-shaped fixtures, with sensitive data removed. Include known historical cases when compatibility matters. Measure flaky tests and eliminate hidden time, order, and shared-state dependencies before trusting the suite as a change gate.

## Review prompts

- Which consumers would notice this behavior moving?
- What is the smallest stable contract we can lock down?
- Which behavior is deliberately temporary, and who decides its replacement?
- What signal will tell us whether the migration is safe?
