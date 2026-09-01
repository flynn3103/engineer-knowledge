# Snapshot & Approval Testing — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Snapshot & Approval Testing** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Snapshot & Approval Testing

*The discipline that separates a snapshot suite that catches real regressions from one that's an unreviewable green rubber stamp — normalization, characterization, and smelling the smell.*

---

## Core Concept 1 — When it's the right tool vs a crutch

The senior question is never "should we use snapshots?" but "is this snapshot earning its place?" Use this split:

**It's the right tool when:**

- The output is **wide and structured** and the spec is genuinely implicit (rendered HTML, an AST, a serialized config, a 50-field response). Hand-assertion would be less readable, not more.
- You're **characterizing legacy behavior** you can't yet specify — the whole point is "alert me if *anything* changes."
- A diff is **the most honest review medium** for the kind of change you're guarding against.

**It's a crutch when:**

- The expected value is **small and knowable** (`"OK"`, `42`, a three-field object). A snapshot here hides the fact that you didn't bother to assert the actual contract.
- The snapshot is **load-bearing for correctness you never verified** — the only "test" of a new feature is `toMatchSnapshot()`, capturing whatever the fresh, unreviewed code produced.
- It exists to **make the coverage number go up** without encoding any intent.

A blunt heuristic: *if you can write the explicit assertion in a couple of lines and you know it's right, do that.* Snapshots are for output too wide to type, not for thinking you can skip.

---

## Core Concept 2 — Normalization & scrubbing non-determinism

A snapshot is only useful if a diff means "behavior changed." The instant your output contains a timestamp, UUID, absolute path, or unordered map, the test fails on every run for reasons that have nothing to do with behavior — and the team's reflex becomes blind `-u`, which kills the suite. **Normalization is non-negotiable for any real-world snapshot.**

The fix is to scrub volatile fields to stable placeholders *before* comparing. Jest supports **property matchers** for exactly this:

```js
test("createOrder returns a stable shape", () => {
  expect(createOrder({ item: "Widget", qty: 2 })).toMatchSnapshot({
    id: expect.any(String),          // UUID — assert type, don't pin value
    createdAt: expect.any(Date),     // timestamp — type only
    total: 9.0,                      // deterministic — pin it
  });
});
```

The snapshot stores `"Any<String>"` for `id`, so the test asserts *"there is a string id"* without coupling to a specific UUID.

For free-form text (Go golden files, ApprovalTests), scrub with regex before writing/comparing:

```go
var (
	reUUID = regexp.MustCompile(`[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}`)
	reTime = regexp.MustCompile(`\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z`)
)

func scrub(s string) string {
	s = reUUID.ReplaceAllString(s, "<UUID>")
	s = reTime.ReplaceAllString(s, "<TIMESTAMP>")
	return s
}

func TestRenderEvent(t *testing.T) {
	got := scrub(RenderEvent(sampleEvent()))
	golden := filepath.Join("testdata", "event.golden")
	if *update {
		os.WriteFile(golden, []byte(got), 0o644)
	}
	want, _ := os.ReadFile(golden)
	if got != string(want) {
		t.Errorf("mismatch\n--- want\n%s\n--- got\n%s", want, got)
	}
}
```

The committed golden now reads `"id": "<UUID>", "at": "<TIMESTAMP>"` — stable forever. ApprovalTests offers built-in **scrubbers** (`Scrubbers.scrubGuids`, date scrubbers, custom regex) that do the same.

Two further determinism rules: **sort unordered collections** before serializing (map iteration order, sets), and **inject clocks/ID generators as dependencies** so tests can fix them. A snapshot over un-normalized output isn't a snapshot test — it's a flaky-test generator.

---

## Core Concept 3 — Small & focused: the size discipline

The reviewability of a snapshot is inversely proportional to its size. A 12-line snapshot gets read; a 600-line snapshot gets `-u`'d. Brittle giant snapshots are the number-one reason snapshot suites rot.

Tactics that keep them small and focused:

