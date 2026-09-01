# OO Design and Modeling

## Purpose

This roadmap turns object-oriented design ideas into decisions you can use during implementation, review, and refactoring. Work through topics in order when the area is new; otherwise start with the design pressure you are seeing.

## Topics

| Topic | Use it when |
| --- | --- |
| [GRASP Responsibility Assignment](01-grasp-responsibility-assignment/junior.md) | You see a controller coordinates everything or a class depends on information it does not own. |
| [OO Metrics: CK Suite](02-oo-metrics-ck-suite/junior.md) | You see high complexity, coupling, inheritance depth, or response surface hides change risk. |
| [Thread-Safe Object Design](03-thread-safe-object-design/junior.md) | You see mutable shared fields, check-then-act logic, and leaking internal collections. |
| [Designing for Extension and Polymorphism](04-designing-for-extension-and-polymorphism/junior.md) | You see conditionals grow for types, subclasses violate contracts, or extension leaks internals. |

## Learning path

- **Junior:** recognize the concern and make one safe local improvement.
- **Middle:** explain a component-level design trade-off.
- **Senior:** manage boundaries, migration, and system risk.
- **Professional:** establish team practices and measure outcomes.

## How to study

1. Pick a real change, not a hypothetical class diagram.
2. Read the level that matches the scope you own.
3. Use the “Practical move” as a review or pairing prompt.
4. Capture evidence from code, tests, and change history before declaring success.
