# Prompt Engineering — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run prompt engineering as a durable, org-wide operating model — a shared prompt library, a review process, regression testing — so a dozen teams stop independently re-deriving the same lessons, without a central team reviewing every prompt change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — The Predictable Failure Without an Operating Model

An organization with a dozen teams each building LLM-backed features tends to converge on the same shape of problem independently: each team writes its own "summarize this document" prompt, its own "classify into these labels" prompt, its own ad hoc handling of few-shot examples and output format — because nobody told them not to, and because each team's version looks like it works fine in isolation. The result, viewed from above, is a dozen prompts doing functionally the same task with inconsistent quality, inconsistent handling of edge cases, no shared regression testing, and no institutional memory of what any team already learned the hard way (the confusable-category problem from the middle-level guide, the injection surface from the senior-level guide) that every other team is about to rediscover independently.

The organizational fix mirrors the golden-base-image pattern from container infrastructure: instead of every team independently choosing and re-justifying a base, make the well-engineered choice the default, owned centrally, consumed everywhere.

## Core Concept 2 — A Shared Prompt Library as the Paved Road

A **prompt library** is a platform-owned, versioned collection of prompt templates for common task shapes — a standard "extract structured data from a document" template, a standard "classify into a fixed label set" template, a standard "summarize with length and audience constraints" template — that teams build on top of instead of writing from scratch:

```python
# Instead of every team independently writing and re-debugging its own
# classification prompt:
prompt = f"Classify this into one of: {labels}\n\n{text}"

# Teams consume a platform-maintained, versioned template:
from prompt_library import templates

prompt = templates.get("classify-fixed-label-set", version="v3").render(
    labels=MY_TEAM_LABELS,
    text=my_ticket_text,
)
```

The library template already encodes the lessons from the middle and senior levels — output-format constraints, guidance on when few-shot examples earn their cost, delimiting for any untrusted content slot — so a team adopting it inherits those lessons instead of relearning them through their own production incident. Exactly like a shared code library, the value only materializes if the library is genuinely easier to use than writing a prompt from scratch: documented, versioned, with clear examples of how to adapt it to a specific label set or document type.

## Core Concept 3 — Prompt Review as Code Review

A prompt change affecting a production-facing feature goes through the same review a code change would — not as bureaucratic overhead, but because the senior-level guide already established that a prompt change is functionally a code change with the same regression risk. Concretely:

1. **The change is a diff against a versioned prompt**, reviewable the same way a code diff is (Core Concept 1 of the senior-level guide).
2. **The golden-set regression suite runs automatically** against the proposed change before it can merge, the same way a CI test suite blocks a broken code change.
3. **A reviewer with context on the prompt's history** — ideally the template's owner, not just anyone on the submitting team — looks at whether the change introduces the kind of accumulated-contradiction risk covered at senior level, not just whether it "looks right" in isolation.
4. **The review bar scales with blast radius** — a one-team-internal prompt used by a low-traffic feature can have a lighter review than a shared library template a dozen teams depend on; treating every prompt change with library-template-level rigor is as wasteful as requiring a full architecture review for a one-line internal script change.

## Core Concept 4 — Ownership and Escalation for Shared Templates

Once multiple teams depend on a shared template, it needs the same ownership contract a shared internal API or a golden base image needs:

- **A named owning team** for each shared template — not "whoever wrote it originally," but a team accountable for maintaining it, reviewing changes to it, and fielding questions from consuming teams.
- **A support/version contract**, mirroring the golden-base-image pattern: which template version is current, which older versions are still supported, and advance notice before a version is deprecated.
- **A breaking-change process** — if a change to the shared "classify into fixed label set" template would alter behavior for existing consumers (a different confidence threshold, a changed output shape), it goes through the same change-review and advance-notice process a breaking API change would, because for a team that built on the old behavior, it functionally is a breaking change.
- **Accountability follows the contract** — if a shared template's owning team ships a regression that reaches a consuming team's production feature, that's the owning team's incident to own; if a consuming team ignores a deprecation notice and breaks on the old version's removal, that's on the consuming team.

## Core Concept 5 — Outcome Measures and Exit Conditions

A prompt-governance program needs measures that show it's actually reducing incidents and speeding detection, not just producing a library nobody uses:

```yaml
metrics:
  library_adoption: "production LLM features using a shared library template / total production LLM features"
  regression_catch_rate: "prompt regressions caught by golden-set testing before production / total prompt regressions found (pre- and post-production)"
  prompt_incident_rate: "production incidents attributable to a prompt change, per quarter"
  time_to_detect: "median time from a prompt regression shipping to it being caught, before vs after golden-set testing existed"
exit_conditions:
  pilot_to_expansion: "the pilot team's regression_catch_rate rises measurably after adopting golden-set testing, and prompt_incident_rate for the pilot's feature drops for at least one full quarter"
  program_maturity: "library_adoption above a majority of production LLM features, and prompt_incident_rate trending down org-wide for two consecutive quarters"
```

`regression_catch_rate` before vs. after the golden-set process existed is the number that actually justifies the program: a library with high adoption but no measurable improvement in how many regressions get caught before reaching production is a documentation exercise, not a governance program delivering its intended outcome. Track adoption as a leading indicator that the paved road exists and is being used; track regression-catch rate and incident rate as the outcome measures that prove it's working.

## Core Concept 6 — Cross-Team, Sustained-Delivery Scenario

