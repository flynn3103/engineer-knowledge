---
name: generating-engineering-knowledge
description: Use when creating or substantially expanding a progressive engineering topic guide, learning module, or knowledge path in this repository.
---

# Generating Engineering Knowledge

Create a four-level learning module that turns engineering theory into decisions and actions. Match the repository's established voice while making each level a genuine progression.

## Establish the target

Identify the topic, output directory, audience, and domain constraints from the request and repository context. Inspect the nearest related topic plus `engineering-thinking/01-computational-thinking/01-decomposition` before drafting.

Ask only for missing information that would materially change the result. Do not overwrite an existing lesson unless the user explicitly authorizes it.

For the required progression and content expectations, read [references/level-structure.md](references/level-structure.md).

## Create the module

Create these files in the target topic directory:

```text
junior.md
middle.md
senior.md
professional.md
```

Treat them as one curriculum:

- Build later levels on concepts already established.
- Increase scope, ambiguity, consequences, and decision responsibility at each level.
- Avoid repeating the same introduction with more jargon.
- Teach when a technique applies, how to perform it, and how to verify the result.

Use realistic engineering situations. Prefer concrete inputs, outputs, constraints, failure behavior, evidence, and trade-offs over generic advice. Add code, commands, configuration, or tables only when they improve application.

Research authoritative primary sources when claims are current, niche, disputed, safety-sensitive, or likely to change. Cite those sources near the supported claims. Never invent citations, benchmarks, incidents, or production results.

## Visualize selectively

Use Mermaid only when it clarifies structure or interaction:

- `flowchart` for workflows, dependencies, decisions, or component relationships.
- `sequenceDiagram` for time-ordered actor or component interactions.

Keep one idea per diagram, normally with no more than 5–8 meaningful nodes or participants. Use descriptive labels and explain the takeaway in nearby prose. Replace an overloaded diagram with multiple small diagrams, a table, or a list. Do not require a diagram in every file.

## Review before completion

Confirm that:

- All four files exist and match nearby Markdown conventions.
- Each level adds new capability and decision depth.
- Advice is actionable and includes observable verification.
- Examples expose relevant dependencies and failure modes.
- Mermaid uses only the allowed diagram types and remains compact.
- The final section contains only a plain list of comprehension questions; it has no answer text or disclosure markup.
- Claims are accurate and sourced where freshness or risk requires it.
- No unrelated or unauthorized files changed.
