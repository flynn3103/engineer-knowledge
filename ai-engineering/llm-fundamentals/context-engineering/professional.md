# Context Engineering — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run context engineering as a durable, org-wide operating model — a shared assembly library, standardized observability into what's actually in the context window at each production call, and governance for assembly changes — so multiple teams building RAG and agentic products stop each reinventing inconsistent, undebuggable context logic?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Ownership Aligned to Cognitive Load

The predictable failure mode at organizational scale: every team building a RAG pipeline or an agent independently writes its own context-assembly logic — its own ranking, its own truncation, its own delimiting convention, often its own bugs in each of those. No central review process can keep up once more than a handful of teams are shipping LLM-backed features, and worse, a central team trying to review every team's assembly code lacks the product context to judge whether a given ranking or truncation choice is actually right for that team's use case. The split that scales:

| Layer | Owner | Responsibility |
|---|---|---|
| **Shared context-assembly library** | Platform / AI infrastructure team | Implement ranking, precedence, truncation, and delimiting once, correctly, as a reusable component every team calls instead of reimplementing |
| **Source-specific relevance signals** | The team that owns the product | Their retrieval scoring, their tool integrations, their domain-specific priority tweaks — because they know their own data and users |
| **Observability and tracing infrastructure** | Platform / AI infrastructure team | The logging and storage that captures assembly records (per [senior.md](senior.md)) for every production call, queryable after the fact |
| **Golden-set regression testing** | Shared tooling, owned jointly with each product team's contribution of test cases | The infrastructure to run assembly changes against a labeled set before rollout; the actual test cases come from the teams closest to the product |
| **Program health and adoption** | A governance group spanning platform, security, and product | Track adoption, incident rate, and outcome measures across the org; decide when a pilot is ready to expand |

This mirrors the split a mature organization already applies to prompt engineering (see [Prompt Engineering](../prompt-engineering/README.md)) and to token-budget management (see [Context Window](../context-window/README.md)): a shared library for the mechanism that's the same everywhere, team-owned judgment for the parts that genuinely differ by product.

## Core Concept 2 — The Shared Library as a Paved Road

A shared context-assembly library exists so the correct behavior — rank sources, enforce precedence, truncate the lowest-priority tail, delimit every source explicitly, log what happened — is the *default* a team gets by calling a function, not something every team's engineers have to independently discover, implement, and get right:

```python
# Instead of every team hand-rolling assembly logic with its own bugs:
context = system_prompt + "\n\n" + "\n\n".join(chunks) + "\n\n" + question

# Teams call a shared library that implements ranking, precedence,
# truncation, and delimiting once:
context = assembly.build(
    instructions=system_prompt,
    sources=[
        assembly.Source("history", history_turns, priority=2, compress_after=6),
        assembly.Source("tool_results", tool_outputs, priority=2, recency_wins=True),
        assembly.Source("retrieved", ranked_chunks, priority=3),
    ],
    question=user_question,
    budget_tokens=8000,
)
# context.text -> the assembled, delimited string
# context.trace -> the assembly record logged automatically
```

The library only earns adoption if it's genuinely easier than the alternative: it needs to handle the common cases (a RAG pipeline, a tool-using agent, a plain chat history) without every team fighting its defaults, it needs to emit the observability record automatically so no team has to build that separately, and it needs clear documentation so adopting it doesn't require a standing question to the platform team every time. A shared library nobody actually prefers to hand-rolled code is a paved road nobody drives on.

## Core Concept 3 — Standardized Observability as a First-Class Operational Signal

At senior scope, an assembly record for one call is a debugging tool. At professional scope, assembly records across every production call, from every team, become an operational and analytical dataset — the same way distributed request tracing is standard infrastructure, not an optional add-on, for any service at scale:

- **Every production LLM call logs its assembled context**: which sources were candidates, their token counts, their included/excluded/truncated status, and the final total against budget — exactly the record shape from [senior.md](senior.md), but now emitted uniformly by the shared library rather than reimplemented (or skipped) per team.
- **This becomes queryable for offline analysis**, not just single-incident debugging: "what fraction of calls last week truncated a retrieved chunk that later analysis shows was relevant?" or "does answer quality correlate with how much conversation history got compressed versus dropped?" are questions only answerable if assembly records are structured, consistent, and retained — not scattered across whichever teams happened to build their own logging.
- **It becomes a leading indicator, not just a postmortem tool.** A rising rate of `excluded_stale` tool results or a rising rate of documents truncated at high relevance scores are signals worth alerting on before they produce a wave of user complaints, not only after.

Without this as an org-wide standard, every "the assistant gave a wrong answer" investigation starts from zero — a different team's ad hoc logging (or none at all), a different record shape, no way to compare across products.

## Core Concept 4 — Governance for Context-Assembly Changes

