# End-to-End Testing — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **End-to-End Testing** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → End-to-End Testing
>
> *Stability is engineered, not wished for. This tier is the architecture of an E2E suite that stays fast, trustworthy, and debuggable as it grows.*

---

## Core Concept 1 — Stable Selectors as an Architectural Decision

Selector strategy is not a per-test choice; it's a contract between the app and its tests. Decide it once, enforce it everywhere.

**Priority order:**

1. **Role + accessible name** (`getByRole('button', { name: 'Submit' })`) — also asserts accessibility.
2. **Label / placeholder / text** for form fields and copy.
3. **`data-testid`** — explicit, decoupled from styling and copy; the workhorse for non-semantic or frequently-changing UI.
4. ❌ **CSS classes, tag structure, `nth-child`, XPath positions** — forbidden; they couple tests to incidental DOM shape.

Make test ids a first-class part of the component:

```tsx
// React component — testid travels with the component, not the markup
export function CheckoutButton({ disabled }: Props) {
  return (
    <button data-testid="checkout-submit" disabled={disabled}>
      Place order
    </button>
  );
}
```

Pin the attribute name in config so locators read cleanly:

```ts
// playwright.config.ts
export default defineConfig({
  use: { testIdAttribute: 'data-testid' },
});
```

```ts
page.getByTestId('checkout-submit'); // resolves data-testid="checkout-submit"
```

**Governance tip:** a lint rule or PR-review norm — "interactive elements in critical journeys must carry a `data-testid`" — keeps the contract intact as the UI evolves.

---

## Core Concept 2 — The Page Object Model and Its Alternatives

As tests multiply, raw locators scattered across specs become unmaintainable: one UI change forces edits in twenty files. The **Page Object Model** centralizes a page's locators and actions behind meaningful methods.

```ts
// pages/LoginPage.ts
import { Page, Locator, expect } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly email: Locator;
  readonly password: Locator;
  readonly submit: Locator;

  constructor(page: Page) {
    this.page = page;
    this.email = page.getByLabel('Email');
    this.password = page.getByLabel('Password');
    this.submit = page.getByRole('button', { name: 'Log in' });
  }

  async goto() {
    await this.page.goto('/login');
  }

  async login(email: string, password: string) {
    await this.email.fill(email);
    await this.password.fill(password);
    await this.submit.click();
  }

  async expectLoggedIn() {
    await expect(this.page.getByRole('heading', { name: 'Dashboard' }))
      .toBeVisible();
  }
}
```

```ts
// tests/login.spec.ts — reads like a user story
test('user can log in', async ({ page }) => {
  const login = new LoginPage(page);
  await login.goto();
  await login.login('ada@example.com', 'correct-horse');
  await login.expectLoggedIn();
});
```

**Alternatives / refinements:**

- **Playwright fixtures** — inject a ready-to-use page object (or an already-logged-in `page`) via `test.extend`, eliminating boilerplate.
- **App Actions (Cypress idiom)** — skip the UI for setup; e.g. log in by hitting the API and setting the session, only using the UI for the behavior under test.
- **Component/screen objects** for reusable widgets (a `CartWidget`, a `DatePicker`) instead of one giant page class.

**POM pitfalls:** don't put assertions you don't need inside actions; don't let a page object become a god-class. Keep methods at the level of *user intent*, not *button mechanics*.

---

## Core Concept 3 — Hermetic Environments and State Seeding

The biggest lever on E2E reliability is the environment. A **hermetic** environment behaves identically on every run because it controls every input.

A hermetic E2E setup typically:

- Spins up the app + a **fresh, seeded database** (often via Docker Compose / Testcontainers).
- **Stubs or sandboxes third parties** (payments, email, SMS, feature flags) so external systems can't flake your suite.
- **Seeds state via API or DB**, never by clicking through prerequisite UI.

```ts
// fixtures.ts — a logged-in page with a seeded account, no UI setup
import { test as base } from '@playwright/test';

export const test = base.extend<{ authedPage: Page }>({
  authedPage: async ({ browser, request }, use) => {
    // Seed a user + auth token directly through a test API
    const res = await request.post('/api/test/users', {
      data: { email: 'seed@example.com', plan: 'pro' },
    });
    const { token } = await res.json();

    const context = await browser.newContext({
      storageState: { cookies: [], origins: [
        { origin: 'https://staging.example.com',
          localStorage: [{ name: 'auth', value: token }] },
      ]},
    });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },
});
```

Now a test starts already authenticated, with a known account, in milliseconds — no fragile login-by-UI in every spec. Seeding strategy is a topic of its own: see [Test Data Management](../11-test-data-management/README.md) and the **test-data-management** skill.

---

## Core Concept 4 — Controlling Time and Randomness

Time and randomness are silent flakiness factories: a test that asserts "expires in 7 days" or relies on "newest first" ordering can fail at midnight or when two records share a timestamp.

**Freeze the clock** so time-based UI is deterministic:

```ts
test('shows "expires in 7 days"', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-01-01T00:00:00Z') });
  await page.goto('/subscription');           // app sees a fixed "now"
  await expect(page.getByTestId('expiry'))
    .toHaveText('Expires in 7 days');
  // advance virtual time to test expiry behavior
  await page.clock.fastForward('07:00:00:00'); // 7 days
});
```

**Control randomness** at the source: seed the app's RNG in test mode, fix ordering with explicit sort keys, and avoid asserting on values the app generates randomly (IDs, tokens) — assert on *structure* or *presence* instead.

```ts
// Don't assert the exact generated id; assert it exists and is well-formed
await expect(page.getByTestId('order-id')).toHaveText(/^ORD-[0-9]{8}$/);
```

