# Communication — Middle

**Your question:** How do I tailor my message to different audiences? How do I handle difficult conversations? How do I build alignment when people disagree?

Junior level teaches you to communicate clearly. At middle level, you're communicating with impact — adapting your message to your audience, handling conflict, and building alignment even when people have different perspectives.

## Tailor your message to your audience

Different audiences need different information:

**For engineers:**
- Technical details matter
- Show the trade-offs
- Explain the reasoning
- Example: "We're migrating to PostgreSQL because it supports ACID transactions and complex queries. The trade-off is we can't scale horizontally as easily."

**For product managers:**
- Business impact matters
- Show the customer value
- Explain the timeline
- Example: "This migration will reduce our infrastructure costs by 30% and improve query performance, which will make the product faster for users."

**For executives:**
- Business outcomes matter
- Show the ROI
- Explain the risk
- Example: "This migration will save $500k/year in infrastructure costs with a 3-month implementation timeline. The risk is we might need to adjust the timeline if we hit unexpected issues."

**For customers:**
- User impact matters
- Avoid technical jargon
- Explain the benefit
- Example: "We're improving our database to make the product faster and more reliable for you."

## The method: know your audience, adapt your message

1. **Identify your audience.** Who are you talking to? What do they care about?

2. **Identify your goal.** What do you want them to understand or do?

3. **Tailor your message.** What information matters to them? What's the best way to present it?

4. **Check for understanding.** Do they get it? Do they have questions?

## Handling difficult conversations

Difficult conversations happen when:
- Someone made a mistake
- There's disagreement
- Someone's feelings are hurt
- There's conflict

**The method: prepare, listen, understand, resolve**

1. **Prepare.** Know what you want to say. Know what outcome you want.

2. **Listen first.** Ask the other person their perspective. Really listen.

3. **Understand their perspective.** Even if you disagree, understand why they think what they think.

4. **Share your perspective.** Explain your view clearly and honestly.

5. **Find common ground.** What do you both agree on? What's the shared goal?

6. **Resolve.** What's the path forward? What will you both do?

## A concrete example: Difficult conversation

**Situation:** A colleague's code review comments were harsh and unhelpful. You need to address it.

**Bad approach:**
"Your code review comments were too harsh. You need to be nicer."

Problems:
- Accusatory
- Vague
- Doesn't invite dialogue

**Good approach:**

**Prepare:** I want to help them give better feedback. I want to understand why they gave harsh feedback.

**Listen first:** "I wanted to talk about the code review you did on the payment feature. Can you tell me what you were thinking when you wrote those comments?"

**Understand:** They explain: "I was frustrated because the code seemed inefficient. I wanted to push back on it."

**Share your perspective:** "I understand you wanted to push back. I was frustrated too because I didn't understand what was wrong or what you would have done differently. When I get feedback like that, I feel defensive instead of learning."

**Find common ground:** "We both want to write good code and help each other improve. I think we can do that better if we explain the reasoning behind our feedback."

**Resolve:** "Next time, can you explain what you think is inefficient and suggest an alternative? That would help me learn."

Better because:
- You listened first
- You understood their perspective
- You shared your perspective honestly
- You found common ground
- You resolved it together

## Building alignment when people disagree

When people disagree, your job is to:
1. Make sure everyone understands the options
2. Make sure everyone understands the trade-offs
3. Make a decision
4. Make sure everyone supports the decision

**The method: present options, discuss trade-offs, decide, commit**

1. **Present options clearly.** What are the real options? What are the trade-offs?

2. **Discuss trade-offs.** What does each option gain? What does it lose?

3. **Make a decision.** After discussion, make a clear decision. You don't need consensus; you need to understand the trade-offs.

4. **Commit to the decision.** Everyone agrees to support the decision, even if they would have chosen differently.

## A concrete example: Building alignment

**Situation:** The team disagrees on whether to use PostgreSQL or MongoDB.

**Bad approach:**
"We're using PostgreSQL. Everyone agrees, right?"

Problems:
- Doesn't surface disagreement
- Doesn't explain reasoning
- People don't commit

**Good approach:**

**Present options:**
"We have two main options: PostgreSQL and MongoDB. Let me explain the trade-offs.

PostgreSQL:
- Pros: Strong consistency, rich query language, mature
- Cons: Harder to scale horizontally

MongoDB:
- Pros: Horizontal scaling, flexible schema
- Cons: Eventual consistency, weaker query language"

**Discuss trade-offs:**
"Our consistency requirements are strict, so strong consistency is important. But we also need to scale. Let me ask: how important is horizontal scaling in the next 12 months?"

Engineer 1: "I think we'll need it. We're growing fast."

Engineer 2: "I think we can live with PostgreSQL for now and migrate later if needed."

**Make a decision:**
"Here's what I'm hearing: we need consistency now, and we might need horizontal scaling later. I'm going to choose PostgreSQL because our consistency requirements are strict. We'll design the schema to support sharding if we need it later. We'll revisit this decision in 12 months."

**Commit to the decision:**
"Does everyone agree to support this decision? I know some of you would have chosen MongoDB, but I think this is the right call given our constraints. Let's move forward together."

Better because:
- Everyone understands the options
- Everyone understands the trade-offs
- The decision is clear
- Everyone commits to it

## Common mistakes at middle level

| Mistake | Why it hurts | Fix |
|---|---|---|
| Using the same message for all audiences | Different audiences have different needs | Tailor your message to what matters to them |
| Avoiding difficult conversations | Problems fester and get worse | Address issues early and directly |
| Not listening in difficult conversations | The other person feels unheard | Listen first, understand their perspective |
| Making decisions without explaining trade-offs | People don't understand why you chose that option | Explain the options and trade-offs |
| Not getting commitment after a decision | People don't support the decision | Make sure everyone commits to it |

## Hands-on exercise

Pick a difficult conversation you need to have:

1. Identify your audience and what they care about
2. Identify your goal
3. Prepare what you want to say
4. Listen to their perspective
5. Share your perspective
6. Find common ground
7. Resolve together

## Verify your thinking

- [ ] Do you know what your audience cares about?
- [ ] Have you tailored your message to them?
- [ ] Are you prepared for the conversation?
- [ ] Will you listen first?
- [ ] Can you explain the trade-offs?
- [ ] Will you get commitment after the decision?

Continue to [`senior.md`](senior.md).
