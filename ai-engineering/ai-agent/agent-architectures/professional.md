# Agent Architectures — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run agent architecture as a durable, org-wide operating model — shared scaffolding, a real rubric for when multi-agent orchestration is justified versus overengineering, and clear accountability for cost and reliability — so every team ships loops with the same baseline safeguards without a central team reviewing every agent?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Ownership Aligned to Cognitive Load

The predictable failure mode: a central AI-platform team tries to personally review and approve every team's agent design, and becomes a bottleneck the moment more than a handful of teams are shipping agents. The split that scales distributes ownership by who actually has the context to sustain each decision:

| Layer | Owner | Responsibility |
|---|---|---|
| **Shared agent scaffolding** (loop implementation, iteration caps, repeated-call detection, memory-store client, observability hooks) | Platform/AI-infra team | Build and maintain the loop primitives once, correctly, so no team hand-rolls its own iteration cap or discovers context exhaustion the hard way |
| **Domain-specific tools, prompts, and sub-agent design** | The team that owns the product surface | Everything above the scaffold — their own tool set, their own system prompts, their own decision on single- vs. multi-agent for their domain |
| **Multi-agent justification rubric and cost/reliability standards** | A governance group spanning platform and the product teams that use it most | Defines the objective criteria for when a split is justified (Core Concept 3) and the SLOs every agent-driven workflow is accountable to |
| **Cost and incident accountability** | The owning product team, against org-wide SLOs | Each team owns its own agent's cost-per-task and reliability against a shared bar, not a central team owning every team's numbers |

This mirrors how a platform team owns a shared container base image while each service team owns its own Dockerfile layers on top of it: the primitive is centralized because getting it wrong is expensive and repetitive to rediscover; the domain logic is decentralized because no central team can sustain understanding every product's specific needs.

## Core Concept 2 — Shared Scaffolding as a Paved Road

A shared agent framework exists so the loop, its safeguards, and its observability are implemented once rather than reinvented — with bugs — by every team. This is not a hypothetical: real frameworks exist specifically to provide this scaffolding, such as LangGraph for building and running agent loops as explicit graphs, or an equivalent internal framework built on top of a model provider's native tool-calling API. The paved road provides, out of the box:

- A loop runner with a configurable but *mandatory* iteration cap and repeated-identical-call detection (Core Concept 4 of the senior guide), so no team ships an agent with no upper bound at all.
- A memory-store client with the persist/discard split already modeled, so teams plug in their own summarization logic without re-deriving the short-term/long-term distinction from scratch.
- Standard tracing: every Thought, Action, and Observation logged with enough structure that an incident review doesn't start with "does anyone have a transcript of what happened."

A paved road only earns adoption if it's genuinely easier than building an ad hoc loop — versioned, documented, with a working example a new team can fork in under a day. If the shared scaffold is harder to use than rolling a bespoke loop, teams will route around it, and the org loses the one lever it has for consistent baseline safety.

## Core Concept 3 — A Rubric for Multi-Agent, Not a Vibe

The middle-level decision rule (tool count, task structure, ownership) works for one team deciding about one system. At org scale, the risk flips: multi-agent orchestration becomes the *default* choice because it looks more sophisticated on an architecture diagram, regardless of whether any team's actual signals justify it. A governance rubric makes the bar explicit and checkable before a new orchestrator is approved to ship:

```yaml
multi_agent_justification_checklist:
  - non_overlapping_tool_domains: "Can you name two or more tool sets with no shared tool, each independently useful?"
  - measured_routing_target: "What routing accuracy will you validate against a labeled test set before launch, and what's the minimum acceptable number?"
  - cost_budget_signoff: "What's the per-request call-count increase versus a single-agent baseline, and has the owning team accepted that cost?"
  - ownership_boundary: "Which team owns each sub-agent, and is there a written boundary for tools no sub-agent shares?"
```

A team that cannot answer all four concretely has not justified a split — it has proposed one. This isn't bureaucracy for its own sake; each question maps directly to a failure mode the middle-level guide already named (tool-selection confusion, misrouting cost, duplicate ownership of a high-stakes tool).

## Core Concept 4 — Cost and Reliability Accountability

Every agent-driven workflow in production needs an explicit, owned SLO — not a general expectation that "the agent should work well":

- **Task success rate** — the fraction of runs that reach a correct Final Answer without human escalation, measured against a held-out evaluation set (see [AI Evaluation](../../ai-evaluation/) for the measurement methodology itself).
- **Cost per resolved task** — total LLM and tool spend divided by successfully resolved tasks, tracked as a trend, not a one-time snapshot.
- **Escalation rate to humans** — how often a safeguard or a stuck loop forces a handoff; a rising trend here is often the first visible symptom of a scaffolding regression or a tool that started returning malformed data upstream.

