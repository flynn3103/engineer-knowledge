# Integration Testing — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Integration Testing** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Integration Testing
>
> *Where two pieces of code meet, a bug is waiting — integration tests are how you find it before production does.*

---

## Core Concept 1 — What Integration Testing Is

Picture three rings around your code:

1. **Unit** — one class, everything else faked. Milliseconds. No I/O.
2. **Integration** — your code + a *real* dependency (a real DB, a real broker). Hundreds of milliseconds.
3. **End-to-end** — the whole running system, clicked like a user would. Seconds to minutes. See [End-to-End Testing](../04-end-to-end-testing/README.md).

Integration sits in the middle. The defining trait is **real I/O across a boundary**: instead of a mock that *pretends* to be Postgres, you talk to an actual Postgres.

There's a spectrum even within "integration":

- **Narrow integration** — your code + **one** real dependency. Example: your `UserRepository` against a real Postgres. This is the sweet spot and most of what you'll write.
- **Broad integration** — several of your services wired together. Heavier, slower, fewer of them.

As a junior, focus almost entirely on **narrow** integration tests. They give you most of the safety for a fraction of the cost.

---

## Core Concept 2 — What It Catches That Unit Tests Can't

This is the heart of the topic. A unit test with a mocked database can be 100% green while the real thing is 100% broken. Here is what the mock *can't* see:

- **Wrong SQL.** A typo in a column name, a `JOIN` that returns duplicates, a `WHERE` that's off. The mock returns whatever you told it to; the real DB rejects your query.
- **Serialization mismatches.** Your code writes a timestamp one way; the DB stores and returns it another. JSON field named `userId` in code but `user_id` in the payload.
- **Transaction behaviour.** Did your code actually commit? Does a rollback undo what you think? A mock has no transactions.
- **Config and wiring.** Wrong connection string, missing migration, a default that only bites in the real engine.
- **The mocked-vs-real gap.** Your mock said `findById` returns `null` for a missing row — but the real driver throws, or returns an empty `Optional`. Your code handles the mock's version and crashes on the real one.

> **The "unit tests pass, system broken" problem.** Every team has shipped a release where CI was green and production fell over on the first request. Almost always it's a seam a unit test couldn't reach. Integration tests exist to close that gap.

---

## Core Concept 3 — Real Dependency vs Mock vs In-Memory

When your code needs a database in a test, you have three options. Understanding the trade-off here is the single most important idea at this level.

| Option | What it is | Fidelity | Speed | Verdict |
|---|---|---|---|---|
| **Mock the DB** | Replace the repo/driver with a fake | None — tests nothing real | Fastest | Fine for *unit* tests; proves nothing about real SQL |
| **In-memory DB (H2/SQLite)** | A different DB engine that runs in RAM | **Low — it lies** | Fast | A classic trap (see below) |
| **Real DB via Testcontainers** | The actual prod engine, in Docker | High | Slower (seconds) | The modern default |

**Why in-memory is a trap.** H2 and SQLite are *different database engines* from your production Postgres. Different SQL dialect, different type handling, different behaviour around constraints and concurrency. A test that passes against H2 can fail against Postgres — so the test gave you false confidence. (The senior file has a concrete `H2 passes, Postgres fails` example.) The rule of thumb: **if it isn't the engine you run in production, it can lie to you.**

The modern answer is **Testcontainers**: start the *real* Postgres in a throwaway Docker container, run your test against it, throw it away. Same engine as production, no shared state between runs.

---

## Core Concept 4 — Your First Testcontainers Test

Let's write a narrow integration test: a `UserRepository` against a real Postgres. Here it is in three languages so you can find yours.

**Java (JUnit 5 + Testcontainers):**

```java
@Testcontainers
class UserRepositoryIT {

    @Container
    static PostgreSQLContainer<?> postgres =
        new PostgreSQLContainer<>("postgres:16-alpine");

    DataSource dataSource;

    @BeforeEach
    void setUp() {
        // Point your code at the container's real connection details.
        dataSource = buildDataSource(
            postgres.getJdbcUrl(),
            postgres.getUsername(),
            postgres.getPassword());
        runMigrations(dataSource); // create the real schema
    }

    @Test
    void savesAndLoadsUser() {
        var repo = new UserRepository(dataSource);
        repo.save(new User("ada@example.com", "Ada"));

        var found = repo.findByEmail("ada@example.com");

        assertThat(found).isPresent();
        assertThat(found.get().name()).isEqualTo("Ada");
    }
}
```

