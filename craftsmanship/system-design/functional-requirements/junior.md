# Functional Requirements — Junior

Write requirements as observable behaviors: "The system shall accept a user login with email and password" rather than "The system shall be secure." Each requirement must be testable—you should be able to write a test that passes or fails.

## The mental model

A functional requirement describes:
1. **Who** (actor or user role)
2. **What** (action or behavior)
3. **When** (trigger or condition)
4. **Result** (observable outcome)

Example: "When a user submits a form with valid email and password, the system shall create a session and redirect to the dashboard."

## Step-by-step method

1. Identify the user role or actor (customer, admin, system).
2. Describe the action they perform or request.
3. State the precondition (what must be true first).
4. State the expected outcome (what the system does).
5. List acceptance criteria (how you verify it works).

## Small example

**Requirement:** User login

**Precondition:** User has a registered account with email and password.

**Action:** User enters email and password on the login page and clicks "Sign In."

**Expected outcome:** System validates credentials and creates a session.

**Acceptance criteria:**
- Valid credentials → session created, user redirected to dashboard
- Invalid password → error message displayed, no session created
- Non-existent email → error message displayed, no session created
- Empty fields → form validation error shown

## Common beginner mistakes

1. **Mixing what with how:** "The system shall use bcrypt to hash passwords" is implementation, not a requirement. The requirement is "The system shall securely store passwords."

2. **Vague acceptance criteria:** "The system shall be fast" is not testable. Instead: "The login response shall complete within 500 ms."

3. **Forgetting edge cases:** Only listing the happy path. Always include error cases and boundary conditions.

4. **Ambiguous language:** "The system shall handle errors gracefully" is unclear. Instead: "When an error occurs, the system shall display an error message and allow the user to retry."

## Hands-on checklist

For each requirement, verify:

- [ ] Can you write a test that passes when the requirement is met?
- [ ] Does it describe observable behavior, not implementation?
- [ ] Are preconditions and postconditions clear?
- [ ] Are edge cases and error cases included?
- [ ] Is the language specific and unambiguous?

## Test yourself

1. What makes a requirement testable?
2. Why should you separate "what" from "how"?
3. How do you know when a requirement is complete?
4. What are three common acceptance criteria for a login feature?

Continue to [`middle.md`](middle.md).
