# Refactoring as a Discipline — Senior

## Goal

Change legacy and architectural structures without betting the system on a rewrite.

## Build safety first

- Add characterization tests that record current behavior.
- Find seams around I/O, state, and external systems.
- Add telemetry before moving high-risk traffic.

## Scale the change

- Use a strangler path to replace a subsystem gradually.
- Use branch by abstraction to support old and new implementations.
- Migrate data and clients incrementally; monitor each step.

## Decide honestly

Refactor when behavior can be protected and value arrives in slices. Rewrite only when the existing system blocks every safe path and the replacement has a funded migration plan.
