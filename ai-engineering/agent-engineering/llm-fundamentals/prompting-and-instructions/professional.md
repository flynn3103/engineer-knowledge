# Prompting and Instructions — Professional

<!-- level-focus -->
At professional level, focus on this question:

> Can you treat instruction files as a governed team asset — owned, reviewed, measured for effect, and defended against drift and bloat?

---

## Instructions are infrastructure

- Across a team, standing files shape every agent interaction — thousands of calls a week inherit whatever they say. That's infrastructure: it needs an owner, a review process, and quality bars, like any shared system.
- Unowned instruction files drift into folklore: a mix of current truth, stale rules, and one person's preferences — all paid for on every call.

## Ownership and review

- Named owner per standing file (AGENTS.md, CLAUDE.md, shared skill library) — the person who merges changes and prunes dead rules.
- Review trigger: any PR that changes what the file describes (build tooling, conventions, layout, model choice) reviews the file in the same PR. The file follows reality; reality doesn't discover the file later.
- Skills and shared prompt libraries get the same treatment as code: versioned, reviewed, tested before merge.

## Measuring whether a rule works

- The professional question about any standing rule: *did it change behavior?* Testable via the eval loop:
  - Run a task set with and without the rule (the bake-off from [Choosing and Tuning — Middle](../choosing-and-tuning/middle.md)); a rule that doesn't move its target metric is dead weight — costing tokens and attention on every call.
  - For compliance-type rules (commit format, test commands), sample real agent outputs periodically and rate adherence — that's the rule's actual effect in production, not its effect in the author's demo.
- Retirement is the default outcome for unmeasured rules: if nobody can say what a rule improves, it's a candidate for deletion.

## Fighting the two failure modes

- **Bloat**: rules accumulate (each incident adds one; none are ever removed). Countermeasures: hard length caps enforced in review, a "one in, one out" norm, and periodic pruning sprints with adherence data as the evidence for what stays.
- **Drift**: rules stop matching reality (renamed commands, moved directories, changed conventions). Countermeasures: the PR-review trigger above, plus a scheduled audit — have an agent (or a person) *execute* the file's commands and flag what breaks.
- Both failure modes compound each other: stale files grow because rules nobody trusts are easier to add than to clean.

## Cross-team standards

- Standardize the *shape*: a common template (build commands, conventions, gotchas, review checklist), length caps, and the verifiability bar from [Senior](senior.md) — so every team's file is parseable by humans and agents alike.
- Share skills via a common library rather than per-repo copies — a tested skill in one place beats five diverging copies.
- Track the org-level metrics: file lengths, adherence rates on sampled rules, count of rules with no measured effect. What's visible gets maintained.

## Common Mistakes

- **No named owner.** Every edit is drive-by; nothing is ever pruned; the file becomes an archive of every argument the team has had.
- **Files reviewed only at creation.** Reality moves, the file doesn't, and the model is confidently misdirected on every call.
- **Rules adopted without measurement.** The cost is certain (tokens, attention on every call); the benefit is assumed.
- **Per-repo skill copies.** Five versions of the same skill diverge silently; fixes land in one and never propagate.

## Apply It

1. Assign a named owner to each standing instruction file in your team's repos.
2. Add the PR-review trigger to the team's definition of done for build/convention changes.
3. Measure one rule: run the with/without eval, or sample production outputs for adherence — and make the keep/retire call from the number.
4. Run one pruning pass with length cap and adherence data; delete what neither earns.
5. Stand up (or adopt) a shared skill library with versioning.

## Verify Your Work

- Every standing file has an owner and lands in reviews of the changes it describes.
- At least one rule's effect has been measured, and unmeasured rules are flagged for audit.
- File length is capped and adherence is sampled periodically.
- Shared skills exist in one versioned place, not per-repo copies.

## Review Questions

- Why is an instruction file infrastructure rather than documentation, concretely?
- What measurement retires a standing rule, and what's the default for unmeasured ones?
- How do bloat and drift compound each other, and what breaks the cycle?