The owning product team is accountable for these numbers against an org-wide floor; the platform team is accountable for the scaffolding not being the *cause* of a regression (e.g., a shared iteration-cap default that's too aggressive for a legitimately multi-step task). When a metric degrades, the first diagnostic question is which layer changed — the team's own prompt/tools, or the shared scaffold underneath everyone.

## Core Concept 5 — Rollout Decomposition

Mandating "every team migrates to the shared scaffold by end of quarter" produces the same theater any infrastructure mandate produces. Decompose instead:

1. **Pilot with one team already fighting a real problem** — a team whose bespoke loop has no iteration cap and has already had a runaway-cost incident is a motivated, concrete first adopter.
2. **Extract the scaffold's actual shape from what the pilot needed**, not from a committee's guess at every team's future requirements.
3. **Publish the multi-agent rubric as advisory first**, surfacing how many existing orchestrators in the fleet would fail it today, before it blocks any new design.
4. **Turn the rubric blocking for new orchestrators only**, with existing non-compliant ones getting a scheduled review rather than an overnight redesign requirement.
5. **Expand adoption team by team**, tracking it as a fraction of agents on the shared scaffold, not a binary migrated/not-migrated status.

## Core Concept 6 — Outcome Measures and Exit Conditions

```yaml
program_health:
  scaffold_adoption: "agents built on the shared scaffold / total production agents"
  safeguard_incident_rate: "runaway-loop or cost-blowout incidents per quarter, trending down"
  rubric_pass_rate: "new multi-agent proposals passing the justification checklist on first submission"
  median_task_success_rate: "across all production agents, tracked quarterly"
exit_conditions:
  pilot_to_expansion: "pilot team's safeguard incidents drop to zero for one full quarter after adopting the scaffold, and the platform team can update scaffold defaults without the pilot team's direct involvement"
  program_maturity: "scaffold_adoption > 80% of production agents, and safeguard_incident_rate trending down for two consecutive quarters"
```

`safeguard_incident_rate` is the number that actually proves the program is working — high scaffold adoption with incidents still happening means the scaffold's defaults are wrong or being bypassed, not that governance succeeded.

## Core Concept 7 — Cross-Team Contracts and Sustained Delivery

- The shared scaffold publishes a support contract like any internal platform dependency: current major version, deprecated versions still patched, and an end-of-support date, so teams plan upgrades rather than get surprised by one.
- A breaking change to scaffold defaults (tightening the default iteration cap, changing the memory-store interface) goes through the same advance-notice change process as a breaking API change, because for a team that tuned their agent against the old default, it functionally is one.
- New agents onboard onto the shared scaffold by default, not as an opt-in retrofit only applied after an incident — the paved road should be the path of least resistance for a brand-new agent from day one.
- A recurring program review (quarterly is typical) asks explicitly: is the safeguard-incident rate actually falling, and if not, is the bottleneck scaffold defaults, rubric enforcement, or teams routing around both?

---

## Real-World Examples

- **A runaway-cost incident funds scaffold adoption.** A team's bespoke agent loop has no cost ceiling; a malformed input sends it into hundreds of tool calls against a paid API before anyone notices. Migrating to the shared scaffold's mandatory cost ceiling becomes the concrete, demonstrated justification for expanding adoption beyond that one team, rather than a mandate imposed on faith.
- **A rubric catches a proposed split with no real justification.** A team proposes an orchestrator with three sub-agents whose tool sets substantially overlap; walking through the justification checklist surfaces that the "domains" aren't actually non-overlapping, and the team ships a single agent with a slightly larger tool set instead — at a fraction of the call-count cost.
- **High adoption, incidents still happening.** An org reaches 85% scaffold adoption but safeguard incidents haven't dropped, because teams are adopting the scaffold's loop runner while overriding its default iteration cap to a much higher number to "avoid false escalations." The next quarter's focus shifts from adoption outreach to auditing default overrides.

## Common Mistakes

- **Centralizing every agent design review in one platform team.** That team cannot sustain reviewing every product team's domain-specific tool and prompt decisions; the queue becomes the actual bottleneck.
- **Treating multi-agent orchestration as inherently more mature or robust.** Without the rubric, it becomes the default choice for the wrong reason — it looks sophisticated — while quietly adding cost and a misrouting failure mode most single-agent systems never had.
- **Rolling out the rubric as blocking for the entire existing fleet at once.** Breaks or stalls teams' in-flight work over a standard that postdates their design; gate new orchestrators first, review the existing fleet on a scheduled cadence.
- **Measuring only scaffold adoption, never safeguard-incident rate.** High adoption with unchanged incident rates looks like program success on a dashboard while delivering none of the actual reliability benefit the program exists to produce.
- **Leaving scaffold defaults silently overridable with no audit trail.** A team quietly raising its iteration cap or disabling the repeated-call detector defeats the entire point of a shared safety baseline, and nobody finds out until an incident.

---

## Apply It

1. Inventory the agents currently running in production across teams you have visibility into, and classify each as single-agent or multi-agent, on shared scaffolding or bespoke.
2. Run the multi-agent justification rubric (Core Concept 3) retroactively against one existing multi-agent system, and identify which checklist items it would fail today.
3. Define the outcome measures from Core Concept 6 for your org specifically, and write the concrete exit condition that would justify expanding scaffold adoption beyond a pilot team.
4. Draft a one-page support contract for your shared scaffold: current version, deprecation timeline for defaults you intend to tighten, and who teams contact about a breaking change.
5. Design an audit mechanism that surfaces when a team has overridden a scaffold safety default (iteration cap, cost ceiling), rather than assuming defaults are always left in place.

## Verify Your Work

- The inventory names specific agents and their architecture, not a general impression of "most things use the shared framework."
- The retroactive rubric run identifies concrete, specific gaps in an existing system, not a hypothetical exercise.
- The outcome measure is falsifiable — a rate or count with a clear numerator and denominator — not a vague "agents are more reliable now."
- The support contract states an actual deprecation trigger or date, not an open-ended "eventually."
- The audit mechanism actually detects a deliberately introduced default override in a test, not just in theory.

## Review Questions

- Why does centralizing agent-design review in one platform team tend to fail as the number of teams grows?
- What does a rubric checklist item like "non-overlapping tool domains" actually prevent, concretely?
- Why can high scaffold adoption coexist with an unchanged safeguard-incident rate, and what does that combination reveal?
- What turns a shared scaffold's default values into something teams can plan against, rather than a surprise when they change?
- Who is accountable when a cost regression traces back to a shared scaffold default versus a team's own prompt or tool change, and how do you tell which it was?
