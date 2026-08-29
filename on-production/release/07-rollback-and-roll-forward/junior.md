# Rollback & Roll-Forward — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Rollback & Roll-Forward** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Rollback & Roll-Forward

*When a release goes bad, you have two exits: go back to what worked, or push a fix forward. Learn to do both calmly.*

---

## Core Concept 1 — What "rollback" and "roll-forward" actually mean

Imagine you deployed version `v2.4.0` and the checkout page started returning 500 errors.

**Rollback** means: stop running `v2.4.0`, start running `v2.3.0` again — the version that worked an hour ago. The system returns to a state you *know* was healthy. You do this when the previous version is trustworthy and you want safety fast.

**Roll-forward** means: keep `v2.4.0`, find the bug, fix it, and ship `v2.4.1`. The system never goes backward. You do this when going back is impossible or risky (for example, the data already changed in a way `v2.3.0` can't read), or when the fix is genuinely tiny and fast.

```
Timeline:

  v2.3.0  ──►  v2.4.0 (broken)  ──┬──►  v2.3.0  again      = ROLLBACK
                                  │
                                  └──►  v2.4.1 (fixed)      = ROLL-FORWARD
```

The instinct for a junior should usually be: **roll back first, debug later.** Restoring service is the priority; understanding the bug can happen once users are no longer affected. Roll-forward is for when rollback isn't safe (you'll learn to spot that in Concept 4).

---

## Core Concept 2 — Your first rollback: `kubectl rollout undo`

Kubernetes keeps a history of your Deployment's revisions. Rolling back is one command.

```bash
# See the history of a deployment
kubectl rollout history deployment/checkout

# Output:
# REVISION  CHANGE-CAUSE
# 1         initial deploy v2.3.0
# 2         deploy v2.4.0   <-- the broken one (current)

# Roll back to the immediately previous revision
kubectl rollout undo deployment/checkout

# Or roll back to a specific revision number
kubectl rollout undo deployment/checkout --to-revision=1

# Watch it happen
kubectl rollout status deployment/checkout
```

That's it. Kubernetes spins up pods running the previous image and drains the broken ones. Within seconds to a couple of minutes, you're back on `v2.3.0`.

If you use **Helm**, the equivalent is:

```bash
helm history checkout          # list releases and their revisions
helm rollback checkout 1       # go back to revision 1
```

Two things to internalize:

1. **You can practice this safely.** Deploy a no-op change, then `rollout undo`. Build the muscle memory *before* the incident, not during it.
2. **Set a change-cause** so history is readable: `kubectl annotate deployment/checkout kubernetes.io/change-cause="deploy v2.4.0"` (or use `--record` in older clusters).

---

## Core Concept 3 — Roll back the binary, not the source

A classic junior mistake under pressure: "the deploy is broken, let me `git revert` the commit and rebuild." That is the *slowest* possible rollback.

```
Slow (minutes to tens of minutes, can fail):
  git revert  →  CI builds new image  →  tests  →  push to registry  →  deploy

Fast (seconds):
  re-deploy the exact previous image that you already built and tested
```

The previous artifact — say `myapp:v2.3.0` with digest `sha256:abc123…` — was already built, already tested, already proven in production. Rebuilding from source introduces a *new* artifact that has never run anywhere. A dependency could have moved, the base image could have changed, the build could fail at the worst moment.

**Rule of thumb: roll back to an artifact, not to a commit.** Pull the known-good image from the registry by its immutable tag or digest and deploy that. This is why immutable, retained artifacts in a registry matter — see [Registries & Distribution](../05-registries-and-distribution/middle.md).

---

## Core Concept 4 — The database does not roll back with the code

This is the single most important idea on this page. **Code rolls back in seconds. The database does not.**

When you roll back `v2.4.0` → `v2.3.0`, you replace the running code. But if `v2.4.0` had a database migration — say it *dropped* a column — that column is **still gone** after rollback. Now the old `v2.3.0` code starts up, tries to read the column it expects, and crashes. You rolled back the code straight into a broken database.

```sql
-- Migration shipped with v2.4.0 (DANGEROUS)
ALTER TABLE users DROP COLUMN legacy_email;   -- destructive!

-- Now you roll back to v2.3.0, whose code still does:
SELECT id, legacy_email FROM users;           -- ERROR: column does not exist
```

The takeaway for now: **a destructive migration can make rollback impossible.** This is why senior engineers insist that schema changes be *backward-compatible* — the new code and the old code must both work against the same database. You'll learn the full technique (called expand/contract) in the middle tier, and you can read the `database-migration-patterns` skill for the deep version.

For now, just remember: **if a release changed the database in a way the old code can't handle, you cannot simply roll back — you must roll forward.**

---

## Core Concept 5 — When to roll back vs roll forward

A simple decision aid for your first year:

