# Integration Testing — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Integration Testing** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Integration Testing
>
> *At org scale, integration testing stops being a coding skill and becomes infrastructure economics — who owns it, what it costs, and how it runs in CI.*

---

## Core Concept 1 — Integration Testing in CI

Integration tests need Docker on the CI runner, which is the first place they break. The mechanics matter:

- **Docker availability.** The runner must expose a Docker daemon. GitHub Actions Linux runners ship one; many self-hosted/Kubernetes runners need **DooD** (mount the host socket) or a sidecar daemon. Testcontainers also needs its **Ryuk** reaper to run, or you leak orphaned containers across jobs.
- **Stage placement.** Integration tests belong in their own pipeline stage, *after* fast unit tests. Fail cheap and early: lint → unit (seconds) → integration (minutes) → e2e (longer). Don't make every PR wait on the slow stage to learn a typo broke the build.

```yaml
# GitHub Actions — integration as its own gated stage
jobs:
  unit:
    runs-on: ubuntu-latest
    steps: [ {run: ./gradlew test} ]          # fast; fails first
  integration:
    needs: unit                                # only after unit is green
    runs-on: ubuntu-latest                     # Docker preinstalled
    steps:
      - uses: actions/checkout@v4
      - run: ./gradlew integrationTest         # Testcontainers spins real Postgres/Kafka
```

- **Reproducibility over reuse.** The senior trick of container reuse is a *local-dev* feature. In CI, every job gets fresh, pinned containers so a green run means the same thing every time. Pin image digests, not floating tags.
- **Required-checks gating.** Make the integration stage a required check on the protected branch so nothing merges without it — but only once the flake rate is low enough that the gate is trusted (a flaky required check is worse than none). See the `ci-cd-pipeline-design` skill and the broader quality-gates discipline.

---

## Core Concept 2 — Container Caching & CI Resource Limits

Two forces fight on every CI run: **image pull time** and **runner resources.**

**Image caching.** Pulling `postgres:16.4-alpine` + `confluentinc/cp-kafka` on a cold runner can cost 30–90 seconds per job. Options:

- **Registry mirror / pull-through cache** in your network so pulls are LAN-speed, not internet-speed.
- **Pre-baked runner images** that already contain the test dependency images.
- **Layer caching** for your *own* test images (a base image with extensions/seed data pre-installed).
- **Minimal images** (`-alpine`, slim) to shrink the bytes pulled.

**Resource limits.** A CI runner has finite CPU/RAM. Each container (Postgres, Kafka, Redis, localstack) consumes a slice, and parallel workers multiply it. Symptoms of overcommit: OOM-killed containers, timeouts, and *intermittent* failures that look like flakes but are really resource starvation.

- **Budget the job.** Sum container memory × parallelism and keep it under the runner's RAM with headroom. Kafka especially is memory-hungry.
- **Right-size parallelism to the runner**, not to your laptop. 8 workers on a 2-CPU runner thrash.
- **Cap container resources** explicitly so one heavy test can't starve the rest:

```java
new PostgreSQLContainer<>("postgres:16.4-alpine")
    .withCreateContainerCmdModifier(cmd ->
        cmd.getHostConfig().withMemory(512L * 1024 * 1024)); // 512 MB cap
```

- **localstack/heavy AWS fakes** — start only the services you use (`SERVICES=s3,sqs`), not the whole suite.

The recurring lesson: many "CI-only flakes" are actually **resource exhaustion**, not non-determinism. Profile runner memory before blaming the test.

---

## Core Concept 3 — The Cost Model of an Integration Suite

Integration tests cost real money and time. A professional reasons about them as an investment with a measurable return.

**The cost side:**

```
cost_per_run ≈ (runner_minutes × runner_$/min)
             + maintenance_time (flake triage, fixture upkeep)
             + feedback_latency_tax (devs waiting on the suite)
```

A 12-minute suite running on every PR across 40 engineers pushing 8×/day is not free — it's thousands of runner-minutes daily plus the compounding cost of every developer waiting on it. Feedback latency is the sneaky line item: a suite slow enough to context-switch on taxes throughput far beyond its compute bill.

**The value side:** integration tests catch a *specific class* of bug (wiring, SQL, serialization, transactions) that nothing cheaper catches and that is expensive in production. The ROI question per test is: *does this test catch a class of bug worth more than its lifetime run-and-maintain cost?*

