# End-to-End Testing — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **End-to-End Testing** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → End-to-End Testing
>
> *The only test that proves the whole thing actually works — the way a real user touches it.*

---

## Core Concept 1 — What End-to-End Testing Is

Imagine your app as a black box. You don't look inside. You only do what a user does, and you check what a user would see.

```
   ┌──────────────────────────────────────────────┐
   │                  Your System                   │
   │                                                │
 You → [ Browser ] → [ Frontend ] → [ API ] → [ DB ] │
   │            ← rendered page ←                    │
   └──────────────────────────────────────────────┘
   ↑ the test acts here, from the outside
```

An E2E test:

1. Opens the real app (often a real browser).
2. Performs a real action sequence (type email, click "Log in").
3. Asserts on what the user sees (dashboard appears, name shows).

Everything in between — JavaScript bundles, API routes, database queries, authentication — runs for real. That is why a passing E2E test is the strongest evidence your software works.

**Key idea:** E2E tests answer *"does the whole product work for the user?"* — not *"is this function correct?"* (that's a unit test's job).

---

## Core Concept 2 — Where E2E Sits in the Test Pyramid

The **test pyramid** says: write many fast, cheap tests at the bottom and few slow, expensive tests at the top.

```
          /\
         /E2E\        ← few   (slow, high confidence, fragile)
        /------\
       / integr.\     ← some  (medium)
      /----------\
     /   unit      \  ← many  (fast, cheap, precise)
    /--------------\
```

E2E is the **top**: the smallest slice. A common, painful anti-pattern is the **ice-cream cone** — lots of E2E tests, few unit tests. It feels safe ("we test like a user!") but the suite becomes slow, flaky, and impossible to maintain.

The discipline you'll learn: **use E2E for confidence, not for coverage.** Cover the few critical journeys end-to-end; push everything else (validation rules, edge cases, error formatting) down into unit and integration tests where they run in milliseconds.

See [Test Strategy & the Pyramid](../01-test-strategy-and-the-pyramid/) for the full picture.

---

## Core Concept 3 — Your First Playwright Test

[Playwright](https://playwright.dev) is the modern default for browser E2E. It drives real Chromium, Firefox, and WebKit, and it **auto-waits** for elements — which kills most flakiness for free.

Install and scaffold:

```bash
npm init playwright@latest
```

A first test — log in and see the dashboard:

```ts
// tests/login.spec.ts
import { test, expect } from '@playwright/test';

test('user can log in and reach the dashboard', async ({ page }) => {
  // 1. Go to the real app
  await page.goto('https://staging.example.com/login');

  // 2. Act like a user
  await page.getByLabel('Email').fill('ada@example.com');
  await page.getByLabel('Password').fill('correct-horse-battery');
  await page.getByRole('button', { name: 'Log in' }).click();

  // 3. Assert on what the user sees
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  await expect(page).toHaveURL(/\/dashboard/);
});
```

Run it:

```bash
npx playwright test                 # headless
npx playwright test --headed        # watch the browser
npx playwright test --ui            # interactive UI mode (great for learning)
```

Notice: you never told Playwright to "wait." `expect(...).toBeVisible()` is a **web-first assertion** — it keeps re-checking until the heading appears or it times out. That is the foundation of stable E2E tests.

---

## Core Concept 4 — Finding Elements with Stable Selectors

How you locate elements decides whether your test survives next week's CSS refactor.

**Bad** — brittle, tied to styling or DOM structure:

```ts
await page.click('.btn.btn-primary.css-1x9f');     // breaks when class changes
await page.click('div > form > button:nth-child(3)'); // breaks when layout changes
```

**Good** — prefer how a *user* identifies things (role, label, text), then a dedicated test id:

```ts
await page.getByRole('button', { name: 'Log in' });   // accessible role + name
await page.getByLabel('Email');                        // form label
await page.getByText('Welcome back');                  // visible text
await page.getByTestId('checkout-submit');             // explicit test hook
```

To use `getByTestId`, add a `data-testid` attribute in your app:

```html
<button data-testid="checkout-submit">Place order</button>
```

**Rule of thumb (Playwright's own guidance):** prefer **role/label/text** selectors because they also verify accessibility; fall back to **`data-testid`** when text is ambiguous or changes often. Avoid CSS-class and positional selectors — they're the #1 cause of brittle tests.

---

## Core Concept 5 — Why You Should Never Use sleep

The single most common rookie mistake is "the page is slow, so I'll wait 3 seconds."

**Flaky — uses a fixed sleep:**

```ts
test('shows order confirmation', async ({ page }) => {
  await page.getByRole('button', { name: 'Place order' }).click();
  await page.waitForTimeout(3000);                  // ❌ guessing
  expect(await page.getByTestId('confirmation').textContent())
    .toContain('Thank you');
});
```

Why this is broken:
- On a slow CI machine, 3 seconds isn't enough → **fails randomly**.
- On a fast machine, you waste 3 seconds every run → **slow suite**.
- It hides the real timing of your app.

**Stable — wait for the actual condition (auto-wait):**

```ts
test('shows order confirmation', async ({ page }) => {
  await page.getByRole('button', { name: 'Place order' }).click();
  await expect(page.getByTestId('confirmation'))     // ✅ retries until true
    .toContainText('Thank you');
});
```

The web-first assertion waits *exactly* as long as needed and no longer. **"`sleep` is a bug"** — engrave it. We'll go deeper on flakiness in [Flaky Tests & Reliability](../12-flaky-tests-and-reliability/).

---

## Real-World Examples

- **E-commerce checkout.** One E2E test: search a product → add to cart → enter shipping → pay (test card) → see confirmation. This single test catches "checkout is down" — the most expensive bug a shop can ship.
- **SaaS onboarding.** Sign up → verify email (read from a test mailbox) → complete profile → land on the empty dashboard. Proves a new customer can actually start.
- **API-level E2E.** Not every E2E needs a browser. Hitting the public REST API end-to-end (`POST /orders` then `GET /orders/{id}`) is a *cheaper, faster* E2E variant — see the **api-testing** skill.

---

## Common Mistakes

| Mistake | Why it hurts | Do instead |
|---------|--------------|------------|
| Using `waitForTimeout`/`sleep` | Slow + flaky | Use web-first assertions / auto-wait |
| CSS-class or `nth-child` selectors | Break on any UI change | Use role/label/text or `data-testid` |
| Writing E2E for every edge case | Slow, flaky, unmaintainable suite | Push edge cases to unit/integration |
| Testing against production | Pollutes real data, risky | Use a staging / hermetic environment |
| Asserting internal HTML structure | Brittle | Assert what the *user* sees |
| No screenshot/trace on failure | Can't debug CI failures | Enable Playwright traces (next tier) |

---

## Apply it

1. Choose one small, known input for **End-to-End Testing**.
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

- What problem does End-to-End Testing solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
