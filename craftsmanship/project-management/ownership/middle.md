# Ownership — Middle

**Your question:** How do I make commitments that I can actually deliver? How do I negotiate scope? How do I estimate accurately?

Middle level teaches you to make clear commitments, negotiate scope effectively, and estimate accurately. The key is understanding what you're committing to and being honest about risks.

## Making clear commitments

A clear commitment includes:
1. **What you're committing to** (the outcome)
2. **What you're NOT committing to** (out of scope)
3. **Your assumptions** (what must be true)
4. **Your risks** (what could go wrong)
5. **Your timeline** (when you'll deliver)
6. **Your checkpoints** (how you'll know you're on track)

## A concrete example: Making a clear commitment

**Bad commitment:**
"I'll build the payment system by end of month."

Problems:
- Unclear what "payment system" means
- No assumptions stated
- No risks identified
- No checkpoints

**Good commitment:**
"I'm committing to:
- Integrate Stripe payment gateway
- Handle successful payments
- Handle payment failures and retries
- Add monitoring and alerts

I'm NOT committing to:
- Refunds (that's a separate task)
- Subscription billing (that's a separate task)
- PCI compliance (that's handled by Stripe)

Assumptions:
- Stripe API documentation is accurate
- No breaking changes to Stripe API
- QA can test by end of month

Risks:
- Stripe API might have undocumented behavior (40% chance, +2 days)
- Integration might have issues with our payment flow (30% chance, +1 day)

Timeline:
- Week 1: Integrate Stripe, handle successful payments
- Week 2: Handle failures and retries
- Week 3: Add monitoring, testing, and documentation
- Week 4: Buffer for issues

Checkpoints:
- End of week 1: Successful payments working in staging
- End of week 2: Failures and retries working
- End of week 3: Monitoring and documentation complete
- End of week 4: Ready for production"

Better because:
- Clear about what you're committing to
- Clear about what you're NOT committing to
- Assumptions are explicit
- Risks are identified
- Timeline is realistic
- Checkpoints are clear

## Negotiating scope

When scope is unclear or too large, negotiate:

1. **Understand the business need.** Why do they want this? What's the priority?

2. **Propose a smaller scope.** What's the minimum viable version?

3. **Offer a phased approach.** What can you do now? What can you do later?

4. **Make trade-offs explicit.** If we do X, we can't do Y.

## A concrete example: Negotiating scope

**Situation:** You're asked to build a payment system. The scope includes: payments, refunds, subscriptions, invoicing, and reporting.

**Bad approach:**
"I'll build all of it by end of month."

Problems:
- Too much scope
- Unrealistic timeline
- Will fail and damage trust

**Good approach:**

**Understand the business need:**
"I understand you want a complete payment system. What's the priority? What do we need first to launch?"

Product: "We need to launch the product. Payments are critical. Refunds are important but not critical. Subscriptions, invoicing, and reporting can wait."

**Propose a smaller scope:**
"What if we do this:
- Phase 1 (end of month): Payments and basic refunds
- Phase 2 (month 2): Subscriptions
- Phase 3 (month 3): Invoicing and reporting

That way, we can launch with payments, and add features incrementally."

Product: "That works. But we need refunds to be robust."

**Make trade-offs explicit:**
"If we make refunds robust, we need more time. We can either:
- Spend 2 weeks on payments and basic refunds (launch on time, but refunds are basic)
- Spend 3 weeks on payments and robust refunds (launch 1 week late, but refunds are solid)

Which is more important?"

Product: "Robust refunds are more important. Let's launch 1 week late."

**Commit to the negotiated scope:**
"OK, so I'm committing to:
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

## Estimating accurately

Estimate by breaking work into pieces and using historical data:

1. **Break work into pieces.** Don't estimate "build payment system." Estimate "integrate Stripe" (3 days), "handle failures" (2 days), etc.

2. **Look at similar past work.** How long did similar tasks actually take?

3. **Estimate with a range.** Optimistic, most-likely, pessimistic.

4. **Add assumptions and risks.** What could go wrong?

5. **Track actual vs. estimated.** Learn from your estimates.

## Common mistakes at middle level

| Mistake | Why it hurts | Fix |
|---|---|---|
| Committing without understanding scope | You commit to something impossible | Understand scope first |
| Not stating assumptions | People don't know what you're assuming | State assumptions explicitly |
| Not identifying risks | Risks materialize and you miss deadline | Identify risks upfront |
| Estimating without historical data | Your estimate is just a guess | Look at similar past work |
| Not negotiating scope | You overcommit and fail | Negotiate scope when it's too large |
| Not tracking actual vs. estimated | You don't improve your estimates | Track and learn from estimates |

## Hands-on exercise

Pick a commitment you need to make:

1. Understand the business need
2. Propose a scope
3. Identify assumptions and risks
4. Estimate with a range
5. Commit to the scope with checkpoints
6. Track actual vs. estimated

## Verify your thinking

- [ ] Do you understand the business need?
- [ ] Is the scope realistic?
- [ ] Have you stated assumptions?
- [ ] Have you identified risks?
- [ ] Is your estimate based on historical data?
- [ ] Will you track actual vs. estimated?

Continue to [`senior.md`](senior.md).

Acceptance tests align stakeholders; unit tests protect implementation detail. Neither replaces exploratory, security, performance, or recovery testing.

## Collaboration and disagreement

Critique the proposal, not the person. State facts, assumptions, and values separately. Summarize the strongest opposing view before responding. Once a decision is made, commit to execution unless new evidence changes the risk.

## Mentoring in daily work

Do not only provide answers. Ask the learner to predict, attempt, and explain. Pair on real work, give specific feedback, and gradually reduce support. The goal is independent judgment, not dependence on the mentor.

## Test yourself

1. Write a professional “no” to an unsafe production change.
2. Why should estimates include validation and rollout?
3. What does an acceptance test prove that a unit test may not?
4. How do you disagree and still support the final team decision?

Continue to [`senior.md`](senior.md).
