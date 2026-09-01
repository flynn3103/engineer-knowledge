# Load Shedding — Professional

<!-- level-focus -->
At professional level, focus on this question:

> Can you govern organization-wide overload policy so capacity allocation, fairness, and customer commitments remain explicit during growth and crisis?

---

## A product and capacity contract

Load-shedding policy encodes priority. Maintain a reviewed classification of critical journeys, tenant commitments, emergency access, and degradable work. Capacity teams publish limits and test scenarios; product leaders approve customer-facing fairness choices. Do not leave these decisions to whatever gateway rule was written during the last incident.

## Growth scenario

A launch doubles traffic while enterprise and free tiers share infrastructure. Roll out quotas by cohort, publish retry semantics, and reserve a tested emergency pool. Use staged load tests and canaries; exit only when protected journeys, fairness measures, and dependency saturation remain within targets at forecast load.

## Accountability

Track rejected-work impact by cohort, protected-journey success, capacity forecast error, and exception use. Escalate when contractual service is routinely shed: the answer may be investment, changed promise, or demand control—not a stealthier rejection.

## Apply it

1. Define an ownership matrix for policy, enforcement, and customer commitments.
2. Plan a launch with load stages and rollback gates.
3. Choose fairness and reliability measures.

## Verify your work

- Priority policy is understandable to product and support teams.
- Tests cover forecast peak and a dependency failure.
- Customer-impact data informs the next capacity decision.

## Review questions

- Why is load shedding a product decision as well as a technical one?
- Which exit conditions prove a launch is safe?
- What should happen when contractual traffic is repeatedly shed?
