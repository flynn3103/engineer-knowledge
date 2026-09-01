# What Is Technical Debt — Junior

## Goal

Recognize debt as a future cost, not simply ugly code.

## The metaphor

- The shortcut is the principal.
- Extra effort on future changes is the interest.
- Debt can be deliberate when the benefit and repayment plan are clear.

## Not the same thing

- A bug produces wrong behavior now.
- Debt may produce correct behavior that is costly or risky to change.
- A style preference is not debt unless it creates a real future cost.

## Notice it

- Copy-pasted rules.
- Magic values with no owner.
- A change that requires touching many unrelated places.
- Missing tests around code you need to alter.

## Practice

When you take a shortcut, write down why, what it costs later, and the trigger for fixing it.
