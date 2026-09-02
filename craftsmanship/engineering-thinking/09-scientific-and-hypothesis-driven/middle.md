# Scientific and Hypothesis-Driven Thinking — Middle

**Your question:** How do I design a real experiment — with a baseline and one isolated variable — instead of just trying something and eyeballing the result?

Junior level teaches you to state a falsifiable prediction and measure before/after. At middle level, "before/after on my laptop" stops being good enough, because real systems change for reasons that have nothing to do with your code — traffic shifts, other deploys land, caches warm up differently. A real experiment has to isolate your one variable from everything else that's moving.

## The method: baseline, one variable, watch for confounds

1. **Establish a baseline (control).** Measure the current behavior under conditions as close as possible to the ones the treatment will run under — same traffic pattern, same time of day, same hardware.
2. **Change exactly one variable.** If you change the serialization format *and* the connection pool size in the same test, a result can't tell you which one mattered.
3. **Run the treatment under matching conditions.** Same input distribution, same load, same measurement method as the baseline — only the one variable differs.
4. **Actively look for confounds.** A confound is something else that changed at the same time and could explain the result instead of your variable. Ask: "what else happened during this window?"
5. **Compare treatment to baseline, not treatment to your prediction alone.** The baseline is what tells you the treatment caused the difference, not just that time passed.

## Write the experiment design before touching code

Junior-level checks can live in your head. A real experiment should be written down *before* you run it, so you can't unconsciously shift the goalposts once you see the result. At minimum, write:

```text
Hypothesis:   What you believe, with the mechanism and the predicted number.
Baseline:     What you're comparing against, and under what conditions.
Variable:     The single thing that differs between baseline and treatment.
Population:   What traffic, users, or inputs this experiment covers.
Metric:       The one number that decides the outcome.
Duration:     How long or how many repetitions before you look at the result.
Decision:     What you'll do for each possible outcome (helped / no effect / hurt).
```

Filling this in forces two useful things to happen before any code changes: you notice if the metric is actually measurable with your current tooling, and you notice if you don't actually know what you'd do with a "no effect" result — which usually means the experiment isn't worth running yet.

## Confounds: the trap that invalidates a result

A confound doesn't make your test *look* wrong — it makes it wrong while still looking clean. Common sources:

| Confound | How it sneaks in |
|---|---|
| A second deploy landed in the same window | Another team's change to a shared dependency ships the same afternoon as your test |
| Traffic pattern shifted | A marketing campaign or batch job spikes traffic during your "after" window but not your "before" window |
| Cache state differs | Baseline ran cold; treatment ran after the cache had warmed up from earlier requests |
| Time-of-day effect | Baseline measured at 2am traffic, treatment measured at 2pm traffic |
| Measurement method changed | Baseline used server-side timing; treatment accidentally included client network latency |

**The check:** before trusting a result, ask "what else changed in this window besides my one variable?" If you can't rule something out, the result is a correlation, not evidence of causation.

## A concrete example: serialization format change

**Proposal:** Switch internal service-to-service communication from JSON to Protobuf to reduce latency and payload size.

**Baseline (control):** Current JSON-based calls between the order service and the pricing service, measured over one hour of production-mirrored traffic replayed in staging. p50 = 18ms, p95 = 64ms, average payload = 2.1KB.

**One isolated variable:** Serialization format only. Same staging environment, same replayed traffic, same hardware, same hour-long window shape, same connection pool configuration — nothing else changes.

**Treatment:** Protobuf-encoded calls, same replayed traffic. p50 = 11ms, p95 = 39ms, average payload = 0.6KB.

**Confound check:** Was anything else different between the two runs? The team notices the Protobuf run happened after a JVM restart, so the JIT compiler hadn't fully warmed up — which would bias *against* Protobuf, not for it, so the result direction is trustworthy. They also confirm no other deploy touched the pricing service in either window, and both runs replayed the identical captured traffic file, ruling out a traffic-shape confound.

**Conclusion:** The latency and payload improvements are attributable to the serialization change, not to an uncontrolled variable — because the one thing that differed between runs was the format, and the one thing that could have biased the result worked against the outcome observed, not toward it.

## How many repetitions are enough

A single run of a benchmark is a sample of one, and single samples are noisy — a background process, a cold cache, or a GC pause can swing one run by double digits of percent. Before trusting a benchmark-style result:

