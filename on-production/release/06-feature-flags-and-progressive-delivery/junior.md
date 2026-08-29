# Feature Flags & Progressive Delivery — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Feature Flags & Progressive Delivery** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Feature Flags & Progressive Delivery

*Shipping the code is not the same as turning it on. A flag is the switch in between.*

---

## Core Concept 1 — Deploy Is Not Release

The most important sentence in this whole topic:

> **Deploy** means the code is on the server. **Release** means users get the behavior. Flags let you do them at different times.

Without flags, these are welded together. The feature goes live the moment the deploy finishes, at 2pm on a Friday, whether or not your on-call person is ready. With flags, the deploy is a calm, boring event — code lands, switched off — and the *release* is a separate, deliberate flip you make when the time is right.

This buys you three things immediately:

1. **Ship incomplete work safely.** You can merge a half-built feature behind a flag that's off. The code is in production (so it stays integrated and tested by CI), but no user ever runs it. This is what lets teams avoid long-lived feature branches.
2. **Decouple risk.** A deploy that ships ten features behind ten off flags can be released one at a time. If feature 7 misbehaves, you flip *its* flag off — the other nine stay live.
3. **Instant off-switch.** Turning a flag off is a config change that takes effect in seconds. Rolling back a deploy can take many minutes and re-introduces whatever else was in that build.

```text
TRADITIONAL:   merge ──► build ──► deploy = release (all at once)
WITH FLAGS:    merge ──► build ──► deploy (off) ──────► flip flag = release (later, on your terms)
```

---

## Core Concept 2 — Your First Flag

The simplest flag is a boolean read from configuration. Here it is in three languages, from crudest to cleanest.

**The crude version — an environment variable:**

```go
// Works, but: requires a restart to change, no targeting, no per-user control.
if os.Getenv("FEATURE_NEW_CHECKOUT") == "true" {
    return newCheckout(cart)
}
return oldCheckout(cart)
```

This is a real flag and it's fine for a tiny project. Its weakness: changing it means redeploying or restarting, so you lose the "flip it without a deploy" superpower.

**The better version — an SDK that evaluates at runtime:**

```js
// JavaScript with an OpenFeature-style client.
const client = OpenFeature.getClient();

async function checkout(user, cart) {
  const useNew = await client.getBooleanValue("new-checkout", false, {
    targetingKey: user.id,
  });
  return useNew ? newCheckout(cart) : oldCheckout(cart);
}
```

Two things to notice. First, `false` is the **default value** — if the flag service is down or the flag doesn't exist, you get `false` and the old, safe path runs. Always make the default the *safe* choice. Second, `targetingKey: user.id` tells the system *who* is asking, so the answer can differ per user. That's what powers gradual rollouts.

**In Java, the shape is the same:**

```java
Client client = OpenFeatureAPI.getInstance().getClient();
boolean useNew = client.getBooleanValue("new-checkout", false,
    new MutableContext(user.getId()));
return useNew ? newCheckout(cart) : oldCheckout(cart);
```

The pattern never changes: *ask the SDK, supply a safe default, branch on the answer.*

---

## Core Concept 3 — Where the Flag Value Comes From

When you call `getBooleanValue`, where does the answer live? Three common setups:

1. **A config file or env var.** Simplest. Value is baked at deploy or restart. No live control.
2. **A flag service the SDK talks to.** A managed product (LaunchDarkly, Split, Flagsmith) or a self-hosted one (Unleash). You flip values in a web dashboard; the SDK picks up the change in seconds. This is the common professional setup.
3. **A streamed/cached value.** The SDK keeps a local copy of all flag values and refreshes it (by streaming updates or polling every few seconds). Evaluation is then a fast in-memory lookup — no network call per request.

Why the local cache matters: you do *not* want to make a network call to a flag vendor on every single request. If you did, the flag service becoming slow or unreachable would make *your* service slow or unreachable. Instead the SDK fetches the ruleset once, keeps it in memory, evaluates locally, and falls back to your default if it ever has nothing.

> **The golden rule:** if the flag system disappears, your app must still work. That's why every flag read takes a default, and the default is the safe path.

---

## Core Concept 4 — Turning It On for a Few People First

The whole point of a per-user flag is that you don't have to go from 0% to 100% in one step. You can release *gradually*. This is **progressive delivery**.

The gentlest version is a **percentage rollout**: turn the flag on for 1% of users, watch your dashboards, then 5%, 25%, 100%. If something breaks at 5%, only 5% of users were affected and you flip back to 0% instantly.

A close cousin is **targeting by attribute** — turn it on for specific groups before everyone:

```yaml
# A targeting rule, vendor-neutral shape.
flag: new-checkout
default: false           # everyone else: off
rules:
  - if: user.email endsWith "@ourcompany.com"
    then: true           # internal staff see it first (dogfooding)
  - if: user.country == "NZ"
    then: true           # small market first
  - rollout:
      percentage: 5      # then 5% of remaining users
      then: true
```

