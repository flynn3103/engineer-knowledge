# Context Fundamentals — Professional

<!-- level-focus -->
At professional level, focus on this question:

> Can you set organization-wide policy for context budgets and prompt-cache economics across many agents and teams — so no single team's design choice silently inflates everyone's inference bill?

---

## Context cost is an infrastructure line item, not a per-agent detail

Once an org runs dozens of agents, unmanaged context growth becomes a budget problem, not a UX detail:

- **Cost attribution.** Every agent's per-turn token count should be measurable and attributable to a team/product, the same way cloud spend is tagged. A single agent silently including a 15k-token schema for a tool it rarely calls is invisible in a demo and expensive at 1M calls/day.
- **Cache-hit rate as a KPI.** If prompt caching cuts cost 5-10x on cached tokens, an org-wide metric on "% of tokens served from cache" turns prefix stability (see the middle level) from a nice-to-have into a monitored number teams are accountable for.
- **Context budget review as part of launch review.** Before a new agent ships, require its context-assembly design to state its per-category budget and expected steady-state fill — the same way a service states its expected QPS and memory footprint before a production launch.

## Org-wide policy to set

| Policy | What it prevents |
|---|---|
| Max tool schemas per agent (audited quarterly) | Schema bloat accumulating unnoticed as tools get added and never removed. |
| Standard truncation/compaction library, not per-team reinvention | Every team hand-rolling its own (differently buggy) truncation logic. |
| Required token-budget section in agent design docs | Context cost discovered only after a production incident or a surprise bill. |
| Shared eval harness for context-fill degradation (see senior level) | Teams shipping context changes with no regression signal. |
| Prefix-stability lint/review for new system prompts | Volatile content in the cached prefix silently destroying cache hit rate org-wide. |

## The trade-off this level actually owns

More context budget generally buys better recall and fewer follow-up turns, at higher cost and latency and higher context-rot risk. This is a genuine trade-off, not a solved problem — the professional-level job is making that trade-off **visible and chosen**, not defaulting to "give it the biggest window available" or "cap it arbitrarily to save money" without evidence either way.

- Require: for any request to raise a context budget, the requesting team shows the eval-set evidence (senior level) that the current budget is actually limiting quality, not just "we'd feel safer with more room."
- Require: for any cost-cutting truncation policy, evidence it doesn't regress the accuracy eval before it ships broadly.

## Comprehension check

- Why does a per-agent context budget become an org-level concern once there are dozens of agents in production?
- Name two org-wide policies that reduce the risk of one team's context design decision inflating cost for everyone.
- What evidence should be required before approving a request to raise an agent's context budget?
- How does treating cache hit rate as a monitored KPI change how teams write system prompts?
