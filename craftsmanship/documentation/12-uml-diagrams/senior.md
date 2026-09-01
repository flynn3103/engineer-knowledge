# UML Diagrams — Senior

## Outcome

Shape documentation at a system boundary where mistakes have wider cost. By the end, you can apply this topic in a way that another engineer can trust and act on.

## Core idea

Use UML selectively to communicate structure, interactions, state, or deployment decisions precisely.

## At this level

Define ownership, sources of truth, and failure handling across teams or services.

## Practical workflow

1. Identify the reader, their task, and the decision they must make.
2. Write the minimum accurate information that unblocks that task.
3. Link to the authoritative source instead of duplicating volatile facts.
4. Ask a real reader to follow it; fix the first point of confusion.
5. Update, automate, archive, or delete the page when the system changes.

## What good looks like

- A reader can find the answer quickly and knows its scope.
- Facts have an owner or an observable source of truth.
- Examples use realistic names, safe defaults, and expected outcomes.
- The page names risks, limits, and the next escalation path when relevant.

## Topic focus

Pick the diagram type that matches the question, keep notation consistent, and explain assumptions.

Do not model every class or let formal notation obscure the decision the reader needs to make.

## Review checklist

- Is the purpose clear in the first few lines?
- Is each instruction current, specific, and safe to perform?
- Are assumptions, permissions, and failure cases visible?
- Can a link, example, or command be verified?
- Is there a named owner or a clear maintenance trigger?

## Practice

Design a lightweight standard for a recurring decision, then test it during a change or incident.

## Remember

Documentation succeeds when it reduces uncertainty at the moment someone needs to act.