A change to the shared library's ranking or truncation logic can silently change what every consuming team's production system answers, even when no team touched their own prompt. This deserves the same rigor already established for prompt changes:

- **Every change to the shared library's precedence, ranking, or truncation logic is versioned**, with a changelog stating what changed and why.
- **Changes are regression-tested against each consuming team's golden set before rollout** — a labeled set of realistic queries with known-correct context expectations, the same discipline covered in [Prompt Engineering](../prompt-engineering/README.md) for prompt changes. A change to truncation logic that shifts which chunks survive under budget pressure for a *different* product's typical query shape is exactly the kind of regression a shared library's own unit tests won't catch, because those tests exercise the library's general behavior, not any one team's specific data distribution.
- **Rollout is staged, not global-on-merge.** A change ships to one or two consuming teams first, with their assembly records and answer-quality metrics watched for a defined window, before it becomes the default for every team on the library.
- **A rollback path is explicit** — pinning to the prior library version is a one-line change for a consuming team, not a re-implementation.

Treating an assembly-logic change as low-risk because "the prompt didn't change" is the specific mistake this governance exists to prevent — the prompt is only half of what the model sees.

## Core Concept 5 — Rollout: Pilot, Extract, Expand

Mandating "every team migrates to the shared library by end of quarter" produces the same theater any top-down infrastructure mandate does — rushed adoption to hit a deadline, not because the library was validated against real usage. A decomposed rollout:

1. **Pilot with the team experiencing the most context-related incidents** — the team whose "wrong or outdated answer" complaint volume is highest gives the clearest before/after signal and the strongest incentive to adopt carefully rather than superficially.
2. **Extract the library's actual interface from what the pilot needs**, rather than designing every source type and every configuration option speculatively in advance — a pilot reveals which precedence rules, which compression triggers, and which observability fields are actually used, and which were guessed at and never needed.
3. **Ship observability as non-optional from day one of the pilot**, even before governance or golden-set testing are fully built out — the assembly records are what let the pilot's own outcome be measured, so they can't be the part added last.
4. **Add golden-set regression testing once the pilot has real, representative queries to build the golden set from** — a golden set invented before any real usage risks testing the wrong things.
5. **Expand team by team**, each new team's onboarding informed by what the previous team's pilot surfaced, tracking adoption as a fraction of teams and services, not as a single binary migration event.

## Core Concept 6 — Outcome Measures and Exit Conditions

```yaml
# Program health dashboard, reviewed quarterly.
metrics:
  library_adoption: "services using the shared assembly library / total LLM-backed services"
  context_incident_rate: "user-reported 'wrong/outdated answer' incidents per week, tracked per team"
  mean_time_to_diagnose: "time from incident report to root cause identified, using assembly records"
  truncation_quality: "fraction of production calls where a high-relevance source (score above the team's threshold) was truncated or excluded"
  golden_set_regression_catch_rate: "regressions caught by golden-set testing before rollout / total regressions later found in production"
exit_conditions:
  pilot_to_expansion: "pilot team's context_incident_rate drops measurably, mean_time_to_diagnose drops from hours to minutes using assembly records, and the platform team can update the library without the pilot team's code changing"
  program_maturity: "library_adoption > 80% of active LLM-backed services, and context_incident_rate trending down for two consecutive quarters across adopting teams"
```

`mean_time_to_diagnose` is the measure that most directly proves the observability investment is paying off — a team can adopt the shared library for its ranking and truncation logic alone and see little change in incident rate if nobody actually uses the assembly records to diagnose incidents faster. Track it explicitly rather than assuming observability adoption follows automatically from library adoption. `truncation_quality` is the measure that catches a subtler failure: a library that's fast and widely adopted but whose default ranking or truncation logic is quietly wrong for a particular team's data shape, discoverable in the assembly records themselves.

## Core Concept 7 — Cross-Team Scenario: A Wave of Complaints With No Common Root Cause

Multiple teams across an organization are independently building RAG and agentic products — a support assistant, an internal knowledge-search tool, a coding assistant with repository context. Each team's context-assembly logic is its own: different ranking heuristics, different truncation behavior, no shared observability. A wave of "the assistant gave a wrong or outdated answer" complaints arrives across several of these products in the same month, and there is no way to tell, from outside each team's own code, whether the complaints share a root cause or are three unrelated problems.

The response, applied per Core Concepts 5 and 6:

