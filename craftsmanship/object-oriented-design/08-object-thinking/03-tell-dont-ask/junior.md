# Tell, Don’t Ask — Junior

## Outcome

Apply the idea safely in one small, well-defined change.

## Core idea

**Tell, Don’t Ask** means tell an object the desired outcome instead of pulling out state to decide externally. It is useful only when it makes ownership, change, or correctness easier to see.

## Recognize it

Look for:

- getters feed conditional logic in distant callers.
- A change that feels larger than the business rule it implements.
- Tests that must know internal details instead of observable behavior.

## Apply it

1. Name the concept in the code you are changing.
2. Identify one concrete symptom and the behavior it harms.
3. Make the smallest reversible improvement.
4. Add or update a focused test for the behavior.
5. Explain the before/after in a review note.

## Practical move

**Default move:** move the decision to the object that owns the relevant state.

Before editing, write one sentence in this form: “When _[event]_ happens, _[object]_ is responsible for _[decision]_.” If that sentence is hard to write, the responsibility or boundary is still unclear.

## Check your result

- **Evidence:** One scenario is simpler to read and test; unrelated callers keep working.
- **Guardrail:** Do not widen the refactor while learning the technique.
- **Review prompt:** Can a new reader identify the owner of the rule without tracing implementation details?

## Practice

Choose one real workflow. Mark the current owner of each decision, move or clarify one responsibility, then compare the resulting test setup and change surface. Keep the change if the rule is easier to explain; otherwise revert and record why.

## Next step

Read the next level when you can apply this move without a checklist and can explain the trade-off to a teammate.
