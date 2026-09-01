# Test Design & Fixtures — Middle

## Goal

Build independent tests with useful data and the right kind of test double.

## Test design

- Apply F.I.R.S.T.: fast, independent, repeatable, self-checking, timely.
- Use parameterization for the same rule across several inputs.
- One test may have several assertions when they prove one behavior.

## Fixtures and doubles

- Fresh mutable fixtures are the safe default.
- Use a builder when tests need varied valid data.
- Use a stub for inputs, a spy for recorded calls, and a fake for a lightweight working implementation.
- Put cleanup in fixture teardown so it runs after failures.

## Check

- Can this test run alone and in any order?
- Does the setup reveal what matters?
- Would a reader know why a double exists?