1. **Pilot the shared library, with mandatory observability, on the team with the highest complaint volume** — say, the support assistant, since it has the most user-facing incidents and the clearest before/after comparison.
2. **Within the pilot, assembly records immediately surface a concrete, specific cause**: a large fraction of incidents trace back to stale tool results (the recency-precedence gap from [senior.md](senior.md)'s Core Concept 5) rather than to retrieval ranking, which the team had assumed was the culprit and had been tuning for weeks with no improvement.
3. **`mean_time_to_diagnose` for the pilot team drops** from a multi-hour investigation (re-running sessions, guessing at causes) to a direct read of the assembly record for the specific failing call — a concrete, measured before/after, not an impression.
4. **`context_incident_rate` for the pilot team drops** once the specific, now-identified precedence gap is fixed in the shared library, benefiting every future consumer of that library automatically rather than requiring each team to independently discover the same bug.
5. **The knowledge-search and coding-assistant teams adopt next**, each contributing their own golden-set queries and each getting the fix for the recency-precedence gap for free, since it's now enforced in the library rather than needing to be independently rediscovered by every team that happened to have the same bug pattern.

The outcome that justifies the investment isn't "we built a shared library" — it's the measured drop in mean-time-to-diagnose and incident rate on the pilot team, used as the concrete evidence to justify expanding rather than a mandate imposed on faith.

---

## Real-World Examples

- **A pilot's root-cause finding redirects weeks of misdirected tuning.** A team spends weeks tuning retrieval ranking to fix "wrong answer" complaints, with no measurable improvement, because the actual cause — stale tool results outranking fresh ones with no recency rule — was never visible without an assembly record. Adopting shared observability surfaces the real cause within days of the pilot starting.
- **Adoption looks strong, incident rate doesn't move.** An org reaches high adoption of the shared assembly library across teams, but context-related incident rate stays flat, because teams adopted the library for its ranking and truncation code without actually querying their assembly records when incidents occur — the tooling existed but wasn't used. The next quarter's investment shifts from library adoption outreach to training teams on using the observability data during incident response.
- **A library change regresses one team silently.** A platform team improves the shared library's default truncation behavior based on the pilot team's data shape, ships it as the new default for every consumer, and a different team's answer quality quietly degrades because their typical query shape truncates differently under the new default — caught only because their golden-set regression suite, run before the change reached them, flagged it. Staged rollout with per-team golden-set testing (Core Concept 4) is what catches this before it reaches production.

## Common Mistakes

- **Building the shared library's interface speculatively, before any real team has piloted it.** Produces a library shaped by guesses about what teams need instead of what a real pilot revealed they actually use.
- **Treating observability as an optional add-on to be built after the library is adopted.** Assembly records are what make the pilot's own outcome measurable — without them from day one, there's no evidence to justify expanding beyond the pilot.
- **Shipping a shared-library change globally without staged rollout or per-team golden-set testing.** A change validated against one team's data shape can silently regress a different team's answer quality.
- **Measuring only library adoption, never incident rate or mean-time-to-diagnose.** High adoption with flat incident rates and slow diagnosis looks like program success on a dashboard while delivering little of the actual reliability benefit the program exists for.
- **Assuming teams will use assembly records during incident response just because the records exist.** Observability infrastructure without training or an established habit of using it during incidents delivers a fraction of its potential value.

---

## Apply it

1. Inventory the LLM-backed products across an organization you have visibility into, and identify which ones have their own hand-rolled context-assembly logic with no shared observability.
2. Design the interface for a shared context-assembly library covering the common source types (retrieved documents, tool results, conversation history) with explicit priority and truncation behavior, per Core Concept 2.
3. Identify which team would make the strongest pilot — highest context-related complaint volume — and define the outcome measures you'd track for that pilot, starting with `context_incident_rate` and `mean_time_to_diagnose`.
4. Draft the governance process for a change to the shared library's ranking or truncation logic: what regression testing is required, what staged rollout looks like, and what the rollback path is.
5. Write the concrete exit condition that would justify expanding the library beyond the pilot team to the rest of the organization.

## Verify your work

- The inventory names specific products with ad hoc, unobserved context-assembly logic, not a general impression that "some teams probably have inconsistent logic."
- The pilot's outcome measures are specific and falsifiable (a rate or duration with a clear numerator and denominator), not a vague statement like "better answers."
- The governance process names a concrete regression-testing step and a concrete rollback path, not just "changes will be reviewed carefully."
- The exit condition ties expansion to a measured improvement (incident rate, diagnosis time) on the pilot team, not to elapsed time or library adoption alone.
- You can explain, using the cross-team scenario in Core Concept 7 as a model, how assembly records specifically — not just the shared library's ranking code — are what shortens diagnosis time.

## Review questions

- Why does centralizing all context-assembly code review in one platform team tend to fail as the number of teams grows, and what ownership split addresses it?
- Why is observability described as something that has to ship from day one of a pilot, rather than something added once the library itself proves useful?
- What specifically can go wrong when a shared library's ranking or truncation logic changes and ships to every consuming team without staged rollout or per-team golden-set testing?
- Why can library adoption stay high while context-related incident rate stays flat, and what does that combination reveal about how the program is actually being used?
- In the cross-team scenario, what specifically let the team distinguish a stale-tool-result problem from a retrieval-ranking problem, after weeks of tuning retrieval had failed to help?
