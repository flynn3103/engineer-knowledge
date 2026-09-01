# Acceptance & BDD — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Acceptance & BDD** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Acceptance & BDD
>
> *Unit tests ask "is the code right?" Acceptance tests ask "did we build the thing the customer asked for?" — this tier teaches the difference and your first behaviour scenario.*

---

## Core Concept 1 — Two Different Questions

Imagine a "transfer money" feature. Two tests can both pass while the product fails the customer.

```python
# UNIT TEST — "is the code correct?"
def test_transfer_subtracts_amount():
    account = Account(balance=100)
    account.withdraw(30)
    assert account.balance == 70   # the function does what it says
```

This is true and useful. But it never asks: *should the user be allowed to transfer when their account is frozen? What error do they see if they're overdrawn? Does the money actually arrive in the other account?* Those are **business questions**, and they need a different kind of test:

```gherkin
# ACCEPTANCE TEST — "does it do what the customer wanted?"
Scenario: A customer cannot overdraw their account
  Given my account balance is $50
  When I try to transfer $80 to my landlord
  Then the transfer is declined
  And I see the message "Insufficient funds"
  And my balance is still $50
```

The unit test lives *inside* one function. The acceptance test describes *observable behaviour* the customer cares about. Both matter. The trap is thinking green unit tests mean the feature is right.

| | Unit / Integration | Acceptance |
|---|---|---|
| Question | Is this code correct? | Did we build what was asked? |
| Audience | Developers | Business + QA + developers |
| Language | Code/technical | Plain business language |
| Fails when | A function misbehaves | The system doesn't meet the requirement |

---

## Core Concept 2 — Acceptance Criteria as the Definition of Done

Before writing a line of code, a good team agrees on **acceptance criteria**: the specific conditions that make the story "done". They turn a vague request into something testable.

A vague story:

> *As a user, I want to reset my password.*

The same story with acceptance criteria:

- Given a registered email, requesting a reset sends a reset link valid for 1 hour.
- An expired link shows "This link has expired" and offers to resend.
- An unknown email shows the *same* success message (so attackers can't tell which emails exist).
- After a successful reset, the old password no longer works.

Notice what happened: the fourth criterion (the security one) was probably *missing* from the original request, and writing criteria surfaced it. **This is the whole point** — agreeing on concrete examples before coding finds the gaps while they're cheap to fix. Each criterion is a candidate acceptance test.

---

## Core Concept 3 — What BDD Is (and Isn't)

BDD grew out of TDD. Dan North coined it because new developers kept asking *"where do I start? what do I test? what do I call the test?"* He found that phrasing tests as **behaviour** — sentences starting with "should" — answered all three. The `test-driven-development` skill covers the red-green-refactor loop BDD builds on.

The single most important thing to learn now:

> **BDD is mainly about *conversation*, and only secondarily about tools.** Its value is getting business, QA, and developers to agree on what "correct behaviour" means *before* code is written. The Gherkin files and Cucumber tests are a *by-product* of that conversation.

Most teams get this backwards. They install Cucumber, write Gherkin alone at their desks, and wonder why it feels like extra paperwork. **Gherkin without the conversation is pure overhead.** Remember the order: talk first, write examples together, *then* automate them. As a junior, your job is mostly to recognise this so you don't mistake "we use Cucumber" for "we do BDD".

---

## Core Concept 4 — Your First Gherkin Scenario

Gherkin has a small, fixed vocabulary. The core is **Given / When / Then**:

| Keyword | Role | Plain meaning |
|---|---|---|
| `Feature` | Names the capability | "What are we building?" |
| `Scenario` | One concrete example | "Here's one situation." |
| `Given` | Context / starting state | "The world is set up like this." |
| `When` | The action / event | "This happens." |
| `Then` | The expected outcome | "We should observe this." |
| `And` / `But` | Continue the previous step | Chains more Givens/Thens. |

A complete feature file for a shopping cart:

```gherkin
Feature: Free shipping threshold
  As a customer
  I want free shipping over $50
  So that I'm encouraged to buy a little more

  Scenario: Order qualifies for free shipping
    Given my cart total is $60
    When I check out
    Then shipping is free

  Scenario: Order does not qualify
    Given my cart total is $40
    When I check out
    Then shipping costs $5.99
```

Read it aloud. A product owner with no coding background understands it completely — that is the design goal. Each `Scenario` is one example; together they pin down the rule.

---

## Core Concept 5 — Wiring Gherkin to Code with Step Definitions

A Gherkin step is just a sentence. To make it *run*, you write a **step definition**: a small function matched to the sentence by a pattern. Here it is in Python with `pytest-bdd`:

```python
# features/free_shipping.feature  → the Gherkin above
# test_free_shipping.py           → the step definitions

from pytest_bdd import scenarios, given, when, then, parsers

scenarios("free_shipping.feature")   # load every scenario in the file

@given(parsers.parse("my cart total is ${total:d}"), target_fixture="cart")
def cart_with_total(total):
    return Cart(subtotal=total)

@when("I check out", target_fixture="checkout")
def check_out(cart):
    return checkout(cart)

@then("shipping is free")
def shipping_is_free(checkout):
    assert checkout.shipping == 0

@then(parsers.parse("shipping costs ${cost:f}"))
def shipping_costs(checkout, cost):
    assert checkout.shipping == cost
```

The flow is always the same:

1. The runner reads the `.feature` file.
2. For each step, it finds the step definition whose pattern matches the sentence.
3. It calls that function, passing any captured values (`$60` → `total=60`).
4. `Then` steps assert; if an assertion fails, the scenario fails — and the failure is reported in *business language*, e.g. *"Order qualifies for free shipping → shipping is free: FAILED"*.

The same scenario could be wired in Java (Cucumber), JavaScript (Cucumber.js), or Go (Godog). The Gherkin is portable; only the glue code changes.

---

## Core Concept 6 — Manual UAT vs Automated Acceptance Tests

Acceptance testing comes in two flavours, and they complement rather than compete.

**User Acceptance Testing (UAT)** is *people* — usually the product owner or real users — trying the feature against the acceptance criteria, by hand, before it's accepted. It's the final "yes, this is what we asked for" sign-off. UAT catches things automation can't easily judge: *does this actually feel right? is the wording clear? is the flow sensible?* Its weakness is that it's slow, manual, and doesn't repeat cheaply — you can't run UAT on every commit.

**Automated acceptance tests** are the same criteria, encoded (often as Gherkin scenarios) so a machine checks them on every change. They're fast and repeatable, so they protect against *regression* — the feature silently breaking later. Their weakness is that they only check what you thought to encode; they can't notice the wording feels off.

| | Manual UAT | Automated acceptance |
|---|---|---|
| Who runs it | A person (PO / real user) | The CI pipeline |
| When | Before accepting a story / release | Every commit |
| Strength | Judgement, feel, the unexpected | Speed, repeatability, regression safety |
| Weakness | Slow, doesn't repeat cheaply | Only checks what was encoded |

A healthy team uses both: automate the criteria you can pin down precisely, and keep human UAT for judgement and final sign-off. Crucially, both are driven by the *same acceptance criteria* — that's why agreeing on them up front (Concept 2) pays off twice.

---

## Real-World Examples

- **Login lockout.** Story: "lock the account after 5 failed attempts." A scenario nails the edge: `Given I have failed to log in 4 times / When I enter a wrong password again / Then my account is locked`. The "is it the 5th attempt or the 6th?" ambiguity gets settled by the example, not by guessing.
- **Discount codes.** Product wants "SAVE10 gives 10% off." Writing scenarios surfaces the unasked questions: does it stack with other offers? does it apply before or after tax? is it case-sensitive? Each becomes a `Scenario`.
- **UAT before launch.** A bank's product owners spend a day clicking through the new statements feature against a checklist of acceptance criteria. They find that statements show the wrong currency symbol for EU accounts — a requirement gap no unit test was looking for.

---

## Common Mistakes

- **Confusing "we use Cucumber" with "we do BDD."** The tool is not the practice. The conversation is the practice.
- **Writing scenarios after the code, alone.** Then they're just a slow, awkward way to write unit tests, with none of the shared-understanding payoff.
- **Treating acceptance tests as a replacement for unit tests.** They answer different questions. You need both; you need *far more* unit tests than acceptance tests.
- **Putting UI clicks in Gherkin** (`When I click the button with id "submit"`). Keep Gherkin in business language; the *how* belongs in step definitions. (You'll learn this discipline properly at [Middle Level](./middle.md).)
- **One giant scenario that tests everything.** One scenario = one behaviour. Split them.

---

## Apply it

1. Choose one small, known input for **Acceptance & BDD**.
2. Predict the output or observable behavior.
3. Run the smallest example or probe that exercises the concept.
4. Change one input to trigger a failure or boundary case.
5. Explain the evidence using the guide's vocabulary.

## Verify your work

- Record the exact input, command or code path, and output.
- Repeat the probe and confirm the result is consistent.
- Show one expected success and one expected failure.
- Resolve any difference between the prediction and the evidence.

## Review questions

- What problem does Acceptance & BDD solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
