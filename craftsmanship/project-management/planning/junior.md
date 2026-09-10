# Planning — Junior

**Your question:** How do I break down work? How do I estimate effort? How do I identify dependencies?

At junior level, planning starts with breaking down work into manageable pieces. This makes estimation easier and helps you understand what you're building.

## Breaking down work

Work breakdown means taking a large feature and splitting it into smaller tasks:

1. **Understand the feature.** What are you building? Why does it matter?

2. **Identify major components.** What are the main parts?

3. **Break into tasks.** What are the concrete steps?

4. **Estimate each task.** How long will each task take?

5. **Identify dependencies.** What needs to happen first?

## A concrete example: Breaking down work

**Feature:** Build a user profile page

**Bad breakdown:**
- Build user profile page (2 weeks)

Problems:
- Too vague
- Hard to estimate
- Hard to track progress

**Good breakdown:**

**Understand the feature:**
"The user profile page shows user information (name, email, bio, avatar). Users can edit their profile. Changes are saved to the database."

**Identify major components:**
1. Frontend: Display user information
2. Frontend: Edit form
3. Backend: API to fetch user data
4. Backend: API to update user data
5. Database: Store user data

**Break into tasks:**

| Task | Effort | Dependencies |
|---|---|---|
| Design user profile page | 1 day | None |
| Create API to fetch user data | 2 days | Database schema |
| Create API to update user data | 2 days | Database schema |
| Build frontend to display profile | 2 days | Fetch API |
| Build frontend to edit profile | 2 days | Update API |
| Add validation and error handling | 1 day | All APIs |
| Write tests | 2 days | All components |
| Deploy and monitor | 1 day | All tests pass |

**Total effort:** 13 days

**Identify dependencies:**
- Database schema must be ready before APIs
- Fetch API must be ready before display frontend
- Update API must be ready before edit frontend
- All components must be ready before testing

Better because:
- Clear breakdown
- Realistic estimates
- Easy to track progress
- Dependencies are visible

## Estimating effort

Estimate by breaking work into pieces and using historical data:

1. **Break work into small tasks.** Each task should be 1-3 days.

2. **Look at similar past work.** How long did similar tasks actually take?

3. **Estimate with a range.** Optimistic, most-likely, pessimistic.

4. **Add buffer for unknowns.** Add 20-30% for integration and testing.

5. **Track actual vs. estimated.** Learn from your estimates.

## A concrete example: Estimating effort

**Task:** Create API to fetch user data

**Estimate:**
- Optimistic: 1 day (if everything goes smoothly)
- Most-likely: 2 days (normal case)
- Pessimistic: 3 days (if there are issues)

**Add buffer:**
- Total: 2 days + 0.5 days buffer = 2.5 days

**Track actual:**
- Actual: 2 days (good estimate!)

## Identifying dependencies

Dependencies are things that must happen before other things:

1. **List all tasks.**

2. **For each task, ask:** What must be done before this?

3. **Draw a dependency diagram.**

## A concrete example: Identifying dependencies

**Tasks:**
1. Design user profile page
2. Create API to fetch user data
3. Create API to update user data
4. Build frontend to display profile
5. Build frontend to edit profile
6. Add validation and error handling
7. Write tests
8. Deploy and monitor

**Dependencies:**
- Task 2 (Fetch API) depends on: Database schema
- Task 3 (Update API) depends on: Database schema
- Task 4 (Display frontend) depends on: Task 2 (Fetch API)
- Task 5 (Edit frontend) depends on: Task 3 (Update API)
- Task 6 (Validation) depends on: Task 2, 3, 4, 5
- Task 7 (Tests) depends on: Task 2, 3, 4, 5, 6
- Task 8 (Deploy) depends on: Task 7

**Dependency diagram:**
```
Database schema
    ↓
Task 2 (Fetch API) ──→ Task 4 (Display frontend)
Task 3 (Update API) ──→ Task 5 (Edit frontend)
    ↓
Task 6 (Validation)
    ↓
Task 7 (Tests)
    ↓
Task 8 (Deploy)
```

## Common beginner mistakes

| Mistake | Why it hurts | Fix |
|---|---|---|
| Not breaking down work | Hard to estimate and track | Break into small tasks |
| Estimating without historical data | Estimates are just guesses | Look at similar past work |
| Not identifying dependencies | Tasks block each other | Identify dependencies upfront |
| Underestimating effort | You miss deadlines | Add buffer for unknowns |
| Not tracking actual vs. estimated | You don't improve estimates | Track and learn |

## Hands-on exercise

Pick a feature you need to build:

1. Break it down into tasks
2. Estimate each task
3. Identify dependencies
4. Draw a dependency diagram
5. Track actual vs. estimated

## Verify your thinking

- [ ] Have you broken down the work into small tasks?
- [ ] Have you estimated each task?
- [ ] Have you identified dependencies?
- [ ] Have you added buffer for unknowns?
- [ ] Will you track actual vs. estimated?

Continue to [`middle.md`](middle.md).
