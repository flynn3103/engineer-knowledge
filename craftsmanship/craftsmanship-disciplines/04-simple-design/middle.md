# Simple Design — Middle

## Goal

Use simple design to resist both under-design and speculative abstraction.

## Working rules

- YAGNI: build for the requirement in hand, not imagined variants.
- Prefer two clear copies over one abstraction with unrelated reasons to change.
- Generalize after repeated examples expose stable shared knowledge.
- Treat one-way decisions carefully; a small planned seam can be cheaper than a later migration.

## Review questions

- Does this abstraction remove a real decision or only move code?
- Would deleting it make the current feature harder?
- Is this duplication likely to change together?
