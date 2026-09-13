# Meeting — Senior

**Your question:** How do I use meetings to guide decisions without controlling them? How do I know when not to meet?

Middle level teaches you to design meetings that surface disagreements and build alignment. At senior level, you're using meetings strategically — to guide decisions without controlling them, to know when a meeting is a waste of time, and to build a culture where meetings are rare and valuable.

## The method: guide, don't control

1. **Set the frame.** Define the problem, constraints, and decision rights. "We need to decide on the API design. The decision is yours; I want to make sure we've considered the trade-offs."

2. **Ask questions, don't give answers.** "What are the trade-offs between these approaches? What would break if we chose this option?"

3. **Surface assumptions.** "I notice we're assuming the API will be used by mobile clients. Is that a hard requirement?"

4. **Let them decide.** After discussion, let them make the decision. Your role is to make sure they've thought through the trade-offs, not to control the outcome.

5. **Support the decision.** Once they've decided, support it. Don't second-guess or undermine it.

## Knowing when not to meet

Meetings are expensive. A 1-hour meeting with 5 people is 5 hours of work. Ask yourself:

**Don't meet if:**
- The decision is reversible and low-risk (decide asynchronously)
- It's just information sharing (send an email or document)
- The decision maker is not present (reschedule)
- There's not enough information to decide (gather more data first)
- The decision is urgent but not important (decide quickly without a meeting)

**Do meet if:**
- The decision is irreversible or high-risk
- There's disagreement that needs to be surfaced
- You need to build alignment across teams
- The decision requires real-time discussion and trade-off analysis

## Realistic scenario: Architectural decision

**The situation:** Your team needs to decide on the architecture for a new service. There are three options with different trade-offs. You're the senior engineer, but the tech lead should make the decision.

**Bad approach:**
You call a meeting, present your preferred option, and ask for feedback. People agree because you're senior. The tech lead feels like they didn't really decide.

**Good approach:**
You send a document with the three options, trade-offs, and your analysis. You ask the tech lead to review and come back with their recommendation.

In the meeting:
- Tech lead presents their recommendation and reasoning
- You ask questions: "Why did you choose this over the other options? What's the biggest risk?"
- You surface assumptions: "I notice you're assuming we'll have 2 engineers on this. What if we only have 1?"
- You let them decide: "I think you've thought through the trade-offs well. I support this decision."

**After the meeting:**
- You document the decision and reasoning
- You support the decision publicly, even if you would have chosen differently
- You help them navigate the implementation

## Guiding without controlling

The key is to ask questions that help people think through the problem, not to give them the answer.

**Bad (controlling):**
"I think we should use PostgreSQL because it's more consistent."

**Good (guiding):**
"What are the consistency requirements for this system? How important is horizontal scaling? What are the trade-offs between consistency and scalability?"

**Bad (controlling):**
"We need to migrate to microservices. Here's the plan."

**Good (guiding):**
"We're hitting scaling limits with the monolith. What are the options? What are the trade-offs? What would you recommend?"

## Building a culture where meetings are rare

At scale, meetings become a problem. People spend all day in meetings and no time doing work. Build a culture where:

1. **Decisions are made asynchronously.** Use documents, comments, and email. Meet only when necessary.

2. **Meetings have a clear purpose.** If you can't state it in one sentence, don't meet.

3. **Meetings are short.** 30 minutes is better than 1 hour. 15 minutes is better than 30.

4. **Meetings have a decision.** Every meeting should end with a clear decision or next step.

5. **Meetings are optional.** If someone doesn't need to be there, they shouldn't be.

## Handling disagreement in meetings

Sometimes people disagree strongly. Your role is to:

1. **Understand the disagreement.** What are they really disagreeing about? Is it the decision itself, or underlying assumptions?

2. **Surface the trade-offs.** "I hear you. You're concerned about scalability. The other option is simpler to implement. We're trading off simplicity for scalability."

3. **Make the decision.** After understanding the disagreement, make a clear decision. You don't need consensus.

4. **Commit to revisit.** "We're choosing simplicity now. We'll revisit this in 6 months if our assumptions change."

5. **Support the decision.** Once you've decided, support it. Don't let people undermine it.

## Questions that expose weak assumptions

1. What are we assuming about the future?
2. What would have to change for this decision to be wrong?
3. How will we know if this decision is working?
4. What's the cost of reversing this decision?
5. Who is most affected by this decision?

## Test yourself

1. How do you guide a decision without controlling it?
2. When should you not meet?
3. How do you handle strong disagreement in a meeting?
4. What makes a meeting culture healthy?

Continue to [`professional.md`](professional.md).
