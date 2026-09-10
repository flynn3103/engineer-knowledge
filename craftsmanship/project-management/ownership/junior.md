# Ownership — Junior

**Your question:** How do I build trust with my team? How do I say yes and no clearly? How do I define scope?

At junior level, ownership starts with building trust. Trust comes from being reliable, communicating clearly, and doing what you say you'll do.

## Building trust through reliability

Trust is built by:
1. **Being honest about what you know and don't know.** Don't pretend to understand something you don't.
2. **Communicating progress.** Don't wait until the deadline to say something is wrong.
3. **Doing what you say you'll do.** If you commit to something, deliver it.
4. **Asking for help early.** Don't wait until you're stuck.
5. **Admitting mistakes.** Don't hide problems.

## The method: understand, commit, communicate, deliver

1. **Understand the work.** What are you being asked to do? What does "done" look like?

2. **Commit clearly.** Say yes or no. If yes, state what you're committing to and when.

3. **Communicate progress.** Share updates regularly. Raise issues early.

4. **Deliver what you committed.** Do what you said you'd do.

## A concrete example: Building trust

**Bad approach:**
Manager: "Can you fix the login bug by Friday?"
You: "Sure, I'll get it done."
[Friday arrives]
You: "I'm still working on it. It's more complex than I thought."

Problems:
- You didn't understand the work before committing
- You didn't communicate progress
- You broke your commitment
- Trust is damaged

**Good approach:**

**Understand the work:**
"I can help with the login bug. Let me understand it first. Can you describe what's happening? Who's affected? What's the impact?"

Manager: "Users with special characters in their password can't log in. It's affecting 5% of users. It's blocking our release."

**Commit clearly:**
"OK, I understand. Let me investigate for 2 hours to understand the scope. Then I'll give you a realistic estimate. I'll update you by 3 PM today."

[After investigation]

"I found the issue. It's in the password validation regex. I can fix it by Friday if:
- I can test in the staging environment
- The QA team can test it by Thursday
- No other urgent issues come up

If any of those change, I'll let you know immediately. I'll send you daily updates on progress."

**Communicate progress:**
[Daily updates]
"Day 1: Fixed the regex, added test cases. All tests pass locally.
Day 2: Deployed to staging. QA is testing. Found one edge case with unicode characters. Fixing today.
Day 3: All tests pass. Ready for QA final review."

**Deliver what you committed:**
"The fix is ready. All tests pass. QA has approved it. It's ready to deploy."

Better because:
- You understood the work before committing
- You gave a realistic estimate with conditions
- You communicated progress daily
- You delivered what you committed
- Trust is built

## Saying yes and no clearly

**Saying yes:**
- Be clear about what you're committing to
- Be clear about the conditions
- Be clear about the timeline
- Be clear about what you're NOT committing to

Example: "I can fix the login bug by Friday if QA can test it by Thursday. I'm not committing to deploying it to production—that's a separate decision."

**Saying no:**
- Be clear about why you're saying no
- Offer an alternative if possible
- Be respectful

Example: "I can't take on the payment system redesign right now. I'm committed to the login bug fix through Friday. What I can do: I can review the design and give feedback. I can help after Friday."

## Defining scope

Scope is what you're committing to. Be specific:

**Bad scope:**
"I'll fix the login bug."

Problems:
- Unclear what "fix" means
- Unclear what's included

**Good scope:**
"I'll fix the login bug by:
1. Updating the password validation regex to accept special characters
2. Adding test cases for special characters
3. Testing in staging environment
4. Deploying to production

I'm NOT committing to:
- Changing password requirements
- Adding new authentication methods
- Updating documentation (that's separate)"

## Common beginner mistakes

| Mistake | Why it hurts | Fix |
|---|---|---|
| Saying yes before understanding | You commit to something impossible | Understand first, then commit |
| Not communicating progress | People don't know if you're on track | Share updates regularly |
| Hiding problems | Issues get worse | Raise issues early |
| Not asking for help | You get stuck | Ask for help when blocked |
| Changing scope without telling anyone | People think you're not delivering | Communicate scope changes |
| Saying yes to everything | You overcommit and burn out | Say no when you need to |

## Hands-on checklist

Before you commit to work, verify:

- [ ] Do you understand what you're being asked to do?
- [ ] Do you know what "done" looks like?
- [ ] Have you identified dependencies and risks?
- [ ] Can you give a realistic estimate?
- [ ] Are you clear about what you're committing to?
- [ ] Are you clear about what you're NOT committing to?
- [ ] Will you communicate progress regularly?

## Test yourself

1. How do you build trust with your team?
2. What should you do before saying yes to a commitment?
3. How do you say no respectfully?
4. Why is communicating progress important?

Continue to [`middle.md`](middle.md).
