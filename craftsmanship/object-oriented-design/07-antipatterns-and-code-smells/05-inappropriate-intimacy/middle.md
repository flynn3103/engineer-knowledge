# Inappropriate Intimacy — Middle

## Outcome

Make and explain a local design trade-off in an existing component.

## Core idea

**Inappropriate Intimacy** means two classes knowing too much about each other’s internals. It is useful only when it makes ownership, change, or correctness easier to see.

## Recognize it

Look for:

- paired edits, direct state manipulation, and helpers exposing private decisions.
- A change that feels larger than the business rule it implements.
- Tests that must know internal details instead of observable behavior.

## Apply it

1. Map the callers, data owners, and change paths.
2. Write two plausible placements for the behavior.
3. Choose the option with clearer ownership and fewer dependencies.
4. Refactor in small commits with behavior-preserving tests.
5. Record the trade-off and rejected alternative.

## Practical move

**Default move:** hide internals, move behavior, or create an explicit boundary object.

Before editing, write one sentence in this form: “When _[event]_ happens, _[object]_ is responsible for _[decision]_.” If that sentence is hard to write, the responsibility or boundary is still unclear.

## Check your result

- **Evidence:** The component has a clearer seam, fewer coordinated edits, and targeted tests.
- **Guardrail:** Avoid optimizing a metric or pattern name at the expense of a coherent workflow.
- **Review prompt:** Can a new reader identify the owner of the rule without tracing implementation details?

## Practice

Choose one real workflow. Mark the current owner of each decision, move or clarify one responsibility, then compare the resulting test setup and change surface. Keep the change if the rule is easier to explain; otherwise revert and record why.

## Next step

Read the next level when you can apply this move without a checklist and can explain the trade-off to a teammate.
