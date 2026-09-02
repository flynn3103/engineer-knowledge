# First-Principles Thinking — Middle

**Your question:** What would I build if I started from the fundamentals instead of the nearest existing pattern?

Junior level teaches you to check whether a small rule is a real constraint or borrowed precedent. At middle level the stakes are bigger: you're choosing an approach for a whole feature or component, and the fastest path is always "copy the nearest pattern we already have." That's often correct — most problems really are similar to ones already solved. The risk is doing it *by default*, without ever checking whether the fundamentals of your problem actually match the fundamentals of the problem the pattern was built for.

## The method: Rebuild from fundamentals, then compare with precedent

1. **State the actual need as an outcome, not as the shape of an existing solution.** Not "we need a message queue" — "we need an email to eventually send even if a worker crashes mid-send, with no duplicate sends the user notices, at roughly 200 events/day."
2. **List the true fundamentals**, each backed by a number or a rule, not a guess: real scale, real latency budget, real failure tolerance, real consistency requirement, real cost ceiling.
3. **Derive a solution shape from those fundamentals alone**, as if no existing pattern in your codebase existed. What's the smallest mechanism that satisfies every fundamental you listed?
4. **Only now compare with the nearest existing pattern or precedent.** Does the precedent's design match the fundamentals you just derived, or was it built for a different set of numbers?
5. **If they match:** use the precedent — it's reasoning-by-analogy that just survived a first-principles check, and you get the benefit of proven code for free. **If they diverge:** the divergence names exactly which assumption doesn't transfer, and that's your signal to build something different, not to force-fit the existing pattern.

## A worked scenario

**Proposal:** "We need to fan out a notification when an order ships. We always use Kafka for event fan-out — let's add a topic."

**Step 1 — state the outcome:** Notify up to 5 downstream consumers (email, SMS, warehouse dashboard, analytics, loyalty-points service) within about a minute of an order shipping. Occasional duplicate delivery is fine because every consumer is already idempotent. No ordering guarantee is required across consumers.

**Step 2 — list the fundamentals, with numbers:**
- Volume: ~200 ship events/day, bursting to ~40/hour during a sale.
- Latency budget: consumers need the event within 60 seconds, not milliseconds.
- Durability: an event must not be silently lost if a consumer is down for a few minutes.
- Consumers: 5 known, internal, stable — not an open set of external subscribers.

**Step 3 — derive a solution from those fundamentals alone:** at 200 events/day with a 60-second budget and 5 known internal consumers, the smallest mechanism that satisfies every fundamental is an outbox table written in the same transaction as the order-ship update, plus a worker that polls it every 10 seconds and calls each consumer. No broker, no partitioning, no consumer-group coordination — none of those are needed to satisfy anything on the list.

**Step 4 — compare with the precedent:** the existing Kafka cluster was stood up for the checkout event stream, which runs at ~50,000 events/sec, needs strict per-key ordering, and serves consumers the team doesn't control (external partners). None of those fundamentals hold for order-ship notifications.

**Step 5 — decide:** skip Kafka for this feature. Use the outbox-and-poll pattern; it's simpler to operate, has one fewer moving part to fail, and every fundamental is met. Write down the threshold that would change the answer — e.g., "revisit if volume exceeds ~10,000 events/day or an external, uncontrolled consumer needs to subscribe" — so the next engineer doesn't have to redo this trace from scratch.

## Challenge one architectural assumption with evidence

Picking a fight with an assumption because it's old is not first-principles thinking — it's contrarianism wearing a lab coat. The method needs evidence, not just doubt:

1. **Name the assumption precisely.** "All writes go through the primary region" — not "our replication setup seems off."
2. **Name what evidence would prove or disprove it.** A load test, a query against real latency logs, a re-read of the actual SLA text, a count of how often the assumption has already been silently violated.
3. **Gather that evidence before proposing a change.** If you can't get the evidence, say so explicitly — "I believe X, but I haven't verified it" is honest; presenting a guess as a finding is not.
4. **Decide based on what the evidence actually shows**, including the possibility that the assumption holds and should stay.

## Recognize when analogy is doing the work

"It worked for company X," "our last project used this," "the framework's example does it this way" — these are all reasoning-by-analogy, and analogy is a legitimate shortcut, not a fallacy, when the underlying constraints actually match.

| Analogy is probably fine | Analogy is risky |
|---|---|
| The referenced system faced the same scale, latency, and failure requirements | The referenced system's numbers were never checked against yours |
| The cost of being wrong is low and easily reversed | The cost of being wrong is high, or the choice is expensive to undo |
| Someone has already verified the constraints transfer | "It worked elsewhere" is the entire argument, with no fundamentals listed |
| The problem is well-precedented and boring | The combination of constraints is actually new for your team |

The tell that analogy has quietly replaced reasoning is that nobody in the conversation can state the actual numbers for *your* system — only for the system being copied.

## Common mistakes at middle level

| Mistake | Fix |
|---|---|
| Defaulting to the nearest existing pattern without listing the fundamentals first | Write the outcome and the numbers before naming a solution, even if you expect to land on the same pattern |
| Deriving a solution "from fundamentals" using guessed numbers instead of measured ones | Get an actual figure — a log query, a load test, a spec — before it counts as a fundamental |
| Rejecting a working precedent purely because you personally didn't choose it | Compare its fundamentals to yours; reject it for a stated mismatch, not for unfamiliarity |
| Treating "it worked at my last company" as sufficient justification | State the constraints that made it work there, and check they hold here |
| Deriving a bespoke solution for a genuinely well-precedented, low-stakes problem | If the derived design matches the precedent, use the precedent — don't rebuild for its own sake |

## Hands-on exercise

Pick a component you're about to build or a recent one you built by copying an existing pattern.

1. Write the outcome it needs to produce, in one sentence, without naming any technology.
2. List 3-5 fundamentals with real numbers: scale, latency budget, failure tolerance, consistency requirement.
3. Derive a solution shape from those fundamentals alone, as if the existing pattern in your codebase didn't exist.
4. Compare it to the pattern you were about to copy (or already copied). Do the fundamentals match?
5. If they diverge, name the specific fundamental that doesn't transfer. If they match, note that the precedent is validated, not just habitual.

## Verify your thinking

- [ ] Can you state the outcome your solution needs to produce without naming a technology?
- [ ] Does every fundamental on your list have a number or a verifiable rule behind it, not a guess?
- [ ] Did you derive a solution before comparing it to the nearest existing pattern, not after?
- [ ] If you kept the existing pattern, can you say why its fundamentals actually match yours?
- [ ] If you challenged an assumption, did you gather evidence before proposing the change?

Continue to [`senior.md`](senior.md).
