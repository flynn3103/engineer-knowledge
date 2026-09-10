# Planning — Middle

**Your question:** How do I write OKRs? How do I define Epics? How do I create a work breakdown structure?

Middle level teaches you to plan at scale using OKRs, Epics, and work breakdown structures. These frameworks help you align teams and make trade-off decisions.

## OKR: Objectives and Key Results

OKRs are a planning framework that connects business goals to concrete outcomes:

- **Objective:** What do you want to achieve? (Qualitative, inspiring)
- **Key Results:** How will you measure success? (Quantitative, measurable)

## A concrete example: Writing OKRs

**Bad OKR:**
"Build a better user profile"

Problems:
- Vague
- Not measurable
- No clear success criteria

**Good OKR:**

**Objective:** Improve user engagement with their profile

**Key Results:**
1. 50% of users visit their profile at least once per month (up from 20%)
2. 30% of users update their profile information (up from 5%)
3. User satisfaction with profile feature increases to 4.5/5 (up from 3.5/5)

Better because:
- Clear objective
- Measurable key results
- Success is defined upfront
- Easy to track progress

## Epic: A large body of work

An Epic is a large feature or initiative that takes multiple weeks or months:

1. **Define the Epic.** What are you building?

2. **Write the OKR.** Why does it matter? How will you measure success?

3. **Break into Stories.** What are the concrete user stories?

4. **Estimate effort.** How long will it take?

5. **Identify dependencies.** What needs to happen first?

## A concrete example: Defining an Epic

**Epic:** User Profile System

**OKR:**
- Objective: Improve user engagement with their profile
- Key Results:
  1. 50% of users visit their profile at least once per month
  2. 30% of users update their profile information
  3. User satisfaction increases to 4.5/5

**Stories:**
1. As a user, I can view my profile information
2. As a user, I can edit my profile information
3. As a user, I can upload a profile picture
4. As a user, I can see my profile activity history
5. As a user, I can share my profile with others

**Effort estimate:**
- Story 1: 3 days
- Story 2: 3 days
- Story 3: 2 days
- Story 4: 4 days
- Story 5: 3 days
- Total: 15 days

**Dependencies:**
- Stories 1-3 can be done in parallel
- Story 4 depends on Story 1
- Story 5 depends on Story 1

## Work Breakdown Structure (WBS)

A WBS is a hierarchical decomposition of work:

```
Epic: User Profile System
├── Story 1: View profile
│   ├── Task 1.1: Design profile page
│   ├── Task 1.2: Build frontend
│   ├── Task 1.3: Build backend API
│   └── Task 1.4: Write tests
├── Story 2: Edit profile
│   ├── Task 2.1: Design edit form
│   ├── Task 2.2: Build frontend
│   ├── Task 2.3: Build backend API
│   └── Task 2.4: Write tests
├── Story 3: Upload picture
│   ├── Task 3.1: Design upload UI
│   ├── Task 3.2: Build frontend
│   ├── Task 3.3: Build backend API
│   └── Task 3.4: Write tests
└── Story 4: Activity history
    ├── Task 4.1: Design history view
    ├── Task 4.2: Build frontend
    ├── Task 4.3: Build backend API
    └── Task 4.4: Write tests
```

## Planning with constraints

Real planning has constraints:

1. **Timeline:** When do you need to deliver?

2. **Resources:** How many people do you have?

3. **Dependencies:** What must happen first?

4. **Quality:** What quality standards must you meet?

## A concrete example: Planning with constraints

**Constraint:** Deliver user profile system in 4 weeks with 2 engineers

**Available effort:** 2 engineers × 4 weeks × 5 days = 40 days

**Estimated effort:** 15 days for all stories

**Analysis:**
- You have 40 days available
- You need 15 days
- You have 25 days buffer

**Options:**
1. Do all stories in 4 weeks (15 days work, 25 days buffer for testing, review, deployment)
2. Do stories 1-3 in 4 weeks, do story 4 later
3. Do stories 1-2 in 4 weeks, do stories 3-4 later

**Recommendation:**
"Do all stories in 4 weeks. You have enough time and buffer for testing and deployment."

## Common mistakes at middle level

| Mistake | Why it hurts | Fix |
|---|---|---|
| OKRs are too vague | Hard to measure success | Make OKRs specific and measurable |
| Epics are too large | Hard to estimate and track | Break Epics into smaller stories |
| No work breakdown | Hard to track progress | Create a detailed WBS |
| Not considering constraints | Plans are unrealistic | Consider timeline, resources, dependencies |
| Not identifying dependencies | Tasks block each other | Identify dependencies upfront |

## Hands-on exercise

Pick an initiative you need to plan:

1. Write the OKR
2. Define the Epic
3. Break into Stories
4. Create a WBS
5. Estimate effort
6. Identify dependencies
7. Consider constraints

## Verify your thinking

- [ ] Is the OKR clear and measurable?
- [ ] Is the Epic well-defined?
- [ ] Are the Stories clear?
- [ ] Is the WBS detailed?
- [ ] Have you estimated effort?
- [ ] Have you identified dependencies?
- [ ] Have you considered constraints?

Continue to [`senior.md`](senior.md).
