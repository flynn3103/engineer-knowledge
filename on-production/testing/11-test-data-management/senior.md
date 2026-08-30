# Test Data Management — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Test Data Management** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Test Data Management
>
> *Test data as strategy and as liability — designing a builder library that scales, and handling production-derived data without leaking PII.*

---

## Core Concept 1 — Test Data Strategy at Scale

At small scale, ad-hoc builders suffice. At scale — dozens of services, thousands of tests, multiple teams — the *absence* of a strategy shows up as: every team reinvents an order builder; data setup is the slowest part of CI; nobody can produce a realistic dataset for a new E2E test; and one team's seed leaks PII into a shared environment.

A test-data strategy answers these explicitly:

- **Ownership.** Who owns the shared builder library? (Concept 2.)
- **Provenance.** Where does realistic data come from — synthetic, masked-prod, or hand-built? (Concepts 4–6.)
- **Isolation at scale.** Schema-per-worker, ephemeral databases per CI run, or per-team namespaces?
- **Lifecycle.** How often is data refreshed, and who is accountable when it goes stale? (Concept 7.)
- **Compliance.** What is forbidden (raw PII in lower envs), and how is that enforced, not just documented?

The deliverable is a written, enforced policy plus the tooling that makes the compliant path the *easy* path. If doing it right is harder than doing it wrong, engineers will do it wrong under deadline.

---

## Core Concept 2 — A Builder Library as Shared Infrastructure

Treat your builders like a published library: versioned, tested, documented, and owned. The signature of a mature builder library:

```python
# testkit/builders/order.py  — shipped as an internal package
class OrderBuilder:
    def __init__(self):
        self._customer = None         # lazily defaulted, so callers can inject
        self._items = [_default_item()]
        self._status = OrderStatus.PENDING
        self._created_at = FIXED_CLOCK.now()   # injectable clock, never wall time

    def for_customer(self, c): self._customer = c; return self
    def with_status(self, s):  self._status = s; return self
    def with_items(self, *items): self._items = list(items); return self

    def build(self):
        return Order(customer=self._customer or a_customer().build(),
                     items=self._items, status=self._status,
                     created_at=self._created_at)

    def save(self, db):
        o = self.build(); db.add(o); db.flush(); return o   # persisted variant
```

Design rules that keep such a library healthy:

1. **Composable.** Builders nest: an `OrderBuilder` defaults its customer via `a_customer()`, so a test that doesn't care about the customer says nothing about it. This is what makes "only specify what matters" hold at depth.
2. **Build *and* save.** Offer `build()` (in-memory) and `save(db)` (persisted) so unit and integration tests share one builder.
3. **Clock-injected.** Every default date comes from an injectable clock, so the whole suite is time-deterministic by construction.
4. **Backward compatible.** When the schema gains a field, add a default — never break existing callers. The library absorbs schema churn so the suites don't.
5. **Owned, not orphaned.** A specific team (often the platform/QE team) owns it, reviews changes, and treats a broken builder as a P1 — because it breaks *every* suite at once. A builder library with no owner rots into the very junk drawer it was meant to prevent.

The payoff: realistic, isolated, deterministic data becomes a one-liner everywhere, so engineers reach for it instead of hand-rolling fragile setup.

---

## Core Concept 3 — Data for Large Integration and E2E Suites

Unit tests build objects in memory; the hard problems live in integration and E2E, where data must be persisted, referentially consistent, and isolated across parallel runs.

- **Ephemeral databases.** Spin a fresh database (a container, a template clone) per CI run or per worker, seed reference data, and discard it after. This gives perfect isolation without truncation overhead and is the modern default for large suites.
- **Layered seeding.** Seed *reference data* (countries, plans, feature flags) once into the ephemeral DB; build *test-case data* per test inside an isolation boundary (transaction or namespace). Never mix the two.
- **Builders that persist a full graph.** An E2E "checkout" test needs a customer, a cart, inventory, and a payment method, all linked. A scenario builder assembles the whole graph in one call:

