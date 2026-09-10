# Systems Thinking — Middle

**Your question:** Is this feedback loop balancing or reinforcing, and where's the leverage point that changes it?

Junior level teaches you to find a loop. At middle level, you classify it — because the fix that's safe for one kind of loop makes the other kind worse — and you learn to pick a change with outsized effect instead of the first parameter that looks tunable.

## Classify the loop: balancing or reinforcing

**Balancing loop:** self-correcting. It pushes a variable *toward* a target and settles.
- An autoscaler adds pods until CPU utilization drops back to target, then stops.
- A rate limiter throttles requests until the queue drains, then admits more.
- A retry with a low, fixed cap (2 attempts, then fail fast) resolves transient blips without compounding.

**Reinforcing loop:** self-amplifying. It has no built-in limit — it grows (or shrinks) until something *external* to the loop stops it, usually by breaking.
- Timeouts triggering retries that add load that causes more timeouts.
- A cold cache getting colder as traffic drops, driving traffic down further.
- Technical debt slowing delivery, which forces rushed changes, which adds more debt.

**Why the distinction matters:** the same-looking intervention — "add more capacity," "increase the retry count," "add another cache layer" — is a safe tweak inside a balancing loop and fuel inside a reinforcing one. If you can't tell which kind you're looking at, you can't tell whether your fix will stabilize the system or accelerate its collapse.

### How to tell them apart

1. **Perturb it mentally.** If you nudge the variable up, does the loop push back (balancing) or push further in the same direction (reinforcing)?
2. **Check for a built-in stopping condition.** Balancing loops have one by design (a target, a cap, a limit). Reinforcing loops stop only when something outside the loop breaks — a connection pool exhausts, memory runs out, users leave.
3. **Look at the trend, not the snapshot.** A single spike doesn't tell you which kind of loop you have. A metric that keeps climbing *after* the triggering event ends is reinforcing.

### A balancing loop that looks broken

**Symptom:** `CheckoutService`'s pod count oscillates between 8 and 14 every few minutes during a busy afternoon. An on-call engineer, paged by a "pod count changed" alert, assumes the autoscaler is misconfigured and disables it, pinning replicas at 14.

**What's actually happening:** This is a balancing loop working as designed — CPU rises, the autoscaler adds pods, CPU falls, the autoscaler removes the ones it no longer needs, and the cycle repeats around a moving target as traffic itself fluctuates. The oscillation *is* the loop converging, not the loop failing.

**Why it matters:** Pinning replicas at the peak "fixes" the alert but removes the balancing loop's ability to scale back down overnight, quietly tripling compute spend. Classifying the loop correctly — balancing, not broken — points to tuning the alert threshold (a low-leverage, appropriate fix here) instead of removing the loop entirely (a structural change applied to a loop that didn't need one).

**Lesson:** classification isn't only about spotting danger in reinforcing loops. Misreading a healthy balancing loop as broken, and "fixing" it by disabling the loop itself, is the mirror-image mistake — solving a problem that wasn't there by removing a mechanism that was working.

## Find the leverage point, not the nearest knob

A leverage point is a place in the loop where a small change produces a disproportionate effect. Not every place in a loop is equally powerful to change:

