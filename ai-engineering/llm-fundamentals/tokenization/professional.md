# Tokenization — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run token-budget governance — a shared counting library, per-vendor tokenizer contracts, and cost monitoring — as a durable, org-wide operating model, so no team's LLM-calling code silently ships a `len(text) / 4` estimate that breaks the day a non-English market launches or a vendor rotates its tokenizer?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Ownership Aligned to Cognitive Load

The predictable failure mode at scale: every team hand-rolls its own token estimate — usually some variant of `len(text) // 4` — because nothing central exists to depend on instead, and by the time ten teams have each done this independently, the org has ten slightly different, all-approximately-wrong estimates instead of one correct one. The split that scales distributes ownership by who actually has the context to sustain each decision:

| Layer | Owner | Responsibility |
|---|---|---|
| **Shared token-counting library/service** | AI platform/infra team | Build and version a counting function per vendor/model, wrapping `tiktoken`, SentencePiece, and vendor count-tokens endpoints, so no team re-implements or re-approximates this |
| **Per-vendor tokenizer contracts** | AI platform/infra team | Track, in one place, which tokenizer (name and version) each deployed model actually uses, and update the registry the moment a vendor ships a model with a new tokenizer |
| **Cost governance and monitoring** | FinOps/platform team | Per-team, per-service token usage dashboards and budget alerts, catching a runaway prompt-bloat regression before the monthly invoice does |
| **Application-specific logic** | The team that owns the product/service | Prompt design, truncation UX, which strategy (hard cut, summarize, reject) fits their product — built on top of the shared library, not around it |
| **Program health and enforcement** | A governance working group spanning platform, security/finance, and product | Track adoption, estimate-vs-actual error trends, and truncation-incident rate across the org; escalate when a service falls behind |

This keeps each layer within what its owner can actually sustain: no product team is expected to track tokenizer version changes across every vendor, and no central team is expected to understand every product's specific truncation UX needs.

## Core Concept 2 — A Shared Token-Counting Library as the Paved Road

A **shared token-counting library** exists to make the accurate choice the *default* choice, rather than something every team has to independently discover is even necessary:

```python
# token_counter/count.py — one internal package every LLM-calling
# service imports, instead of each team writing its own estimate.

def count_tokens(text: str, vendor: str, model: str) -> int:
    """Return the exact token count for `text` under `model`'s real
    tokenizer. Raises on an unregistered vendor/model pair rather than
    silently falling back to a character-count guess."""
    ...

# Usage — replaces every ad hoc `len(text) // 4` in the codebase:
n = count_tokens(user_message, vendor="openai", model="gpt-4o")
```

The library only earns adoption if it's genuinely easier to use than the alternative: published with clear docs, fast enough to call inline on the request path (cached tokenizer instances, not reloaded per call), and tested against known strings for each vendor so a regression in the library itself is caught before it reaches every consumer at once. This is the same leverage as any shared internal library — fix a tokenizer edge case once, upstream of everyone who depends on it, instead of once per team that happens to notice.

## Core Concept 3 — Per-Vendor Tokenizer Contracts

A **tokenizer registry**, maintained centrally, answers "which tokenizer does this deployed model actually use, right now" without anyone having to ask around:

| Model deployment | Vendor | Tokenizer | Approx. vocab size | Last verified |
|---|---|---|---|---|
| `gpt-4o` (primary) | OpenAI | `o200k_base` | ~200,000 | On last model version bump |
| `gpt-3.5-turbo` (legacy path) | OpenAI | `cl100k_base` | ~100,000 | On last model version bump |
| `claude-*` (fallback provider) | Anthropic | Claude's own tokenizer | — | On last model version bump |
| `llama-*` (self-hosted) | Open-weight | SentencePiece | Model-specific | On last checkpoint change |

The trigger for updating this registry is not a calendar — it's any event that can change a tokenizer out from under a service: a vendor ships a new model version, a self-hosted checkpoint is swapped, or a fallback provider is added or changed. Without a registry, "which tokenizer is behind this model today" is a question someone has to re-derive from scratch during every incident; with one, it's a lookup.

## Core Concept 4 — Cost Governance

Per-team, per-service token usage monitoring exists to catch a cost regression while it's still cheap to fix — not after the monthly bill lands. A concrete alerting design:

```yaml
# cost_alerts.yaml
alerts:
  daily_token_spend_deviation:
    condition: "team's daily token spend deviates > 30% from its 7-day rolling average"
    action: "page the owning team's on-call channel, not finance"
  cost_per_request_drift:
    condition: "median cost-per-request for a service rises > 20% week over week with no corresponding feature launch"
    action: "flag in the weekly platform review"