---

## Core Concept 5 — Parallelization and Sharding

E2E is slow per test, so speed comes from running many at once. Two layers:

- **Parallelism (workers):** Playwright runs files in parallel workers by default. Within a file, `test.describe.configure({ mode: 'parallel' })` parallelizes tests too — only safe if tests are isolated.
- **Sharding (machines):** split the whole suite across CI machines.

```bash
# Local: use available cores
npx playwright test --workers=4

# CI: 4 machines, each runs a quarter (combine with a matrix)
npx playwright test --shard=1/4
npx playwright test --shard=2/4
# ...
```

```yaml
# GitHub Actions matrix
strategy:
  matrix:
    shard: [1, 2, 3, 4]
steps:
  - run: npx playwright test --shard=${{ matrix.shard }}/4
```

**Prerequisite for safe parallelism: isolation.** Parallel tests sharing a database row, a user account, or a global feature flag will corrupt each other. Give each worker its own data namespace (per-worker user, per-test record prefix) so they never collide.

---

## Core Concept 6 — E2E in CI: Placement, Artifacts, Quarantine

**Where E2E runs is a strategy decision, not a default:**

| Stage | What runs | Why |
|-------|-----------|-----|
| **Pre-merge (PR)** | Fast critical-journey subset (smoke), headless, sharded | Keep PRs fast; catch the worst breakage before merge |
| **Post-merge / nightly** | Full E2E suite, all browsers | Broader coverage without blocking developers |
| **Pre-deploy / smoke-on-prod** | A few read-only journeys against the deploy | Catch environment/config breakage — see [Testing in Production](../13-testing-in-production/README.md) |

**Artifacts are non-negotiable** — a CI failure you can't reproduce locally is useless without evidence. Capture trace, screenshot, and video on failure:

```ts
// playwright.config.ts
export default defineConfig({
  retries: process.env.CI ? 2 : 0,
  use: {
    headless: true,
    trace: 'on-first-retry',     // full timeline when a test flakes
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
});
```

Open a failed run's trace locally:

```bash
npx playwright show-trace trace.zip
```

**Quarantine** is how you keep the pipeline trustworthy without ignoring red: tag a known-flaky test, move it to a non-blocking job, file a ticket, and fix or delete it on a deadline. Quarantine is a holding pen, not a graveyard — a test that lives there forever should be deleted.

```ts
test('flaky-while-investigated @quarantine', async ({ page }) => { /* ... */ });
// CI: blocking job runs --grep-invert @quarantine; a separate job runs @quarantine
```

---

## Core Concept 7 — Diagnosing a Flaky Suite Systematically

When flake appears, resist the reflex to bump timeouts. Work it methodically:

1. **Measure.** Track per-test flake rate over many runs (Playwright's HTML/blob reports, or a service like Currents). Don't fix by anecdote.
2. **Reproduce.** Run the suspect test under load and repetition to surface races: `npx playwright test flaky.spec.ts --repeat-each=20 --workers=4`.
3. **Read the trace.** The trace shows the exact DOM/network state at failure — usually a missing wait, a race, or shared state.
4. **Classify the cause** (sleep, isolation, time/random, third party, genuine product race) and apply the matching fix from the [Middle tier](./middle.md#core-concept-5----flakiness-the-1-enemy).
5. **Quarantine if it blocks**, but with a ticket and an owner.

Crucially: **a flaky E2E test is sometimes telling the truth.** Intermittent failures can reveal a real race condition or eventual-consistency bug in your *product*. Never paper over flake with retries before ruling that out. Deep dive: [Flaky Tests & Reliability](../12-flaky-tests-and-reliability/README.md).

---

## Real-World Examples

- **Per-worker data namespacing.** A team made parallel E2E safe by giving each worker a unique account (`worker-${index}@test.example.com`) and prefixing all created records — collisions and order-dependent flake vanished.
- **Trace-driven debugging.** A checkout test failed only in CI. The trace showed the "Pay" button was momentarily covered by a cookie banner; the fix was to dismiss the banner in setup, not to add a sleep.
- **Smoke vs nightly split.** Pre-merge runs 8 smoke journeys in ~3 minutes across 4 shards; the full 45-test suite runs nightly across all browsers. PRs stay fast; coverage stays broad.
- **App-action login.** Replacing UI login in 30 specs with API-based session seeding cut suite time ~40% and removed login-flake from every test.

---

## Common Mistakes

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Selectors in raw specs | One UI change breaks many files | Centralize in page objects |
| God-class page objects | Unmaintainable, coupled | Screen/component objects, intent-level methods |
| Non-hermetic env (shared staging) | Cross-test interference, flake | Seeded DB + stubbed externals per run |
| Parallel without isolation | Tests corrupt each other's data | Per-worker namespaced data |
| No traces/artifacts in CI | Unreproducible failures | Trace/screenshot/video on failure |
| Permanent quarantine | Dead tests, false safety | Owner + deadline; fix or delete |
| Bumping timeouts to "fix" flake | Hides real races, slows suite | Diagnose via trace and repeat-each |

---

## Apply it

1. State the system invariant that **End-to-End Testing** must protect.
2. Mark ownership, state, and failure propagation at each boundary.
3. Compare two designs under load, dependency failure, and future change.
4. Define recovery and compatibility behavior before implementation.
5. Test the riskiest assumption with a focused experiment.

## Verify your work

- The experiment supports the design with evidence, not preference.
- Failure injection shows the blast radius and recovery path.
- Compatibility checks cover old and new callers or data.
- Operational signals reveal invariant violations and recovery progress.

## Review questions

- Which invariant must remain true when End-to-End Testing fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
