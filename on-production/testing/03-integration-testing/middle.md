# Integration Testing — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Integration Testing** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Integration Testing
>
> *Fidelity is the whole point — a fast test against the wrong engine is a confident lie.*

---

## Core Concept 1 — The Fidelity / Speed Trade-off

Every test-double decision is a point on a line between **fidelity** (does it behave like production?) and **speed** (how fast does the test run?).

```
  low fidelity                                            high fidelity
  fast                                                            slow
  |---------------------------------------------------------------|
  mock        in-memory (H2)     Testcontainers     shared staging DB
  (unit)      (fast, lies)       (real engine)      (real but shared/flaky)
```

The naive instinct is "pick the fast one." But a fast test that doesn't reflect production isn't cheaper — it's **negative value**, because it gives confidence that's wrong. The right question is: *what is the cheapest option that still catches the class of bug I care about?*

- Testing pure business logic with no I/O → **mock** (it's a unit test).
- Testing your repository's SQL, transactions, constraints → **Testcontainers** (real engine, nothing less).
- Testing an external partner's API shape → **contract test**, not a live call (see [Contract Testing](../05-contract-testing/README.md)).

For database code there's essentially no middle ground worth taking: it's the real engine or it's not really tested.

---

## Core Concept 2 — The "H2 Passes, Postgres Fails" Trap

This is the canonical reason in-memory substitutes are dangerous. H2 (and SQLite) are *different database engines*. They speak a different enough SQL dialect that real-world queries pass in one and fail in the other. A concrete case:

```sql
-- Postgres: upsert with ON CONFLICT
INSERT INTO accounts (id, balance) VALUES (?, ?)
ON CONFLICT (id) DO UPDATE SET balance = accounts.balance + EXCLUDED.balance;
```

Run your repository test against **H2** in PostgreSQL-compatibility mode and it may quietly accept (or silently misinterpret) `EXCLUDED` and the `ON CONFLICT` target. The test goes green. Ship it. In **production Postgres** the same statement behaves differently around the conflict target or returns a different affected-row count, and your balance update is wrong.

Other classic divergences that bite:

- **Type handling** — Postgres `jsonb`, arrays, `timestamptz`, `numeric` precision. H2 fakes some, mishandles others.
- **Constraint timing** — deferred constraints, `ON DELETE CASCADE` semantics.
- **Concurrency / locking** — `SELECT ... FOR UPDATE`, isolation levels (see the `transaction-isolation` skill). In-memory engines often ignore them.
- **Case sensitivity and identifier quoting** — different defaults.
- **Window functions, CTEs, `RETURNING`** — partial or different support.

The lesson is blunt: **the only database that behaves like your production database is your production database engine.** Testcontainers gives you exactly that, disposably.

```java
// Same engine and version you run in production — pin it.
@Container
static PostgreSQLContainer<?> pg =
    new PostgreSQLContainer<>("postgres:16.4-alpine"); // not :latest
```

Pin the version. `:latest` reintroduces the same drift problem from a different direction.

---

## Core Concept 3 — Database Isolation Strategies

A real database has state, and state leaks between tests. Four strategies, with their trade-offs:

| Strategy | Speed | Isolation | When to use |
|---|---|---|---|
| **Recreate schema** per test | Slowest | Total | Schema-level tests only |
| **Truncate tables** per test | Medium | High | Default for most suites |
| **Transaction rollback** per test | Fastest | High (caveats) | Tests that don't manage their own tx |
| **Unique data per test** (namespacing) | Fast | Logical | Read-heavy, parallel suites |

**Truncate** is the reliable default:

```sql
TRUNCATE users, orders, payments RESTART IDENTITY CASCADE;
```

`RESTART IDENTITY` resets auto-increment so IDs are predictable; `CASCADE` follows foreign keys. Run it in teardown so the next test starts clean regardless of what failed.

**Namespacing** (give each test its own tenant/prefix) lets tests run in parallel without truncation contention — but only if your code respects the namespace and you never assert on global counts.

---

## Core Concept 4 — Transaction-Rollback-Per-Test

The fastest isolation pattern: open a transaction in setup, run the test, **roll back** instead of committing. Nothing ever hits disk permanently, so the next test sees a pristine DB.

**Spring (Java) — `@Transactional` on the test:**

```java
@SpringBootTest
@Testcontainers
@Transactional        // each test runs in a tx that is rolled back at the end
class OrderServiceIT {

    @Container
    static PostgreSQLContainer<?> pg = new PostgreSQLContainer<>("postgres:16-alpine");

    @Autowired OrderService orders;

    @Test
    void placingOrderReservesStock() {
        orders.place(new Order("sku-1", 2));
        assertThat(orders.stockFor("sku-1")).isEqualTo(8);
    } // tx rolled back here — DB is clean for the next test
}
```

**The caveat that trips people up:** rollback-per-test **silently breaks** when the code under test manages its own transactions or commits explicitly (e.g. a service that opens a `REQUIRES_NEW` transaction, or any code that calls `commit()` itself). The test's outer rollback can't undo a child commit, and you can end up *not testing the real commit path at all*. If your code's correctness depends on commit/visibility behaviour, **use truncate, not rollback** — you want the commit to actually happen.

**Manual rollback (Go):**

```go
func withRollback(t *testing.T, db *sql.DB, fn func(tx *sql.Tx)) {
    tx, err := db.Begin()
    require.NoError(t, err)
    defer tx.Rollback() // always undo
    fn(tx)
}
```

Rule of thumb: **rollback for speed on simple repository tests; truncate when commit semantics matter.**

---

## Core Concept 5 — HTTP / API Integration & WireMock

Two distinct HTTP situations show up in integration tests:

**(a) Testing *your* HTTP layer.** Spin up your real application server (real controllers, real serialization) and hit it over actual HTTP. This catches routing bugs, JSON (de)serialization mismatches, status codes, and middleware behaviour — none of which a unit test on the handler sees.

```java
@SpringBootTest(webEnvironment = RANDOM_PORT)
@Testcontainers
class UserApiIT {
    @Autowired TestRestTemplate http;

    @Test
    void createReturns201WithLocation() {
        var res = http.postForEntity("/users",
            Map.of("email", "ada@example.com"), Void.class);
        assertThat(res.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        assertThat(res.getHeaders().getLocation()).isNotNull();
    }
}
```

**(b) Faking an *external* HTTP dependency.** Your code calls a third-party API (payments, geocoding). You don't want to hit the real one in tests — it's slow, rate-limited, and non-deterministic. Use **WireMock** (or MockServer) to stand up a fake HTTP server returning canned responses:

```java
@RegisterExtension
static WireMockExtension wm = WireMockExtension.newInstance()
    .options(wireMockConfig().dynamicPort()).build();

@Test
void chargesViaPaymentGateway() {
    wm.stubFor(post("/charge")
        .willReturn(okJson("""{"status":"approved","id":"ch_1"}""")));

    var gateway = new PaymentGateway(wm.baseUrl());
    var result = gateway.charge(100, "usd");

    assertThat(result.approved()).isTrue();
    wm.verify(postRequestedFor(urlEqualTo("/charge")));
}
```

WireMock also lets you simulate failures (500s, timeouts, malformed bodies) so you can test your retry and error handling against realistic HTTP behaviour.

> **The integration / contract boundary.** WireMock proves *your client works against the response you stubbed.* It does **not** prove the real provider actually sends that shape. That guarantee is what [Contract Testing](../05-contract-testing/README.md) provides (Pact, Spring Cloud Contract). Use WireMock for "does my code handle this response?"; use contract tests for "do the two sides still agree?".

---

## Core Concept 6 — Testing Migrations Against a Real Engine

Your migrations (Flyway, Liquibase, golang-migrate, Alembic) are code that runs against the real DB — so test them against the real DB. The cleanest pattern: let the test container start empty and **run your actual migration tool** as part of setup.

```java
@BeforeEach
void migrate() {
    Flyway.configure()
        .dataSource(pg.getJdbcUrl(), pg.getUsername(), pg.getPassword())
        .load()
        .migrate();   // your real V1__, V2__ scripts, against real Postgres
}
```

This catches: a migration that fails on the real engine, a migration that's incompatible with existing data, and the drift between "schema in code" and "schema your tests assume." See the `database-migration-patterns` skill for expand/contract and zero-downtime patterns; integration tests are how you verify those migrations actually apply.

---

## Real-World Examples

- **The `ON CONFLICT` that worked in H2.** A team ran repository tests against H2 for speed. An upsert behaved differently in production Postgres and double-counted balances. Switching to Testcontainers caught the next such bug at PR time.
- **The retry that never fired.** A payment client had a unit test mocking a `500`. WireMock revealed the client only retried on connection errors, not HTTP 5xx — the mock had hidden the bug because it threw the wrong exception type.
- **The migration that locked the table.** An `ALTER TABLE ... ADD COLUMN ... DEFAULT` took a full table lock on the real engine. A migration integration test against a seeded container surfaced the long lock before it hit production.

---

## Common Mistakes

- **Using H2/SQLite to test Postgres SQL.** The single most common false-confidence trap.
- **Rollback-per-test on code that commits itself.** You skip the very path you meant to verify.
- **Stubbing external APIs and calling it contract testing.** WireMock ≠ Pact.
- **`:latest` container tags.** Non-reproducible; reintroduces engine drift.
- **Asserting on global state in parallel tests.** Counts and IDs collide. Namespace or serialize.
- **One container per test by default.** Wildly slow; reuse where you can (see [senior](senior.md)).
- **Not testing the failure paths.** Stub the timeout, the 500, the malformed body — that's where bugs hide.

---

## Apply it

1. Find a real component where **Integration Testing** affects an interface or dependency.
2. Write two plausible choices and the constraint that favors each one.
3. Make the smallest reversible change at that boundary.
4. Exercise the component alone, then exercise the integrated flow.
5. Keep the decision note with the evidence that selected the option.

## Verify your work

- A focused check proves the local behavior.
- An integrated check proves callers and dependencies still agree.
- Logs, traces, compiler output, or benchmarks expose the boundary.
- Reverting the change restores the previous behavior without unrelated edits.

## Review questions

- Which boundary is most affected by Integration Testing?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
