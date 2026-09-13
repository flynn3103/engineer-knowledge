# First-Principles Thinking — Mistake

Common mistakes at each move, and how to catch them.

## Deconstruct mistakes

**Decompose**

- **Splitting into tasks instead of parts you can check independently.** "Implement login" cut into 50 steps that only make sense together isn't decomposition — it's a to-do list.
  - Fix: each part should be understandable and checkable on its own, like a wheel is still a wheel off the bike.
- **Boundary too large.** "The whole system" isn't a decomposed part — you can't reason about something you can't hold in your head.
  - Fix: keep splitting until each piece is small enough to fully understand.
- **Boundary too small.** A single line isn't a part either — you lose the shape of the problem.
  - Fix: a part should map to one recognizable piece of the original problem (one bike component, not one bolt).

**Recognize patterns**

- **Calling something a pattern after seeing it once.** One occurrence is a coincidence, not a pattern.
  - Fix: a real pattern shows up across multiple decomposed parts, not just one.
- **Forcing two different things into one pattern.** Two parts that look similar but play different roles — merging them too early hides that difference.
  - Fix: confirm what's actually shared (the role) before merging what differs (the specifics).

**Abstract**

- **Abstracting away detail that's actually needed.** If the abstraction hides *whether it succeeded*, whoever uses it can't handle failure.
  - Fix: abstraction removes irrelevant detail, never relevant behavior.
- **Not abstracting at all.** Exposing every internal detail means every internal change breaks everything downstream.
  - Fix: name what's actually needed and hide the rest.

**Reduce to truths**

- **Stopping at "common knowledge" instead of an actual truth.** "That's just the market price" or "that's just how it's done" is a restated assumption, not a fact you've verified.
  - Fix: keep asking why until you hit something you can check — a measurement, a law, a material cost — not a habit.
- **Optimizing the form instead of the function.** For roughly 4,000 years, wheeled carts and leather travel bags both existed — nobody put wheels on a suitcase until 1970. Generations of bag-makers kept refining the *bag* (form) instead of asking what the bag was actually for: moving things with less effort (function).
  - Fix: name the function first, in words that don't mention the current shape of the solution. Only then ask what parts could deliver that function.
- **Judging the future by the old form.** "Where are the flying cars?" mistakes the question — the function (fast point-to-point travel through the air) was already delivered, just not in car-shaped packaging. It's called an airplane.
  - Fix: when a solution looks like it "isn't what was promised," check whether the function was actually delivered in a different form before concluding it wasn't solved.

## Reconstruct mistakes

**Recombine**

- **Doing the analysis and stopping there.** Listing out the raw materials, the true costs, the fundamental constraints — and never recombining them into an actual proposal — is deconstruction without reconstruction. That's half the mechanism.
  - Fix: the deconstruction isn't done being useful until you've put the parts back together into something concrete.
- **Recombining into something that only looks new.** Swapping cosmetic details while keeping the same underlying assembly isn't reconstruction — it's decoration.
  - Fix: check whether the reconstructed version could have existed without ever deconstructing the original. If yes, nothing was actually rebuilt.
- **Committing to the first recombination without generating alternatives.** Whatever assembly comes to mind first is usually the old form wearing new material — not because it's actually best, but because it's the only one considered.
  - Fix: diverge into at least a couple of structurally different recombinations before judging any of them; Osborn's brainstorming premise — quantity breeds quality — applies here too.
- **Reaching for a lateral technique (random entry, provocation) as decoration instead of because the recombination genuinely stalled.** These moves exist to break a fixed pattern; used on a recombination that was never stuck, they just add noise.
  - Fix: try the obvious recombination first — only reach for a deliberately unrelated connection once it stops producing anything new.
- **Letting the first recombination proposed in a group anchor everyone else, or watching visible agreement hide private doubt.** People react to and refine whatever was said first, especially from a senior voice, and a room can converge in minutes without anyone voicing a real objection.
  - Fix: have people write candidate recombinations individually and silently before anyone discusses them out loud, then ask directly, "what's the strongest case against this one?" — silence or a strawman answer means the disagreement is real but unspoken.

**Design the algorithm**

- **Skipping the plan and going straight to code.** You end up debugging logic you never actually wrote down anywhere.
  - Fix: write the ordered steps in plain language first, even five bullet points.
- **No clear stop condition.** An algorithm without a defined end runs forever or fails unpredictably.
  - Fix: state the starting point, the finishing point, and every step between, explicitly.
- **Only describing the happy path.** The steps work when everything succeeds and fall apart the moment one step fails.
  - Fix: for every step, decide what happens on failure before moving to the next one.

**Optimizing the rebuilt solution**

- **Optimizing before measuring.** People are frequently wrong about where a solution is actually slow or expensive — the "obvious" bottleneck usually isn't the real one.
  - Fix: profile or measure first, find where time/resources actually go, then optimize that spot. In practice, a small fraction of the design accounts for most of the cost — optimize that fraction, not your guess.
- **Optimizing too early, at the cost of clarity.** A "fully optimized" version that nobody can follow introduces more problems than it prevents, and most micro-optimizations save only a few percent.
  - Fix: get the algorithm right first — algorithm-level improvements dwarf micro-optimizations. Only optimize fine detail once the design has stabilized.
- **Optimizing something that will change anyway.** Polishing a part of the solution that's about to be redesigned wastes the work twice.
  - Fix: optimize after the design has stabilized, not before.

## Judgment mistakes

- **Applying it to every decision, including the boring, reversible ones.** Re-deriving a solved, low-stakes problem from raw materials burns effort for no new information.
  - Fix: reasoning by analogy is the right tool when the problem is well-precedented and cheap to get wrong — save first-principles effort for where the current approach is genuinely expensive, uncertain, or worth challenging.
- **Confusing contrarianism with first-principles thinking.** Doubting an assumption because it's old, without checking anything, is just doubt wearing a lab coat.
  - Fix: the method needs an actual answer to "what would prove this true or false," not just suspicion.
- **Treating "nobody has done this" as proof it can't be done.** This is the inverse mistake — accepting a limit as a law of nature because it hasn't been broken yet, the same error as accepting a price as fixed because it's always been quoted that way.
  - Fix: ask specifically what would have to be true for the limit to hold, and check whether that's still the case.
- **Treating the six moves as a one-time, linear pass instead of a loop.** Abstracting can reveal a pattern you missed; a broken algorithm can mean the decomposition was wrong in the first place.
  - Fix: after the evaluate check fails, go back to whichever move the failure actually points to — don't just patch the symptom in the rebuilt solution.

Continue to [Best Practise](best-practise.md).
