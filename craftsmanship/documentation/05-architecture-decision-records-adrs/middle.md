# Architecture Decision Records (ADRs) — Middle

## Outcome

Own a local document and make explicit trade-offs. By the end, you can apply this topic in a way that another engineer can trust and act on.

## Core idea

Preserve the context, decision, alternatives, and consequences behind durable technical choices.

## At this level

Compare alternatives, coordinate with direct users, and validate the result in the real workflow.

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

Record a decision when reversing it would be costly or future readers will ask why.

Do not rewrite history; supersede an ADR with a new record when the decision changes.

## Review checklist

- Is the purpose clear in the first few lines?
- Is each instruction current, specific, and safe to perform?
- Are assumptions, permissions, and failure cases visible?
- Can a link, example, or command be verified?
- Is there a named owner or a clear maintenance trigger?

## Practice

Improve one existing page, explain the trade-off you made, and add a check that prevents its most likely failure.

## Remember

Documentation succeeds when it reduces uncertainty at the moment someone needs to act.
