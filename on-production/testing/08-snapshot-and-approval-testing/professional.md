# Snapshot & Approval Testing — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Snapshot & Approval Testing** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Snapshot & Approval Testing

*Governing golden tests at scale: when they're the right tool versus a crutch, the standards that keep them honest, and how to safely refactor untested code then migrate the net to real assertions.*

---

## Core Concept 1 — Right tool vs crutch: a decision framework

The central professional judgment is distinguishing a *legitimate* golden test from a *crutch* — a snapshot that exists because someone didn't want to think about the expected value. Use this framework:

| Question | "Right tool" answer | "Crutch" answer |
|----------|--------------------|-----------------|
| Is the expected value small and knowable? | No — it's large/structured | Yes — could be `toBe(x)` |
| Why a snapshot? | Output is wide; hand-asserting is impractical | "Faster than writing assertions" |
| Is the captured value *verified* correct? | Yes, reviewed at creation | Never reviewed — "it passed" |
| What does it protect? | Unintended *change* in a known-good artifact | Nothing specific |
| Can a reviewer understand a diff? | Yes — small, focused, normalized | No — 600 lines of noise |

Legitimate territory: rendered HTML/markup, serialized data, generated code, CLI output, full API response bodies, formatter output, and **characterization of legacy code you're about to refactor**. Crutch territory: a function returning a single scalar, a config object with five fields, anything where the team can state the right answer in one sentence but chose `toMatchSnapshot` to skip typing it.

The tell is intent. A snapshot you *chose* because the output is genuinely unwieldy is engineering. A snapshot you *defaulted* to because assertions felt like work is debt. Part of your job is making the default the right one — which is the rest of this page.

---

## Core Concept 2 — Governance: size limits, review discipline, normalization standards

Ungoverned golden tests trend toward exactly the behaviors that make them worthless. Codify standards so the lazy path is the correct path.

**Size limits.** Set a hard cap (e.g. external snapshots over ~50 lines require justification; over ~200 are rejected). Big snapshots are unreviewable; a reviewer cannot distinguish a real regression from incidental churn in a 600-line blob, so they rubber-stamp. Small, focused snapshots make the diff legible.

**Review discipline.** A snapshot/golden change in a PR is a *behavior* change and must be reviewed as such. The standard: the PR description must explain *why* the golden changed. "Updated snapshots" is not a reason. Reviewers approve the diff, not the fact that CI is green.

**Normalization standards.** Centralize scrubbers so every test treats time, ids, ordering, paths, and locale identically. Ad-hoc per-test normalization drifts and leaks non-determinism. One shared module, one set of placeholders (`<TIMESTAMP>`, `<UUID>`), applied everywhere.

```ts
// test/normalize.ts — the single source of normalization truth
const RULES: [RegExp, string][] = [
  [/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z/g, "<TIMESTAMP>"],
  [/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/g, "<UUID>"],
  [/\/Users\/[^/]+\//g, "<HOME>/"],
];

export function normalize(s: string): string {
  return RULES.reduce((acc, [re, repl]) => acc.replace(re, repl), s);
}
```

Document these three policies where engineers will see them: the testing guidelines, the PR template, and a lint rule (Concept 6). A standard that lives only in your head is not a standard.

---

## Core Concept 3 — Approval tests as a refactoring scaffold for untested code

This is the use case where golden tests are not a smell but the *correct, expert* move — and it deserves a rigorous treatment because juniors and seniors apply it informally while professionals apply it as a repeatable procedure.

You inherit a 400-line method with no tests, due for refactoring. You cannot write explicit assertions because you don't yet know the intended behavior; you only have *current* behavior. The Feathers procedure (from *Working Effectively with Legacy Code*), executed with approval tests:

1. **Find a seam** — a place to capture output without rewriting internals. Often the return value, or a wrapper that serializes side effects to text.
2. **Pin behavior across a broad input matrix.** Use combination/table approvals to drive many input permutations through the seam in one `verify`. The goal is *coverage of behavior*, not correctness — you are photographing the legacy beast from every angle.
3. **Approve the current output as the baseline** — explicitly accepting "this is what it does today," not "this is right."
4. **Refactor under the net.** Any approval-test failure now means *you changed behavior* — exactly what you must not do during a pure refactor. Green means behavior preserved.
5. **Once refactored and understood, migrate** the pinning tests to explicit assertions for the behaviors you've now articulated (Concept 5), and delete the now-redundant golden net.

