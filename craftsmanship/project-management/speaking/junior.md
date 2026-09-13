# Communication — Junior

**Your question:** How do I explain my ideas clearly? How do I listen to others? How do I give feedback without hurting feelings?

Clear communication is the foundation of everything. At junior level, you're learning to express yourself clearly, listen actively, and give feedback that helps people improve without making them defensive.

## The method: clarity, listening, and feedback

1. **Be clear about what you're saying.** Use simple language. Avoid jargon. If you must use technical terms, explain them.

2. **Listen actively.** Don't just wait for your turn to talk. Ask questions. Try to understand what the other person is really saying.

3. **Give feedback on the work, not the person.** "This function doesn't handle null values" is feedback. "You didn't think about edge cases" is criticism.

4. **Be specific.** "This is good" is vague. "This error handling is clear and covers the main cases" is specific.

5. **Be honest.** Don't sugarcoat problems. But deliver the truth with respect.

## Clarity: the STAR framework

Use STAR to explain a situation clearly:

- **Situation:** What was the context?
- **Task:** What needed to be done?
- **Action:** What did you do?
- **Result:** What was the outcome?

This framework helps you tell a complete story without rambling.

## A concrete example

**Bad explanation:**
"I fixed the login bug. It was a problem with the password validation. I changed the code and now it works."

Problems:
- Vague (what was the bug exactly?)
- No context (why was it a problem?)
- No detail (what did you change?)
- No outcome (how do you know it works?)

**Good explanation (using STAR):**
"**Situation:** Users with special characters in their password (like `P@ss!word`) couldn't log in.

**Task:** I needed to fix the password validation to accept special characters.

**Action:** I reviewed the validation regex and found it was rejecting special characters. I updated the regex to allow them, added a test case for special characters, and verified it works on both web and mobile.

**Result:** Users can now log in with special characters. All existing tests still pass. I added a test case to prevent regression."

Better because:
- Clear context (what was the problem?)
- Specific action (what exactly did you change?)
- Measurable result (how do you know it works?)

## Active listening

Listen to understand, not to respond. Use these techniques:

1. **Ask clarifying questions.** "Can you give me an example?" "What do you mean by that?"

2. **Paraphrase what you heard.** "So you're saying the API is slow when there are many concurrent requests. Is that right?"

3. **Don't interrupt.** Let the other person finish their thought.

4. **Pay attention to body language.** Are they frustrated? Confused? Excited?

5. **Acknowledge their point.** "I hear you. That's a valid concern."

## Giving constructive feedback

Use the SBI framework (Situation-Behavior-Impact):

- **Situation:** When did this happen? What was the context?
- **Behavior:** What specifically did the person do?
- **Impact:** What was the result? How did it affect you or the team?

## A concrete example

**Bad feedback:**
"Your code review comments were too harsh."

Problems:
- Vague (which comments?)
- Accusatory (implies bad intent)
- No specific impact (how did it affect me?)

**Good feedback (using SBI):**
"**Situation:** In the code review for the payment feature, you left several comments.

**Behavior:** You wrote 'This is inefficient' and 'Why would you do it this way?' without explaining what was wrong or suggesting an alternative.

**Impact:** I felt defensive and didn't learn anything. I would have appreciated understanding why you thought it was inefficient and what you would have done differently."

Better because:
- Specific situation (which code review?)
- Specific behavior (which comments?)
- Clear impact (how did it affect you?)
- Constructive (implies the person can improve)

## Common beginner mistakes

| Mistake | Why it hurts | Fix |
|---|---|---|
| Rambling without a point | People don't understand what you're saying | Use STAR to structure your explanation |
| Not listening, just waiting to talk | People feel unheard | Ask questions and paraphrase what you heard |
| Giving feedback on the person, not the work | People get defensive | Focus on the specific behavior and its impact |
| Being vague | People don't know what to improve | Be specific about what you observed |
| Being harsh | People shut down and don't learn | Deliver feedback with respect and curiosity |
| Not asking for clarification | You misunderstand and make wrong assumptions | Ask questions when you don't understand |

## Hands-on checklist

Before you communicate something important, verify:

- [ ] Can you explain it in simple language?
- [ ] Have you used STAR or SBI to structure your message?
- [ ] Are you being specific, not vague?
- [ ] Are you focusing on the work/behavior, not the person?
- [ ] Are you being honest?
- [ ] Have you listened to the other person's perspective?

## Test yourself

1. What does STAR stand for?
2. Why is listening important in communication?
3. What's the difference between feedback on the work and feedback on the person?
4. How do you give feedback without making someone defensive?

Continue to [`middle.md`](middle.md).