| Situation | Do this | Why |
|-----------|---------|-----|
| Code-only change is broken, no DB change | **Roll back** | Fast, safe, reversible. |
| You're unsure what's wrong | **Roll back** | Stop the bleeding, debug calmly. |
| The bad release dropped/renamed a column | **Roll forward** | Old code can't read the new DB. |
| Fix is one line and you're confident | Either; often **roll forward** | But rollback is still safer if untested. |
| Incident is escalating fast | **Roll back** | Time pressure favors the proven version. |

The senior mantra: **"Roll back to recover, roll forward to fix."** Recovery first, root cause second.

A second thing to internalize early: **rolling back is not an admission of failure.** It's a normal, healthy operation. The best teams roll back often and without drama, precisely because they treat it as a routine safety move rather than a confession. A team that *never* rolls back is usually either lucky, not shipping much, or quietly leaving users in pain because someone is embarrassed to hit undo. Reaching for rollback quickly is a sign of operational maturity, not weakness.

---

## Core Concept 6 — The kill switch: rollback without deploying

There's a rollback so fast it doesn't involve a deploy at all: the **feature-flag kill switch.**

If the risky part of your release is wrapped in a feature flag, you can turn it *off* without touching the running code. The bad code is still installed on the servers — it's just dormant. No pods restart, no image changes, no traffic moves. The feature simply stops running.

```python
# Code shipped with a flag guard
if flags.is_enabled("new-checkout"):
    return new_checkout(cart)     # the risky new path
else:
    return old_checkout(cart)     # the proven old path
```

When `new-checkout` causes problems, you flip it off in the flag dashboard and *every* request immediately takes the old path — within seconds, globally. That is the single fastest way to recover from a bad feature.

This is why feature flags and rollback are tightly linked. Wrapping a risky change in a flag gives you an instant "undo" that doesn't depend on `kubectl` or rebuilds at all. You'll go deep on this in [Feature Flags & Progressive Delivery](../06-feature-flags-and-progressive-delivery/junior.md), but the takeaway for now: **if a change is risky, putting it behind a flag buys you the cheapest possible rollback.**

Note the limit: a kill switch only works for the parts of your change that are *behind a flag*. A bad library upgrade, a broken config, or a schema change can't be flipped off — those need a real rollback or roll-forward.

---

## Core Concept 7 — Know your last known-good version before you need it

You cannot roll back to a version you can't name. The most embarrassing way to fail an incident is to decide "let's roll back" and then spend ten minutes figuring out *what to roll back to.*

Build the habit of knowing, at any moment, what the last known-good version is:

```bash
# What's running right now, and what was running before?
kubectl rollout history deployment/checkout

# REVISION  CHANGE-CAUSE
# 5         deploy v2.4.0   <-- current (suspected bad)
# 4         deploy v2.3.0   <-- last known-good  <- your target

# Confirm the exact image of the good revision
kubectl rollout history deployment/checkout --revision=4
```

Two practices that make this painless:

1. **Always set a change-cause** on every deploy so the history is human-readable, not a wall of hashes. A revision labeled `deploy v2.3.0 (release train 2026-W24)` tells you instantly what it is.
2. **Tag releases meaningfully** so the version in `rollout history` maps to a real, findable artifact in your registry. See [Versioning & SemVer](../01-versioning-and-semver/junior.md).

If you can answer "what's the last good version?" in five seconds, your rollback is five seconds from starting. If you can't, your rollback hasn't even begun — and the clock is running while users suffer.

---

## Real-World Examples

- **Bad config deploy.** A team ships a Deployment with a wrong environment variable; the service can't reach its database. They run `kubectl rollout undo deployment/api`, service recovers in 40 seconds, and they investigate the config in a branch. Textbook rollback.
- **The migration trap.** A team ships a feature that renames `full_name` → `name` in one migration, coupled with code that uses `name`. The feature has a bug. They try to roll back — and the old code crashes because `full_name` no longer exists. They're forced to roll forward under pressure. The lesson: never couple a destructive schema change to the deploy.
- **Tiny typo, roll forward.** A copy change shows "Welcom" instead of "Welcome." Nobody rolls back for that; they ship `v2.4.1` with the fix. Low risk, no data involved — roll-forward is the natural choice.

---

## Common Mistakes

- **Rebuilding from source to roll back.** Slow and risky; deploy the existing known-good artifact instead.
- **Forgetting the database.** Rolling back code over a destructive migration crashes the old code. Always ask "did this release change the schema?"
- **Panicking and debugging in prod first.** Recover service, *then* investigate. Users don't care about your root-cause analysis while they're seeing 500s.
- **No idea what the previous version was.** If you can't name the last known-good version, you can't roll back. Know your `rollout history`.
- **Never having practiced.** The first time you run `rollout undo` should not be during a Sev-1.

---

## Apply it

1. Choose one small, known input for **Rollback & Roll-Forward**.
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

- What problem does Rollback & Roll-Forward solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