This is the **ring model** in miniature: internal users → a small friendly cohort → a small percentage → everyone. Each ring is a chance to catch a problem before it reaches the next, larger group. The infrastructure-level version of the same idea is a **canary deploy**, where a small slice of *traffic* (not users) goes to the new version first.

---

## Core Concept 5 — Cleaning Up After Yourself

Here is the discipline that separates a flag from a liability. A flag you added to roll out "new-checkout" has a job: get the feature safely to 100%. Once it's at 100% and stable, **the flag's job is over and it should be deleted**, along with the old code path.

Why this matters even at junior level:

- Every flag left in the code is a fork in the road. Two flags = four possible combinations. Ten flags = 1,024. Nobody tests all of them, so untested combinations become bugs waiting to happen.
- Old code paths behind dead flags rot — they don't get updated, and one day someone flips the wrong stale flag and runs ancient code in production. (The most famous version of this disaster is later in this topic.)

A simple habit: when you add a release flag, add a reminder to remove it. Treat the cleanup as part of the feature, not optional homework.

```go
// Good: a comment that dates the flag so it gets noticed and removed.
// FLAG new-checkout — release toggle, added 2026-06-22, REMOVE after 100% rollout.
if flags.Enabled("new-checkout", user) {
    return newCheckout(cart)
}
return oldCheckout(cart)
```

---

## Core Concept 6 — The Four Kinds of Flag (a First Look)

So far we've talked about flags as if they're all the same. They're not. The word "flag" covers several tools that share a mechanism but serve different purposes. You'll meet all four in detail at the next tier; for now, just learn to recognize them, because they behave very differently.

| Kind | What it's for | How long it lives | Example |
|---|---|---|---|
| **Release toggle** | Hide unfinished work until it's ready | Short — deleted after the feature is fully on | The off-by-default `new-checkout` flag |
| **Kill-switch** (ops toggle) | Turn off a whole subsystem in an emergency | Long — kept around for years as a safety brake | `disable-recommendations` when the service overloads |
| **Experiment** | Show different versions to measure which is better | A few weeks, for one experiment | Green vs blue "Buy" button |
| **Permission** (entitlement) | Give a feature only to certain plans/accounts | Permanent — it's really business rules | "Pro plan gets CSV export" |

The single most useful habit: **before you create a flag, decide which kind it is.** If it's a release toggle, you already know its fate — it gets deleted once the feature reaches everyone. If it's a kill-switch, you know to *keep* it. Mislabeling them is how teams end up unable to tell which flags are safe to remove.

```go
// Same mechanism, very different intent — name the kind in the flag itself.
flags.Enabled("checkout.release.new-flow", user)     // release: will be deleted
flags.Enabled("search.ops.kill-switch", user)        // kill-switch: kept forever
```

A release toggle is a loan you pay back by deleting it. A kill-switch is a tool you keep in the drawer. An experiment is a measuring tape. A permission flag is part of your product's rules. Knowing which one you're holding tells you everything about how to treat it.

---

## Real-World Examples

- **Shipping a redesign quietly.** A team rebuilds the settings page over three weeks, merging daily behind an `off` flag. The new page is in production the whole time but invisible. On launch day they flip it to 100% — no scramble, no big-bang deploy.
- **Dogfooding.** A flag targets `@ourcompany.com` emails so employees use the new feature for a week before customers. Real usage surfaces bugs that staging never did.
- **The 2am save.** A new pricing calculation ships and starts producing wrong totals. On-call flips the `new-pricing` flag off from their phone. Fixed in 30 seconds — no deploy, no rollback, no waking the whole team.
- **The 1% experiment.** Marketing wants to know if a green "Buy" button outsells blue. A flag shows green to 50% of users; the data decides. (This is an *experiment* flag — more on the different kinds at the next tier.)

---

## Common Mistakes

- **Default to the *new* path.** If the flag service is unreachable and your default is `true`, an outage in the flag system silently force-enables an unfinished feature. Default to the safe, old path.
- **Calling the flag service on every request.** Without local caching, the vendor's latency becomes your latency. Use the SDK's cached evaluation.
- **Treating env-var flags as flippable.** A flag read from `os.Getenv` only changes on restart — you lose the instant-off benefit. Fine for tiny projects; not a real progressive-delivery flag.
- **Forgetting the flag exists.** The feature reaches 100%, everyone moves on, and the flag (plus dead `oldCheckout`) lives forever. Set a removal reminder when you add it.
- **No targeting key.** Without passing the user id, you can't do percentage or per-user rollouts — every user gets the same answer, so "gradual" is impossible.

---

## Apply it

1. Choose one small, known input for **Feature Flags & Progressive Delivery**.
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

- What problem does Feature Flags & Progressive Delivery solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
