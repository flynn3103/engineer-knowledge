# Manage Up — Middle

**Your question:** How do I manage expectations? How do I negotiate scope? How do I handle feedback?

Middle level teaches you to manage expectations proactively, negotiate scope effectively, and handle feedback constructively. The key is being honest about what you can deliver and what you need.

## Managing expectations

Expectations are what your manager thinks you'll deliver. Manage them by:

1. **Be clear about what you're committing to.** Don't be vague.

2. **Be clear about constraints.** What could prevent you from delivering?

3. **Update expectations as reality changes.** Don't hide problems.

4. **Deliver what you committed to.** Follow through on your promises.

## A concrete example: Managing expectations

**Bad approach:**
Manager: "Can you have the payment feature ready by Friday?"
You: "Sure, I'll get it done."
[Friday arrives]
You: "I'm still working on it. It's more complex than I thought."

Problems:
- You didn't understand the work before committing
- You didn't communicate progress
- You broke your commitment
- Manager is disappointed

**Good approach:**

Manager: "Can you have the payment feature ready by Friday?"

You: "Let me understand the scope first. What exactly needs to be done? Do we need refunds? Multiple payment methods?"

Manager: "Just basic payments and refunds. Stripe integration."

You: "OK, let me investigate for 2 hours. Then I'll give you a realistic estimate."

[After investigation]

You: "I found the scope. It's:
- Stripe integration (3 days)
- Payment form (2 days)
- Refund flow (2 days)
- Testing (2 days)
- Total: 9 days

I can have it ready by Friday if:
- I can test in staging today
- QA can test by Thursday
- No other urgent issues come up

If any of those change, I'll let you know immediately."

Manager: "That works. Let me know if anything changes."

[During the week]
You: "Day 1: Stripe integration done. Day 2: Payment form done. Day 3: Refund flow done. Day 4: Testing in progress. On track for Friday."

[Friday]
You: "Feature is ready. All tests pass. QA approved. Ready to deploy."

Better because:
- You understood the scope before committing
- You gave a realistic estimate
- You communicated progress
- You delivered what you committed
- Manager's expectations were met

## Negotiating scope

When scope is unclear or too large, negotiate:

1. **Understand the business need.** Why do they want this? What's the priority?

2. **Propose a smaller scope.** What's the minimum viable version?

3. **Offer a phased approach.** What can you do now? What can you do later?

4. **Make trade-offs explicit.** If we do X, we can't do Y.

## A concrete example: Negotiating scope

**Situation:** Your manager asks you to build a payment system. The scope includes: payments, refunds, subscriptions, invoicing, and reporting.

**Bad approach:**
"I'll build all of it by end of month."

Problems:
- Too much scope
- Unrealistic timeline
- Will fail and damage trust

**Good approach:**

You: "I understand you want a complete payment system. Let me understand the priority. What do we need first to launch?"

Manager: "We need to launch the product. Payments are critical. Refunds are important but not critical. Subscriptions, invoicing, and reporting can wait."

You: "What if we do this:
- Phase 1 (end of month): Payments and basic refunds
- Phase 2 (month 2): Subscriptions
- Phase 3 (month 3): Invoicing and reporting

That way, we can launch with payments, and add features incrementally."

Manager: "That works. But we need refunds to be robust."

You: "If we make refunds robust, we need more time. We can either:
- Spend 2 weeks on payments and basic refunds (launch on time, but refunds are basic)
- Spend 3 weeks on payments and robust refunds (launch 1 week late, but refunds are solid)

Which is more important?"

Manager: "Robust refunds are more important. Let's launch 1 week late."

You: "OK, so I'm committing to:
- Payments (2 weeks)
- Robust refunds (1 week)
- Launch end of month + 1 week

I'm NOT committing to:
- Subscriptions (phase 2)
- Invoicing (phase 3)
- Reporting (phase 3)"

Better because:
- You understood the business need
- You proposed a realistic scope
- You made trade-offs explicit
- You committed to something achievable

## Handling feedback

Feedback is how you improve. Handle it constructively:

1. **Listen without defending.** Don't interrupt or make excuses.

2. **Ask clarifying questions.** Make sure you understand.

3. **Thank them for the feedback.** Show appreciation.

4. **Reflect on the feedback.** Think about what they said.

5. **Take action.** Make changes based on the feedback.

## A concrete example: Handling feedback

**Bad approach:**
Manager: "Your code quality has been declining. You're not writing enough tests."

You: "That's not fair. I've been busy. I don't have time for tests."

Problems:
- You're defensive
- You're not listening
- You're not taking responsibility

**Good approach:**

Manager: "Your code quality has been declining. You're not writing enough tests."

You: "Thank you for the feedback. I appreciate you bringing this up. Can you give me a specific example?"

Manager: "The payment API code doesn't have tests for error cases. The refund flow doesn't have tests for edge cases."

You: "I understand. You're right. I've been focused on getting features done quickly, and I've been skipping tests. That's a mistake. I need to slow down and write tests.

What would you like me to do? Should I:
1. Go back and add tests to the payment API and refund flow?
2. Make sure all new code has tests going forward?
3. Both?"

Manager: "Both. And let's talk about how to balance speed and quality."

You: "OK, I'll add tests to the existing code this week. And I'll make sure all new code has tests. Let's talk about how to balance speed and quality in our next 1-on-1."

Better because:
- You listened without defending
- You asked clarifying questions
- You thanked them for the feedback
- You took responsibility
- You took action

## Escalating issues

Sometimes you need to escalate issues to your manager:

1. **Identify the issue.** What's the problem?

2. **Explain why you can't solve it.** Why do you need help?

3. **Propose a solution.** What should happen?

4. **Ask for help.** What do you need from your manager?

## A concrete example: Escalating issues

**Situation:** Your team is overloaded. You have too much work and not enough time.

**Bad approach:**
"We're too busy. We need more people."

Problems:
- Vague
- No data
- No proposed solution

**Good approach:**

You: "I need to escalate an issue. Our team is overloaded.

Here's the data:
- We have 5 engineers
- We have 20 stories in the backlog
- Each story takes 3 days on average
- That's 60 days of work
- We have 20 days available (1 sprint)

We're 3x overloaded.

Options:
1. Hire more engineers (takes 2-3 months)
2. Reduce scope (defer some stories)
3. Extend timeline (push some stories to next sprint)
4. Reduce quality (skip tests, skip review) - NOT RECOMMENDED

I recommend option 2 or 3. What would you prefer?"

Manager: "Let's do option 2. Which stories can we defer?"

You: "Let's look at the backlog together and prioritize."

Better because:
- You identified the issue with data
- You explained why you can't solve it
- You proposed options
- You asked for help

## Common mistakes at middle level

| Mistake | Why it hurts | Fix |
|---|---|---|
| Not managing expectations | Manager is disappointed | Be clear about what you're committing to |
| Not negotiating scope | You overcommit and fail | Negotiate scope when it's too large |
| Being defensive about feedback | You don't improve | Listen and take responsibility |
| Not escalating issues | Issues get worse | Escalate when you can't solve it |
| Not following up | Manager forgets what you discussed | Send a summary after meetings |

## Hands-on exercise

For your next 1-on-1:

1. Manage expectations about what you're working on
2. Negotiate scope if needed
3. Ask for feedback
4. Handle feedback constructively
5. Escalate any issues

## Verify your thinking

- [ ] Are you managing expectations?
- [ ] Are you negotiating scope when needed?
- [ ] Are you handling feedback constructively?
- [ ] Are you escalating issues appropriately?
- [ ] Are you following up after meetings?

Continue to [`senior.md`](senior.md).