- **Run it more than once.** Three to five repetitions of both baseline and treatment is a reasonable floor for a local or staging benchmark; note the spread (min/max or standard deviation), not just one number.
- **Check the spread against the effect you're claiming.** If baseline runs vary between 400ms and 460ms on their own, a treatment result of 410ms is not obviously an improvement — it's within the noise you already observed in the baseline alone.
- **Discard warm-up runs deliberately, not accidentally.** If the first run is always slower (JIT warm-up, cold cache), decide up front whether you're measuring cold-start behavior or steady-state behavior, and be consistent between baseline and treatment.
- **Prefer the median or a percentile over the mean for latency-style measurements.** A few outlier runs (a stalled CI runner, a network blip) can drag a mean far from what a typical run looks like.

This is a lightweight version of a real statistical concern — at senior level, the same question ("is this difference bigger than the noise?") gets a more rigorous treatment for production-scale experiments.

## Time-boxed spikes: retire one unknown before building

A spike is not a smaller version of the feature — it's a throwaway experiment whose only job is to answer one specific question before you commit real engineering time.

**How to run one:**

1. **Write the one question the spike must answer.** Not "explore the new search library" — "can the new search library sustain 50 req/s at under 100ms p95 with our real index size?"
2. **Time-box it.** A day or two, not open-ended. If the question isn't answered by the deadline, that itself is information (the unknown is bigger than expected).
3. **Write throwaway code.** No error handling, no tests, no production concerns — the code exists only to produce the measurement.
4. **Answer the question, then stop.** Don't let the spike quietly become the production implementation; if the answer is "yes," a real implementation still needs to be built properly.
5. **Record the answer and discard the code**, or explicitly flag it for a full rewrite before it ships.

**Example:** Before committing two weeks to migrating search infrastructure, a two-day spike answers only: "does the candidate library return correct results for our top 20 query patterns, and can it hit 50 req/s at under 100ms with our current index size?" The spike script hardcodes credentials, skips retries, and would never pass code review — and that's fine, because it never ships. The answer ("yes, but p95 was 140ms until we added a warm cache") shapes the real design before a single line of production code exists.

## Common mistakes at middle level

| Mistake | Fix |
|---|---|
| Comparing treatment to a baseline measured under different conditions (different time, different traffic) | Re-measure the baseline under matching conditions, in the same window if possible |
| Changing two variables in one test because "we're already in there" | Split into two sequential experiments; resist the urge to batch changes |
| Skipping the confound check because the result looked good | Ask "what else changed?" precisely *because* the result looked good — good results get less scrutiny by default, not more |
| Letting a spike's throwaway code get merged into production | Decide before starting whether the spike's output is a decision or a deliverable; if it's a decision, delete the code once it's answered |
| Treating a spike with no time box as "still exploring" indefinitely | Set the deadline before starting; a spike with no end date isn't retiring an unknown, it's just unplanned work |
| Trusting a single benchmark run because the number looked convincing | Run it several times and compare the spread; a single run can't distinguish a real effect from noise |
| Writing the experiment design after seeing the result, to match what happened | Write hypothesis, metric, and decision rule before running anything — a design written after the fact isn't a test, it's a story |

## Hands-on exercise

Pick a change you're planning that isn't trivial to reverse.

1. Write the baseline you'd need to measure, and the exact conditions (traffic, time window, environment) it must match.
2. Name the single variable your experiment isolates.
3. List three things that could confound the result if they changed at the same time as your variable.
4. If there's an unknown blocking the decision (will this library handle our load? will this API return what we need?), write the one question a time-boxed spike would answer, and the time box.
5. Decide in advance: if the spike's code turns out useful, what has to happen before any of it reaches production?
6. Fill in the experiment-design template (hypothesis, baseline, variable, population, metric, duration, decision) for this change, and check whether you can actually name a decision for every possible outcome.

## Verify your thinking

- [ ] Did you write the experiment design (hypothesis, metric, decision rule) before running anything, not after?
- [ ] Did you measure the baseline under conditions that match the treatment, not just "recently"?
- [ ] Did you change exactly one variable between baseline and treatment?
- [ ] Did you actively check for confounds, especially when the result looked good?
- [ ] Did you run enough repetitions to know whether your result is bigger than the normal spread?
- [ ] If you ran a spike, did it answer one specific question within a fixed time box?
- [ ] Would a teammate reviewing your experiment be able to name what, besides your variable, could explain the result?

Continue to [`senior.md`](senior.md).
