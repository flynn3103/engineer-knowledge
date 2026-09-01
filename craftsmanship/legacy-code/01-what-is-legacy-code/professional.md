# What Is Legacy Code — Professional

## Lead legacy work as value delivery

- Technical legacy is missing feedback; the leadership challenge is funding and sequencing the work.
- Do not ask for a vague “debt quarter.” Attach safety work to an outcome the business already needs.
- Deliver in small slices so stakeholders can see reduced risk and faster follow-up changes.

## Translate engineering risk into outcomes

| Avoid this | Say this instead |
| --- | --- |
| “Billing has no tests.” | “Billing changes are slow and can cause revenue-impacting incidents.” |
| “We need a refactor.” | “We need a safe path to ship the new pricing tier.” |
| “There is lots of tech debt.” | “These three components drive most incidents and rework.” |

- Pair the claim with evidence: change lead time, incident history, support load, or blocked roadmap work.
- Be honest when a low-churn, low-risk area should wait. Selective investment builds trust.

## Use an investment decision

1. **Churn:** How often has this area changed recently?
2. **Risk:** What happens if it fails, and how often has it failed?
3. **Pull:** Is a funded feature about to enter this code?
4. **Testability:** What is the smallest seam or characterization effort?
5. **Knowledge:** Is a single person carrying the specification?

Invest now when an imminent or frequent change meets high risk or key-person risk. Defer stable, low-risk code. Replace gradually when the current design cannot be made safe at a reasonable cost.

## Make the economics concrete

- Compare the cost of coverage with the expected cost of incidents, slow delivery, and repeated investigation.
- Measure the next similar change after coverage. That is the strongest proof of payback.
- Avoid false precision: risk estimates are decision aids, not guarantees.

```text
Safe feature slice:
1. Capture current behavior.
2. Add the smallest useful tests and seams.
3. Deliver the requested behavior.
4. Measure time, defects, and confidence on the next change.
```

## Avoid rewrite traps

- A rewrite can discard years of undocumented edge cases.
- Before replacing a component, characterize its observable behavior.
- Migrate through a stable boundary, route one slice at a time, and compare old and new results where possible.
- Keep the old implementation as an executable source of truth until each slice is proven.

## Build an operating model

- Include “cover before modifying” in feature estimates for risky areas.
- Maintain a small portfolio of hotspots ranked by churn, risk, and business pull.
- Review incident and delivery data regularly; move investment as the product changes.
- Reward engineers for reducing future change cost, not only for shipping the immediate feature.
- Teach teams to preserve behavior first and improve behavior deliberately second.

## Leadership checklist

- [ ] Each investment is tied to a specific product, reliability, or delivery outcome.
- [ ] The work ships incrementally rather than disappearing into a rewrite.
- [ ] We use evidence to prioritize and to show payback.
- [ ] Tests and characterization reduce key-person risk as well as defects.
- [ ] Teams know when to cover, defer, replace, or strangle a legacy area.

## Recall questions

- Which business outcomes make legacy work legible to stakeholders?
- How do you avoid turning a safety investment into a value-free rewrite?
- What evidence would change your prioritization next quarter?
