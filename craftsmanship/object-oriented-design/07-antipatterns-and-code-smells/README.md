# Antipatterns and Code Smells

## Purpose

This roadmap turns object-oriented design ideas into decisions you can use during implementation, review, and refactoring. Work through topics in order when the area is new; otherwise start with the design pressure you are seeing.

## Topics

| Topic | Use it when |
| --- | --- |
| [God Class](01-god-class/junior.md) | You see large constructors, many reasons to change, broad tests, and frequent merge conflicts. |
| [Anemic Domain Model](02-anemic-domain-model/junior.md) | You see getters/setters everywhere, procedural service methods, and invalid state assembled in callers. |
| [Feature Envy](03-feature-envy/junior.md) | You see long navigation chains and repeated queries against one collaborator. |
| [Refused Bequest](04-refused-bequest/junior.md) | You see overridden methods that reject work, unused inherited members, and type checks around subclasses. |
| [Inappropriate Intimacy](05-inappropriate-intimacy/junior.md) | You see paired edits, direct state manipulation, and helpers exposing private decisions. |
| [Shotgun Surgery](06-shotgun-surgery/junior.md) | You see similar changes across files, duplicated rules, and coordination-heavy releases. |
| [Yo-Yo Problem](07-yo-yo-problem/junior.md) | You see methods delegating through ancestors, fragile overrides, and unclear ownership. |
| [Data Clumps](08-data-clumps/junior.md) | You see repeated parameter groups, parallel fields, and duplicated validation. |
| [Primitive Obsession](09-primitive-obsession/junior.md) | You see format checks scattered across callers, magic values, and invalid combinations. |

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