An organization has a dozen teams, each independently prompt-engineering a similar task — every team building a "summarize this document" feature has its own ad hoc prompt, of visibly inconsistent quality, with no shared regression testing and no one place to fix a wording bug that affects several of them at once.

**Decomposing the rollout, reversibly:**

1. **Pilot on the team with the highest prompt-related incident rate**, not the team most enthusiastic about the idea — this makes the win concrete and measurable rather than speculative, and gives the strongest evidence for expansion if it works.
2. **Extract the shared template's structure from what the pilot actually needed**, rather than designing it by committee up front — the pilot reveals which variables the template needs (document type, target length, audience), which output-format constraints matter, and which speculative options nobody uses.
3. **Build the golden-set regression suite from the pilot team's own historical incidents** — past cases where their ad hoc prompt produced a bad summary become the first golden-set entries, so the suite is grounded in real failures, not hypothetical ones.
4. **Run the new shared template and golden-set suite in parallel with the pilot's existing prompt first**, comparing output quality and regression-catch behavior before switching the pilot's production traffic over — this isolates "does the new template work" from "did we break something switching to it."
5. **Measure the pilot's before/after**: `prompt_incident_rate` for that team's feature, and `regression_catch_rate` on the golden-set suite versus their prior ad hoc, undocumented review (if any).
6. **Expand team by team**, each new team's onboarding contributing back any task-specific golden-set cases they find into the shared suite, rather than each team maintaining an isolated copy — the same "fix once, benefit everyone" leverage as the golden base image.

Each step stays reversible: if the shared template needs a structural change after the third team adopts it, that's a version bump reviewed through the process in Core Concept 3, not a program failure — no later step assumed the pilot's first version was final.

## Real-World Examples

- **A pilot's incident-rate drop funds expansion.** The team with the worst prompt-related incident history adopts the shared summarization template and golden-set suite; their prompt-incident rate drops measurably over the following quarter, giving the platform team a concrete, demonstrated result to justify expanding to other teams rather than a mandate imposed on the strength of the idea alone.
- **A shared template surfaces an injection gap three teams shared without knowing it.** While building golden-set cases from the pilot team's history, the platform team finds a case where a document's embedded text overrode the summarization instructions — the senior-level injection pattern. Fixing the delimiting in the shared template fixes it for every consuming team simultaneously, instead of three teams independently discovering and separately patching the same underlying issue months apart.
- **High adoption, flat incident rate reveals a process gap, not a tooling gap.** An org reaches strong library adoption across teams, but prompt-related incidents don't drop, because teams are consuming the library templates but skipping the golden-set check before shipping their own customizations on top. The next quarter's investment shifts from library promotion to making the regression suite a hard merge gate, not an optional step.

## Common Mistakes

- **Building the shared library speculatively, with no pilot team's real usage behind it.** Produces a template shaped by guesswork rather than the actual confusions and edge cases a real production feature hits.
- **Reviewing every prompt change — from a one-team internal script to a shared library template — with the same weight.** Over-applies review overhead to low-blast-radius changes and under-resources review for the changes that actually affect many teams.
- **Leaving a shared template with no named owner.** When it breaks or needs a breaking change, there's no one accountable for reviewing the change or communicating it to consumers.
- **Measuring only library adoption, never regression-catch rate or incident rate.** High adoption with no measurable drop in prompt-related incidents means the program produced a library, not the outcome the library exists to deliver.
- **Letting each team maintain its own copy of golden-set cases instead of contributing back to a shared suite.** Repeats the exact fragmentation the program exists to fix, one layer down.

---

## Apply it

1. Inventory the LLM-backed features across a set of teams you have visibility into, and identify which ones are solving a similar task shape (summarization, classification, extraction) with independently written prompts.
2. Identify the team with the highest prompt-related incident rate (or the most visible quality complaints) among them, and design that team's pilot: which shared template would replace their ad hoc prompt, and which of their past incidents becomes the first golden-set entries.
3. Define the outcome measures for this program, scoped first to the pilot team, and write the specific exit condition that would justify expanding beyond it.
4. Draft a one-page ownership contract for the shared template: who owns it, what counts as a breaking change, and how consuming teams are notified.
5. Design the review process for changes to the shared template specifically — who reviews, what the golden-set gate requires, and how the review bar differs for a low-blast-radius, single-team prompt change.

## Verify your work

- The pilot is chosen based on a real incident or quality signal for that team, not general enthusiasm for the idea.
- The golden-set suite's first entries trace to specific past failures from the pilot team's own history, not hypothetical cases invented in the abstract.
- The outcome measure is specific and falsifiable (a rate with a clear numerator and denominator, or a duration), not a vague statement like "better prompt quality."
- The ownership contract names an actual accountable team and a concrete breaking-change process, not an open-ended "the platform team will handle it."
- You can state, for the pilot, the before/after number on at least one of `prompt_incident_rate` or `regression_catch_rate` — not just that adoption happened.

## Review questions

- What specific organizational failure does a shared prompt library address that a well-written middle-level template, used only by one team, does not?
- Why does prompt review need to scale its rigor with blast radius rather than applying the same process to every prompt change?
- What does a flat prompt-incident rate reveal about a governance program even when library adoption is high?
- In the cross-team rollout, why does building the golden-set suite from the pilot team's own past incidents matter more than writing hypothetical test cases?
- What would have to be true of a shared template's ownership contract for a consuming team to plan around a breaking change instead of being surprised by it?
