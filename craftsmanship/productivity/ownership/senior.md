# Ownership — Senior

**Your question:** How do I deliver under pressure? How do I maintain quality when deadlines are tight? How do I protect my team?

Senior level teaches you to deliver under pressure while maintaining quality and protecting your team. The key is making trade-offs explicit and protecting what matters most.

## Delivering under pressure

Pressure comes from tight deadlines, urgent issues, or high stakes. Your role is to:

1. **Make pressure visible.** Don't hide it. Acknowledge it.

2. **Identify what matters most.** What's non-negotiable? What can be deferred?

3. **Make trade-offs explicit.** If we do X, we can't do Y.

4. **Protect quality where it matters.** Don't cut corners on critical systems.

5. **Communicate clearly.** Keep stakeholders informed.

## A concrete example: Delivering under pressure

**Situation:** A critical bug is affecting customers. You need to fix it by end of day. The fix is complex and risky.

**Bad approach:**
"I'll fix it by end of day. Don't worry."
[Rushes the fix, introduces new bugs, makes things worse]

Problems:
- Didn't assess the risk
- Didn't communicate the trade-offs
- Made things worse

**Good approach:**

**Make pressure visible:**
"I understand this is critical. We need to fix it today. Let me assess the options and the risks."

**Identify what matters most:**
"The most important thing is that customers can use the system. The second priority is that we don't introduce new bugs."

**Assess the options:**
"I have two options:
1. Quick fix (2 hours): Patch the immediate issue. Risk: might introduce new bugs.
2. Proper fix (4 hours): Fix the root cause. Risk: takes longer, but more robust.

Given the time pressure, I recommend option 1 (quick fix) with a plan to do option 2 (proper fix) tomorrow."

**Make trade-offs explicit:**
"If we do the quick fix:
- Pros: Customers can use the system today
- Cons: We need to do the proper fix tomorrow, and there's a small risk of new bugs

If we do the proper fix:
- Pros: More robust, no risk of new bugs
- Cons: Takes 4 hours, customers are affected longer

I recommend the quick fix today + proper fix tomorrow. Does that work?"

**Protect quality where it matters:**
"For the quick fix, I'll:
- Test it thoroughly in staging
- Have QA test it
- Have a rollback plan ready
- Monitor it closely after deployment

I won't skip testing or monitoring just because we're in a hurry."

**Communicate clearly:**
"Here's the plan:
- 2 PM: Quick fix deployed to production
- 3 PM: Monitor for issues
- Tomorrow: Proper fix
- I'll send updates every hour until it's deployed"

Better because:
- You made pressure visible
- You identified what matters most
- You assessed options and risks
- You made trade-offs explicit
- You protected quality where it matters
- You communicated clearly

## Maintaining quality under pressure

Quality is not all-or-nothing. Identify what's non-negotiable:

| Risk | Non-negotiable quality controls |
|---|---|
| Data loss | Backup, restore test, migration rehearsal |
| Security breach | Security review, negative tests |
| Availability loss | Load test, canary, rollback plan |
| Customer impact | User testing, monitoring |
| Minor bug | Code review, basic testing |

When time is tight, reduce scope or exposure. Don't skip critical quality controls.

## Protecting your team

Your role is to protect your team from unsustainable pressure:

1. **Push back on unrealistic deadlines.** If something is impossible, say so.

2. **Protect focus.** Don't let constant interruptions derail the team.

3. **Prevent burnout.** Don't let people work unsustainable hours.

4. **Make trade-offs visible.** If we do X, we can't do Y.

5. **Escalate when needed.** If the pressure is unsustainable, escalate.

## A concrete example: Protecting your team

**Situation:** Your manager wants a feature done in 1 week. Your team estimates 3 weeks.

**Bad approach:**
"OK, we'll do it in 1 week." [Team works 80-hour weeks, burns out, delivers buggy code]

Problems:
- Unsustainable pressure
- Team burns out
- Quality suffers

**Good approach:**

**Push back on unrealistic deadline:**
"I understand the urgency. Let me be honest: 1 week is not realistic for this feature. Here's why:
- Design: 3 days
- Implementation: 5 days
- Testing: 3 days
- Buffer: 2 days
Total: 13 days

If we try to do it in 1 week, we'll either:
- Cut corners and introduce bugs
- Work unsustainable hours and burn out
- Deliver incomplete work"

**Propose alternatives:**
"What if we do this:
- Week 1: Core feature (what's most important)
- Week 2: Advanced features (nice to have)

That way, we can launch something in 1 week, and add features incrementally."

**Make trade-offs visible:**
"If we do the core feature in 1 week:
- Pros: We launch on time
- Cons: Some features are missing

If we do everything in 3 weeks:
- Pros: Complete feature
- Cons: We launch 2 weeks late

Which is more important?"

**Protect your team:**
"If we commit to 1 week, I need to make sure:
- The team doesn't work unsustainable hours
- We don't skip critical quality controls
- We have a clear scope (what's in, what's out)"

Better because:
- You pushed back on unrealistic deadline
- You proposed alternatives
- You made trade-offs visible
- You protected your team

## Common mistakes at senior level

| Mistake | Why it hurts | Fix |
|---|---|---|
| Accepting unrealistic deadlines | Team burns out, quality suffers | Push back and propose alternatives |
| Skipping quality controls under pressure | Bugs and issues multiply | Protect critical quality controls |
| Not communicating trade-offs | Stakeholders don't understand the cost | Make trade-offs explicit |
| Not protecting team focus | Constant interruptions derail progress | Protect focus time |
| Not escalating unsustainable pressure | Team burns out | Escalate when needed |

## Hands-on exercise

Pick a situation where you're under pressure:

1. Make pressure visible
2. Identify what matters most
3. Assess options and risks
4. Make trade-offs explicit
5. Protect quality where it matters
6. Communicate clearly

## Verify your thinking

- [ ] Have you made pressure visible?
- [ ] Have you identified what matters most?
- [ ] Have you assessed options and risks?
- [ ] Have you made trade-offs explicit?
- [ ] Are you protecting quality where it matters?
- [ ] Are you protecting your team?

Continue to [`professional.md`](professional.md).
