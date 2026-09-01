# Dependency-Breaking Techniques — Senior

Dependency breaking is boundary design under constraints. The right move reduces the cost of the requested change without creating a larger, permanent abstraction problem.

## Map dependency direction

Identify domain rules, orchestration, infrastructure, and external contracts. Move volatile details outward; keep policy inward. An adapter should translate an external model into a model the domain understands, not mirror every vendor method.

## Select a migration strategy

- **Extract and inject:** best for a locally owned dependency.
- **Branch by abstraction:** add an interface, route old and new implementations through it, then migrate gradually.
- **Strangler adapter:** put a stable facade in front of a legacy subsystem while replacing internals.
- **Characterization wrapper:** intercept an unchangeable boundary temporarily to observe and test it.

## Manage risk

Characterize behavior before moving it. Maintain a single source of truth during dual-running. Make failures, retries, transaction boundaries, and ordering explicit; these are common places where an “equivalent” replacement is not equivalent.

## Senior review questions

- Does the new boundary match business ownership and change rate?
- Which consumers depend on undocumented behavior?
- Can old and new paths be compared in production safely?
- What removes the temporary bridge, and when?
