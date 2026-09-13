# Communication — Senior

**Your question:** How do I facilitate communication between teams? How do I resolve conflicts? How do I shape how decisions are communicated?

Middle level teaches you to communicate with impact and handle difficult conversations. At senior level, you're facilitating communication across teams, resolving conflicts, and shaping how decisions are communicated to the organization.

## Facilitating communication between teams

When teams need to communicate, your role is to:
1. **Make sure they understand each other.** Different teams have different perspectives.
2. **Surface disagreements early.** Don't let them fester.
3. **Help them find common ground.** What do they both want?
4. **Facilitate a decision.** Help them decide together.

## The method: understand, surface, align, decide

1. **Understand each team's perspective.** What do they care about? What are their constraints?

2. **Surface disagreements.** "I'm hearing that Team A wants to migrate to microservices, but Team B is concerned about the complexity. Is that right?"

3. **Find common ground.** "You both want the system to be scalable and maintainable. You just disagree on how to get there."

4. **Facilitate a decision.** "Let's talk about the trade-offs. What would it take for each of you to support this decision?"

## A concrete example: Cross-team conflict

**Situation:** Team A (Backend) wants to migrate to microservices. Team B (DevOps) is concerned about operational complexity.

**Bad approach:**
"Team A, you're right. Let's migrate to microservices."

Problems:
- Doesn't address Team B's concerns
- Team B won't support the decision
- Conflict will fester

**Good approach:**

**Understand each perspective:**

You talk to Team A: "Why do you want to migrate to microservices?"
Team A: "We're hitting scaling limits with the monolith. We need to scale different services independently."

You talk to Team B: "What are your concerns?"
Team B: "Microservices are operationally complex. We'll need to manage multiple deployments, monitoring, and debugging will be harder."

**Surface disagreements:**
"I'm hearing that Team A wants to scale independently, but Team B is concerned about operational complexity. Is that right?"

Both teams: "Yes."

**Find common ground:**
"You both want the system to be scalable and reliable. You just disagree on how to get there. Is that fair?"

Both teams: "Yes."

**Facilitate a decision:**
"Let's talk about the trade-offs. Team A, what would it take to address Team B's concerns? Team B, what would make you comfortable with microservices?"

Team A: "We could start with a staged migration. We could migrate one service at a time."

Team B: "That would help. We could build the operational infrastructure for one service, then scale it."

**Outcome:**
"OK, here's what I'm hearing: we'll do a staged migration. We'll migrate one service first, build the operational infrastructure, and then decide whether to continue. Does that work for both of you?"

Both teams: "Yes."

Better because:
- Both teams feel heard
- You found common ground
- You facilitated a decision together
- Both teams support the decision

## Resolving conflicts

Conflicts happen when:
- Teams have different priorities
- Teams have different perspectives
- Teams have different constraints
- Teams don't understand each other

**The method: understand, acknowledge, reframe, resolve**

1. **Understand both sides.** What does each side want? Why?

2. **Acknowledge both perspectives.** "I understand why you both feel this way."

3. **Reframe the conflict.** "This isn't about who's right. It's about finding a solution that works for both of you."

4. **Resolve together.** "What would it take for both of you to support this decision?"

## Shaping how decisions are communicated

How a decision is communicated affects whether people support it. Your role is to:

1. **Explain the reasoning.** Why was this decision made? What trade-offs were considered?

2. **Acknowledge the trade-offs.** "We're choosing X over Y. That means we're gaining A but losing B."

3. **Commit to revisit.** "We'll revisit this decision in 6 months if our assumptions change."

4. **Make it safe to disagree.** "I know some of you would have chosen differently. That's OK. Let's move forward together."

## A concrete example: Communicating a decision

**Situation:** You decided to migrate to PostgreSQL instead of MongoDB.

**Bad communication:**
"We're using PostgreSQL. Everyone agrees, right?"

Problems:
- Doesn't explain reasoning
- Doesn't acknowledge trade-offs
- Doesn't make it safe to disagree

**Good communication:**

**Explain the reasoning:**
"We decided to use PostgreSQL because our consistency requirements are strict. We need to guarantee that orders are never lost and inventory is never oversold. PostgreSQL's ACID transactions give us that guarantee."

**Acknowledge the trade-offs:**
"The trade-off is that PostgreSQL is harder to scale horizontally than MongoDB. But we don't need horizontal scaling right now. We can design the schema to support sharding if we need it later."

**Commit to revisit:**
"We'll revisit this decision in 12 months. If we need to scale horizontally, we'll reconsider MongoDB or other options."

**Make it safe to disagree:**
"I know some of you would have chosen MongoDB. I understand why. But I think PostgreSQL is the right call given our constraints. Let's move forward together. If you have concerns, let me know."

Better because:
- Everyone understands the reasoning
- Everyone understands the trade-offs
- Everyone knows when we'll revisit
- Everyone feels safe to disagree

## Common mistakes at senior level

| Mistake | Why it hurts | Fix |
|---|---|---|
| Not understanding both sides before facilitating | You make a bad decision | Understand both perspectives first |
| Taking sides in a conflict | The losing side feels unheard | Acknowledge both perspectives |
| Not surfacing disagreements | Conflicts fester | Surface disagreements early |
| Making a decision without explaining trade-offs | People don't understand why | Explain the options and trade-offs |
| Not making it safe to disagree | People don't voice concerns | Make it clear that disagreement is OK |

## Hands-on exercise

Pick a conflict between two teams:

1. Understand each team's perspective
2. Surface the disagreement
3. Find common ground
4. Facilitate a decision
5. Communicate the decision with reasoning and trade-offs

## Verify your thinking

- [ ] Do you understand both sides of the conflict?
- [ ] Have you acknowledged both perspectives?
- [ ] Have you found common ground?
- [ ] Can you explain the trade-offs?
- [ ] Will you make it safe to disagree?

Continue to [`professional.md`](professional.md).