- **Snapshot the slice you care about, not the whole object.** If the test is about pricing, snapshot the pricing fields, not the entire 80-field order.
- **Prefer inline snapshots for small output** — they cap their own size by sheer visual pressure and put the value in front of reviewers.
- **One behavior per snapshot.** A snapshot covering "rendering + pricing + permissions" fails for three unrelated reasons; split it so each failure points at one cause.
- **Set a hard size budget in review.** "No snapshot over N lines without justification" is a reasonable team rule; it forces the question "should this output be this wide, or am I avoiding writing the real assertion?"

A focused snapshot has a *narrow coupling surface*: it ties itself to as little of the output as the behavior requires. Wide coupling is what makes snapshots change on every unrelated edit (Core Concept 7).

---

## Core Concept 4 — Characterization testing to refactor legacy code

This is the legitimate use that justifies the technique's existence. You inherit code with no tests and behavior you don't fully understand. You must not change behavior, but you can't assert behavior you can't specify. **Characterization tests** (Feathers, *Working Effectively with Legacy Code*) resolve the paradox: capture *current* behavior as golden/approved files, then refactor under that net.

The workflow — this is the core loop the `refactoring-techniques` skill formalizes:

1. **Find a seam** to drive the legacy code with a range of representative inputs.
2. **Capture outputs** for those inputs as approved/golden files. Don't judge correctness — you're recording reality, not blessing it.
3. **Run the suite green** — the net is in place.
4. **Refactor in small steps**, re-running constantly. Any diff means you changed behavior; investigate immediately.
5. When the refactor is done and the code is comprehensible, **migrate the characterization snapshots to explicit assertions** where you now understand the contract (see professional tier).

```python
# pytest + approval-style golden via syrupy or plain file
import pytest

LEGACY_INPUTS = [
    {"plan": "free", "seats": 1, "addons": []},
    {"plan": "pro", "seats": 12, "addons": ["sso"]},
    {"plan": "enterprise", "seats": 250, "addons": ["sso", "audit"]},
]

@pytest.mark.parametrize("payload", LEGACY_INPUTS, ids=lambda p: p["plan"])
def test_billing_characterization(payload, snapshot):
    # snapshot = whatever billing CURRENTLY computes; the net, not the spec
    assert compute_invoice_legacy(payload) == snapshot
```

Approval testing fits this best because its forced diff tool makes you *look* at what you're pinning. The honest framing: these tests assert "I didn't change anything," which is exactly the guarantee a refactor needs — and nothing more.

---

## Core Concept 5 — A wrong output got approved: a failure story

A concrete cautionary tale, because the abstract warning never lands.

A payments team added a new "partial refund" feature. The only test was:

```js
test("partial refund response", () => {
  expect(buildRefund(order, { amount: 30 })).toMatchSnapshot();
});
```

The fresh code had an off-by-one in proration: it refunded `30.00` but reported the **remaining balance** as `70.00` when it should have been `69.99` (a rounding bug in the fee handling). Nobody computed the right answer by hand — the snapshot just captured whatever the brand-new code produced. The PR review saw a clean green snapshot and approved it. The wrong number was now the golden value.

Three weeks later a refactor touched the fee module. The snapshot test went red — correctly showing the remaining balance was now `69.99`. The on-call engineer, under time pressure, saw "a snapshot changed in the payments refactor," assumed it was expected churn, and ran `jest -u`. The bug was re-approved. It shipped, and finance caught a reconciliation discrepancy a month later.

Two distinct failures, both classic:

1. **Capture without verification.** The original snapshot enshrined an unverified output. A snapshot asserts *sameness*, never *correctness* — so the first capture must be reviewed against a hand-computed expectation, or paired with an explicit assertion on the load-bearing value (`expect(refund.remaining).toBe(69.99)`).
2. **Blind update under pressure.** The red test was the system *working* — it caught the bug being fixed — and a reflexive `-u` discarded the signal.

The fix is policy, not tooling: load-bearing values get **explicit assertions** even inside snapshot-heavy tests, and **no `-u` without reading and explaining the diff** — enforced in review.

---

## Core Concept 6 — Reviewing snapshot diffs like code

A snapshot change in a PR is a *behavior change*. It deserves the same scrutiny as a logic change — more, because it's easy to skim.

Reviewer checklist for any PR touching `.snap`/`.golden`/`.approved` files:

- **Does every diff line have an explanation?** If the PR refactors pricing, why did the *rendering* snapshot change? Unexplained collateral diffs are the tell of a real bug or an over-coupled snapshot.
- **Is the new value actually correct,** or merely different? "The test passes again" is not the bar. Spot-check load-bearing numbers against intent.
- **Did the diff get bigger than the code change justifies?** A one-line code fix that rewrites a 200-line snapshot signals brittleness — flag the snapshot for splitting/scrubbing.
- **Was this an update or a genuine new capture?** A flood of `-u` across many files in a "tests passing" commit is the rubber-stamp smell.

Make it cultural: snapshot diffs are not noise to scroll past. A team that treats them as code catches the bug in Core Concept 5 at review time.

---

## Core Concept 7 — Brittleness: snapshots that change on every edit

A brittle snapshot fails for changes unrelated to what it tests. Every false failure trains the team toward blind `-u`, which is how a suite dies. Sources of brittleness and their fixes:

| Source | Why it breaks | Fix |
|---|---|---|
| Snapshotting the whole object | Any field change anywhere fails the test | Snapshot only the relevant slice |
| Volatile fields not scrubbed | Time/UUID/path differ every run | Normalize (Core Concept 2) |
| Unordered collections | Map/set iteration order varies | Sort before serializing |
| Whitespace / formatting noise | A prettier change rewrites the snapshot | Normalize formatting; snapshot semantic content, not exact bytes |
| Over-wide coupling surface | Test ties to internals it doesn't care about | Project to a stable, intentional shape before snapshotting |

The unifying principle: **the only thing that should change a snapshot is the behavior the snapshot is meant to guard.** Every other source of change is noise that must be designed out — because noise is what makes blind updating feel reasonable.

---

## Core Concept 8 — Knowing the smell: snapshots as missing assertions

Honesty about the technique's reputation: snapshots are *often* a smell, and a senior engineer should be able to name when.

The smell is **"I used a snapshot because I didn't want to think about what correct means."** Symptoms:

- A new feature whose *only* test is `toMatchSnapshot()` on output nobody hand-verified.
- Snapshots used where the expected value is small and obvious — hiding a contract instead of stating it.
- Coverage-driven snapshots that exist to color a file green.
- A suite where most failures are resolved by `-u`, not by thought.

The antidote isn't "never use snapshots" — it's **asymmetry of intent**. When you can articulate the expected value, assert it explicitly. When the output is genuinely wide and the spec is implicit, snapshot it — *and* pin the load-bearing values with explicit assertions alongside. A snapshot should complement assertions, not replace the thinking they represent.

---

## Real-World Examples

- **Compiler/transpiler golden tests.** Input source in `testdata/`, golden ASTs/output. Wide, structured, spec implicit — textbook right-tool use, with paths and temp dirs scrubbed.
- **Email/notification templates.** Rendered HTML snapshotted with dates and recipient IDs scrubbed; a diff means the template changed, which is exactly the review you want.
- **A legacy pricing engine refactor.** Approval tests over 200 historical orders pinned current behavior; the team split a god-function into a rule table with byte-identical output, then migrated the highest-value scenarios to explicit `expect(total).toBe(...)` assertions.
- **The anti-example.** A microservice where every handler test is one `toMatchSnapshot()` over the full HTTP response — 40 brittle, un-scrubbed snapshots that go red on any shared-model change and get mass-`-u`'d every sprint. Green, large, and worthless.

---

## Common Mistakes

1. **No normalization.** Un-scrubbed timestamps/UUIDs/ordering make the suite flaky and train blind updates.
2. **Whole-object snapshots.** Wide coupling surface → brittle → mass `-u` → dead suite.
3. **Snapshot as the only test of new code.** Capturing unverified output and calling it tested (the Core Concept 5 trap).
4. **Skimming snapshot diffs in review.** Treating behavior changes as noise; rubber-stamping regressions.
5. **Never migrating off characterization snapshots.** Leaving "alert on any change" scaffolding in place forever, where explicit assertions would be clearer once the code is understood.

---

## Apply it

1. State the system invariant that **Snapshot & Approval Testing** must protect.
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

- Which invariant must remain true when Snapshot & Approval Testing fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
