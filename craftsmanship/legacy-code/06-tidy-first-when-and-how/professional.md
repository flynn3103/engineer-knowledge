# Tidy First — When and How — Professional

Team-scale tidying succeeds when structure changes are cheap to trust: small, reviewable, tested, and unlikely to create conflict.

## Team operating rules

- Label structure-only changes clearly, for example `tidy:`.
- Keep behavior changes and tidyings in separate commits or pull requests.
- Require the same automated checks used for production changes.
- Prefer small changes in files already being modified; avoid broad formatting churn.
- Record the expected payoff when a tidy exceeds a few minutes.

## Review a tidy differently

Reviewers ask whether behavior is preserved and whether the new structure makes the next change clearer. They should not require an unrelated redesign. Authors should provide the before/after intent, tests run, and any assumption that could affect behavior.

## Balance throughput

Use a short, bounded tidy within planned feature work when it reduces near-term delivery risk. Escalate larger work into a planned investment with owner, scope, milestones, and stop condition. Resolve conflicts by optimizing the team’s flow, not one engineer’s local ideal.

## Signals to monitor

- Review time and rework for structure-only changes.
- Merge-conflict rate in frequently tidied areas.
- Cycle time for repeated changes in a hotspot.
- Defects or rollbacks attributed to “refactors.”

If tidy labels become a way to hide behavior changes, stop and restore trust through smaller, better-evidenced changes.