```python
scenario = a_checkout_scenario().with_stock("SKU-1", qty=5).build(db)
# returns linked customer + cart + inventory, ready for the E2E flow
```

- **Cross-service data.** In a microservice E2E, each service owns its data store. Seed each via its own API or builder, not by reaching into another service's database — that couples your test to a private schema. (See [Contract Testing](../05-contract-testing/README.md) for testing boundaries without full data setup.)

The discipline from earlier levels still rules: even in a 50-step E2E test, each step should set only the data that step depends on. Large suites fail not from too little data but from too much undifferentiated data nobody can reason about.

---

## Core Concept 4 — Production-Derived Data: Value and Risk

The temptation is universal: "our test data is fake and misses edge cases; let's just copy production." The **value** is real — production data has the messy distributions, weird Unicode names, null fields, and volume that synthetic data often lacks, and it catches bugs synthetic data hides.

The **risk** is catastrophic and non-negotiable: **raw production data contains real PII.** Copying it into a staging, dev, or CI environment means real customers' names, emails, addresses, payment details, and health or financial records now live in systems with weaker access controls, broader access, and no consent for that use.

The hard rule: **never copy raw production data with real PII into a lower environment.** Under GDPR, CCPA, HIPAA, and similar regimes, a developer laptop with a prod dump is a reportable data breach. The fact that "it's just for testing" is no defense — regulators care about where the data *is*, not your intent.

Production data is valuable *after* it has been stripped of identity. The next two concepts are the only safe ways to harvest that value: transform it (mask/anonymise) or replace it (synthesise).

---

## Core Concept 5 — Anonymisation, Pseudonymisation, and Masking

Three related transforms, with different reversibility and different legal weight.

**Masking** obscures a field's value while preserving its *shape*, so code that depends on format still works:

```python
def mask_email(email: str) -> str:
    name, domain = email.split("@")
    return f"{name[0]}{'*' * (len(name) - 1)}@{domain}"

def mask_card(pan: str) -> str:
    return "*" * (len(pan) - 4) + pan[-4:]      # ****-****-****-1234
```

**Pseudonymisation** replaces identifiers with reversible tokens. A keyed mapping lets you re-identify if absolutely necessary, which means the data is still legally personal data under GDPR (re-identification is possible). Use it only when you genuinely need to reconcile back to a real record:

```python
def pseudonymise(user_id: str, key: bytes) -> str:
    return hmac.new(key, user_id.encode(), hashlib.sha256).hexdigest()[:12]
```

**Anonymisation** is irreversible: identity is destroyed so no key can recover it. Truly anonymised data falls outside most PII regimes — but achieving real anonymity is hard, because quasi-identifiers (zip + birthdate + gender) can re-identify people even after names are removed. Treat "anonymised" as a claim you must verify, not assume.

The critical constraint across all three: **preserve referential integrity and distribution.** If you mask `customer.email` but a foreign key elsewhere references the original, you've broken the data. If you replace all ages with `0`, you've destroyed the distribution that made prod data valuable. Good masking pipelines transform consistently (the same input maps to the same masked output, so joins survive) and preserve realistic shapes.

---

## Core Concept 6 — Synthetic Data Generation

Synthetic data is generated from scratch and contains **no real records**, which sidesteps the PII problem entirely. Three tiers of sophistication:

**Rule-based / faker-driven.** Seeded fakers (from the middle level) scaled up: generate millions of realistic-looking rows with valid formats and plausible distributions.

```python
Faker.seed(2024)
def synth_customers(n):
    return [Customer(name=fake.name(), email=fake.email(),
                     country=fake.country_code(),
                     signup=fake.date_between("-3y", "today"))
            for _ in range(n)]
```

**Constraint-aware generation.** Tools that understand your schema and generate referentially-intact graphs — orders that reference real customers, line items that reference real products — so the synthetic dataset is internally consistent.

**Model-based / distribution-matching.** Generators that learn the statistical distributions of production (without copying any row) and emit synthetic data with the same shape — the right tool when realistic distribution is what catches the bugs.