| Leverage | Example change | Effect |
|---|---|---|
| Low | Tune a numeric parameter (retry count, timeout value, pool size) | Shifts *when* the loop breaks, rarely *whether* it breaks |
| Medium | Change what information flows and when (surface queue depth before it's critical, alert earlier) | Lets the system — or a human — react before the loop runs away |
| High | Change the rule the loop obeys (circuit breaker, backpressure, admission control) | Changes the loop's *structure*, not just its speed |
| Highest | Change what the system is optimizing for (the goal itself) | Changes what "correct" behavior even means — rarely available without redesign, covered at senior level |

**Rule of thumb:** if your proposed fix is a number (raise the retry count, add 2 more replicas, extend the timeout), you are pulling a low-leverage lever inside a loop you haven't changed the shape of. That's fine for a balancing loop under normal load. It's dangerous for a reinforcing one.

### Recognize the pattern in other domains

The same low-vs-high-leverage split shows up outside infrastructure code:

| Domain | Low-leverage move | High-leverage move |
|---|---|---|
| Support queue backlog | Hire more support agents | Change the rule for what reaches a human vs. self-service |
| Feature flag rollout | Raise the rollout percentage faster | Change the promotion rule from "time-based" to "metric-gated" |
| On-call load | Add people to the rotation | Change what's allowed to page a human at all (alert severity policy) |
| Code review backlog | Ask reviewers to review faster | Change the rule for what size of diff requires full review vs. a lighter check |

In each row, the low-leverage move adds more of the same resource to a loop whose *rule* is unchanged — it buys time without changing the dynamic. The high-leverage move changes what the loop is allowed to do, which is why it tends to require more design work and more agreement to ship, but survives longer than a headcount or capacity bump.

## Anticipate second-order effects: ask "and then what?" twice

Before shipping a change to a loop, state the first-order effect, then ask "and then what happens because of that?" at least twice.

### Worked scenario

**Proposed fix:** Checkout drops 2% of orders to payment-gateway timeouts. Increase the retry count from 2 to 5 to reduce dropped orders.

**First-order effect:** Fewer orders are lost to a single transient timeout. Drop rate should fall.

**And then what?** During a real gateway slowdown (not a blip — sustained saturation), every one of those extra 3 retries per request also hits the gateway. Retry volume roughly triples during exactly the window when the gateway can least afford it.

**And then what happens because of that?** The gateway, already near its connection-pool limit, saturates *faster* and stays saturated *longer* than before the change. The incident that used to self-resolve in 4 minutes (gateway recovers once load drops) now takes 25 minutes, because retry traffic is keeping load elevated even after the initial spike passed.

**Verdict:** the fix looks correct in isolation (reduces drops under a one-off blip) and makes the reinforcing loop worse under sustained load — exactly the condition the fix was meant to help with. This is a low-leverage change (a number) applied to a reinforcing loop, and it doesn't survive two rounds of "and then what."

**Higher-leverage alternative:** cap concurrent in-flight retries with a circuit breaker, and use exponential backoff with jitter instead of a fixed 2-second delay. This changes the loop's *rule* — retries stop compounding once the gateway shows saturation — rather than changing how many times the loop repeats.

## Verification: trace the loop under two conditions

A fix that's safe only under normal load isn't verified yet.

- **Normal-load check:** Does the change behave as intended when the system is healthy? (Retries still recover from a one-off blip.)
- **Saturated-load check:** Does the change behave safely when the upstream dependency is already struggling? (Retries back off instead of adding to the pile-on.)
- **Trend check:** After the fix, does the affected metric return to baseline once the triggering event ends, or does it keep climbing past the event? A metric still climbing after the trigger stopped is evidence the loop is still reinforcing.

## Common mistakes at middle level

| Mistake | Fix |
|---|---|
| Tuning a parameter inside a reinforcing loop instead of changing its rule | Ask whether the loop has a built-in stop; if not, add one (breaker, backpressure) rather than a bigger number |
| Calling a balancing loop "broken" because it oscillates near its target | Autoscalers and rate limiters hunt around equilibrium by design — check whether it's converging, not whether it's perfectly flat |
| Shipping a change after asking "and then what" zero times | Write the first-order effect, then force yourself to write two more rounds before merging |
| Adding a fix that helps this week's incident and strengthens the reinforcing loop for the next one | Test the fix under saturated-load conditions, not just the blip that motivated it |
| Treating "hasn't blown up yet" as "safe" | A reinforcing loop with a high limiting threshold looks stable right up until traffic crosses it — check the threshold, not just current behavior |

## Hands-on exercise

Take a recent change you shipped or reviewed — a PR, an incident hotfix, a config bump.

1. Identify the loop it touches. Is it balancing or reinforcing? State your evidence (does it have a built-in stop, or not?).
2. Write the first-order effect of the change in one sentence.
3. Ask "and then what happens because of that?" twice, in writing.
4. Classify the change's leverage: is it a parameter (low), a visibility change (medium), or a rule change (high)?
5. If the change is low-leverage inside a reinforcing loop, propose one rule-level alternative.

## Verify your thinking

- [ ] Can you state, with evidence, whether the loop you're changing is balancing or reinforcing?
- [ ] Did you write out two rounds of "and then what happens because of that?" before considering the fix done?
- [ ] Can you name the leverage level (parameter, visibility, or rule) of your proposed change?
- [ ] Did you check the fix under saturated-load conditions, not just the normal case?
- [ ] After the triggering event ends, does the affected metric return to baseline, or keep moving?

Continue to [`senior.md`](senior.md).
