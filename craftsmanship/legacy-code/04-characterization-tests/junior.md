# Characterization Tests — Junior

A characterization test records what code does **now**. It is a photograph, not a claim that the behavior is correct. Write one before changing unfamiliar code without a safety net.

## The loop

1. Choose an input near the change you need.
2. Run the code and observe its return value, exception, state change, or emitted event.
3. Write that observed result into a test.
4. Run the test until it is green.
5. Add another example for an important branch or boundary.

```python
def shipping_cost(total: float) -> float:
    return 0 if total >= 50 else 7.5

def test_shipping_cost_at_the_current_threshold():
    assert shipping_cost(50) == 0
```

Do not “correct” a surprising result while characterizing it. First pin it; later decide, with product intent, whether it is a defect to change.

## Good targets

- A branch your change might affect.
- An odd input: empty, zero, boundary, duplicate, or malformed value.
- An externally visible effect: saved record, outgoing message, or error.

## Checklist

- Does the test describe observed behavior in its name?
- Is it deterministic?
- Does it avoid real network, time, and database dependencies where possible?
- Can you explain why this behavior matters before editing it?
