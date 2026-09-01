# Test Design & Fixtures — Junior

## Goal

Write tests that clearly show the setup, action, and expected result.

## Arrange, act, assert

1. Arrange only the data needed for the behavior.
2. Act once.
3. Assert the meaningful outcome.

    def test_discounted_price():
        cart = Cart(total=100)
        result = cart.apply_discount(10)
        assert result == 90

## Fixtures

- A fixture is the known starting state for a test.
- Give it a clear name and keep it near the test when small.
- Prefer literals and simple helpers over hidden shared setup.

## Practice

- Rename one vague test to describe behavior.
- Remove irrelevant setup from one test.
- Split a test that checks unrelated outcomes.
