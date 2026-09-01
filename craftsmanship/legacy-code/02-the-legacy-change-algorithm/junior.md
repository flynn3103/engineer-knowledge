# The Legacy Change Algorithm — Junior

## The five-step algorithm

Use this order whenever you must change code that has little or no test coverage:

1. **Identify change points** — locate the behavior that must change.
2. **Find test points** — find an input, output, or collaborator you can observe.
3. **Break dependencies** — make that behavior reachable from a test.
4. **Write a characterization test** — record what the code does now.
5. **Make the change** — change behavior in small steps and keep tests green.

## Why the order matters

- Changing first destroys the only evidence of the old behavior.
- A test point tells you where feedback can come from.
- Dependency breaking is not cleanup; it enables safe observation.
- Characterization tests protect existing behavior, including behavior you may later decide to change deliberately.

## Work a small example

```python
def delivery_fee(total: float, is_member: bool) -> float:
    if is_member:
        return 0
    return 8 if total < 50 else 0


def test_existing_member_delivery_rule():
    assert delivery_fee(total=20, is_member=True) == 0
```

1. The change point is the delivery rule.
2. The return value is a test point.
3. This pure function needs no dependency break.
4. The test characterizes current member behavior.
5. Now add the intended new rule and update or add a test for it.

## Ask two questions repeatedly

- **Where do I need to change behavior?**
- **How can a test observe that behavior?**

If you cannot answer the second question, do not guess. Find or create a seam first.

## Common mistakes

- Writing a test for the new behavior before proving the old behavior.
- Refactoring unrelated code while trying to create the first test.
- Testing private details instead of an observable result.
- Making a large change before running the safety test.
- Treating a failing characterization test as proof the old code is wrong; first confirm the test setup and expected behavior.

## Quick checklist

- [ ] I can name the exact behavior that must change.
- [ ] I have chosen an observable input, output, or collaborator.
- [ ] I have the smallest seam required to test it.
- [ ] A test captures current behavior before my change.
- [ ] I will change one small step at a time.

## Recall questions

- Which step protects you from accidentally changing existing behavior?
- Why might you need to break a dependency before writing a test?
- What should a junior do when no test point is visible?
