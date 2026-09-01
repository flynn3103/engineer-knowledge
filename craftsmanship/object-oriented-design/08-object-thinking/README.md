# Object Thinking

## Purpose

This roadmap turns object-oriented design ideas into decisions you can use during implementation, review, and refactoring. Work through topics in order when the area is new; otherwise start with the design pressure you are seeing.

## Topics

| Topic | Use it when |
| --- | --- |
| [Behavior-First Mindset](01-behavior-first-mindset/junior.md) | You see callers manipulate fields and coordinate rules themselves. |
| [Anthropomorphism](02-anthropomorphism/junior.md) | You see nouns become passive records and verbs become giant services. |
| [Tell, Don’t Ask](03-tell-dont-ask/junior.md) | You see getters feed conditional logic in distant callers. |
| [Responsibility-Driven Design](04-responsibility-driven-design/junior.md) | You see classes are named by data or framework role rather than a reason to act. |
| [CRC Cards Technique](05-crc-cards-technique/junior.md) | You see a design is hard to explain or one card owns every scenario. |
| [Domain Modeling from Requirements](06-domain-modeling-from-requirements/junior.md) | You see requirements map directly to tables, endpoints, or CRUD handlers. |
| [When Object Thinking Fails](07-when-object-thinking-fails/junior.md) | You see tiny transformations acquire layers, factories, and speculative hierarchies. |

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
