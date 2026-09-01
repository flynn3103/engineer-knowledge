# Characterization Tests — Middle

Characterization is a focused exploration: learn enough about the code paths around a planned change to detect unintended movement.

## Work from paths, not random examples

Map the decision points, inputs, outputs, and side effects. Cover the path you will modify, its nearest alternatives, and any boundary values that change the decision.

```python
def label(score: int) -> str:
    if score < 0:
        return "invalid"
    return "pass" if score >= 60 else "retry"

def test_negative_scores_are_currently_invalid():
    assert label(-1) == "invalid"
```

Use a failing sentinel when output is unknown: assert a deliberately wrong value, run it, inspect the actual result, then replace it with the observation. Record surprises in the test name or a nearby note.

## Handle effects deliberately

- Return values: assert exact values where stable.
- Exceptions: assert type and useful message fragments.
- State changes: inspect the public state after the call.
- I/O: introduce a seam and assert the request or command sent to a fake.

Avoid snapshotting huge outputs by default. A smaller set of assertions explains behavior better and fails more usefully.

## Stop condition

Stop when you can describe the nearby behavior, the relevant paths are pinned, and a proposed edit would produce a meaningful red test. Then make the behavior change in a separate commit.