```

The specific regression this catches: a code change that accidentally duplicates conversation history into the prompt, a debug dump left in a system prompt, or a newly added multilingual market quietly costing 2–3x more per request than the English-only baseline it was budgeted against. Each of these is invisible in a per-request unit-economics spreadsheet updated monthly, and visible within a day in a dashboard tracking the trend.

## Core Concept 5 — Rollout: Pilot Where the Naive Estimate Is Most Wrong

Mandating "every team adopts the shared token-counting library by end of quarter" produces the same theater any top-down infra mandate produces — rushed, unverified swaps made to hit a deadline. Decompose the rollout instead, starting where the error is largest and therefore most motivating:

1. **Pilot on the highest-cost or most multilingual service first.** The char-count estimate's error is largest exactly where the content least resembles English prose — a multilingual support product or a code-heavy developer tool — so that's where switching to real per-vendor counting produces the most visible, most defensible win.
2. **Extract the library's real interface from what the pilot needed**, rather than designing it by committee up front — the pilot reveals which vendors, which models, and which call patterns are actually in use.
3. **Wire usage monitoring as a non-blocking dashboard first**, before any budget check becomes a hard gate — this surfaces how far off the existing estimates are across the pilot's traffic without breaking anything on day one.
4. **Turn budget enforcement blocking only for new requests going forward**, not retroactively for traffic patterns that were already working under the old estimate — an overnight, fleet-wide gate change breaks unrelated teams' launches over an estimate that predates the policy.
5. **Expand service by service**, tracking adoption as a fraction (services using the shared library / total LLM-calling services) and, more importantly, the estimate-vs-actual error trend for each newly onboarded service.

Each step stays reversible: a service can revert to its own estimate at any point without waiting on other teams, because the shared library exposes the same simple interface the ad hoc estimates did — this rollout replaces the internals, not the contract.

## Core Concept 6 — Migration, Governance, and Multilingual Risk

Rolling this out across an org with years of accumulated LLM-calling code surfaces risk a single pilot doesn't:

- **Legacy services on unexamined char-count estimates.** Services built years before a market expansion often have `len(text) // 4` baked in with no comment explaining it was ever an approximation — discovery starts with an inventory of LLM-calling code paths, not with asking teams to self-report.
- **Vendor tokenizer drift.** A vendor shipping a new model version with a new tokenizer, silently, is a supply-chain-shaped risk for any service whose budget constants assume the old one — the registry in Core Concept 3 exists specifically to catch this before an incident does.
- **Multilingual cost and truncation risk compounding at market-launch scale.** A char-count estimate tuned on English-only traffic doesn't fail occasionally in a new non-English market — it fails systematically, for the entire user base in that market, the moment volume is large enough to notice.

## Core Concept 7 — Outcome Measures and Exit Conditions

```yaml
# token_governance_dashboard.yaml — reviewed quarterly
metrics:
  library_adoption: "services using the shared token-counting library / total LLM-calling services"
  estimate_vs_actual_error: "median absolute % difference between the old char-count estimate and the real tokenizer count, tracked per language and per content type"
  truncation_incident_rate: "count of silent-truncation incidents per month, org-wide"
  cost_per_request_variance: "stddev of daily cost-per-request vs. its rolling average, per team"
exit_conditions:
  pilot_to_expansion: "pilot service's estimate-vs-actual error drops to near zero, and cost/truncation dashboards for the pilot are stable for two consecutive weeks"
  program_maturity: "library_adoption > 80% of active LLM-calling services, and truncation_incident_rate trending toward zero for two consecutive quarters"
```

