# Estimation — Middle

**Your question:** How do I build estimates that are actually accurate? How do I estimate across multiple tasks and dependencies?

Junior level teaches you to give ranges with assumptions. At middle level, you're building **calibrated estimates** — estimates that are actually accurate over time. You track where actual results land in your ranges, adjust your assumptions, and estimate across dependent tasks.

## Build calibrated estimates

A calibrated estimate is one where:
- Your optimistic case happens about 10% of the time
- Your most-likely case happens about 60% of the time
- Your pessimistic case happens about 20% of the time
- Your actual results land in the range about 80% of the time

**How to calibrate:**
1. Track actual vs. estimated for every task
2. If actual is always faster than pessimistic, your pessimistic case is too pessimistic
3. If actual is always slower than most-likely, your most-likely case is too optimistic
4. Adjust your estimates based on what you learn

## The three-point technique with historical data

For each task, estimate:

- **O (optimistic):** best case, ~1-in-10 outcome
- **M (most-likely):** realistic case with normal friction
- **P (pessimistic):** worst case you'd still call plausible, ~1-in-10 outcome

**PERT formula:** `E = (O + 4M + P) / 6`

But don't invent O, M, P from imagination. Anchor them in data:

1. **Outside view first:** Look at the last 5 similar tasks. What was the range? Use that as your starting point.
2. **Inside view second:** What's different about this task? Adjust for those differences.

## Realistic scenario: Estimating a feature across multiple tasks

**Feature:** Add user authentication with email/password and social login (Google, GitHub)

**Tasks:**
1. Set up authentication library and database schema
2. Implement email/password login
3. Implement Google OAuth
4. Implement GitHub OAuth
5. Add password reset flow
6. Write tests and documentation

**Historical data:**
- Last 3 authentication tasks took: 2, 3, 2 days (range: 2-3 days)
- Last 2 OAuth integrations took: 1, 2 days (range: 1-2 days)
- Last 3 testing/docs tasks took: 1, 2, 1 days (range: 1-2 days)

**Estimates with calibration:**

| Task | O | M | P | PERT | Assumptions |
|---|---|---|---|---|---|
| Auth setup | 1 | 2 | 3 | 2.0 | Library docs are clear, no schema conflicts |
| Email/password | 1 | 2 | 4 | 2.3 | No password reset yet, basic validation only |
| Google OAuth | 1 | 1.5 | 3 | 1.6 | Google API is stable, no rate limiting issues |
| GitHub OAuth | 1 | 1.5 | 3 | 1.6 | Similar to Google, reuse patterns |
| Password reset | 0.5 | 1 | 2 | 1.1 | Email service is already set up |
| Tests & docs | 1 | 2 | 3 | 2.0 | Standard coverage, no edge cases |
| **Total** | **5.5** | **9.5** | **18** | **10.6** | |

**Confidence:** "I'm 70% confident we'll finish between 9-12 days. If any OAuth provider has API issues or we need to handle edge cases, it could go to 15 days."

## Estimating dependent tasks

When tasks depend on each other, you can't just add the estimates. You need to account for:
- Waiting time (Task B can't start until Task A is done)
- Rework (Task A's output affects Task B's estimate)
- Parallelization (Some tasks can run in parallel)

**Example: Feature with dependencies**

```
Auth setup (2 days)
    ↓
Email/password (2 days) ← depends on auth setup
    ↓
Password reset (1 day) ← depends on email/password
    
Google OAuth (1.5 days) ← depends on auth setup (can run in parallel with email/password)
GitHub OAuth (1.5 days) ← depends on auth setup (can run in parallel)

Tests & docs (2 days) ← depends on all above
```

**Critical path:** Auth setup → Email/password → Password reset → Tests = 2 + 2 + 1 + 2 = 7 days minimum

**With parallelization:** Auth setup (2) → [Email/password (2) + Google OAuth (1.5) + GitHub OAuth (1.5)] → Password reset (1) → Tests (2) = 2 + 2 + 1 + 2 = 7 days (if you have 3 people)

## Tracking and improving calibration

After each task, record:
- Estimated range (O, M, P)
- Actual time
- What was different from assumptions

**Example tracking:**

| Task | O | M | P | Actual | Notes |
|---|---|---|---|---|---|
| Auth setup | 1 | 2 | 3 | 2.5 | Schema conflicts with existing code, took longer |
| Email/password | 1 | 2 | 4 | 1.5 | Simpler than expected, good library docs |
| Google OAuth | 1 | 1.5 | 3 | 2 | Rate limiting issues, needed retry logic |

**Lessons learned:**
- Schema conflicts are common (adjust future estimates +0.5 days)
- OAuth integrations often hit rate limiting (adjust pessimistic case to 3.5 days)
- Email/password is simpler than expected (adjust most-likely to 1.5 days)

## Common mistakes at middle level

| Mistake | Why it hurts | Fix |
|---|---|---|
| Range is too narrow ("2-3 days") | Doesn't reflect real uncertainty | Make pessimistic case genuinely uncomfortable (2-5 days) |
| Never tracking actual vs. estimated | You can't improve calibration | Record actual time and assumptions after each task |
| Ignoring dependencies | Total estimate is wrong | Map dependencies and identify critical path |
| Anchoring on first number | Team converges on wrong estimate | Have each person estimate silently, then discuss |
| Not adjusting for team differences | Same task takes different time for different people | Track by person and adjust for skill level |

## Hands-on exercise

Take a real feature you're planning:

1. Break it into 5-10 tasks
2. For each task, look up the last 3 similar tasks and their actual duration
3. Estimate O, M, P for each task based on historical data
4. Compute PERT estimate for each
5. Map dependencies and identify critical path
6. Commit to tracking actual vs. estimated
7. After completion, review what was different and adjust future estimates

## Verify your thinking

- [ ] Does your range come from historical data, not imagination?
- [ ] Have you mapped dependencies and identified the critical path?
- [ ] Is your pessimistic case genuinely plausible and uncomfortable?
- [ ] Can you explain why each task's estimate is what it is?
- [ ] Will you track actual vs. estimated to improve calibration?

Continue to [`senior.md`](senior.md).
