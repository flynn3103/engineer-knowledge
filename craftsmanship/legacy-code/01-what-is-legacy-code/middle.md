# What Is Legacy Code — Middle

## Use a spectrum, not a label

- Legacy code is still **code without useful automated feedback**.
- The important measure is not readability; it is the cost and risk of change.
- A well-tested 600-line class can be safer to modify than a pretty, untested service.

## Make the feedback gap visible

| Where a defect is found | Typical delay | Cost of correction |
| --- | --- | --- |
| Local test | Seconds | Lowest |
| CI | Minutes | Low |
| Staging or QA | Hours or days | High |
| Production | Days or weeks | Highest |

- Untested code pushes discovery toward the expensive end of the table.
- Your job is to move feedback left: from production toward a local test.

## Spot likely legacy code

Tests define legacy code. These signals help you estimate the work:

- Dependencies are created inside the logic instead of supplied to it.
- A method mixes parsing, rules, I/O, and persistence.
- Behavior is hidden in global state or side effects.
- The team says “do not touch that module.”
- Copy-paste fixes, commented-out code, or recurring bugs cluster nearby.

## Estimate testability first

| Shape | First move |
| --- | --- |
| Pure function | Test it directly. |
| Dependencies passed as arguments | Pass fakes in a test. |
| Dependencies created internally | Add a seam before testing. |
| Global state and side effects only | Isolate one dependency or observable result at a time. |

```python
class Notifier:
    def __init__(self, clock, mailer, users):
        self.clock = clock
        self.mailer = mailer
        self.users = users

    def send_overdue_notice(self, user_id: str) -> None:
        user = self.users.get(user_id)
        if user.is_overdue(self.clock.today()):
            self.mailer.send(user.email, "Your payment is overdue")
```

- Supplying the clock, mailer, and repository creates test seams.
- A test can use fakes and assert the visible result without a database or email server.

## Choose where to invest

Prioritize code that has both a reason to change and a costly failure mode:

1. Is a funded feature or bug fix about to touch it?
2. How often does it change?
3. What is its blast radius and incident history?
4. Can you add a small characterization test now?
5. Is replacement cheaper than making it testable?

- Do not chase a coverage percentage in isolation.
- Prefer the smallest test that makes the next change safer.

## Keep terms separate

- **Legacy code:** missing safety feedback.
- **Technical debt:** a present shortcut that creates future cost.
- They often overlap, but either can exist without the other.

## Working checklist

- [ ] I know the behavior my next change could damage.
- [ ] I know where the feedback currently arrives.
- [ ] I have chosen the smallest seam or test that shortens that loop.
- [ ] I am investing because of churn, risk, or an imminent change—not cosmetic dislike.

## Recall questions

- Why is testability a better risk signal than readability?
- Which shape of code needs a seam before its first isolated test?
- What evidence would justify deferring tests for an untouched module?
