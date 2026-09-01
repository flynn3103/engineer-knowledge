# Feature Envy — Senior

## Outcome

Shape a safe approach at a changing system boundary.

## Core idea

**Feature Envy** means a method using another object’s data more than its own. It is useful only when it makes ownership, change, or correctness easier to see.

## Recognize it

Look for:

- long navigation chains and repeated queries against one collaborator.
- A change that feels larger than the business rule it implements.
- Tests that must know internal details instead of observable behavior.

## Apply it

1. Trace the concept across modules, teams, and operational paths.
2. State invariants, compatibility constraints, and failure modes.
3. Introduce a boundary that allows staged migration.
4. Measure change cost, coupling, or reliability before and after.
5. Review whether the new design still fits the domain language.

## Practical move

**Default move:** move the behavior to the data owner or introduce a focused collaborator.

Before editing, write one sentence in this form: “When _[event]_ happens, _[object]_ is responsible for _[decision]_.” If that sentence is hard to write, the responsibility or boundary is still unclear.

## Check your result

- **Evidence:** A planned change can move independently through the boundary with measurable risk reduction.
- **Guardrail:** Do not impose a uniform design where different domains need different trade-offs.
- **Review prompt:** Can a new reader identify the owner of the rule without tracing implementation details?

## Practice

Choose one real workflow. Mark the current owner of each decision, move or clarify one responsibility, then compare the resulting test setup and change surface. Keep the change if the rule is easier to explain; otherwise revert and record why.

## Next step

Read the next level when you can apply this move without a checklist and can explain the trade-off to a teammate.
