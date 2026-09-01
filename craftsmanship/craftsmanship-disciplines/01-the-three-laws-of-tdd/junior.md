# The Three Laws of TDD — Junior

## Goal

Use a tiny feedback loop: write one failing test, make it pass, then improve the code.

## The laws

1. Write no production code until a failing test requires it.
2. Write only enough test code to fail.
3. Write only enough production code to pass.

## The loop

1. Pick one observable behavior.
2. Write the smallest pytest test that describes it.
3. Run it and see it fail for the expected reason.
4. Add the smallest implementation.
5. Run the test. Refactor only while all tests pass.

## Example

    def test_adds_two_numbers():
        assert add(2, 3) == 5

    def add(left, right):
        return left + right

## Practice

- Build is_even, then fizz_buzz, one example at a time.
- Name tests after behavior, such as test_empty_cart_has_zero_total.
- Stop when the next test is unclear; make the current code clearer first.
