# Planning — Senior

**Your question:** How do I run planning meetings? How do I align stakeholders? How do I finalize plans through multiple meeting turns?

Senior level teaches you to run effective planning meetings, align stakeholders, and make trade-off decisions. The key is structuring meetings to converge on a plan through multiple turns.

## Planning meeting structure

A planning meeting has multiple turns to converge on a plan:

**Turn 1: Understand the goal**
- What are we trying to achieve?
- Why does it matter?
- What are the constraints?

**Turn 2: Propose solutions**
- What are the possible approaches?
- What are the trade-offs?
- What are the risks?

**Turn 3: Evaluate and decide**
- Which approach is best?
- What are the next steps?
- Who owns what?

**Turn 4: Finalize and commit**
- What are we committing to?
- What's the timeline?
- How will we track progress?

## A concrete example: Planning meeting with multiple turns

**Situation:** You need to plan a payment system feature. You have 3 stakeholders: Product, Engineering, and Design.

### Turn 1: Understand the goal

**Meeting 1 (30 min)**

**Product:** "We need to add payment processing to our platform. Users should be able to pay for subscriptions. We want to launch in 6 weeks."

**Engineering:** "What's the scope? Do we need to handle refunds? Subscriptions? Multiple payment methods?"

**Product:** "For launch, we need: payments, basic refunds, and one payment method (Stripe). Subscriptions and multiple payment methods can come later."

**Design:** "Do we have any design constraints? Should it match our existing UI?"

**Product:** "Yes, match our existing UI. Keep it simple."

**Engineering:** "OK, so the scope is: payments, basic refunds, Stripe integration. Timeline is 6 weeks. We have 2 engineers."

**Outcome:** Everyone understands the goal, scope, and constraints.

### Turn 2: Propose solutions

**Meeting 2 (1 hour, 1 week later)**

**Engineering proposes 3 approaches:**

**Approach A: Build from scratch**
- Pros: Full control, custom features
- Cons: Takes 8 weeks, high risk
- Effort: 40 days

**Approach B: Use Stripe + custom integration**
- Pros: Faster, lower risk
- Cons: Less customization
- Effort: 15 days

**Approach C: Use payment platform (Stripe + Adyen)**
- Pros: Multiple payment methods, scalable
- Cons: More complex, takes longer
- Effort: 25 days

**Design:** "Approach B looks good. Simple and fast."

**Product:** "Approach B works for launch. We can do Approach C later for multiple payment methods."

**Engineering:** "Approach B is 15 days. We have 40 days available (2 engineers × 4 weeks). We have 25 days buffer for testing, review, deployment."

**Outcome:** Everyone agrees on Approach B.

### Turn 3: Evaluate and decide

**Meeting 3 (1 hour, 1 week later)**

**Engineering presents detailed plan:**

**Stories:**
1. Integrate Stripe API (3 days)
2. Build payment form (3 days)
3. Handle payment success/failure (2 days)
4. Build refund flow (2 days)
5. Add monitoring and alerts (2 days)
6. Write tests (2 days)
7. Deploy and monitor (1 day)

**Total: 15 days**

**Timeline:**
- Week 1: Stories 1-2
- Week 2: Stories 3-4
- Week 3: Stories 5-6
- Week 4: Story 7 + buffer

**Risks:**
- Stripe API might have undocumented behavior (30% chance, +2 days)
- Integration might have issues (20% chance, +1 day)

**Mitigation:**
- Allocate 3 days buffer for issues
- Have QA test thoroughly
- Have rollback plan ready

**Product:** "This looks good. Can we launch in 4 weeks instead of 6?"

**Engineering:** "We have 15 days work + 3 days buffer = 18 days. We have 40 days available. So yes, we can launch in 4 weeks."

**Design:** "I'll have the design ready by end of week 1."

**Outcome:** Everyone agrees on the plan and timeline.

### Turn 4: Finalize and commit

**Meeting 4 (30 min, 1 week later)**

**Engineering:** "Here's the final plan:

**Commitment:**
- Deliver payment system with Stripe integration
- Handle payments, basic refunds
- Launch in 4 weeks

**Scope:**
- In: Payments, refunds, Stripe integration, monitoring
- Out: Multiple payment methods, subscriptions, advanced features

**Assumptions:**
- Stripe API is stable
- No major blockers
- QA can test by week 3

**Risks:**
- Stripe API issues (30% chance, +2 days)
- Integration issues (20% chance, +1 day)

**Timeline:**
- Week 1: Stripe integration, payment form
- Week 2: Payment success/failure, refund flow
- Week 3: Monitoring, tests
- Week 4: Deploy and monitor

**Checkpoints:**
- End of week 1: Stripe integration working
- End of week 2: Refund flow working
- End of week 3: All tests passing
- End of week 4: Ready for production"

**Product:** "Great. I'm committing to launch marketing by week 4."

**Design:** "I'm committing to design review by end of week 1."

**Outcome:** Everyone is committed to the plan.

## Key principles for planning meetings

1. **Separate understanding from proposing.** First understand the goal, then propose solutions.

2. **Make trade-offs explicit.** Show the pros and cons of each approach.

3. **Involve all stakeholders.** Get input from Product, Engineering, Design, etc.

4. **Use data to decide.** Use effort estimates, risk analysis, and historical data.

5. **Commit to the plan.** Make sure everyone is committed before moving forward.

6. **Document the plan.** Write down what you're committing to, scope, timeline, risks, and checkpoints.

## Running effective planning meetings

**Before the meeting:**
- Send agenda and background materials
- Ask people to come prepared
- Set clear objectives

**During the meeting:**
- Start with understanding the goal
- Propose multiple approaches
- Evaluate trade-offs
- Make decisions
- Assign ownership

**After the meeting:**
- Document the plan
- Share with stakeholders
- Track progress against plan

## Common mistakes at senior level

| Mistake | Why it hurts | Fix |
|---|---|---|
| Mixing understanding and proposing | Confusion and poor decisions | Separate into different meeting turns |
| Not involving all stakeholders | Decisions are made without input | Involve Product, Engineering, Design, etc. |
| Not making trade-offs explicit | People don't understand the cost | Show pros and cons of each approach |
| Not using data to decide | Decisions are based on opinion | Use effort estimates, risk analysis, data |
| Not documenting the plan | People forget what was decided | Write down the plan and share |
| Not tracking progress | You don't know if you're on track | Track progress against plan |

## Hands-on exercise

Plan a feature using multiple meeting turns:

1. **Turn 1:** Understand the goal (30 min)
2. **Turn 2:** Propose solutions (1 hour)
3. **Turn 3:** Evaluate and decide (1 hour)
4. **Turn 4:** Finalize and commit (30 min)

## Verify your thinking

- [ ] Have you understood the goal?
- [ ] Have you proposed multiple approaches?
- [ ] Have you made trade-offs explicit?
- [ ] Have you involved all stakeholders?
- [ ] Have you used data to decide?
- [ ] Have you documented the plan?
- [ ] Is everyone committed to the plan?

Continue to [`professional.md`](professional.md).
