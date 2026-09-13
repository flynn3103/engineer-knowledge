# Critical Thinking — Mistake

## When it pays off, and when it's a cost

- **Reach for it when:** the decision is expensive to reverse (a data store migration, a service boundary, a build-vs-buy call), the team is split, or a claim is about to become the basis for a decision without anyone naming the evidence behind it.
- **Reach for it when:** everyone in the room agrees suspiciously fast — unanimous enthusiasm with no stated risk is itself a signal worth checking, not a sign of confidence.
- **Skip the full method when:** the decision is cheap to reverse and the cost of gathering more evidence exceeds the cost of being wrong — a two-line config change doesn't need a weighted comparison matrix.
- **The real cost:** applying full scrutiny to every claim is slow, and constant challenge without a stated reason reads as obstruction, not rigor — reserve it for claims that actually carry decision weight.

## Mistakes when isolating the claim

- **Accepting a claim because it's stated confidently.** Confidence is not evidence — a wrong claim stated firmly is still wrong.
  - Fix: ask "what was measured?" regardless of how sure the speaker sounds.
- **Leaving the claim blended with its evidence in one sentence.** If the claim and its support are never separated, neither one actually gets checked.
  - Fix: write the claim alone, stripped of any supporting language, before evaluating anything.

## Mistakes when evaluating evidence

- **Treating an anecdote or popularity as evidence.** "It worked at my last company" or "everyone's using it now" — this is the appeal-to-popularity fallacy; popularity says nothing about whether it fits your workload, team size, or constraints.
  - Fix: ask what was measured on *your* system, not someone else's.
- **Weighing indirect evidence the same as direct evidence.** A blog post's benchmark on someone else's workload is a hypothesis about your system, not a fact about it.
  - Fix: default to direct evidence (measured on your data); treat outside claims as something to test, not adopt.
- **Confusing correlation with cause.** "Deploys went out and then errors spiked, so the deploy caused it" is plausible, not proven.
  - Fix: check what else changed at the same time before concluding cause.

## Mistakes from cognitive bias (the errors happen in how you think, not just in the argument)

- **Confirmation bias** — only surfacing evidence that supports the option the team already favors; benchmarks get run for the preferred option but not the alternative.
  - Fix: require the same evidence bar for the team's leaning option as for every alternative.
- **Anchoring bias** — the first number or opinion stated in a discussion dominates every estimate that follows, even from people who hadn't thought about it yet.
  - Fix: collect independent estimates before anyone states one out loud.
- **Sunk cost** — continuing an investment because of past effort ("we already spent six weeks on this"), not because of its value going forward.
  - Fix: explicitly separate what was already spent from what continuing costs from here — only the second number belongs in the decision.

## Fallacy mistakes (errors in the argument's structure, not just its evidence)

- **Appeal to authority** — "a senior engineer said we should do it this way," substituted for reasoning about this specific case.
  - Fix: ask for their reasoning, not their title.
- **False dichotomy** — "either we rewrite the whole service or we keep shipping bugs forever," hiding a middle option a spectrum of choices would reveal.
  - Fix: name the option in between before accepting either extreme.
- **Ad hominem** — attacking the person raising a concern instead of the claim itself, which turns a factual disagreement into a social conflict and the claim never gets checked.
  - Fix: restate the claim in neutral terms and ask what would prove or disprove it.

## The meta-mistake

- **Only applying this to other people's claims, not your own.** The isolate → evaluate → alternative-test loop is easiest to run against an idea you already doubt, and easiest to skip on the conclusion you're about to present as your own.
  - Fix: before presenting a recommendation, run the same loop against it yourself and state the strongest reasonable objection before someone else has to.

Continue to [Best Practise](best-practise.md).