**Go (testcontainers-go):**

```go
func TestUserRepository(t *testing.T) {
    ctx := context.Background()
    pg, err := postgres.Run(ctx, "postgres:16-alpine",
        postgres.WithDatabase("app"),
        postgres.WithUsername("test"),
        postgres.WithPassword("test"),
        testcontainers.WithWaitStrategy(
            wait.ForListeningPort("5432/tcp")),
    )
    require.NoError(t, err)
    defer pg.Terminate(ctx)

    dsn, _ := pg.ConnectionString(ctx, "sslmode=disable")
    db, _ := sql.Open("pgx", dsn)
    runMigrations(t, db)

    repo := NewUserRepository(db)
    require.NoError(t, repo.Save(ctx, User{Email: "ada@example.com", Name: "Ada"}))

    got, err := repo.FindByEmail(ctx, "ada@example.com")
    require.NoError(t, err)
    require.Equal(t, "Ada", got.Name)
}
```

**Python (pytest + testcontainers):**

```python
import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="module")
def pg_dsn():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg.get_connection_url()

def test_save_and_load(pg_dsn):
    db = connect(pg_dsn)
    run_migrations(db)
    repo = UserRepository(db)

    repo.save(User(email="ada@example.com", name="Ada"))
    found = repo.find_by_email("ada@example.com")

    assert found is not None
    assert found.name == "Ada"
```

Notice the shape in all three: **start a real Postgres → run your real migrations → run your real code → assert on real results.** No mocks anywhere. That's an integration test.

---

## Core Concept 5 — Cleaning Up Between Tests

Integration tests share a database, so one test's data can pollute the next. You must reset state between tests. Three common strategies, simplest first:

1. **Truncate tables** before/after each test. Easy, reliable, slightly slow.

   ```java
   @AfterEach
   void cleanup() {
       jdbc.execute("TRUNCATE users RESTART IDENTITY CASCADE");
   }
   ```

2. **Rollback a transaction** per test — start a transaction in setup, never commit, roll back in teardown. Fast, but tricky if your code manages its own transactions (the middle file covers this).

3. **Fresh container per test** — maximum isolation, slowest. Reserve for tests that truly need it.

As a junior, **truncate per test** is the safe default. Always make each test responsible for its own data: never assume a row exists because "another test created it." Tests must be able to run in *any* order and *alone*.

A quick way to check you've got isolation right: run a single test by itself, then run the whole class, then run the class twice in a row. If any of those changes the result, your tests are leaking state into each other and one of the three strategies above isn't being applied. A green test that only stays green when its neighbours run first isn't really testing anything — it's testing the *suite's* order.

One more rule worth internalizing early: **run your real migrations in setup, don't hand-craft the schema.** It's tempting to write `CREATE TABLE users (...)` inside the test, but then you're testing against a schema that may not match what production actually has. Point the test at your real Flyway/golang-migrate/Alembic scripts so the schema under test is the schema you ship.

---

## Real-World Examples

- **The repository that lied.** A `findActiveUsers()` method had a mocked unit test asserting it returned 3 users. Shipped. In production it returned 0 — the real SQL used `status = 'ACTIVE'` but the column stored `'active'` (lowercase). A narrow integration test against real Postgres would have failed instantly.
- **The timestamp that drifted.** Code stored `LocalDateTime`; the DB column was `timestamptz`. Reads came back shifted by the server's timezone. The unit test mocked the DB and never noticed. The integration test made it obvious.
- **The migration nobody ran.** A new column was added in code but the migration script had a typo. Unit tests (mocked) passed. The first integration test failed at startup: *column "phone_number" does not exist.* That failure is the test doing its job.

---

## Common Mistakes

- **Calling a mocked test an "integration test."** If there's no real I/O, it's a unit test wearing a costume.
- **Trusting H2/SQLite for Postgres code.** It passes locally, fails in prod. Use the real engine.
- **Tests that depend on order.** Test B passes only because Test A left a row behind. Run them alone and they break.
- **Forgetting teardown.** Leftover rows make the *next* run fail mysteriously.
- **Not running migrations in the test.** You test against a schema that doesn't match production.
- **One giant test that sets up everything.** Keep each test focused; isolate its data.

---

## Apply it

1. Choose one small, known input for **Integration Testing**.
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

- What problem does Integration Testing solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
