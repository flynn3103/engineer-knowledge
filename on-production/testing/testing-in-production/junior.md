# Testing in Production — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Testing in Production** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Testing in Production
> *Why some confidence can only be earned in the real environment — and how to earn it safely.*

---

## Core Concept 1 — Why Staging Is Never Enough

Staging tries to imitate production. It always falls short in ways that hide real bugs:

| Dimension | Staging | Production |
|-----------|---------|------------|
| **Data scale** | A few thousand rows | Billions of rows, skewed distributions |
| **Data shape** | Clean, synthetic | Messy: emoji in names, null in "required" fields, 2008-era records |
| **Traffic** | One engineer clicking | Millions of concurrent, unpredictable users |
| **Dependencies** | Mocked or stubbed | Real third-party APIs that throttle, time out, return garbage |
| **Concurrency** | Almost none | Real race conditions under real load |
| **Configuration** | Simplified | The actual prod config, with its quirks |

A concrete example. Your code paginates database results. In staging the table has 500 rows, so one page covers everything and the pagination bug never fires. In production the table has 40 million rows, the query without a proper index times out, and the page falls over. **No amount of staging testing would have found this**, because the bug is a property of *scale*, and staging has no scale.

This is why we say: *staging answers "does it work?"; production answers "does it work here, now, at this scale, with this data, under this load?"* Those are different questions.

---

## Core Concept 2 — It Is Not Recklessness, It Is Discipline

The single most important idea in this whole topic:

> **Testing in production requires MORE rigor than testing anywhere else — not less.**

When you run a test in CI and it fails, nobody is hurt. When you "test" in production carelessly, real users see errors, lose data, or can't check out. So the bar is *higher*. Safe testing in production rests on four pillars:

1. **Small blast radius** — expose the change to 1% of traffic before 100%, so a failure hurts few people.
2. **Observability** — you can *see* within seconds that something broke (error rate spiked, latency doubled).
3. **Automated rollback / kill switch** — when the signal goes bad, you revert in seconds, automatically.
4. **A budget for risk** — you accept that a tiny, bounded amount of failure is the price of confidence, and you spend it deliberately.

If you don't have all four, you are not "testing in production" — you are gambling. The discipline is what turns the joke into an engineering practice.

---

## Core Concept 3 — Canary Releases

A **canary release** is the gateway technique. Named after the canary in a coal mine: send a small, expendable sentinel ahead to detect danger before it reaches everyone.

The pattern:

1. Deploy the new version alongside the old one.
2. Route **1%** of traffic to the new version (the canary).
3. Watch the canary's metrics versus the old version's for a few minutes.
4. If metrics are healthy, expand: 1% → 5% → 25% → 50% → 100%.
5. If metrics degrade at any step, **stop and roll back automatically**.

A simple canary metric gate, expressed as configuration:

```yaml
# canary-analysis.yaml — the rules that decide promote vs. rollback
canary:
  steps: [1, 5, 25, 50, 100]   # percent of traffic per stage
  interval: 5m                  # watch each stage this long
  metrics:
    - name: error-rate
      threshold: "<= 1%"        # canary must stay under 1% errors
    - name: p99-latency
      threshold: "<= baseline * 1.1"  # no more than 10% slower than old version
  on_failure: rollback          # any breach -> revert to previous version
```

The canary turns deployment from a cliff (all users at once) into a staircase (a few users at a time, with a check at each step). This is the most common form of testing in production, and many teams do it without even calling it "testing in production."

> Canary releases lean heavily on **feature flags and progressive delivery** — see [`../../release/feature-flags-and-progressive-delivery/`](../../release/feature-flags-and-progressive-delivery/) — and on fast, safe [rollback](../../release/rollback-and-roll-forward/).

---

## Core Concept 4 — Synthetic Monitoring

**Synthetic monitoring** runs scripted "fake users" that continuously perform critical journeys against *real production*, around the clock. If checkout breaks at 3 a.m., a synthetic check catches it before the first real customer does.

A synthetic check for a login + dashboard journey:

```javascript
// synthetic/login-journey.js — runs every 60s from 3 regions
import { check, journey } from "synthetics-runtime";

journey("user can log in and see dashboard", async (page) => {
  await page.goto("https://app.example.com/login");
  await page.fill("#email", process.env.SYNTHETIC_USER);
  await page.fill("#password", process.env.SYNTHETIC_PASS);
  await page.click("#submit");

  // Assertions on REAL production
  await check("dashboard loads", () =>
    page.waitForSelector("#dashboard", { timeout: 5000 }));
  await check("loads under 3s", () =>
    page.timing.loadEventEnd < 3000);
});
// On failure -> page the on-call engineer.
```

**How is this different from an end-to-end (E2E) test?**

| | [E2E test](../end-to-end-testing/README.md) | Synthetic monitor |
|---|---|---|
| **When** | Before release (in CI/staging) | Forever, in production |
| **Environment** | Test/staging | Real production |
| **Purpose** | "Is this build correct?" | "Is the live system healthy *right now*?" |
| **On failure** | Block the deploy | Page the on-call engineer |

The script may look almost identical — the difference is *where* and *why* it runs. Synthetic monitoring is your always-on smoke test against the real thing.

---

## Core Concept 5 — You Cannot Test What You Cannot See

Imagine driving a car at night with the headlights off. That's testing in production without observability. The whole practice depends on a simple precondition:

> **If you cannot detect, within seconds, that your change made production worse, you must not test in production.**

The minimum you need before any prod testing:

- **Metrics** — error rate, latency (p50/p99), throughput, saturation — on a dashboard, per version.
- **Logs** — searchable records of what happened, so you can investigate a spike.
- **Traces** — the path of a single request across services, to find *where* it broke.
- **Alerts** — automated notifications when a metric crosses a threshold.

This is the domain of the `observability-stack` and `monitoring-alerting` skills. The mental shortcut: **observability is the headlights; testing in production is driving fast at night.** You need the headlights *first*.

---

## Real-World Examples

- **Facebook / Meta — Gatekeeper:** virtually every change is wrapped in a feature flag and rolled out progressively to employees, then 1% of users, then more — with automatic metric checks at each ring.
- **Netflix — synthetic + canary:** new service versions take a slice of real traffic while an automated canary analysis compares them to the baseline before full rollout.
- **Your own team, probably:** if you've ever shipped a feature "to internal users first" or "to 5% of accounts," you've already tested in production — you just may not have called it that.
- **The pagination bug:** a real, recurring story — code that works on 500 staging rows and dies on 40 million prod rows. Only a canary against real data would have caught it.

---

## Common Mistakes

| Mistake | Why it's wrong | Do instead |
|---------|----------------|------------|
| Treating "test in prod" as skipping tests | It demands *more* rigor, not less | Keep the pyramid; add prod testing on top |
| Testing in prod with no dashboards | You're driving blind | Set up observability *first* |
| Canary to 100% immediately | Defeats the point — full blast radius | Use small steps with checks |
| No automated rollback | A human at 3 a.m. is too slow | Wire SLO-breach → auto-rollback |
| Synthetic monitor with no alert | Detecting silently helps no one | Failed check must page someone |
| Synthetic credentials with real-money side effects | Your fake users place real orders | Use safe test accounts / sandbox paths |

---

## Apply it

1. Choose one small, known input for **Testing in Production**.
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

- What problem does Testing in Production solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