```python
# Pinning a legacy pricing engine across a matrix before refactoring
from approvaltests.combination_approvals import verify_all_combinations

def test_pin_legacy_pricing():
    verify_all_combinations(
        legacy_price,
        [
            [0, 1, 99, 100, 1000],        # quantities (incl. boundaries)
            ["US", "EU", "JP"],            # regions
            [None, "SAVE10", "BOGUS"],     # coupon codes
        ],
    )
    # Approves a table of inputs→outputs. After this, refactor freely;
    # any diff means behavior changed. Then migrate to real assertions.
```

This is the one context where reaching for golden output first is unambiguously correct. Pair it with the `refactoring-techniques` skill for seam identification.

---

## Core Concept 4 — The maintenance cost curve at scale

Snapshot economics are deceptive because the cost is back-loaded and externalized. Make the curve explicit so teams budget for it.

- **Creation cost: near zero.** One line, auto-generated reference. This is precisely why suites accumulate snapshots faster than the team can maintain them.
- **Maintenance cost: superlinear with blast radius.** A change to a shared component, serializer, or template can light up *hundreds* of snapshots. If each requires real review, that's hours; if it doesn't get real review, it's blind `-u` and the suite is now decorative.
- **Cognitive cost: the trust tax.** Once a suite "always fails on unrelated changes," engineers stop reading diffs. From that point every snapshot is a liability — it can no longer catch a regression because nobody looks.

Manage the curve with three levers:
1. **Minimize blast radius** — small, focused snapshots so one logical edit touches few goldens.
2. **Cap the population** — don't snapshot what you can cheaply assert; every snapshot is a recurring liability, not a one-time asset.
3. **Watch golden churn** — if a golden file changes in most PRs that don't intend to change its behavior, it's brittle (encoding noise or scoped too wide) and should be normalized, narrowed, or deleted.

> Heuristic: a snapshot that has been blind-updated three times without anyone reading the diff has negative value. Delete it or convert it to an assertion. A test nobody trusts is worse than no test, because it consumes review attention while catching nothing.

---

## Core Concept 5 — Migrating snapshots to explicit assertions

Snapshots are often a *transitional* artifact: the right tool while you don't yet know the correct value, the wrong tool once you do. Migration is the maturity step most teams skip.

When to migrate a snapshot to assertions:
- The correct behavior is now understood and statable (post-characterization, post-refactor).
- The snapshot is small enough that explicit assertions are practical.
- The snapshot churns on incidental changes (brittle) and you'd rather assert the few fields that matter.

How to migrate without losing coverage:

```js
// BEFORE: opaque snapshot — asserts "same", protects nothing specific
test("creates an order", () => {
  expect(createOrder(cart)).toMatchSnapshot();
});

// AFTER: explicit assertions — each line states a known truth
test("creates an order", () => {
  const order = createOrder(cart);
  expect(order.status).toBe("pending");
  expect(order.total).toBe(4500);            // 3 × $15.00, verified by hand
  expect(order.lineItems).toHaveLength(3);
  expect(order.id).toMatch(/^ord_[a-z0-9]{12}$/);  // shape, not value
});
```

The migrated test is longer but *says what it means*. It fails for *correctness* reasons, not *sameness* reasons; a reviewer can read it without opening a `.snap` file; and it no longer breaks on unrelated field changes. The discipline: when a snapshot has taught you what correct looks like, retire it and encode that knowledge as assertions. Keep snapshots only where output remains genuinely too wide to assert (rendered markup, generated code, large API bodies).

---

## Core Concept 6 — Enforcing discipline in CI

Standards that rely on willpower fail. Encode them as automated gates so the suite can't rot quietly.

**Fail on accidental snapshot writes in CI.** Jest's `--ci` flag refuses to *create* new snapshots in CI — a missing snapshot fails instead of silently writing one. This stops "it passed because CI auto-generated the reference" entirely.

```bash
# CI must never write a reference; a missing/changed snapshot is a failure to review locally
$ jest --ci          # new snapshots → failure, not silent write
$ go test ./...      # never pass -update in CI
```

**Block committed `*.received.*` files.** A committed ApprovalTests received file means someone bypassed the diff tool. Gate it:

```bash
# pre-commit / CI guard
if git ls-files | grep -q '\.received\.'; then
  echo "ERROR: committed *.received.* file — approve via the diff tool, don't copy" >&2
  exit 1
fi
```

**Lint snapshot size.** A custom check that fails the build when any `.snap` or `.golden` exceeds the size cap, forcing a justification or a split.

**Require a reason for golden changes.** A PR check that, when any golden/`.snap` is modified, requires the PR body to contain a rationale section. Cheap to implement, high leverage — it converts "updated snapshots" into a real review prompt.

The point of CI enforcement isn't bureaucracy; it's removing the easy paths to rot so the team doesn't have to remember the discipline every time.

