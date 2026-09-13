# Estimation — Professional

**Your question:** How do I build an organization where estimates are accurate, teams learn from past estimates, and we allocate resources across multiple projects effectively?

Senior level teaches you to estimate dependent tasks and communicate risk. At professional level, you're building systems and culture that enable good estimation across the organization. You're tracking whether estimates are accurate, learning from past projects, and allocating resources across multiple initiatives.

## Design and operations checklist

1. **Establish estimation standards.** How do teams estimate? What format do estimates take? How are they tracked?
2. **Build calibration tracking.** Record estimates and actual outcomes. Score whether estimates are accurate.
3. **Create estimation templates.** Provide templates for common types of work (feature, migration, infrastructure).
4. **Allocate resources across projects.** Use estimates to decide which projects to prioritize and how to allocate people.
5. **Measure estimation health.** Track calibration, accuracy, and whether estimates improve over time.

## Estimation standards and templates

Establish how teams should estimate:

**Standard format:**
- Task name and description
- Optimistic (O), Most-likely (M), Pessimistic (P) estimates
- PERT estimate: (O + 4M + P) / 6
- Key assumptions
- Top 3 risks with probability and impact
- Dependencies on other tasks

**Example template:**

```
Task: Implement payment processing for Adyen

Estimates (in days):
- Optimistic: 3 (everything goes smoothly)
- Most-likely: 5 (normal friction)
- Pessimistic: 8 (API issues, need to reverse-engineer)
- PERT: (3 + 4×5 + 8) / 6 = 5.2 days

Assumptions:
- Adyen API documentation is accurate
- No breaking changes to the API
- We can test in sandbox without production access

Top risks:
1. API documentation is incomplete (40% chance, +2 days)
2. Integration issues with existing code (30% chance, +1 day)
3. Need to handle edge cases (50% chance, +1 day)

Dependencies:
- Depends on: Adyen sandbox setup (Task 1)
- Blocks: Refund flow implementation (Task 3)
```

## Calibration tracking

Track whether estimates are accurate:

1. **Record the estimate** at the time it's made (O, M, P, PERT, confidence level)
2. **Record the actual outcome** when the task completes
3. **Score the estimate** — did it land in the range? Was the confidence level accurate?
4. **Aggregate by team and project type** — are certain types of work consistently over/under estimated?

**Example tracking:**

| Task | O | M | P | PERT | Actual | In range? | Notes |
|---|---|---|---|---|---|---|---|
| Auth setup | 1 | 2 | 3 | 2.0 | 2.5 | Yes | Schema conflicts, took longer |
| Email/password | 1 | 2 | 4 | 2.3 | 1.5 | Yes | Simpler than expected |
| Google OAuth | 1 | 1.5 | 3 | 1.6 | 2.0 | Yes | Rate limiting issues |

**Calibration analysis:**
- 3 out of 3 estimates landed in range (100% accuracy)
- Average error: 0.3 days
- Confidence level: 70% (should be right 70% of the time)

## Allocating resources across projects

Use estimates to decide how to allocate people:

1. **Estimate all active projects** using the standard format
2. **Calculate total effort** for each project (sum of PERT estimates)
3. **Identify critical path** for each project
4. **Allocate people** to projects based on:
   - Priority (which projects matter most?)
   - Dependencies (which projects block others?)
   - Risk (which projects have the highest risk?)

**Example resource allocation:**

| Project | Total effort | Critical path | Priority | Risk | Allocated people |
|---|---|---|---|---|---|
| Adyen migration | 20 days | 15 days | High | High | 3 engineers |
| API redesign | 30 days | 25 days | Medium | Medium | 2 engineers |
| Performance optimization | 15 days | 12 days | Low | Low | 1 engineer |

**Timeline:**
- Week 1-2: Adyen migration (critical path)
- Week 2-4: API redesign (can run in parallel)
- Week 4-5: Performance optimization (can run in parallel)

## Learning from past estimates

After each project, review:

1. **Were estimates accurate?** Did actual time land in the estimated range?
2. **What was different?** What assumptions were wrong?
3. **How can we improve?** What should we adjust for future estimates?

**Example retrospective:**

**Project:** Adyen migration

**Estimates vs. actual:**
- Estimated: 13-22 days
- Actual: 18 days
- Accuracy: Good (landed in range)

**What was different:**
- API documentation was incomplete (as predicted)
- Historical transaction migration was simpler than expected
- Parallel testing found fewer issues than expected

**Adjustments for future estimates:**
- Payment gateway integrations: adjust pessimistic case to +3 days (was +2)
- Data migrations: adjust optimistic case to -1 day (simpler than expected)
- Parallel testing: adjust most-likely case to -0.5 days (fewer issues)

## Realistic scenario: Estimating across multiple projects

**Situation:** You have 5 engineers and 3 projects to estimate and prioritize

**Projects:**
1. **Adyen migration** (high priority, high risk)
   - Estimated: 13-22 days
   - Critical path: 15 days
   - Risk: High (API issues, migration complexity)

2. **API redesign** (medium priority, medium risk)
   - Estimated: 20-35 days
   - Critical path: 25 days
   - Risk: Medium (design complexity)

3. **Performance optimization** (low priority, low risk)
   - Estimated: 10-18 days
   - Critical path: 12 days
   - Risk: Low (well-understood problem)

**Resource allocation:**
- Weeks 1-3: Adyen migration (3 engineers) + API redesign (2 engineers)
- Weeks 3-5: API redesign (3 engineers) + Performance optimization (2 engineers)
- Weeks 5-6: Performance optimization (3 engineers)

**Timeline:**
- Adyen migration: 3 weeks (critical path 15 days, 3 engineers)
- API redesign: 4 weeks (critical path 25 days, 2-3 engineers)
- Performance optimization: 2 weeks (critical path 12 days, 2-3 engineers)

**Total timeline:** 6 weeks (with parallelization)

## Common mistakes at professional level

| Mistake | Why it hurts | Fix |
|---|---|---|
| No estimation standard | Different teams estimate differently, hard to compare | Establish a standard format (O, M, P, PERT) |
| Not tracking actual vs. estimated | Can't improve calibration | Record actual time and compare to estimate |
| Ignoring risks in resource allocation | Projects slip because risks materialize | Include risk buffer in timeline |
| Allocating based on optimistic case | Projects always slip | Allocate based on PERT or pessimistic case |
| Not learning from past projects | Same mistakes repeat | Review estimates vs. actual after each project |

## Hands-on exercise

For your organization:

1. Establish an estimation standard (O, M, P, PERT format)
2. Estimate all active projects using the standard
3. Calculate total effort and critical path for each
4. Allocate resources based on priority, dependencies, and risk
5. Create a tracking system for actual vs. estimated
6. After first project completes, review accuracy and adjust future estimates

## Verify your thinking

- [ ] Do all teams use the same estimation format?
- [ ] Are estimates tracked and compared to actual outcomes?
- [ ] Do you allocate resources based on PERT or pessimistic estimates, not optimistic?
- [ ] Do you review past projects to improve future estimates?
- [ ] Can you explain why each project's estimate is what it is?

## Further reading

- Steve McConnell, *Software Estimation: Demystifying the Black Art*
- Agile Estimating and Planning
- The Planning Fallacy and how to overcome it


