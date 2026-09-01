# Over-Engineering Anti-Patterns — Middle

> Good design keeps options open by remaining cheap to change, not by predicting every future.

## Goal

Use evidence and reversibility to decide when a seam, layer, optimization, or configurable rule is justified.

## The rule of three, with judgment

Start concrete. On a second use, compare the cases. On a third similar use, extract the stable variation.

```python
def render_email_receipt(order):
    return render_receipt(order, channel="email")

def render_pdf_receipt(order):
    return render_receipt(order, channel="pdf")

def render_receipt(order, channel):
    return f"{channel}: {order.id}"
```

The rule is not arithmetic. Extract only when the cases share a meaningful name and a likely joint change.

## Decide with four questions

| Question | If no |
|---|---|
| Is there a current requirement? | Defer it. |
| Is the decision hard to reverse? | Prefer the simpler reversible path. |
| Does a real caller need this variation? | Keep the implementation concrete. |
| Can we measure the claimed benefit? | Do not optimize yet. |

## Right-size layers and configuration

- A layer must translate a boundary, enforce a policy, or isolate volatility. Forwarding alone is not a job.
- Composition is usually easier to trace than deep inheritance.
- Keep business rules in code when engineers own the change cycle.
- Make externalized rules typed, validated, versioned, observable, and owned.

## Protect attention

Time-box low-impact choices. Write down the decision criterion, choose a reversible default, and move effort to user impact, reliability, security, or delivery risk.

## Review questions

- What would break if this abstraction were absent?
- What is the smallest experiment that would validate this investment?
- Is this layer reducing coupling or only adding a hop?
- What must be true before this configuration becomes a product capability?

## Check your understanding

1. What evidence would justify a second implementation?
2. How do you tell essential complexity from accidental complexity?
3. Which decision in your design is hardest to reverse?