**Levers when the bill is too high:**

- **Right-size the layer.** Demote logic-only tests to unit; reserve integration for true boundaries (senior Concept 1).
- **Shard and parallelize** so wall-clock latency drops even if total compute holds.
- **Run the full suite on merge, a fast subset on PR** (test impact analysis / changed-module selection) — but keep the full suite gating *somewhere* before production.
- **Kill low-value tests.** A test that has never caught a bug and costs maintenance is a liability; deletion is a legitimate optimization.

Track **cost per green** and suite runtime as first-class metrics, the same way you'd track cloud spend.

---

## Core Concept 4 — Test-Environment Management

Integration tests need dependencies; *where* those come from is a managed decision with a clear hierarchy of preference:

1. **Ephemeral (Testcontainers) — strongly preferred.** Per-job, hermetic, reproducible, no shared state. The default for narrow and most broad integration.
2. **Dedicated ephemeral environments** (spun per PR via IaC) — for broad multi-service integration that can't fit in one Docker host. Costly; reserve for genuine multi-service wiring tests. See the `infrastructure-as-code` skill.
3. **Shared long-lived test environments — last resort.** A persistent "staging DB" everyone points at. Cheap to stand up, *expensive in flakiness*: shared mutable state, noisy-neighbour failures, drift from production, and contention. The classic anti-pattern is the team integration suite that fails because *another* team's run left bad data in the shared database.

**Configuration & secrets.** Tests need connection strings, credentials, feature flags. Inject them per environment; never hard-code prod endpoints; keep secrets out of the repo (use the CI secret store; see the `secrets-management` skill). A test that can accidentally point at production is a security and data-integrity incident waiting to happen.

The strategic push is **toward ephemeral, away from shared**: the more state a test environment shares across runs and teams, the more it leaks flakiness and the less a green result means.

---

## Core Concept 5 — Owning Shared Test Infrastructure

At scale, integration testing has shared assets, and *unowned shared assets rot*. Treat them as a product with a team behind them:

- **A shared Testcontainers base / fixtures library** — common container setup, waits, and a Postgres/Kafka harness so every team isn't reinventing lifecycle and flake-avoidance.
- **Test-data factories** — canonical builders for core domain objects (see [Test Data Management](../test-data-management/README.md) and the `test-data-management` skill), so a schema change updates one factory, not 200 tests.
- **CI runner pools and Docker infra** — capacity, the registry mirror, runner images.
- **Migration-testing harness** — a standard way to verify migrations against the real engine in CI (the `database-migration-patterns` skill).

**Ownership model.** A **test platform / developer-experience team** owns this infrastructure as a product: SLAs on the shared harness, a deprecation process for shared fixtures, and a feedback loop with product teams. Product teams own *their* tests; the platform team owns the *means to run them well*. Without explicit ownership, the base image drifts, fixtures fork, flake rates climb, and every team pays the tax independently — the textbook tragedy of the commons.

A governing **test strategy document** (the unit/integration/e2e split, isolation conventions, the flake policy, the ephemeral-over-shared rule) keeps independent teams from diverging into incompatible local optima. See [Test Strategy & the Pyramid](../test-strategy-and-the-pyramid/README.md).

---

## Core Concept 6 — Suite Health as a Tracked Metric

You manage what you measure. For an integration suite at scale, instrument and trend:

| Metric | Why it matters | Target shape |
|---|---|---|
| **p50 / p95 runtime** | Feedback latency; p95 is what devs *feel* | Bounded; alert on regression |
| **Flake rate** | Trust in the gate | < 0.5%; quarantine on breach |
| **Pass rate on `main`** | Health of the trunk gate | ~100% (flakes excluded) |
| **Cost per green** | Spend efficiency | Trending flat/down |
| **Slowest-N tests** | Where to optimize | Reviewed regularly |
| **Container start failures** | Infra health (Docker/Ryuk/resources) | Near zero |

Put these on a dashboard. A rising flake rate or a creeping p95 is a leading indicator that the suite is about to lose the team's trust — catch it before someone proposes "let's just disable integration tests on PRs." Tie a **flake-rate SLO** to a policy: above threshold, the test is auto-quarantined and a ticket is filed. See [Flaky Tests & Reliability](../flaky-tests-and-reliability/README.md).

---

## Core Concept 7 — Organisational Patterns & the Test Strategy Doc

