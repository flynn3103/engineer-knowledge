# Four-Level Learning Structure

Use these as content requirements, not rigid heading templates. Adapt section names and emphasis to the topic.

## Shared writing pattern

Every file should:

1. State the level-specific question or capability near the beginning.
2. Explain the essential mental model in plain language.
3. Provide a repeatable method or decision framework.
4. Apply it to at least one credible engineering scenario.
5. Cover important mistakes, failure modes, or limits.
6. Show how the learner can verify the result.
7. End with review questions or a practical checklist. Keep the questions unanswered so the learner must recall the material.

Prefer several focused sections over one long essay. Define unfamiliar terms at first use. Make examples internally consistent across prose, code, tables, and diagrams.

## Junior

Focus on performing the skill correctly in a small, well-defined context.

Include:

- Purpose and foundational vocabulary.
- A repeatable step-by-step method.
- A small example with visible inputs and outputs.
- Simple criteria for knowing when the work is done.
- Common beginner mistakes and direct corrections.
- A hands-on exercise or checklist usable in daily work.

Keep abstractions grounded. The learner should finish able to apply the topic with guidance.

## Middle

Focus on choosing boundaries and composing maintainable solutions in a real codebase.

Include:

- How to evaluate competing implementation choices.
- Interfaces, dependencies, testability, debugging, and change cost where relevant.
- Under-application and over-application signals.
- Incremental adoption or refactoring guidance.
- A scenario that crosses multiple functions, modules, or components.
- Verification at both unit and integrated-flow levels.

The learner should finish able to make and explain local design trade-offs independently.

## Senior

Focus on architecture under uncertainty and change.

Include:

- System boundaries, invariants, ownership of data or decisions, and information hiding where relevant.
- Failure modes, recovery, evolution, compatibility, or operational effects.
- Evidence used to validate a proposed design rather than relying on preference.
- At least one realistic cross-component scenario.
- Trade-offs among plausible approaches and conditions that favor each.
- Questions that expose weak assumptions before implementation.

The learner should finish able to shape a system-level approach and contain future change.

## Professional

Focus on organization-scale outcomes and durable delivery.

Include:

- Architecture aligned with team ownership and cognitive load.
- Initiative decomposition into reversible, observable increments.
- Migration, governance, operational, compliance, or coordination risks when applicable.
- Explicit outcome measures and evidence-based exit conditions.
- Cross-team contracts, accountability, and escalation or incident ownership.
- A scenario involving sustained delivery, not only a static target architecture.

The learner should finish able to design an operating model in which teams deliver and learn with limited coordination.

## Diagram selection

Choose a diagram only when it answers a concrete question:

| Question | Diagram |
|---|---|
| What depends on what? | `flowchart` |
| How does work or data move? | `flowchart` |
| Who calls whom, and in what order? | `sequenceDiagram` |
| What happens after a failure or decision? | Small `flowchart` |
| Which option is better under which condition? | Table or prose |
| What are the properties of several items? | Table or list |

Avoid class diagrams, entity-relationship diagrams, timelines, mind maps, and decorative diagrams unless the user explicitly requests them.
