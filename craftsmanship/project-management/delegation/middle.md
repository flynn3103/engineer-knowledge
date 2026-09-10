# Delegation — Middle

**Your question:** How do I hand off a task and let someone own it, while staying informed and making sure it doesn't fail?

Junior level teaches you to be clear and set checkpoints. At middle level, you're delegating bigger pieces of work — not a single task, but a project or area of responsibility. The challenge is to let someone own the outcome without abandoning them, and to know when to step in.

## Delegation with ownership

Ownership means:
- The person makes decisions about how to do the work
- They are accountable for the outcome
- They come to you with problems, not for permission
- You trust them to escalate if they need help

**Ownership is not:**
- Doing whatever they want without feedback
- Leaving them alone to figure it out
- Abdicating responsibility if it fails

## The method: frame the problem, not the solution

1. **Frame the problem clearly.** "We need to reduce payment processing latency from 5s to under 1s. It's currently a bottleneck for checkout. Here's what we know about the current system."

2. **State the constraints and trade-offs.** "We can't change the payment gateway API. We can add caching, but it needs to be consistent with our inventory system. We have 2 weeks."

3. **Let them propose the approach.** "How would you tackle this? What would you try first? What's your biggest uncertainty?"

4. **Agree on the approach and success criteria.** "OK, let's start with caching. We'll measure success as: latency under 1s for 95% of requests, no increase in payment failures, and the solution is maintainable by the team."

5. **Set decision rights.** "You can make decisions about caching strategy, database changes, and testing approach. If you want to change the payment gateway integration, let's discuss it first."

6. **Establish communication cadence.** "Let's sync twice a week. I want to know about blockers immediately, not at the sync."

7. **Review progress and adjust.** At each sync, ask: "What did you learn? What's your biggest blocker? Do we need to adjust the approach?"

## Knowing when to step in

You should step in if:
- The person is stuck and hasn't asked for help (they might not know they're stuck)
- The approach is heading toward failure and they don't see it
- The work is affecting other teams and they don't know
- The person is working too hard and burning out

You should NOT step in if:
- The approach is different from what you would do (but might work)
- The person is learning something new and making mistakes
- The work is on track but slower than you'd like
- You're just curious about the details

## Realistic scenario: Delegating a system redesign

**The problem:** Your database is becoming a bottleneck. You need to redesign the data model to support sharding.

**Bad delegation:**
"We need to redesign the database for sharding. Here's how I think we should do it: use a hash-based sharding key, add a sharding layer, and migrate data incrementally. Let me know when you're done."

Problems:
- You've already decided the approach
- The person can't learn or make decisions
- If it fails, it's your design, not theirs

**Good delegation:**
"Our database is becoming a bottleneck. We need to support sharding to scale. Here's what I know: we have 100M users, we're growing 20% YoY, and we need to support 10x growth without a complete rewrite.

I've sketched a few approaches: hash-based sharding, range-based sharding, and a hybrid. Each has trade-offs in terms of complexity, migration cost, and operational overhead.

I want you to:
1. Evaluate the approaches. Which one would you recommend and why?
2. Design the data model for your recommended approach.
3. Plan the migration strategy. How do we get from here to there without downtime?
4. Estimate the effort and timeline.

Constraints:
- We can't take the system offline for migration
- We need to support both old and new data models during transition
- The solution needs to be maintainable by the team

Let's sync Monday to discuss your initial thoughts. I want to understand your reasoning before you dive deep."

Better because:
- You've framed the problem and constraints
- You've given them the information you have
- You've let them choose the approach
- You've set a checkpoint to discuss reasoning before they commit

**At the Monday sync:**
"I like your recommendation for hash-based sharding. I was leaning toward range-based because it's easier to rebalance, but your point about query patterns is good. Let's go with hash-based.

One thing I'm concerned about: the migration strategy. How do we handle the case where a user's data is split across old and new shards during transition? Let's think through that together."

This is stepping in on a specific concern, not taking over the whole project.

## Feedback and course correction

At each checkpoint:
1. **Ask what they learned.** "What surprised you? What would you do differently?"
2. **Give feedback on the approach.** "I like how you thought about the migration. Here's a risk I see: what if the sharding key is unbalanced?"
3. **Adjust if needed.** "Let's add a rebalancing strategy before we commit to this."
4. **Celebrate progress.** "This is solid work. You've thought through the hard parts."

## Under-delegation and over-delegation

**Under-delegation:** You keep too much control. The person doesn't learn, and you become a bottleneck.

**Over-delegation:** You hand off too much without enough support. The person gets stuck and doesn't ask for help.

Start with clear framing and regular checkpoints. Adjust based on how the person responds.

## Test yourself

1. What is the difference between ownership and autonomy?
2. How do you know when to step in vs. let someone figure it out?
3. What should you do if someone's approach is different from yours but might work?
4. How do you give feedback without taking over the work?

Continue to [`senior.md`](senior.md).
