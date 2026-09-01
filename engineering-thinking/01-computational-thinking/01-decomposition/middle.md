# Decomposition - Middle

At this level, choose boundaries that make code easier to change, understand, and test.

## Judge every split

- **Cohesion:** keep responsibilities that change for the same reason together.
- **Coupling:** minimize knowledge and dependency across boundaries.
- **Rule:** separate responsibilities that change for different reasons.

For every proposed interface, ask:

1. What data crosses it?
2. Does the receiver need all of that data?
3. Does either side know the other's implementation details?
4. Will a normal change require edits on both sides?

## Move from functions to modules

Group related functions by rules and data, then expose a focused API:

```text
avatar/
  validation.py  # file rules
  imaging.py     # resize and format
  storage.py     # upload and retrieve URLs
  service.py     # coordinates the workflow
```

- Let a coordinator call leaf modules when the flow needs orchestration.
- Do not let leaf modules depend on one another without a clear reason.
- Refactor one group at a time and run tests after each move.

## Choose a direction

- Work **top-down** when the user flow is clear: define the outcome, then its responsibilities.
- Work **bottom-up** when a primitive is uncertain: prove it first, then compose it.
- Usually use both: sketch the flow, prove risky parts, then adjust the boundary.

## Find the useful size

Under-decomposition signs:

- One file changes for unrelated work.
- Tests require the entire application.
- A unit has many unrelated dependencies.

Over-decomposition signs:

- One flow requires opening many tiny files.
- Interfaces and wrappers outweigh the useful logic.
- Simple changes cross several layers without adding value.

Keep a separate piece only when it has a clear name, can change independently, or creates a useful test boundary.

## Design recomposition

Trace one real scenario across the proposed modules before accepting the split:

- Count boundary calls and repeated data translations.
- Identify shared mutable state and failure ownership.
- Check that one module can be faked while another is tested.
- Reconsider the cut if integration is harder than the internal logic.

## Use decomposition for estimates and debugging

- For debugging: inspect a middle boundary, eliminate the healthy half, and repeat.
- For estimates: list deliverables with a definition of done and dependencies.
- Include testing, failure handling, deployment, monitoring, and documentation, not just coding.

## Boundary review

```markdown
## Responsibility
What one job does this module own?

## Interface
What inputs, outputs, dependencies, and hidden details does it have?

## Failure and verification
What can fail, who handles it, and how do we test it alone and in the full flow?
```

## Checklist

- [ ] Each module has one clear responsibility.
- [ ] Things that change together live together.
- [ ] Interfaces are small but express the business need.
- [ ] A normal and failure flow have been traced.
- [ ] The design avoids both a giant unit and meaningless fragments.

> Good decomposition creates focused pieces that can change without surprising one another.

Next: [Senior level](senior.md)

## Check your understanding

1. How do cohesion and coupling evaluate a proposed seam?
2. When is a module too small?
3. When should a design start top-down or bottom-up?
