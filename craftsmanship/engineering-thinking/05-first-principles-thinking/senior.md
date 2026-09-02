# First-Principles Thinking — Senior

Senior practice challenges premises embedded in architecture, process, and ownership.

Trace a rule to its original condition. “All writes require one central service” may come from an old audit requirement that now permits signed decentralized events. Removing the premise can eliminate an entire bottleneck.

Model transition constraints separately from destination constraints. Use a reversible slice, compatibility contract, observable shadow path, and rollback. A clean-sheet design that ignores migration is not an engineering solution.

## Test yourself

1. Which current rule may be historical rather than fundamental?
2. How do destination and transition constraints differ?
3. What protects invariants during a premise-changing migration?
4. Which evidence would stop the redesign?

Continue to [`professional.md`](professional.md).
