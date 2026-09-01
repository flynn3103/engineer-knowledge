# Contract Testing — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Contract Testing** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Contract Testing
>
> *Two services agree on an interface — prove it without ever starting them together.*

---

## Core Concept 1 — The combinatorial problem

Say you have 5 consumers and 3 providers, and consumers chain through providers. To gain confidence with end-to-end tests, you'd deploy *all* of them into one environment and run scenarios. The cost grows with the number of pairs and the depth of the call graph:

```
Consumers:  Web, Mobile, Reporting, Fulfilment, Admin
Providers:  Catalog, Payments, Inventory

End-to-end "test them together":
  - Needs every service deployed and healthy at once
  - One flaky service fails the whole suite
  - Slow: real network, real DB, real startup
  - Hard to attribute failures: which pair broke?
  - Combinatorial: N consumers × M providers × scenarios
```

Three things make this hurt:

1. **Cost.** Standing up the full graph for every pipeline run is expensive and slow.
2. **Flakiness.** The probability that *all* services are healthy at once drops as the graph grows. A 1% per-service failure rate across 8 services is roughly an 8% chance the suite fails for reasons unrelated to your change.
3. **Blame.** When the run goes red, you don't know *which* boundary broke.

Contract testing breaks the combinatorics: each consumer–provider *pair* gets one contract, tested twice (once per side), in isolation. No shared environment, no full graph.

---

## Core Concept 2 — What a contract actually is

A contract is a list of **interactions**. Each interaction says: "given some provider state, when I send *this* request, I expect *that* response." It is data, not code — usually JSON.

Here is a minimal pact file fragment for `Orders` (consumer) calling `Payments` (provider):

```json
{
  "consumer": { "name": "OrdersService" },
  "provider": { "name": "PaymentsService" },
  "interactions": [
    {
      "description": "a request for payment 42",
      "providerState": "payment 42 exists",
      "request": {
        "method": "GET",
        "path": "/payments/42"
      },
      "response": {
        "status": 200,
        "headers": { "Content-Type": "application/json" },
        "body": { "id": 42, "status": "settled", "amount": 1999 }
      }
    }
  ]
}
```

Notice what the contract captures: the **shape and semantics at the boundary** — path, method, status, and the fields the consumer reads (`id`, `status`, `amount`). It does *not* capture *how* `Payments` computes the amount. That is the provider's own business — and the provider's own tests.

---

## Core Concept 3 — Consumer and provider

Every API boundary has two roles:

- **Consumer** — the side that *calls*. It depends on the response shape. If a field it reads disappears or changes type, it breaks.
- **Provider** — the side that *responds*. It owns the implementation.

Contract testing tests **both sides against the same contract**, separately:

```
Consumer side                          Provider side
-------------                          -------------
Run consumer test against a            Take the contract and replay
MOCK provider that behaves per         each request against the REAL
the contract. If the consumer          provider. If the real response
code works against the mock, it        matches the contract, the
records the contract.                  provider honors it.

   produces the contract  ─────────►   verifies the contract
```

If both sides pass, you have transitive confidence: the consumer works against *exactly what the contract says*, and the provider *produces exactly what the contract says* — so the consumer works against the real provider, without ever running them together.

---

## Core Concept 4 — A first Pact consumer test

The consumer test is where the contract is *born*. You declare the interaction, point your real client code at Pact's mock provider, and assert your client behaves. Pact records the interaction into a pact file.

```javascript
// orders/test/payments.consumer.pact.test.js
const { PactV3, MatchersV3 } = require('@pact-foundation/pact');
const { getPayment } = require('../src/paymentsClient');

const { like, integer, string } = MatchersV3;

const provider = new PactV3({
  consumer: 'OrdersService',
  provider: 'PaymentsService',
});

describe('Payments client', () => {
  it('fetches a payment by id', () => {
    provider
      .given('payment 42 exists')                 // provider state
      .uponReceiving('a request for payment 42')
      .withRequest({ method: 'GET', path: '/payments/42' })
      .willRespondWith({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: like({                              // matcher: shape, not exact value
          id: integer(42),
          status: string('settled'),
          amount: integer(1999),
        }),
      });

    return provider.executeTest(async (mockServer) => {
      const payment = await getPayment(mockServer.url, 42); // real client code
      expect(payment.status).toBe('settled');               // assert client works
    });
  });
});
```

Two things to internalize:

- **`getPayment` is your real client code**, not a stub. The test proves your code parses the response correctly.
- **Matchers** (`like`, `integer`, `string`) say "I need a field of this *type/shape*," not "this exact value." That keeps the contract about structure, which is what the consumer truly depends on.

When this test passes, Pact writes `OrdersService-PaymentsService.json` — the contract. That file is the artifact the provider will later verify against.

---

## Core Concept 5 — What contract testing does NOT do

This is the most misunderstood part, so learn it early:

- It does **not** test business behavior. The contract says "`/payments/42` returns a body with `status` and `amount`." It does **not** check that the amount is computed correctly, that fraud rules ran, or that the payment actually settled. That is the provider's functional/unit tests.
- It is **not** a replacement for the provider's own tests. It checks the *interface agreement* at the boundary — message shape and semantics — nothing inside.
- It does **not** prove the whole system works. You still want a thin layer of end-to-end checks for critical flows (see the [test pyramid](../test-strategy-and-the-pyramid/junior.md)).

A clean mental split: **contract testing protects the *seam* between services; unit and integration tests protect what happens *inside* each service.**

---

## Real-World Examples

- **Mobile app + backend.** A mobile app (consumer) and a backend (provider) ship on different schedules — you cannot redeploy the app on every backend change. A contract lets the backend team know, before deploy, whether removing a field will crash a shipped app version still in users' hands.
- **A field rename.** `Payments` renames `amount` → `amountCents`. Without contract testing, `Orders` silently reads `undefined` in production. With it, provider verification fails in CI because the contract still expects `amount`.
- **A new required field.** `Orders` starts reading a `currency` field. The consumer test records it into the contract; provider verification fails until `Payments` adds `currency`. The break surfaces in CI, on the right team's screen.

---

## Common Mistakes

- **Asserting exact values instead of shape.** Hard-coding `amount: 1999` in the contract makes it brittle and turns it into a behavior test. Use type matchers.
- **Putting everything the provider returns into the contract.** Only declare fields the consumer actually *reads*. Extra fields couple you to things you don't use.
- **Thinking it replaces all integration/E2E tests.** It removes the *combinatorial* ones; you still keep a few high-value end-to-end smoke tests.
- **Treating it as a behavior test.** "The payment settled correctly" is not a contract concern.

---

## Apply it

1. Choose one small, known input for **Contract Testing**.
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

- What problem does Contract Testing solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
