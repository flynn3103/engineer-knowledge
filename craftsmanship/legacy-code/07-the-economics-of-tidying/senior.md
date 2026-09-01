# The Economics of Tidying — Senior

Senior judgment treats tidying as both a cost-of-change reduction and an option: a small cleanup can preserve the ability to respond cheaply when an uncertain future change arrives.

## Value optionality carefully

A cheap, reversible seam before an imminent integration is a good option: limited downside and substantial potential benefit. A large generalized framework for a hypothetical future is a bad option: high premium, unclear exercise date, and likely lock-in.

## Use portfolio thinking

Invest more in hotspots where change frequency, defect risk, and coupling are high. Invest less in stable, isolated, or retiring code. Combine repository history, incident data, review friction, and roadmap knowledge rather than relying on aesthetics.

## Decision record

For non-trivial cleanup, capture:

- the next changes it enables;
- expected cost and benefit range;
- assumptions and uncertainty;
- rollback or stop condition;
- the metric that will validate the investment.

Avoid false precision. The purpose is to make trade-offs reviewable and to prevent large speculative tidyings from masquerading as small ones.

## Reassess continuously

New roadmap information changes the value. Stop or redirect a cleanup when its expected consumers disappear; accelerate it when repeated delivery delays reveal a hotspot.