Synthetic data's weakness is that it only contains the weirdness you thought to generate; it can miss the genuinely unexpected edge cases that real production traffic produces. The mature answer is usually a **blend**: synthetic data for the bulk and for sensitive fields, plus carefully masked production samples for the long-tail realism — with PII removed in both.

---

## Core Concept 7 — Subsetting and Refresh: The Data Lifecycle

**Subsetting** extracts a small, referentially-intact slice of a large dataset — e.g. "1% of customers and *all* their related orders, payments, and addresses." The hard part is referential integrity: naively selecting 1% of each table breaks foreign keys. Subsetting tools traverse the FK graph so a chosen customer brings exactly their dependent rows. A good subset is small enough to load fast in CI yet complete enough that no join dangles.

**Refresh / lifecycle.** Test data is not "set once." It goes **stale**: the prod schema evolves, new feature flags appear, distributions shift, and last year's masked sample no longer resembles today's traffic. Stale data costs you in false confidence (tests pass against a world that no longer exists) and in churn (engineers fighting datasets that don't match reality). A mature program treats test data as a refreshed artifact: a scheduled job re-subsets and re-masks production into lower environments on a cadence, with the masking pipeline in source control and reviewed like any other code. Define an owner and a refresh SLA, or the data quietly decays.

---

## Core Concept 8 — Data for Performance and Load Tests

Performance and load tests have a data requirement the others don't: **volume and realistic distribution**. A query that's instant against 100 rows can collapse against 100 million; a load test against a tiny, uniform dataset measures nothing real.

- **Volume.** Generate data at production scale (or beyond) so indexes, query plans, and cache behavior reflect reality. Synthetic generation shines here — it's the only way to produce billions of safe rows.
- **Distribution / skew.** Real systems have hot keys (a few customers with millions of orders) and cold ones. Uniform synthetic data hides the hotspots that actually break production. Match the skew, not just the count.
- **Cardinality.** Index selectivity depends on how many distinct values a column has. Synthetic data with the wrong cardinality produces query plans you'll never see in prod.

Generate this data once, snapshot it, and reuse it so runs are comparable. The detailed treatment of running these tests lives in [Performance & Load Testing](../09-performance-and-load-testing/README.md); here the point is that **the data is the experiment** — the wrong data set makes the whole load test a lie.

---

## Real-World Examples

- **The prod-dump audit finding.** A fintech copied a production database into staging for "realistic testing." A SOC 2 audit flagged it; every engineer with staging access had de facto access to customer financial PII. The remediation — a masking pipeline plus synthetic generation — took a quarter and a dedicated team. Building it in from the start would have cost a fraction.
- **The builder library that paid for itself.** A platform team built and owned a `testkit` package. A breaking schema change that would have touched 900 test files was absorbed by a one-line default change in `testkit`. The library's ownership cost was repaid in a single migration.
- **The load test that lied.** A team load-tested against 10,000 uniformly-distributed users and shipped confidently. Production had a few "whale" accounts with millions of rows; the query that was fine in the test timed out in prod. Generating skewed synthetic data reproduced the failure before the next release.
- **The dangling-FK masking bug.** A first attempt at masking replaced emails per-row but used a different random value each time the same user appeared across tables, breaking joins. Switching to deterministic masking (same input → same output) restored referential integrity.

---

## Common Mistakes

| Mistake | Why it hurts | Fix |
|---|---|---|
| Copying raw prod data to lower envs | PII breach; regulatory exposure | Mask/anonymise or synthesise first |
| Builder library with no owner | Rots into a junk drawer; breaks all suites | Assign a team; treat breakage as P1 |
| Masking that breaks foreign keys | Corrupt, unusable dataset | Deterministic, consistent transforms |
| Uniform synthetic data for load tests | Misses hot keys; false confidence | Match production skew and cardinality |
| Never refreshing test data | Stale; tests pass against a dead world | Scheduled re-subset/re-mask with an SLA |
| Assuming "names removed" = anonymous | Quasi-identifiers re-identify | Verify; treat as personal data if reversible |

---

## Apply it

1. State the system invariant that **Test Data Management** must protect.
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

- Which invariant must remain true when Test Data Management fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