---

## Core Concept 7 — Normalization as a versioned contract

At scale, normalization rules *are* part of your test contract, and changing them silently is as dangerous as changing the code. Treat the scrubber set as versioned, reviewed code:

- **Centralized** (Concept 2) so every test scrubs identically.
- **Reviewed** — a change to a scrubber regex can mask a real regression (over-scrubbing) or unleash flakiness (under-scrubbing) across the entire suite. Such PRs get senior review.
- **Tested** — yes, test your normalizers. A scrubber that accidentally matches a real value is a silent correctness hole.
- **Conservative** — scrub the *value*, never the *key*; replace `"createdAt": "2024-..."` with `"createdAt": "<TIMESTAMP>"`, not by deleting the field. Deleting the field means a regression that drops `createdAt` entirely sails through.

The failure mode to fear: an over-broad scrubber (say, replacing every number with `<NUM>`) that makes a genuinely wrong amount indistinguishable from the right one. That converts your whole golden suite into a tautology. Normalization removes *noise*, never *signal* — and at scale, only review discipline keeps that line.

---

## Core Concept 8 — A wrong output got approved: post-mortem and prevention

A concrete failure to make the abstraction visceral.

**What happened.** A team snapshotted a tax-calculation API response to lock the contract. During an unrelated refactor, a junior introduced an off-by-one in the rounding rule, dropping every tax amount by one cent. The snapshot test went red. The diff was 180 lines (the whole response body, un-normalized). Under deadline, the reviewer skimmed it, saw "looks like just the tax fields moved a bit," and approved `jest -u`. The wrong values became the new golden. Three weeks of invoices shipped one cent light before finance noticed a reconciliation gap.

**Why every safeguard failed.** (1) The snapshot was *too large* to review honestly. (2) It asserted *sameness*, so the only signal was a diff nobody could parse. (3) The blind `-u` was frictionless. (4) There was no explicit assertion anywhere stating the *correct* tax for a known input.

**Prevention, mapped to this page:**
- **Size** (C2): split the response so the tax block is its own small snapshot — the one-cent shift would have been unmissable.
- **Anchor assertion** (C5): alongside the snapshot, one explicit `expect(resp.tax).toBe(412)` for a hand-verified case. A snapshot guards *change*; the assertion guards *correctness*. You usually want both for money.
- **Review reason** (C6): a required rationale would have forced "why is tax changing?" — a question with no good answer here.
- **CI `--ci`** (C6): wouldn't have helped (the snapshot existed), but the rationale gate would have.

The lesson is the recurring theme of this topic: a snapshot proves *it's the same*, never *it's right*. Where correctness has a knowable answer — money, security, contracts — back the snapshot with at least one explicit assertion.

---

## Real-World Examples

- **Design-system component library (hundreds of snapshots).** Governance: per-component small snapshots (low blast radius), centralized normalization for generated class hashes, a CI size lint, and a rule that markup-changing PRs explain the diff. Snapshots catch accidental markup drift; explicit assertions cover accessibility attributes and behavior.
- **Compiler test suite.** Golden files for emitted code are legitimate (output is genuinely too large to assert). `-update` is allowed locally, banned in CI; every golden change in a PR requires a note on which optimization or codegen rule moved.
- **Legacy monolith refactor.** A six-month effort pins the billing engine with combination approval tests, refactors module by module under the net, then migrates the now-understood behaviors to explicit assertions and deletes the golden scaffold. Textbook right-tool use.
- **API contract regression suite.** Response-body snapshots (scrubbed) catch accidental field changes, but every money/auth field is *also* asserted explicitly so a wrong value can't be rubber-stamped.

---

## Common Mistakes

1. **Defaulting to snapshots instead of choosing them.** The crutch pattern — using golden output to avoid stating a known answer.
2. **No size cap.** Giant snapshots are unreviewable and guarantee rubber-stamping.
3. **Decentralized normalization.** Per-test scrubbers drift; non-determinism leaks back in.
4. **Allowing `-update` / auto-write in CI.** The reference must be reviewed locally, never minted by the pipeline.
5. **Never migrating.** Keeping opaque snapshots after the correct behavior is well understood.
6. **No anchor assertion for correctness-critical output.** A snapshot alone can rubber-stamp a wrong amount.
7. **Over-scrubbing.** Normalizing away the very signal you needed to catch a regression.
8. **Hoarding distrusted snapshots.** Keeping tests the team always blind-updates instead of deleting them.

---

## Apply it

1. Define the user or business outcome that **Snapshot & Approval Testing** should improve.
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

- Which measurable outcome justifies investing in Snapshot & Approval Testing?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
