# Delegation — Junior

**Your question:** How do I give someone a task and know they'll do it right?

The fear at junior level is that if you hand off work, it won't get done, or it'll be done wrong, or you'll lose track of it. The fix is not to do everything yourself — it's to be clear about what done looks like, check in at the right moments, and give feedback so the person knows if they're on track.

## The method: clarity, ownership, and checkpoints

1. **Be clear about the outcome, not the method.** "Write a function that validates email addresses" is clearer than "make sure emails are validated." The person should know what success looks like before they start.

2. **State the constraints and dependencies.** "This needs to work with our existing user model" or "this should be done by Friday" or "this can't break the payment flow." Constraints are not restrictions — they're information that helps someone make good decisions.

3. **Assign ownership explicitly.** "You own this task" means they decide how to do it, they're responsible if it breaks, and they should come to you with blockers, not wait for you to check in.

4. **Set checkpoints, not surveillance.** "Let's sync on Wednesday to see how it's going" is different from "send me updates every day." Checkpoints are moments to unblock, not moments to verify you're working.

5. **Give feedback on the work, not the person.** "This function doesn't handle null emails" is feedback. "You didn't think about edge cases" is criticism. One helps them improve; the other makes them defensive.

## A concrete example

**Bad delegation:**
"Can you fix the login bug? It's in the auth service. Let me know when you're done."

Problems:
- No clear success criteria (what does "fixed" mean?)
- No constraints (does it need to work on mobile? with SSO?)
- No checkpoints (you won't know if they're stuck until Friday)
- No feedback mechanism (how will they know if they're on the right track?)

**Good delegation:**
"The login bug is that users with special characters in their password can't log in. I need you to:
1. Write a test that reproduces the bug
2. Fix the password validation in auth/validators.py
3. Make sure it still works with our existing password requirements
4. Test it on both web and mobile

Success looks like: the test passes, existing tests still pass, and you can log in with a password like `P@ss!word123`.

Constraints: don't change the password requirements (that's a separate decision), and don't touch the database schema.

Let's sync Wednesday morning to see how it's going. If you get stuck, ping me on Slack — don't wait."

Better because:
- Clear success criteria (test passes, existing tests pass, works on web and mobile)
- Constraints are explicit (don't change requirements, don't touch schema)
- Checkpoint is set (Wednesday morning)
- Feedback mechanism is clear (Slack for blockers)

## Common beginner mistakes

| Mistake | Why it hurts | Fix |
|---|---|---|
| Assigning a task but not the outcome | Person does the task but doesn't know if it's right | State what done looks like before they start |
| Giving too much detail on how to do it | Person can't learn or make decisions | Describe the outcome and constraints, let them choose the method |
| No checkpoints | You don't know they're stuck until it's too late | Set one or two checkpoints before the deadline |
| Checking in too often | Person feels micromanaged and doesn't own the work | Checkpoints are for unblocking, not verification |
| Vague feedback | Person doesn't know what to improve | Give specific feedback on the work, not the person |
| Not following up | Person doesn't know if they did it right | Review the work and give feedback before they move on |

## Hands-on checklist

Before you delegate a task, verify:

- [ ] Can you describe what done looks like in one sentence?
- [ ] Have you stated the constraints and dependencies?
- [ ] Does the person know they own this task?
- [ ] Have you set a checkpoint to check in?
- [ ] Do you have a way for them to ask for help?
- [ ] Will you give them feedback on the work?

## Test yourself

1. What is the difference between assigning a task and delegating?
2. Why is clarity on the outcome more important than clarity on the method?
3. What should a checkpoint accomplish?
4. How do you give feedback without making someone defensive?

Continue to [`middle.md`](middle.md).
