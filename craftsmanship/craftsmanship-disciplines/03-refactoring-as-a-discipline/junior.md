# Refactoring as a Discipline — Junior

## Goal

Improve code structure without changing its observable behavior.

## Rules

- Start with passing tests or another reliable safety check.
- Change one small thing at a time.
- Run tests after each step.
- Keep refactoring separate from adding behavior.

## Useful moves

- Rename misleading names.
- Extract a small function with one purpose.
- Remove duplication after the behavior is clear.
- Inline a variable or wrapper that adds no meaning.

## Practice

1. Choose one confusing name.
2. Rename it with your editor's refactoring tool.
3. Run tests and inspect the diff.
4. Commit the mechanical change separately.
