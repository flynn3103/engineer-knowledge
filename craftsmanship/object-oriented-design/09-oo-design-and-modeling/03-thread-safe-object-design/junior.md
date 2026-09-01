# Thread-Safe Object Design — Junior

## Outcome

Apply the idea safely in one small, well-defined change.

## Core idea

**Thread-Safe Object Design** means making object state and operations safe under concurrent access. It is useful only when it makes ownership, change, or correctness easier to see.

## Recognize it

Look for:

- mutable shared fields, check-then-act logic, and leaking internal collections.
- A change that feels larger than the business rule it implements.
- Tests that must know internal details instead of observable behavior.

## Apply it

1. Name the concept in the code you are changing.
2. Identify one concrete symptom and the behavior it harms.
3. Make the smallest reversible improvement.
4. Add or update a focused test for the behavior.
5. Explain the before/after in a review note.

## Practical move

**Default move:** prefer immutability; otherwise define synchronization, ownership, and atomicity.

Before editing, write one sentence in this form: “When _[event]_ happens, _[object]_ is responsible for _[decision]_.” If that sentence is hard to write, the responsibility or boundary is still unclear.

## Check your result

- **Evidence:** One scenario is simpler to read and test; unrelated callers keep working.
- **Guardrail:** Do not widen the refactor while learning the technique.
- **Review prompt:** Can a new reader identify the owner of the rule without tracing implementation details?

## Practice

Choose one real workflow. Mark the current owner of each decision, move or clarify one responsibility, then compare the resulting test setup and change surface. Keep the change if the rule is easier to explain; otherwise revert and record why.

## Next step

Read the next level when you can apply this move without a checklist and can explain the trade-off to a teammate.