How integration testing is organised across many services shapes everything:

- **Per-service narrow integration + cross-service contracts.** The scalable default: each service tests its own boundaries with Testcontainers; service-to-service agreement is verified with [Contract Testing](../contract-testing/README.md), not broad integration. This avoids the combinatorial explosion of spinning up the whole estate for every team.
- **Broad integration reserved for genuine emergent wiring** — a saga across two services, a specific eventual-consistency path — and run sparingly, in dedicated ephemeral environments.
- **Standardized harness, decentralized tests.** Central team provides the rails (base images, factories, CI templates); product teams write the tests on those rails.
- **A written test strategy** that codifies: the layer split, isolation conventions, the ephemeral-over-shared rule, the flake policy, and what is/isn't a required check. Without it, 30 teams invent 30 conventions and the shared infra can't serve them all.

This is also where integration testing meets [Testing in Production](../testing-in-production/README.md): no pre-prod suite is perfectly faithful, so mature orgs pair a strong integration suite with production observability and synthetic monitoring rather than chasing 100% pre-prod fidelity.

A concrete decision framework for "narrow vs broad vs contract" across services:

| Question being answered | Right tool | Why |
|---|---|---|
| Does my repository's SQL work against the real engine? | Narrow integration (Testcontainers) | Only the real engine exposes dialect/constraint/transaction bugs |
| Does my HTTP layer serialize and route correctly? | Narrow integration (real app server) | Catches JSON/status/middleware bugs a handler unit test misses |
| Do service A and service B still agree on the message shape? | Contract test | Cheap, no need to run both services together |
| Does a saga across A and B converge correctly? | Broad integration (ephemeral env) | Genuinely emergent wiring; reserve for these |

The trap most orgs fall into is reaching for broad integration (spin up everything) for questions the first three rows answer far more cheaply. Broad integration should be the rare exception, justified by genuinely emergent multi-service behaviour that no narrower test can observe.

---

## Real-World Examples

- **The shared staging DB that flaked everyone.** Five teams pointed integration suites at one staging Postgres. Cross-team data collisions produced a ~4% flake rate org-wide. Migrating to per-job Testcontainers dropped it under 0.3% and removed an entire class of "not my bug" triage.
- **The CI memory wall.** A team added Kafka + localstack containers; jobs began OOM-failing intermittently. The "flake" was the runner exceeding RAM under 6 parallel workers. Capping container memory and dropping to 3 workers fixed it — a resource problem, not a test problem.
- **The base-image dividend.** A platform team shipped a shared Testcontainers harness with tuned waits and a Postgres template-DB reset. Adopting teams saw integration suites drop 40% in runtime and flake triage nearly vanish — the value of owned shared infra, quantified.
- **Cost-driven selection.** A 22-minute PR suite was costing more in runner-minutes and developer waiting than it returned. Splitting to changed-module selection on PR + full suite on merge cut PR latency to 6 minutes while keeping the full gate before release.

---

## Common Mistakes

- **Container reuse enabled in CI.** Sacrifices the reproducibility that's the whole point of CI.
- **Floating image tags (`:latest`).** Non-reproducible builds; silent engine drift.
- **Blaming non-determinism for resource exhaustion.** Profile runner RAM/CPU before calling it a flake.
- **Standing up a shared staging DB as the default.** Cross-team collisions and drift; prefer ephemeral.
- **No owner for shared fixtures/base images.** Forks, drift, duplicated effort, rising flake rates.
- **Gating on a flaky integration stage.** Erodes trust until someone removes the gate entirely.
- **Ignoring the cost model.** A 25-minute everyone-waits suite can cost more than it protects.
- **Chasing 100% pre-prod fidelity** instead of pairing integration tests with production observability.

---

## Apply it

1. Define the user or business outcome that **Integration Testing** should improve.
2. Assign one owner for code, contracts, operations, and incidents.
3. Split delivery into reversible increments that produce evidence early.
4. Publish responsibilities, escalation paths, and compatibility windows.
5. Stop or expand only when the agreed measures support that decision.

## Verify your work

- Each increment has an owner, rollback path, and observable exit condition.
- Adoption, reliability, delivery time, and coordination cost are measured.
- Incident and migration exercises prove that responsibility is executable.
- The old path is removed only after telemetry proves it is unused.

## Review questions

- Which measurable outcome justifies investing in Integration Testing?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
