# Meeting — Middle

**Your question:** How do I design a meeting that builds alignment and surfaces disagreements, not just rubber-stamps a decision?

Junior level teaches you to run a focused meeting with a clear purpose. At middle level, you're designing meetings that build shared understanding and surface disagreements early, before they become problems. The goal is not to get everyone to agree — it's to make sure everyone understands the trade-offs and the reasoning.

## The method: frame, discuss, decide

1. **Frame the problem clearly.** What are we trying to solve? What are the constraints? What are the trade-offs?

2. **Present options, not a recommendation.** If you present one option, people will either agree or disagree. If you present multiple options with trade-offs, people will think about the problem.

3. **Invite disagreement.** "I want to hear if you think I'm missing something or if you'd approach this differently."

4. **Listen for the real disagreement.** Often disagreement is not about the decision itself, but about underlying assumptions or values.

5. **Make the decision.** After discussion, make a clear decision. Document the reasoning, including what you considered and why you chose this option.

## Realistic scenario: Choosing a database

**Bad meeting:**
"We need a new database. I think we should use PostgreSQL. Does anyone disagree?"

Problems:
- You've already decided
- People don't understand the trade-offs
- Disagreement is framed as "wrong"

**Good meeting:**
"We need a new database to support our growing data needs. Here's what we know:
- We need to support 100M records
- We need to query across multiple dimensions
- We need strong consistency
- We need to scale horizontally

I've evaluated three options:

**Option 1: PostgreSQL**
- Pros: Strong consistency, rich query language, mature
- Cons: Vertical scaling only, complex sharding
- Effort: 2 weeks to set up, 4 weeks to migrate

**Option 2: MongoDB**
- Pros: Horizontal scaling, flexible schema
- Cons: Eventual consistency, weaker query language
- Effort: 1 week to set up, 2 weeks to migrate

**Option 3: Cassandra**
- Pros: Horizontal scaling, high availability
- Cons: Eventual consistency, complex operations
- Effort: 3 weeks to set up, 6 weeks to migrate

Here are the trade-offs:
- Consistency vs. scalability: PostgreSQL is consistent but harder to scale. MongoDB and Cassandra scale but are eventually consistent.
- Operational complexity: PostgreSQL is simpler to operate. Cassandra is complex.
- Migration effort: MongoDB is fastest, Cassandra is slowest.

I'm leaning toward PostgreSQL because our consistency requirements are strict and our current scale doesn't require horizontal scaling yet. But I want to hear your thoughts.

What am I missing? Would you approach this differently?"

Better because:
- You've framed the problem and constraints
- You've presented multiple options with trade-offs
- You've stated your reasoning
- You've invited disagreement

**During the discussion:**
- Engineer 1: "I'm worried about sharding complexity. What if we need to scale horizontally in 6 months?"
- Engineer 2: "I've used MongoDB at my last company. It was great for flexibility but we had consistency issues."
- You: "Good points. Let me ask: how important is horizontal scaling in the next 12 months? And how much consistency do we really need?"

**After the discussion:**
"Here's what I heard: we're concerned about scaling and consistency. Let me propose this: we go with PostgreSQL for now because our consistency requirements are strict. We'll design the schema to support sharding if we need it later. We'll revisit this decision in 6 months when we have more data on growth.

Does that address your concerns?"

## Surfacing disagreements

Disagreements are valuable — they expose assumptions and risks. But only if you surface them early.

**How to surface disagreements:**
1. **Invite them explicitly.** "I want to hear if you disagree."
2. **Make it safe to disagree.** "Disagreement is good. It helps us make better decisions."
3. **Listen for the real disagreement.** Often it's not about the decision itself, but about underlying values or assumptions.
4. **Acknowledge the disagreement.** "I hear you. You're concerned about scalability. That's a valid concern."
5. **Decide anyway.** After hearing the disagreement, make a clear decision. You don't need consensus; you need to understand the trade-offs.

## Building alignment

Alignment is not agreement. Alignment is when everyone understands the decision and the reasoning, even if they would have chosen differently.

**How to build alignment:**
1. **Explain the reasoning.** Why did you choose this option? What trade-offs did you consider?
2. **Acknowledge the trade-offs.** "We're choosing consistency over scalability. That means we might need to revisit this in 6 months."
3. **Commit to revisit.** "We'll review this decision in 6 months. If our assumptions change, we'll reconsider."
4. **Document the decision.** Write down what was decided, why, and what assumptions it's based on.

## When to meet vs. when not to meet

Not every decision requires a meeting. Ask yourself:
- **Is there disagreement?** If everyone agrees, send an email.
- **Do people need to discuss?** If it's just information sharing, send an email.
- **Is the decision reversible?** If it's reversible, decide quickly. If it's not, take more time.
- **Is the decision urgent?** If it can wait, gather more information first.

## Test yourself

1. How do you present options without biasing people toward your preference?
2. What's the difference between alignment and agreement?
3. How do you surface disagreements in a meeting?
4. When should you meet vs. send an email?

Continue to [`senior.md`](senior.md).
