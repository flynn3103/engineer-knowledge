# Seams and Enabling Points — Junior

## Core idea

- A **seam** is a place where you can change how a program behaves without editing the code at that place.
- An **enabling point** is where you choose the alternative behavior.
- Seams let you replace slow, risky, or external dependencies while testing legacy code.

## A simple example

```python
class ShippingService:
    def __init__(self, rate_client):
        self.rate_client = rate_client

    def quote(self, destination: str, weight: float) -> float:
        return self.rate_client.rate(destination, weight)


class FakeRateClient:
    def rate(self, destination: str, weight: float) -> float:
        return 12.50
```

- The call to `rate_client.rate` is the seam.
- Passing `FakeRateClient` is the enabling point.
- A test can quote shipping without a network call.

## Seams you will meet

| Seam | How you use it |
| --- | --- |
| Object seam | Pass or replace a collaborator. |
| Parameter seam | Supply a value such as time, randomness, or configuration. |
| File/configuration seam | Select a safe test configuration. |
| Process boundary | Replace an external process or API with a fake. |

## Find a seam

1. Identify the dependency preventing a test: database, clock, network, filesystem, or global state.
2. Find where the code chooses or calls that dependency.
3. Make the smallest change that lets a test supply an alternative.
4. Use a fake that is predictable and records what matters.
5. Keep production behavior unchanged.

## Avoid these mistakes

- Adding an abstraction for every class before it is needed.
- Using a fake that behaves nothing like the dependency you rely on.
- Testing the fake instead of the business behavior.
- Moving unrelated logic while introducing a seam.
- Forgetting to run the same behavior through the real collaborator in integration tests.

## Checklist

- [ ] I can name the dependency blocking my test.
- [ ] I know where the program chooses that dependency.
- [ ] The new seam is narrow and keeps production behavior intact.
- [ ] My test uses the seam to observe an important behavior.
