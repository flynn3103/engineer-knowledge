# Manage Up — Junior

**Your question:** How do I communicate with my manager? How do I raise issues? How do I ask for help?

At junior level, managing up starts with clear communication. Your manager needs to know what you're doing, what's working, and what's not working.

## Communicating progress clearly

Your manager can't help if they don't know what's happening. Share progress regularly:

1. **Share what you accomplished.** What did you finish this week?

2. **Share what you're working on.** What are you doing now?

3. **Share blockers.** What's stopping you?

4. **Share what you need.** What do you need from your manager?

## A concrete example: Communicating progress

**Bad communication:**
"I'm working on the login feature. It's going OK."

Problems:
- Vague
- No detail
- Manager doesn't know if you're on track

**Good communication:**

**What you accomplished:**
"This week I:
- Fixed the password validation bug
- Added test cases for special characters
- Deployed to staging

All tests pass. QA is testing now."

**What you're working on:**
"Next week I'm:
- Handling payment failures
- Adding retry logic
- Writing integration tests"

**Blockers:**
"I'm blocked on the payment API. I need the Stripe credentials to test locally. Can you help me get those?"

**What you need:**
"I need:
1. Stripe credentials by tomorrow
2. 30 min to discuss the retry logic with you
3. QA to test by Friday"

Better because:
- Clear what you accomplished
- Clear what you're working on
- Clear what's blocking you
- Clear what you need

## Raising issues early

Don't wait until the deadline to raise issues. Raise them as soon as you see them:

1. **Identify the issue.** What's the problem?

2. **Explain the impact.** How does it affect the deadline or quality?

3. **Propose a solution.** What can you do about it?

4. **Ask for help.** What do you need from your manager?

## A concrete example: Raising issues early

**Bad approach:**
[Friday before deadline]
"I just realized the payment API is more complex than I thought. I won't make the deadline."

Problems:
- Too late to do anything
- Manager is surprised
- Deadline is missed

**Good approach:**

[Tuesday, 3 days into the work]
"I found an issue. The payment API is more complex than expected. It has rate limiting and retry logic that I didn't account for.

Impact: This will add 2 days to my estimate. I was planning to finish Friday, but now I'll finish Monday.

Options:
1. Extend the deadline to Monday
2. Reduce scope (skip retry logic for now)
3. Get help from another engineer

What would you prefer?"

Better because:
- You raised the issue early
- You explained the impact
- You proposed options
- Your manager can help

## Asking for help effectively

Don't struggle alone. Ask for help when you need it:

1. **Be specific about what you need.** Don't just say "I need help."

2. **Explain what you've tried.** Show that you've tried to solve it yourself.

3. **Propose a solution.** Suggest how they can help.

4. **Respect their time.** Ask for a specific amount of time.

## A concrete example: Asking for help

**Bad approach:**
"I'm stuck on the payment API. Can you help?"

Problems:
- Vague
- Manager doesn't know what you need
- Manager doesn't know how much time to allocate

**Good approach:**

"I'm stuck on the payment API. Here's what I've tried:
- Read the documentation
- Looked at example code
- Tried implementing it locally

The issue is: The API returns a 429 (rate limit) error, but the documentation doesn't explain how to handle it.

I need: 30 minutes to pair with you and figure out the retry logic.

Can we do that tomorrow at 2 PM?"

Better because:
- Specific about what you need
- Showed what you've tried
- Proposed a solution
- Respected their time

## Preparing for 1-on-1s

Come prepared to your 1-on-1 meetings:

1. **Write down what you accomplished.** What did you finish?

2. **Write down what you're working on.** What are you doing now?

3. **Write down blockers.** What's stopping you?

4. **Write down what you need.** What do you need from your manager?

5. **Ask for feedback.** How are you doing?

## A concrete example: 1-on-1 preparation

**Before the meeting, write:**

```
1-on-1 with Manager - Week of Sept 9

Accomplished:
- Fixed password validation bug
- Added test cases for special characters
- Deployed to staging
- All tests pass

Working on:
- Payment failure handling
- Retry logic
- Integration tests

Blockers:
- Need Stripe credentials to test locally
- Need clarification on retry logic

What I need:
- Stripe credentials by tomorrow
- 30 min to discuss retry logic
- QA to test by Friday

Feedback:
- How am I doing?
- Any feedback on my work?
- Any areas to improve?
```

**During the meeting:**
- Share your accomplishments
- Share what you're working on
- Raise blockers
- Ask for what you need
- Ask for feedback

## Common beginner mistakes

| Mistake | Why it hurts | Fix |
|---|---|---|
| Not communicating progress | Manager doesn't know what you're doing | Share progress regularly |
| Waiting to raise issues | Issues become crises | Raise issues early |
| Not asking for help | You get stuck and miss deadlines | Ask for help when you need it |
| Being vague | Manager can't help effectively | Be specific about what you need |
| Not preparing for 1-on-1s | Meetings are unproductive | Come prepared with notes |
| Not asking for feedback | You don't know how you're doing | Ask for feedback regularly |

## Hands-on exercise

For your next 1-on-1:

1. Write down what you accomplished
2. Write down what you're working on
3. Write down blockers
4. Write down what you need
5. Prepare questions for feedback
6. Have the meeting

## Verify your thinking

- [ ] Do you communicate progress regularly?
- [ ] Do you raise issues early?
- [ ] Do you ask for help when you need it?
- [ ] Do you prepare for 1-on-1s?
- [ ] Do you ask for feedback?

Continue to [`middle.md`](middle.md).
