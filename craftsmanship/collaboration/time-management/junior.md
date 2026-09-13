# Estimation — Junior

**Your question:** How do I estimate a task without just guessing? How do I give a range instead of a single number?

A point estimate ("this will take 3 days") is a guess dressed up as a fact. It hides uncertainty and makes it impossible to plan. A range with assumptions ("3-5 days if the API is stable, 7-10 days if we need to refactor the data model") is honest and useful.

## The method: range, assumptions, and evidence

1. **Break the task into smaller pieces.** Don't estimate "build the payment system." Estimate "integrate payment gateway" (2-3 days), "add error handling" (1-2 days), "write tests" (1-2 days).

2. **Look at similar past work.** How long did similar tasks actually take? Not how long you think they should take. If you've done 5 similar integrations and they took 2, 3, 2, 4, and 3 days, your range is 2-4 days.

3. **Estimate three scenarios:** optimistic (everything goes right), most-likely (normal friction), pessimistic (one thing goes wrong).

4. **State your assumptions.** "3 days if the API documentation is accurate. 5 days if we need to reverse-engineer the API. 7 days if there's a breaking change mid-integration."

5. **Use the range, not the average.** Tell the team "2-4 days" not "3 days." The range is the honest estimate.

## A concrete example

**Task:** Integrate a third-party payment gateway into the checkout flow.

**Bad estimate:**
"This will take 3 days."

Problems:
- No range (what if it takes 5 days?)
- No assumptions (what if the API is undocumented?)
- No evidence (why 3 days specifically?)

**Good estimate:**
"I estimate 2-4 days for this integration.

**Breakdown:**
- Read API docs and set up sandbox: 4-6 hours
- Implement payment flow: 1-2 days
- Error handling and edge cases: 4-8 hours
- Testing and debugging: 4-8 hours

**Assumptions:**
- API documentation is accurate and complete
- No breaking changes to the API during implementation
- We can test in sandbox without production access
- No unexpected dependencies or conflicts

**Optimistic case (2 days):** Everything goes smoothly, API is well-documented, no blockers.

**Most-likely case (3 days):** Normal friction, one small issue with error handling, need to debug one edge case.

**Pessimistic case (4 days):** API documentation is incomplete, need to reverse-engineer some behavior, one integration issue with our existing code.

**If any of these change, the estimate changes:**
- If we need production access for testing: +1 day
- If the API has breaking changes: +2 days
- If we need to handle multiple payment methods: +2-3 days"

Better because:
- Clear range (2-4 days)
- Broken down into pieces
- Assumptions are explicit
- Scenarios are realistic

## Recognizing bad estimates

Watch for these red flags:

| Red flag | What it means | Fix |
|---|---|---|
| "This will take 3 days" (no range) | False precision, hides uncertainty | Give a range: "2-4 days" |
| "About a week" (vague) | Too uncertain, no breakdown | Break it down into pieces |
| "I'm 90% confident" (overconfident) | You're probably wrong | Be honest about uncertainty |
| "It depends" (no commitment) | You haven't thought it through | Give a range with assumptions |
| "Same as last time" (no adjustment) | Last time was different | Adjust for what's different |

## Hands-on checklist

Before you give an estimate, verify:

- [ ] Have you broken the task into smaller pieces?
- [ ] Have you looked at similar past work?
- [ ] Can you give a range (optimistic, most-likely, pessimistic)?
- [ ] Have you stated your assumptions?
- [ ] Can you explain why the range is what it is?
- [ ] Would you be surprised if the actual time was at the pessimistic end?

## Test yourself

1. Why is a range better than a point estimate?
2. How do you anchor your estimate in evidence?
3. What assumptions should you state?
4. What's the difference between optimistic and most-likely?

Continue to [`middle.md`](middle.md).
