# Tokens and Context — Professional

<!-- level-focus -->
At professional level, focus on this question:

> Can you set token-budget and caching standards for a team — and make token growth a regression that gets caught, not a bill that gets explained?

---

## Token budgets per feature

- Assign every feature an explicit token budget: max input per call, max output, max tokens per task (summed across a multi-call workflow).
- Budgets force the design conversation early: a feature whose budget doesn't close must retrieve, summarize, or compact — not silently exceed (see [Compaction and Memory](../../context-management/compaction-and-memory/)).
- Publish budgets where designs happen (design docs, PR templates), not in someone's head.

## Cache-aware prompt design as a standard

- Make the ordering rule org-wide: **static prefix first, volatile last**, byte-identical prefixes, no timestamps or per-request noise injected mid-prefix.
- Track cache-hit rate as a first-class metric — a drop in hit rate is a regression someone shipped, visible before the invoice confirms it.
- Standardize which components are cacheable (system prompt, tool definitions, static docs) and which never are (user input, fresh retrieval results).

## Token growth as a tracked regression

- Record input/output tokens per call in traces (see [Tracing and Observability](../../agent-evaluation/tracing-and-observability/)).
- Add token totals to the eval pipeline: a prompt change that inflates tokens per call fails review like a correctness regression — because at volume, it is one.
- Alert on trend, not just absolute: gradual growth across many small edits is the common shape of token bloat.

## The org-level bill

- Aggregate spend by feature/team/tenant (see [Cost and Performance](../../agent-evaluation/cost-and-performance/)) so accountability lands with the people who can act on it.
- Review budget-vs-actual monthly; a widening gap means either volume shifted or per-call tokens grew — the traces tell you which.

## Common Mistakes

- **Budgets as guidance instead of gates.** "Try to keep it small" produces exactly the slow bloat budgets exist to prevent.
- **Optimizing tokens while ignoring cache-hit rate.** A prompt refactor that saves 100 tokens but breaks caching loses money.
- **Catching token growth from the invoice.** Weeks late and attributed to nobody; catch it in CI instead.
- **Per-team prompt conventions.** Every team re-learns cache rules and budget discipline; write it once as standard.

## Apply It

1. Write the token-budget standard: per-call maxima, per-task maxima, and where budgets must appear in design docs.
2. Adopt the cache-ordering rule org-wide and add cache-hit rate to your dashboards.
3. Add per-call token totals to traces and token deltas to your eval pipeline's review bar.
4. Set up spend aggregation by feature/team and a monthly budget-vs-actual review.

## Verify Your Work

- Every feature has numeric token budgets visible in its design artifacts.
- Cache-hit rate is tracked, and its drop is treated as a regression.
- Token totals are in traces and token growth blocks review like a correctness failure.
- Spend is attributable to feature/team without manual archaeology.

## Review Questions

- Why must a token budget be a gate rather than guidance?
- Why can a small per-call token saving be a net loss after a refactor?
- What makes token growth a *regression* rather than an invoice surprise?
