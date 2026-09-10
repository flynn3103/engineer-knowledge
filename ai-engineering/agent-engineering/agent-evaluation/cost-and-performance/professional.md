# Cost and Performance — Professional

<!-- level-focus -->
At professional level, focus on this question:

> Can you defend or kill an agent based on its unit economics — with chargeback, forecasting, and a cost SLO that turns "it's expensive" into a decision instead of a complaint?

---

## Chargeback and showback

- **Chargeback**: allocate actual agent cost to the team or business unit that generates it, so the cost shows up on their budget, not as an unexplained shared-infrastructure line item.
- **Showback**: report cost per team/tenant without actually billing them for it — a lighter-weight step toward accountability when full chargeback isn't yet feasible.
- Either requires the per-run cost attribution from [Middle](middle.md) to be reliable at the team/tenant level, not just the agent level.

## Forecast vs. actual

- Forecast expected cost based on projected traffic growth and current cost-per-task, and track actual spend against that forecast monthly — a growing gap between forecast and actual (actual running consistently above forecast) is an early signal that something changed: traffic mix shifted toward more expensive cases, a model price increased, or a regression inflated token usage per run (see [Senior](senior.md) on CI cost regressions).

## Provisioned-throughput commitments

- At sufficient volume, providers often offer provisioned/reserved throughput at a different price structure than pay-as-you-go — evaluate whether committed volume justifies the discount against the risk of over-committing to throughput you don't end up using.

## Cost SLOs and anomaly alerting

- Set a cost SLO (e.g., "cost per resolved ticket stays within X, month over month") the same way you'd set a latency or availability SLO, with an alert when actual cost deviates significantly from the trend — not just a monthly finance review that catches a problem weeks after it started.

## Negotiating quality bar vs. margin

- A quality bar set without regard to cost (see [Evaluation Fundamentals — Professional](../../evaluation-fundamentals/professional.md)) can make an agent economically unviable even if it technically meets the bar — this is a genuine negotiation between the quality-owning team and whoever owns the cost/margin target, not something either side should decide unilaterally.

## Retiring agents whose economics never close

- Not every agent idea is worth running long-term. If cost per resolved task, after reasonable optimization (see [Middle](middle.md) and [Senior](senior.md)), still exceeds the value of what it resolves (e.g., more expensive than a human handling the same ticket type), that's a legitimate signal to retire or scope down the agent, not just a per-quarter cost-cutting exercise to repeat forever.

## Common Mistakes

- **No team/tenant-level cost attribution.** Makes chargeback or showback impossible, and no team feels ownership over the cost it drives.
- **No forecast-vs-actual tracking.** A cost regression is discovered from a surprising bill instead of a trend that was visible weeks earlier.
- **Setting a quality bar without involving whoever owns the cost/margin target.** Produces a bar that's technically correct but makes the agent unprofitable to run.
- **Never considering retirement as an option.** Keeps optimizing an agent whose fundamental economics don't work, when the actual answer is to stop running it.

## Apply It

1. Set up per-team or per-tenant cost attribution for at least one shared agent, and decide whether chargeback or showback fits your organization's stage.
2. Build a forecast for one agent's monthly cost based on current cost-per-task and projected traffic, and compare it against actual spend next month.
3. Set one cost SLO with an anomaly alert, not just a scheduled finance review.
4. For your least cost-effective agent, calculate whether its cost per resolved task, after reasonable optimization, is actually below the value of what it resolves — and make an explicit keep/retire recommendation based on that number.

## Verify Your Work

- Cost is attributed at the team/tenant level, not only at the aggregate agent level.
- A forecast-vs-actual comparison exists and is reviewed on a regular cadence, not only when a bill surprises someone.
- At least one cost SLO exists with an anomaly alert.
- A keep/retire decision for at least one agent is backed by an explicit cost-per-resolved-task-vs-value calculation.

## Review Questions

- Why does per-team cost attribution matter for accountability, beyond just knowing the aggregate number?
- Why is a forecast-vs-actual gap a more useful early signal than a monthly bill review?
- What's the actual criterion for deciding to retire an agent rather than keep optimizing it?
