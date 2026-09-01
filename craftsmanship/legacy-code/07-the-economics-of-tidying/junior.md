# The Economics of Tidying — Junior

Tidying is an investment: spend a little effort now to make later changes cheaper. It is worthwhile when the likely saving is larger than the cost.

## Ask two questions

1. Will this code be changed again soon?
2. Will a small cleanup make that change noticeably easier or safer?

If both answers are yes, a small tidy is usually sensible. If the work is speculative or the cleanup is large, leave it alone until there is a real need.

```text
cost now:       10 minutes to name and extract a confusing rule
saving later:   15 minutes avoided on each of two planned changes
result:         likely worth doing
```

## What counts as a good investment

- A tiny, reversible change.
- A code area you are about to touch repeatedly.
- A cleanup that removes a known source of mistakes.
- A change protected by tests or easy observation.

Tidying is not a reward for making code pretty. Its payoff is lower future change cost. Make the requested behavior change when that payoff is uncertain.
