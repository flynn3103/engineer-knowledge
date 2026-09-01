# GRASP Responsibility Assignment — Professional

## Outcome

Establish repeatable team practice with measurable outcomes.

## Core idea

**GRASP Responsibility Assignment** means using GRASP patterns to place responsibilities deliberately. It is useful only when it makes ownership, change, or correctness easier to see.

## Recognize it

Look for:

- a controller coordinates everything or a class depends on information it does not own.
- A change that feels larger than the business rule it implements.
- Tests that must know internal details instead of observable behavior.

## Apply it

1. Define a lightweight standard and examples for reviews.
2. Add automated checks only where they protect a meaningful rule.
3. Coach teams through representative migrations.
4. Track a small outcome metric such as lead time, defects, or hotspots.
5. Revisit the standard when evidence shows it causes friction or gaming.

## Practical move

**Default move:** apply Information Expert, Creator, Controller, Low Coupling, High Cohesion, and Indirection.

Before editing, write one sentence in this form: “When _[event]_ happens, _[object]_ is responsible for _[decision]_.” If that sentence is hard to write, the responsibility or boundary is still unclear.

## Check your result

- **Evidence:** Teams make consistent decisions without a central gatekeeper, and the chosen metric improves.
- **Guardrail:** Treat guidelines as decision support, not a substitute for context.
- **Review prompt:** Can a new reader identify the owner of the rule without tracing implementation details?

## Practice

Choose one real workflow. Mark the current owner of each decision, move or clarify one responsibility, then compare the resulting test setup and change surface. Keep the change if the rule is easier to explain; otherwise revert and record why.

## Next step

Read the next level when you can apply this move without a checklist and can explain the trade-off to a teammate.
