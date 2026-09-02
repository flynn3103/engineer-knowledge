# Critical Thinking — Middle

**Your question:** Which cognitive bias is actually shaping this team decision, and how do I weigh the real evidence instead?

Junior level teaches you to separate a single claim from its evidence. At middle level, the problem is bigger: a whole team decision — "should we migrate to the new queue system," "should we keep this flaky test suite" — is being shaped by a bias nobody named out loud. The individual sentences might each sound reasonable. The distortion is in *which* evidence got sought, *which* got ignored, and *why* the discussion converged where it did.

## Recognize the three biases you'll see most in team decisions

**Confirmation bias** — the team already favors an option and only surfaces evidence that supports it.
- Signature: benchmarks get run for the preferred option but not the alternative; risks of the favored choice get "we'll figure it out," risks of the alternative get itemized in detail.
- Example: the team wants to adopt gRPC. Three people share blog posts about gRPC's performance wins. No one runs the equivalent benchmark against the current REST setup with connection pooling and caching applied — the honest baseline.

**Sunk cost** — the team keeps investing because of past effort, not future value.
- Signature: "we've already spent six weeks on this" appears in the argument for continuing, but never as evidence about what continuing will *cost or return going forward*.
- Example: a team keeps extending a custom ORM layer that fights the ecosystem at every turn, because "we already built most of it" — the six weeks already spent cannot be recovered either way, and is irrelevant to whether the next six weeks are worth spending.

**Anchoring** — the first number or opinion stated in the discussion dominates everyone after it.
- Signature: the estimate a senior engineer throws out in the first two minutes of a meeting becomes the number everyone else's estimate clusters around, even people who hadn't thought about it yet.
- Example: someone opens a sizing discussion with "this feels like a two-week job." Every subsequent estimate lands between 1.5 and 2.5 weeks, even from people who, asked cold, would have said six.

## The method: Deconstruct the argument's structure

Every argument for a decision has **premises** (the supporting claims) and a **conclusion** (the recommended action). Bias usually hides in a specific premise, not in the conclusion itself.

1. **Write the conclusion in one sentence.** "We should migrate the queue from RabbitMQ to Kafka."
2. **List every premise offered for it**, as separate sentences.
3. **For each premise, mark: fact (verifiable, and verified), assumption (verifiable, not verified), or opinion (not independently verifiable).**
4. **Find the weakest premise the conclusion actually depends on.** If you remove it, does the conclusion still hold on the remaining premises?
5. **Ask what evidence-gathering was skipped**, and whether the pattern of what got checked vs. skipped matches one of the three biases above.

### Worked example: deconstructing a real argument

**Conclusion:** "We should migrate the queue from RabbitMQ to Kafka."

**Premises offered:**
1. "Kafka handles higher throughput." (Fact in general, but unverified for *our* current load — we're at 400 msgs/sec against a broker rated for 10k+.)
2. "We're going to need to scale eventually." (Assumption — no current growth data cited.)
3. "The team that built our observability platform used Kafka and it worked well for them." (Anecdote from a different domain and different team.)
4. "We already spent two sprints prototyping the Kafka integration." (Sunk cost — irrelevant to future value.)
5. "Migrating now avoids a bigger migration later." (Assumption dressed as fact — assumes growth will happen, and that a later migration would be costlier, neither established.)

**Deconstruction result:** Premise 1 is the only one resembling hard evidence, and even it's unverified for the actual current load — 400 msgs/sec is comfortably inside RabbitMQ's range. Premises 2, 3, 4, 5 are assumption, anecdote, sunk cost, and unverified prediction. The conclusion is standing almost entirely on premise 4 (sunk cost) and premise 3 (anecdote) — the two weakest kinds of support.

**What this argument needs to survive scrutiny:** actual current throughput and its growth trend over the last two quarters (not a guess), a cost comparison of migrating now vs. migrating later once growth is confirmed, and an explicit acknowledgment that the two sprints already spent don't change what the next six months of either path cost.

## Weigh competing evidence with an explicit method

"The loudest voice wins" and "whoever spoke first wins" are not evidence-weighing methods — they're bias delivery mechanisms (anchoring and authority bias, respectively). Use this instead:

1. **List every piece of evidence on both sides**, not just the side that's winning the room.
2. **Rate each piece: direct (measured on our system, our data) or indirect (from someone else's system, a blog post, a general principle).**
3. **Weight direct evidence higher than indirect evidence, by default** — someone else's benchmark on someone else's workload is a hypothesis about your system, not a fact about it.
4. **Check dates.** A benchmark from three major versions ago may no longer hold.
5. **If the evidence is thin on both sides, say so explicitly** and treat the decision as a bet with a defined re-evaluation point, not a settled fact.

## Common mistakes at middle level

| Mistake | Why it hurts | Fix |
|---|---|---|
| Naming a bias as an accusation ("you're just anchored") | Turns a reasoning problem into a personal attack; people get defensive instead of re-examining evidence | Name the *pattern*, not the person: "the first estimate might be anchoring the rest of us — let's re-estimate independently" |
| Treating "we discussed it a lot" as "we evidenced it a lot" | Volume of discussion time has nothing to do with evidence quality | Ask, after a long discussion: what new data did we actually surface, versus how many times did we restate opinions? |
| Weighing an anecdote from a FAANG blog post the same as data from your own system | Their scale, traffic shape, and constraints are almost certainly different from yours | Default to direct evidence; treat outside anecdotes as a hypothesis to test, not a conclusion to adopt |
| Letting the sunk-cost premise go unchallenged because it's emotionally uncomfortable | The team keeps paying for a decision that no longer pays off, because reversing feels like admitting the past investment was wasted | Explicitly separate "what did this cost us" from "what does continuing cost us" — only the second number belongs in the decision |

## Hands-on exercise

Pick a decision your team made or is currently debating (a library choice, a "let's rewrite X," a process change).

1. Write the conclusion in one sentence.
2. List every premise that was actually stated in support of it.
3. Classify each premise: fact (verified), assumption (unverified), or opinion.
4. Circle any premise that references past investment ("we already...") — check whether it's being used as evidence about the future, which it can't be.
5. Name which of the three biases (confirmation, sunk cost, anchoring) best explains why the discussion landed where it did, if any.
6. Write one question that, if answered with real data, would most change the strength of the conclusion.

## Verify your thinking

- [ ] Can you separate every premise in the argument from its conclusion?
- [ ] Can you say, for each premise, whether it's fact, assumption, or opinion?
- [ ] Can you name a piece of evidence the team *didn't* look for, and why that gap matters?
- [ ] Can you tell the difference between "we spent a lot of time discussing this" and "we gathered a lot of evidence"?
- [ ] If you removed the sunk-cost argument entirely, would the conclusion still hold?

Continue to [`senior.md`](senior.md).
