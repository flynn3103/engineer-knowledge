# Metacognition and Learning — Middle

**Your question:** Which specific weakness am I targeting, and am I using a learning technique that actually works?

Junior level teaches you to catch the illusion of competence in the moment — recognition dressed up as understanding. Middle level is about pointing practice deliberately at what you're actually weak at, backed by evidence rather than a vague sense of "I should get better at backend stuff," and choosing techniques that produce durable skill instead of ones that just feel productive.

## The method: deliberate practice

**Deliberate practice** targets a specific, identified weakness, just beyond your current ability, with fast feedback and correction. It is not "do more of the job." Doing more tickets, more on-call shifts, or more code review is experience — it's valuable, but it doesn't reliably fix a specific weakness unless the practice is aimed at that weakness and gives you a signal on whether you're improving.

**Passive exposure:** "I'll get better at handling error cases by writing more features."
**Deliberate practice:** "I keep missing edge cases in error handling — I'll run a 10-minute adversarial pass on every PR before submitting it, and track whether review comments about missed edge cases go down."

### How to apply it

1. **Diagnose from evidence, not self-perception.** Pull your last 10–15 pieces of real feedback: code review comments, bug reports assigned to your changes, retro notes, postmortem action items. Categorize them.
2. **Target one weakness.** Pick the category that repeats most. Narrow it until it's specific enough that you'd recognize it in a single review comment — not "write better code," but "missing null checks on optional API response fields."
3. **Design a practice rep with fast feedback.** The feedback loop should resolve in under a day, not "wait for the next real incident." A checklist you apply before submitting a PR, a self-review pass, a small deliberate exercise reproducing the failure mode on a toy example.
4. **Correct and repeat, varying context.** Apply the same targeted check across different kinds of work so the skill transfers, not just recurs in one narrow situation.

## Choosing a learning technique that actually works

Not all "studying" produces skill. Rereading a doc or highlighting a wiki page feels productive because it's fluent — the words make sense as you read them — but fluency while reading is a poor predictor of what you can produce later. These three techniques have a real feedback loop built in; rereading and highlighting don't.

| Technique | What it is | When to use it |
|---|---|---|
| **Retrieval practice** | Testing yourself — trying to produce the answer before checking it | Before relying on something under pressure (an on-call shift, a review checklist, a runbook) |
| **Spaced repetition** | Revisiting the same material after a gap, not all at once | Anything you need durably, not just for the next hour (architecture patterns, failure classes, domain vocabulary) |
| **Elaboration** | Explaining *why* something works, not just restating *what* it is | Anything you need to apply flexibly in a new situation, not just recognize |
| Rereading / highlighting | Passively re-scanning material | Rarely the right choice on its own — feels productive but has weak transfer |

### A concrete example

**Situation:** Over three sprints, six of twenty code review comments received flagged the same issue: missing error-handling edge cases (unhandled timeouts, empty responses, concurrent writes).

**1. Diagnose:** Pulled the last 20 review comments across three sprints and categorized them. 6 of 20 (30%) were specifically about unhandled error paths — the single largest category, ahead of naming (3) and test coverage (4).

**2. Target:** Not "write more robust code" — specifically "identify edge cases in error handling before submitting a PR."

**3. Practice rep:** Before submitting any PR touching an external call or shared state, spend 10 minutes on an adversarial pass: write down what happens if the network call times out, if the response is empty, if two requests hit this path concurrently, if the downstream service returns a 500. Compare that list against what actually shipped, and separately against what the reviewer later flags.

**4. Track:** Recorded edge-case review comments per sprint. Sprint 1 (before starting): 2 of 6 comments. Sprint 2 (practicing): 1 of 7. Sprint 3: 0 of 5. The trend, not a single sprint, is the evidence the practice is working.

**Applying the right technique, not just "studying more":**
- **Elaboration** instead of rereading the team's error-handling wiki page: rather than reading it again, wrote a short explanation for a teammate of *why* each documented pattern prevents a specific failure (e.g., "retry with backoff prevents a downstream service from getting hammered right when it's already struggling to recover" — not just "retry with backoff on 5xx").
- **Retrieval** instead of re-reading the on-call runbook before a shift: closed the runbook and tried to recall the top five failure classes and their first diagnostic step, then checked the runbook against the recalled list.
- **Spaced repetition** instead of a single cram session: revisited that same recalled list a week later, and again before the next on-call rotation a month out, instead of only reviewing right before each shift.

## Common mistakes at middle level

| Mistake | Why it hurts | Fix |
|---|---|---|
| Practicing broadly ("get better at backend") instead of a named weakness | No specific feedback signal, so you can't tell if you're actually improving | Pick one narrow weakness backed by evidence — review comments, bug categories, retro notes |
| Rereading docs or code and calling it "studying" | Feels productive, produces almost no retention or transfer | Replace with retrieval — close the material, try to produce or explain it, then check |
| Doing more of the same work and calling it "practice" | Repetition without a correction checkpoint just repeats the existing mistake at a slightly higher volume | Add a deliberate feedback checkpoint after each rep — a review-comment tally, a self-check against a list |
| Practicing only inside your comfort zone | No growth occurs — the "practice" is actually just habitual work you've already mastered | Target something just beyond current ability, where errors are common but recoverable |
| Cramming a technique once, right before you need it | Weak retention; the skill falls apart under real pressure | Space repetitions across days or weeks instead of a single session |

## Hands-on exercise

1. Pull your last 10–15 pieces of real feedback (review comments, bug reports, retro notes, postmortem action items).
2. Categorize them. Which category repeats most?
3. Name the one weakness you'll target for the next two to four weeks, specific enough to recognize in a single comment.
4. Design a practice rep with a feedback signal you can check in under a day.
5. Pick one technique — retrieval, spacing, or elaboration — and say specifically how you'll apply it, not "study more."
6. After two weeks, check: did the category of feedback about this weakness actually decrease?

## Verify your thinking

- [ ] Is your target weakness named specifically enough that you'd recognize it in a review comment?
- [ ] Did you pick the target from real evidence — comments, bugs, incidents — not a vague feeling?
- [ ] Does your practice loop give you feedback in under a day, rather than "wait for the next real occurrence"?
- [ ] Are you using retrieval or elaboration instead of rereading or highlighting?
- [ ] If you repeated this practice a month from now, would it feel harder than reading the material twice in one sitting? (It should — that difficulty is the sign it's actually building durable skill.)

Continue to [`senior.md`](senior.md).
