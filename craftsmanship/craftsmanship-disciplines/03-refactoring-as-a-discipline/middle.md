# Refactoring as a Discipline — Middle

## Goal

Turn code smells into safe, reviewable changes.

## A practical sequence

1. Name the smell: duplication, long method, unclear branch, or awkward dependency.
2. Pick the smallest matching refactoring.
3. Keep the suite green after every move.
4. Stop when the next change would alter behavior.

## Prepare change safely

- Introduce a new interface or parameter before removing the old path.
- Use automated rename and extract tools; inspect every generated diff.
- Commit cleanup separately from feature work.
- With a slow suite, run focused checks frequently and the full suite before merge.
