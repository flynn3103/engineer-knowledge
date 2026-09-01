# Computational Thinking — Senior

Senior decomposition protects system invariants while enabling incremental change.

## Decompose along change boundaries

Use business capability, data ownership, consistency needs, operational failure, and team ownership as evidence. A service boundary that shares a database and release cycle with its neighbor may add network failure without real independence.

## Prefer vertical slices

A horizontal plan—database this quarter, backend next quarter, UI later—delays feedback. Deliver a thin path through all necessary components, observe it, then expand traffic and behavior.

- Slice 1: one user flow behind a flag.
- Slice 2: real persistence and telemetry.
- Slice 3: more cases and traffic.
- Slice 4: retire the old path.

## Preserve invariants during migration

Write down what must remain true across old and new paths. Use compatibility layers, expand-and-contract schemas, dual reads only when observable, and explicit rollback points. Every temporary component needs an owner and removal condition.

## Avoid abstraction failure

Watch for dependency magnets, shared models with unrelated consumers, interfaces that mirror one implementation, and “platform” packages without clear service levels. These are signs that the model optimizes reuse rather than change.

## Decision record

For a major decomposition, record context, forces, options, chosen boundary, rejected alternatives, invariants, migration stages, observability, and reversal cost.

## Test yourself

1. When does a module deserve to become a service?
2. What makes a vertical slice safe rather than merely small?
3. Which metrics tell you a boundary is causing coordination cost?
4. How do you make a temporary migration seam removable?

Continue to [`professional.md`](professional.md).
