# What Is Legacy Code — Junior

## Core idea

- **Legacy code is code without automated tests.** Its age, author, style, and language do not decide this.
- Ask: *can I change this code and learn quickly if I broke it?*
- New, clean-looking code without tests is legacy code from the day it is merged.

## Why this definition helps

| Unhelpful label | Useful label |
| --- | --- |
| “Old code I did not write” | “Code I cannot safely change” |
| Blames people or age | Identifies missing feedback |
| Has no clear fix | Tells you to add a safety net |

- Think of tests as a circuit breaker: they make mistakes visible early and safely.
- Do not treat legacy code as shameful. Treat it as an area that needs feedback before change.

## Two ways to change code

### Edit and pray

- Read enough code to feel confident.
- Make the change.
- Click around or run the app once.
- Ship while hoping you missed no callers or edge cases.

### Cover and modify

1. Observe the current behavior.
2. Add a test that records that behavior.
3. Make one small change.
4. Run the test after every meaningful step.
5. Refactor only while the test stays green.

> The goal is not to test everything before moving. It is to add enough feedback to make the next change safe.

## Example: clean code can still be legacy

```python
from dataclasses import dataclass


@dataclass
class Item:
    price: float
    quantity: int


def total(items: list[Item], is_member: bool) -> float:
    amount = sum(item.price * item.quantity for item in items)
    if is_member:
        amount *= 0.9
    if amount > 100:
        amount -= 5
    return amount
```

- This function may be readable and new.
- It is still legacy if no automated test checks it.
- First capture today’s behavior before changing its discount rules:

```python
def test_member_discount_and_large_order_discount_are_preserved():
    items = [Item(price=60, quantity=2)]

    assert total(items, is_member=True) == 103
```

## Your first legacy-code workflow

1. Choose the smallest behavior your change could affect.
2. Find a stable input and observe the current output.
3. Write a test with that input and output.
4. Run it to prove it describes the current system.
5. Change a small piece of code.
6. Run the test again before continuing.

## Watch for these traps

- **“It is too small to test.”** Small functions are cheap to test and easy to break later.
- **“I will add tests after the feature.”** The risky moment is during the feature; add the safety net first.
- **“I should rewrite it instead.”** First understand and preserve behavior. Refactoring comes after safety.
- **“Manual testing is enough.”** Manual checks are useful, but they are not repeatable feedback for future changes.

## Quick checklist

- [ ] I judge legacy code by feedback, not age.
- [ ] I can name the behavior I am about to protect.
- [ ] I have a test that captures current behavior before editing it.
- [ ] I make and verify changes in small steps.

## Recall questions

- Why can a brand-new module be legacy code?
- What is the difference between “edit and pray” and “cover and modify”?
- What is the first test you would write before changing a risky function?
