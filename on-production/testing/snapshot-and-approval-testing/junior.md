# Snapshot & Approval Testing — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Snapshot & Approval Testing** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Snapshot & Approval Testing

*Capture the output once, commit it, and let the test scream when it changes.*

---

## Core Concept 1 — What a snapshot actually is

Imagine a function that builds a user-profile object:

```js
function buildProfile(user) {
  return {
    name: `${user.first} ${user.last}`,
    initials: (user.first[0] + user.last[0]).toUpperCase(),
    role: user.admin ? "Administrator" : "Member",
  };
}
```

To test this with explicit assertions you'd write three or four `expect` lines. With a snapshot you write *one line* and let the tool record the whole object:

```js
test("buildProfile shapes the user", () => {
  expect(buildProfile({ first: "Ada", last: "Lovelace", admin: true }))
    .toMatchSnapshot();
});
```

The first time this runs, Jest **writes** a file next to your test, in a `__snapshots__/` folder:

```js
// __snapshots__/profile.test.js.snap
exports[`buildProfile shapes the user 1`] = `
{
  "initials": "AL",
  "name": "Ada Lovelace",
  "role": "Administrator",
}
`;
```

That `.snap` file is now part of your codebase. You **commit it**. It is the expected value — just stored in a file instead of typed inline.

---

## Core Concept 2 — Your first `toMatchSnapshot`

The workflow has exactly three steps:

1. **Write the test** with `.toMatchSnapshot()` (no expected value).
2. **Run it once.** The snapshot file is created. The test passes because there's nothing to compare against yet.
3. **Read the generated snapshot** and confirm it looks right, then commit it.

Step 3 is the one beginners skip — and it's the most important. The snapshot is only as trustworthy as your one-time review of it. If the output was wrong when you first captured it, you just enshrined a bug as the "correct" answer.

```bash
$ npx jest profile.test.js
 PASS  profile.test.js
  ✓ buildProfile shapes the user (3 ms)

 › 1 snapshot written.
```

After that first run, the snapshot is the law. Every future run checks against it.

---

## Core Concept 3 — How a snapshot test fails

Suppose a teammate changes the code so `role` becomes lowercase `"administrator"`. Re-run the test:

```bash
 FAIL  profile.test.js
  ✕ buildProfile shapes the user (8 ms)

  - Snapshot  - 1
  + Received  + 1

    {
      "initials": "AL",
      "name": "Ada Lovelace",
  -   "role": "Administrator",
  +   "role": "administrator",
    }
```

This is a snapshot test earning its keep: a change in behavior produced a visible **diff**, and the test failed. The `-` lines are the saved snapshot; the `+` lines are what the code produces now.

Now you have a decision to make, and it's a *thinking* decision, not a mechanical one:

- **Was the change intended?** Then the snapshot is out of date — update it (next concept).
- **Was the change a bug?** Then the test caught a regression — fix the code, don't touch the snapshot.

A snapshot test never decides this for you. It only flags the difference.

---

## Core Concept 4 — Updating a snapshot on purpose

When the change is intentional, you tell Jest to overwrite the stored snapshot:

```bash
$ npx jest profile.test.js -u      # -u = --updateSnapshot
 › 1 snapshot updated.
```

Now the `.snap` file holds the new lowercase value, and the test passes again. You commit the updated `.snap` alongside the code change.

> **The dangerous habit:** running `-u` *every time a test goes red* without reading the diff. That turns the test into a rubber stamp — it can never fail because you always accept whatever the code currently does. We'll hammer on this at higher tiers, but learn the reflex now: **read the diff before you update.** If you can't explain *why* the snapshot changed, do not update it.

---

## Core Concept 5 — "Same" is not "correct"

This is the single most important idea on the page.

An explicit assertion encodes *your knowledge of the right answer*:

```js
expect(add(2, 3)).toBe(5);   // 5 is provably correct
```

A snapshot encodes *whatever the code happened to produce*:

```js
expect(add(2, 3)).toMatchSnapshot();   // snapshot might say 6 if add() is buggy
```

If `add` returns `6` the first time you capture, the snapshot stores `6`, the test passes forever, and the bug is now "approved." Snapshots assert **"it's the same as before,"** never **"it's right."** They are great at catching *unexpected change* and useless at catching *original wrongness*.

That's why you (a) review the snapshot the moment it's created, and (b) prefer an explicit assertion whenever the expected value is small and you actually know it. Reach for a snapshot when the output is large, structured, and tedious to type by hand — not as a way to avoid thinking about correctness.

---

## Real-World Examples

- **Rendered UI component.** A React component renders to a tree of dozens of nodes. Hand-writing `expect` for every attribute is miserable; a snapshot captures the whole tree and flags any future change.
- **CLI `--help` output.** Capture the help text as a snapshot. If someone accidentally breaks the formatting, the test catches it.
- **API response shape.** Serialize a JSON response to a snapshot so a field rename or removal trips the test.
- **A formatter.** A code formatter takes ugly input and produces clean output. Snapshot the clean output; any change to the formatter shows up as a diff.

In each case the output is *big* and *structured* — exactly where snapshots shine.

---

## Common Mistakes

1. **Not reading the first snapshot.** You enshrine whatever output exists, bug and all.
2. **`-u` as a reflex.** Going red → update → green, without reading the diff. The test now proves nothing.
3. **Giant snapshots.** A 500-line snapshot is unreviewable; nobody can tell a real regression from noise.
4. **Snapshotting random data.** If the output contains a timestamp or random ID, the test fails every run. (Fixing this is "normalization" — covered at higher tiers.)
5. **Using a snapshot when you know the answer.** If the expected value is `5`, write `toBe(5)`. Snapshots are for output too big to type.

---

## Apply it

1. Choose one small, known input for **Snapshot & Approval Testing**.
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

- What problem does Snapshot & Approval Testing solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