`estimate_vs_actual_error`, broken out per language, is the number that matters most here — it's the one that would have caught a CJK-market under-budgeting problem before launch instead of after. Adoption alone is a leading indicator that the paved road exists; the error and incident-rate trends are what prove it's actually preventing the failure it exists to prevent.

## Core Concept 8 — Cross-Team Contracts

Once many teams depend on the shared library and the tokenizer registry, treat both the way an internal API is treated:

- The library publishes a **support contract** — current major version, deprecated-but-still-patched versions, and the date a version stops being maintained.
- Consuming services pin to a specific major version rather than floating, and are expected to plan their own upgrade ahead of a deprecation date rather than being surprised by it.
- A breaking change to the library (a vendor's tokenizer function signature changing, a vendor being dropped) goes through the same change-review and advance-notice process as a breaking API change, because for a team built on the old behavior, it functionally is one.
- Accountability follows the contract: a stale tokenizer-registry entry that causes an incident is the platform team's action item; a team that ignored a deprecation notice and kept using an unsupported library version is the consuming team's.

## Core Concept 9 — Sustained Delivery, Not a One-Time Migration

Getting every team onto the shared library once is not the end state — new vendors, new model versions, and new markets keep arriving indefinitely:

- **A registry-update cadence tied to vendor events**, not a fixed calendar — a new model version or tokenizer change triggers an update as soon as it's known, not on the next quarterly review.
- **An automated notification mechanism** (a bot opening a PR bumping a pinned library version, or an alert to a service owner) when a tokenizer contract changes, so a corrected budget assumption actually reaches production quickly rather than sitting documented-but-unused.
- **New services onboard onto the shared library by default**, not as an opt-in step someone has to remember — the paved road should be the easy path for a brand-new service, not a retrofit applied only after an incident.
- **A periodic retrospective against the outcome measures in Core Concept 7**, asking explicitly: is the estimate-vs-actual error actually falling for every language segment, or only for the ones that were part of the original pilot?

---

## Cross-Team Scenario: A Multilingual Market Launch Exposes a Systematic Estimator Bias

A support-ticket product expands from an English-only market into several CJK-language markets. Weeks after launch, the org discovers its shared token estimator — `len(text) // 4`, tuned and validated years earlier on English-only traffic — was never re-validated for the new markets. CJK text commonly runs close to 1–2 characters per token rather than English's ~4, so a 500-character CJK support message that the estimator predicts as roughly 125 tokens is, in reality, closer to 300–400 tokens: a systematic, market-wide under-budgeting, not an occasional edge case. The result is silent truncation of conversation history for CJK-market users specifically, discovered through qualitative complaints rather than any dashboard, because the estimator itself was what every truncation decision trusted.

A reversible rollout of the fix:

1. **Immediate mitigation, cheap and reversible.** Raise the safety margin for the affected markets' budget checks — over-reserve rather than under-reserve — as a stopgap while the real fix is built, not as the fix itself.
2. **Pilot the shared library specifically on the CJK-serving service.** It has the largest measured estimate-vs-actual error and the clearest business urgency, which makes the win concrete rather than hypothetical.
3. **Measure the before/after error reduction.** Compare `estimate_vs_actual_error` for CJK traffic before and after the swap — this is the number that justifies expanding further, not a general claim that "it's more accurate now."
4. **Expand to other non-English-serving teams** (Arabic, Hindi, and others), each pilot measuring its own segment's error independently rather than assuming the CJK result transfers.
5. **Make per-language error monitoring permanent**, not a one-time launch check, so the next market expansion is caught by the dashboard before launch instead of by user complaints after it.
6. **Keep the rollback path live.** Because the shared library and the old estimate expose the same interface, any service can revert independently if the new counting logic has its own bug, without blocking or being blocked by any other team's rollout.

## Real-World Examples

- **A CJK market launch surfaces a systematic estimator bias.** As above — the failure isn't a rare edge case, it's the estimator being wrong for an entire market segment simultaneously, which is exactly why per-language error tracking (Core Concept 7) catches what a single aggregate accuracy number would hide.
- **An automated tokenizer-registry bot closes a version-drift gap.** A vendor ships a new model version with a new tokenizer; without an automated PR bumping every consuming service's pinned assumption, manual adoption across dozens of teams would take weeks. A bot-opened version-bump PR closes most of that gap within a day.
- **A blocking budget gate rolled out to the whole fleet overnight breaks unrelated teams.** A platform team turns budget enforcement from advisory to blocking for every service at once; several teams' deploys fail on traffic patterns that predate the policy and were never their decision to fix in that moment — the gate is rolled back to advisory for existing traffic while staying blocking for new requests, matching the sequencing in Core Concept 5.
- **Adoption looks strong, truncation incidents don't move.** An org reaches 85% shared-library adoption, but the truncation-incident rate stays flat, because the registry-update notification was a wiki page rather than an automated PR — the next quarter's investment shifts from adoption outreach to automating the notification step.

## Common Mistakes

- **Letting every team maintain its own token estimate.** Guarantees divergent, mostly-wrong approximations instead of one correct, centrally maintained implementation.
- **Mandating full library migration before piloting.** Skips the step where the library's real interface is derived from an actual service's needs, and gets painfully revised after wide adoption instead of cheaply after one pilot.
- **Turning budget enforcement blocking for the entire existing fleet at once.** Breaks many teams' traffic simultaneously over an estimate error that predates the policy; gate new traffic first, remediate the existing fleet on a scheduled window.
- **Measuring only adoption percentage, never estimate-vs-actual error or truncation-incident rate.** High adoption with a stagnant error rate looks like program success on a dashboard while delivering none of the accuracy the program exists to provide.
- **Tracking estimate accuracy in aggregate only, not per language or content type.** Hides exactly the systematic, market-wide bias that a multilingual launch is most likely to expose.
- **Leaving the tokenizer-registry update step manual.** A registry that's accurate in principle but updated only when someone remembers is no better than no registry during the week a vendor's tokenizer actually changes.

---

## Apply it

1. Inventory the LLM-calling services you have visibility into, and identify which ones use a character-count estimate instead of a real tokenizer call.
2. Design the shared token-counting library's interface (`count_tokens(text, vendor, model) -> int`) and identify which vendors/models it needs to support for your current fleet.
3. Pick the pilot service with the largest expected estimate-vs-actual error — the most multilingual or highest-cost one — and define the specific before/after metric that would justify expanding beyond it.
4. Draft a one-page support contract for the shared library: current version, deprecation timeline for anything it replaces, and who consuming teams contact about a breaking change.
5. Design the automated notification mechanism (a bot-opened PR, a CI check, or equivalent) that closes the gap between "the tokenizer registry was updated" and "every consuming service's assumptions actually reflect it," rather than relying on teams noticing on their own.

## Verify your work

- The inventory names specific services relying on a character-count estimate, not a general impression that "some services probably guess."
- The pilot's before/after numbers show a measurable drop in estimate-vs-actual error for a real, non-English or code-heavy content segment, not just an adoption checkbox.
- The outcome measures are specific and falsifiable (a rate or percentage with a clear numerator and denominator), not a vague claim like "more accurate token counting."
- The support contract states an actual deprecation trigger for superseded library versions, not an open-ended "eventually."
- The notification mechanism is automated enough that a tokenizer-registry update reaching every consuming service does not depend on each team remembering to check.

## Review questions

- Why does letting every team maintain its own token estimate tend to produce worse outcomes than one centrally owned counting library, even if each individual estimate seems reasonable?
- What does a stagnant truncation-incident rate reveal about a token-governance program that high library adoption alone does not?
- Why is tracking estimate-vs-actual error per language more useful than tracking it in aggregate?
- Why can turning a budget-enforcement gate blocking for the entire existing fleet at once cause more harm than gating only new traffic first?
- What turns a tokenizer registry into something teams can actually rely on, rather than a document that quietly goes stale?
