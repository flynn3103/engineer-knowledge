# Object-Oriented Design — Professional

Smalltalk’s message-passing model, Java’s nominal interfaces and virtual dispatch, and actor systems such as Akka embody different object boundaries and failure assumptions. Domain-driven design adds bounded contexts because one universal model becomes politically and semantically coupled.

At scale, shared domain libraries and inheritance frameworks become coordination bottlenecks. Track change propagation, dependency cycles, unstable interfaces, ownership concentration, and defect hotspots. Favor contracts and context boundaries over enterprise-wide class hierarchies.

## Design and operations checklist

1. Name invariants and responsible owners.
2. Keep strong connascence inside a boundary.
3. Validate substitution with behavioral contracts.
4. Make concurrency and lifecycle explicit.
5. Evolve public object APIs compatibly.
6. Measure change cost before introducing frameworks.

```text
DOMAIN RULE -> RESPONSIBILITY -> COHESIVE OBJECT -> MESSAGE -> COLLABORATOR
                  invariants + ownership + substitutable contracts
```

## Test yourself

1. How would you split a shared enterprise domain model?
2. Which contract tests prove substitutability?
3. When does an actor boundary improve object safety?
4. How do you measure whether an OO framework reduces change cost?

## Further reading

- Rebecca Wirfs-Brock, *Object Design*.
- Eric Evans, *Domain-Driven Design*.
- Sandi Metz, *Practical Object-Oriented Design*.
- Gamma et al., *Design Patterns*.
