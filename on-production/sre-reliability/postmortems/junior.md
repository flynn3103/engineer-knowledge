# Postmortems — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Can you write a factual, blameless incident record with follow-up actions that reduce a repeat failure?

---

## Purpose

A postmortem turns an incident into durable learning. **Blameless** does not mean consequence-free; it means investigate the system conditions, signals, and decisions that made a reasonable action lead to harm. A document that merely names a person cannot improve detection, controls, or design.

## Minimum structure

| Section | Questions it answers |
|---|---|
| Summary | What did users experience and for how long? |
| Timeline | What happened, when, and what evidence supports it? |
| Impact | Which journeys, regions, or customers were affected? |
| Contributing factors | What conditions made failure possible or harder to detect? |
| Actions | Who will do what, by when, and how will success be verified? |

## Example

A deploy removed a timeout on a payment call. Requests queued, checkout timed out for 24 minutes, and the alert arrived after customers complained. Contributing factors include missing timeout tests, a broad rollout, and an alert on infrastructure CPU rather than successful checkout. “Alex removed the timeout” is factual but insufficient; explain why review, tests, and rollout controls did not catch it.

## Method

1. Start from the incident timeline and monitoring evidence.
2. Separate facts from hypotheses and label uncertainty.
3. Ask “what made this action or state possible?” repeatedly, without asking “who is at fault?”
4. Convert lessons into small, owned actions.
5. Review the document with participants and publish the outcome appropriately.

## Apply it

1. Draft a three-entry timeline for a failed deploy.
2. List three contributing factors across code, process, and detection.
3. Write two actions with a single owner and observable completion condition.

## Verify your work

- A reader can reconstruct user impact without attending the incident.
- Actions have owners, due dates, and evidence of completion.
- The document explains conditions and controls rather than assigning personal blame.

## Review questions

- What makes a postmortem blameless rather than vague?
- Why is a timestamped timeline valuable?
- How does an action item become verifiable?
