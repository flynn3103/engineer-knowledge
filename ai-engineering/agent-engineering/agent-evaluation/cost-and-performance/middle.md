# Cost and Performance — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Can you measure cost per resolved task instead of cost per call, and name the biggest lever to bring it down?

---

## Unit economics: cost per outcome

- Cost per API call is the wrong unit for a business decision — it doesn't account for a cheap model needing 3 retries to succeed, or an expensive model succeeding first try.
- **Cost per resolved task** (e.g., cost per support ticket successfully closed without human escalation) is the unit that actually maps to business value: sum every run's cost for that task, including retries and any escalated human-handling cost, divided by tasks successfully resolved.

## Attribution per step/tool/sub-agent

- Break total cost down by which step, tool, or sub-agent consumed it — a fan-out pattern (see [Orchestration and Delegation](../../agent-workflow/orchestration-and-delegation/)) that calls three sub-agents in parallel needs cost attributed to each sub-agent separately, not lumped into one number, so you know which one to optimize.

## The biggest levers

- **Context size**: the single largest lever in most agents — a bloated system prompt, an ever-growing conversation history, or a tool result dumped in full when only a summary was needed all inflate input-token cost on every single call. See [Compaction and Memory](../../context-management/compaction-and-memory/).
- **Retries**: a step that fails and retries pays for the failed attempt's tokens too — a high retry rate silently multiplies cost without multiplying successful outcomes.
- **Oversized tool outputs**: a tool that returns a full database record when the agent only needs two fields wastes input tokens on every step that includes that result in context afterward.
- **Model tier**: using a large, expensive model for every step when a smaller model would resolve simpler steps (e.g., routing/classification) just as well.
- **Unnecessary steps**: extra reasoning or verification steps that don't change the outcome add cost without adding value — see step-count checks in [Junior](junior.md).

## Prompt caching and batch pricing

- **Prompt caching**: if a fixed prefix (system prompt, tool definitions) repeats across many calls, caching that prefix cuts its cost on every call after the first — worth confirming your provider's caching actually applies to your specific call pattern.
- **Batch pricing**: for non-interactive, non-latency-sensitive work (e.g., bulk reprocessing, offline eval runs), providers commonly offer discounted batch-processing pricing versus real-time API pricing — check whether your workload qualifies before paying real-time rates for something that doesn't need real-time latency.

## Pricing the quality cost of a cheaper model

- Before switching to a cheaper model to cut cost, run it against your eval suite (see [Datasets and Graders](../../datasets-and-graders/)) and compare pass rate against the current model — a 40% cost reduction that also drops pass rate by 10 points may cost more overall once you account for the resulting human escalations or bad outcomes.

## Common Mistakes

- **Reporting cost per API call as if it were the business-relevant number.** Hides the real cost difference between a model that needs retries and one that doesn't.
- **One aggregate cost number with no per-step/tool attribution.** Can't tell you which specific part of the agent to optimize.
- **Switching to a cheaper model without checking eval pass rate first.** Can trade a visible cost saving for an invisible quality regression that costs more in downstream escalations.
- **Ignoring context size as a lever.** Often the single biggest cost driver, and the easiest one to reduce without touching model choice at all.

## Apply It

1. Compute cost per resolved task for one agent, including any retry cost and human-escalation cost for failed automated resolutions.
2. Break total cost down by step/tool/sub-agent and identify the largest single contributor.
3. Before proposing any model downgrade for cost, run it against the eval suite and report the pass-rate delta alongside the cost delta.

## Verify Your Work

- Cost is reported per resolved task, not only per API call.
- Cost is attributed per step/tool/sub-agent, not only as one aggregate number.
- Any model-tier change proposal includes both a cost delta and an eval pass-rate delta.

## Review Questions

- Why is cost per resolved task a better unit than cost per API call?
- Name the biggest cost lever in most agents, and why it's usually the first place to look.
- Why should a cheaper model always be checked against the eval suite before being adopted for cost savings?
