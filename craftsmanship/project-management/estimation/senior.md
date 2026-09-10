# Estimation — Senior

**Your question:** How do I estimate across dependent tasks, account for risk and uncertainty, and give stakeholders a realistic timeline?

Middle level teaches you to build calibrated estimates for individual tasks. At senior level, you're estimating across multiple dependent tasks, accounting for risk, and communicating uncertainty to stakeholders. The challenge is that tasks don't happen in isolation — they depend on each other, they have risks that can delay them, and you need to give a realistic timeline that accounts for all of this.

## Estimating dependent tasks and critical path

When tasks depend on each other, you can't just add the estimates. You need to:

1. **Map dependencies.** Which tasks must finish before others can start?
2. **Identify the critical path.** Which sequence of tasks determines the overall timeline?
3. **Account for parallelization.** Which tasks can run in parallel?
4. **Add risk buffers.** Where are the biggest risks?

## Realistic scenario: Estimating a major feature with dependencies

**Feature:** Migrate payment system from Stripe to a new provider (Adyen)

**Tasks:**
1. Evaluate Adyen API and set up sandbox (2-3 days)
2. Implement payment processing in Adyen (3-5 days) — depends on task 1
3. Implement refund flow in Adyen (2-3 days) — depends on task 2
4. Migrate historical transactions (3-7 days) — depends on task 1
5. Set up monitoring and alerts (1-2 days) — depends on task 2
6. Run parallel testing (Stripe + Adyen) (3-5 days) — depends on tasks 2, 3, 4
7. Cutover and monitoring (1-2 days) — depends on task 6

**Dependency graph:**

```
Task 1: Evaluate Adyen (2-3 days)
    ├─→ Task 2: Payment processing (3-5 days)
    │       ├─→ Task 3: Refund flow (2-3 days)
    │       │       └─→ Task 6: Parallel testing (3-5 days)
    │       │               └─→ Task 7: Cutover (1-2 days)
    │       └─→ Task 5: Monitoring (1-2 days)
    │
    └─→ Task 4: Migrate transactions (3-7 days)
            └─→ Task 6: Parallel testing (3-5 days)
```

**Critical path analysis:**

| Path | Duration | Notes |
|---|---|---|
| 1 → 2 → 3 → 6 → 7 | 2-3 + 3-5 + 2-3 + 3-5 + 1-2 = 11-18 days | Longest path |
| 1 → 2 → 5 | 2-3 + 3-5 + 1-2 = 6-10 days | Parallel with path 1 |
| 1 → 4 → 6 → 7 | 2-3 + 3-7 + 3-5 + 1-2 = 9-17 days | Parallel with path 1 |

**Critical path:** 1 → 2 → 3 → 6 → 7 = 11-18 days

**With parallelization (3 engineers):**
- Engineer A: Task 1 (2-3 days) → Task 2 (3-5 days) → Task 3 (2-3 days) → Task 6 (3-5 days) → Task 7 (1-2 days)
- Engineer B: Task 4 (3-7 days) — can start after Task 1
- Engineer C: Task 5 (1-2 days) — can start after Task 2

**Realistic timeline:** 11-18 days (critical path doesn't change much with parallelization)

## Adding risk buffers

The estimates above assume everything goes smoothly. But there are risks:

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Adyen API has undocumented behavior | 40% | +2-3 days | Start with sandbox testing early |
| Historical transaction migration is complex | 30% | +2-4 days | Pilot migration with subset first |
| Parallel testing finds issues | 50% | +1-2 days | Plan for rework |
| Cutover has issues | 20% | +1-3 days | Have rollback plan ready |

**Risk-adjusted estimate:**
- Base estimate: 11-18 days
- Risk buffer: +2-4 days (for most likely risks)
- **Total estimate: 13-22 days**

**Confidence:** "I'm 70% confident we'll finish in 13-22 days. If we hit multiple risks (API issues + migration complexity), it could go to 25 days."

## Communicating timeline to stakeholders

Don't give a single number. Give a range with assumptions and risks.

**Bad communication:**
"We'll migrate to Adyen in 2 weeks."

Problems:
- No range (what if it takes 3 weeks?)
- No assumptions (what if the API is undocumented?)
- No risks (what if migration is complex?)

**Good communication:**
"We estimate 13-22 days for the Adyen migration, with 70% confidence.

**Breakdown:**
- Evaluate and implement: 8-13 days
- Migrate historical data: 3-7 days
- Testing and cutover: 4-7 days

**Key assumptions:**
- Adyen API documentation is accurate
- Historical transaction migration doesn't have unexpected complexity
- We can run parallel testing without major issues

**Biggest risks:**
- Adyen API has undocumented behavior (40% chance, +2-3 days)
- Historical transaction migration is complex (30% chance, +2-4 days)
- Parallel testing finds issues (50% chance, +1-2 days)

**If any of these risks materialize, the timeline extends to 20-25 days.**

**Triggers for escalation:**
- If evaluation takes >3 days, we escalate the migration timeline
- If migration pilot shows >10% data issues, we add 1 week for rework"

Better because:
- Clear range (13-22 days)
- Assumptions are explicit
- Risks are named with probability and impact
- Triggers for escalation are clear

## Tracking and adjusting estimates

As the project progresses, update your estimates:

1. **After task 1 (Evaluate Adyen):** Did it take 2-3 days as estimated? If it took 4 days, adjust remaining estimates.
2. **After task 2 (Payment processing):** Did it take 3-5 days? If it took 6 days, adjust remaining estimates.
3. **Weekly:** Review progress against critical path. Are we on track?

**Example adjustment:**
- Task 1 took 4 days (longer than estimated)
- Task 2 is taking 6 days (longer than estimated)
- New estimate: 15-25 days (was 13-22 days)
- Communicate the change to stakeholders with reasons

## Common mistakes at senior level

| Mistake | Why it hurts | Fix |
|---|---|---|
| Adding estimates without accounting for dependencies | Total estimate is wrong | Map dependencies and identify critical path |
| Ignoring risks in the estimate | Estimate is too optimistic | List risks with probability and impact, add buffer |
| Giving a single number instead of a range | Stakeholders expect you to hit it exactly | Give a range with confidence level |
| Not tracking actual vs. estimated | You can't improve estimates | Track progress weekly and adjust |
| Communicating only the best case | Stakeholders are surprised when it takes longer | Communicate the range and risks |

## Hands-on exercise

Take a real project you're planning:

1. Break it into 10-15 tasks
2. Map dependencies and identify the critical path
3. Estimate each task with O, M, P
4. Identify the top 5 risks with probability and impact
5. Add a risk buffer to the critical path
6. Communicate the timeline to stakeholders with range, assumptions, and risks
7. Commit to tracking progress weekly and adjusting estimates

## Verify your thinking

- [ ] Have you mapped all dependencies and identified the critical path?
- [ ] Have you identified the top 5 risks with probability and impact?
- [ ] Does your estimate include a risk buffer?
- [ ] Can you communicate the range, assumptions, and risks to stakeholders?
- [ ] Will you track progress weekly and adjust estimates?

Continue to [`professional.md`](professional.md).
