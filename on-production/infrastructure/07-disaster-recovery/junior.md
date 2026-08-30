# Disaster Recovery — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Given a backup schedule and a restore procedure, what is your actual RPO and RTO, and how do you prove those numbers by actually restoring?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Infrastructure](../README.md) → Disaster Recovery

*A backup file sitting in cloud storage is a hypothesis, not a safety net. This level is about stating two numbers — how much data you could lose, and how long you'd be down — and proving both with an actual restore, not a checkbox on a runbook nobody has run.*

---

## Core Concept 1 — Vocabulary: RPO, RTO, and the standby tiers

| Term | Plain-English meaning |
|---|---|
| **Disaster recovery (DR)** | The plan and mechanics for restoring service after a large-scale failure — losing a database, an availability zone, or an entire region — as distinct from day-to-day fault tolerance for a single instance dying. |
| **RPO (Recovery Point Objective)** | How much data you can afford to lose, measured in time: "at most 1 hour of writes." Set by how often you back up or replicate, and whether that backup actually succeeds. |
| **RTO (Recovery Time Objective)** | How long you can afford to be down, measured in time: "at most 4 hours from disaster to restored service." Set by how fast a restore can actually be executed, not how fast it's assumed to be. |
| **Backup** | A point-in-time copy of data, stored somewhere independent of the system that produced it. |
| **Restore** | The act of turning a backup back into a running, serving system — the part that is actually hard, and the part most teams skip practicing. |
| **DR drill / failover test** | A deliberate, scheduled exercise of the restore or failover procedure, used to prove RPO/RTO are real measured numbers instead of numbers someone wrote down once. |

The principle to internalize at this level: **untested backups are not backups.** A backup job exiting with status 0 tells you a file was written somewhere. It tells you nothing about whether that file can be restored, whether the restored data is complete, or whether the application can actually start against it. Only an actual restore answers those questions.

---

## Core Concept 2 — The method, step by step

1. **State target RPO and RTO in writing, before choosing any tooling.** Base them on business impact: "losing more than 1 hour of order data is unacceptable" and "more than 4 hours of checkout downtime is unacceptable" are decisions, not technical facts — make them explicit.
2. **Automate a backup schedule whose frequency matches the RPO target.** If RPO is 1 hour, a nightly backup cannot meet it no matter how reliable it is.
3. **Store the backup somewhere independent of the primary** — a different region, a different account, or both — so the same disaster that destroys the primary doesn't also destroy the only copy of the backup.
4. **Write the restore procedure as literal, runnable commands**, not a paragraph of prose describing the general idea. A restore performed under pressure follows a script; it does not improvise.
5. **Run the restore procedure end to end, on a schedule, and time it.** The number you get from actually restoring is your real RTO — not the number written in step 1.

---

## Core Concept 3 — Worked example: nightly backup of a small Postgres database

**Scenario:** `orders`, a Postgres database backing a small e-commerce app, runs as a single primary instance with no replica. The team sets up a nightly logical backup to object storage.

```bash
# /etc/cron.d/orders-backup — runs nightly at 02:00 UTC
0 2 * * * postgres pg_dump -Fc orders \
  | aws s3 cp - s3://acme-db-backups/orders/orders-$(date +\%Y\%m\%d).dump
```

**Calculating RPO from backup frequency.** The backup runs once every 24 hours, at 02:00 UTC. If the primary fails at 01:50 — just before the next backup would have run — the newest usable backup is already just over 24 hours old. So the **worst-case RPO of this setup is approximately 24 hours**, regardless of what anyone intended. If the business need is "lose at most 1 hour of order data," nightly `pg_dump` does not meet that target; it would need hourly backups, or continuous WAL archiving/streaming replication, to close the gap.

**Running the restore drill.** The team schedules a quarterly restore-to-a-fresh-instance drill and times it:

| Step | Action | Elapsed |
|---|---|---|
| T+0:00 | Primary declared lost; restore begins | 0:00 |
| T+0:05 | Fresh database instance provisioned | 0:05 |
| T+0:07 | Latest dump downloaded from object storage | 0:09 |
| T+0:09 | `pg_restore` into the fresh instance | 0:38 |
| T+0:38 | App config repointed at new DB, app restarted | 0:44 |
| T+0:44 | Smoke test: place a test order, confirm it reads back | 0:52 |

The **measured RTO is 52 minutes** — a number derived from a stopwatch and a timestamped log, not an estimate. That is the deliverable of the drill: a real RPO number (from the backup schedule) and a real RTO number (from the restore), both compared against the stated targets.

---

## Core Concept 4 — Simple success criteria

**The setup succeeds if:**

- Backups run on an automated schedule, confirmed by a log or dashboard entry — not assumed because a cron entry exists.
- The backup is stored somewhere independent of the primary (different region or account), so one disaster can't take out both.
- A restore drill has actually been performed within the last defined period, with a timed, written result.
- The measured RTO is at or below the target RTO; if the backup frequency can't support the target RPO, that gap is written down, not quietly ignored.

**It fails if:** the backup has never been restored, the backup lives next to the primary, the "restore procedure" exists only as tribal knowledge, or nobody can currently state the last time a restore was tested.

At this level, don't confuse a disaster-recovery backup with a routine operational backup. A nightly snapshot kept for point-in-time recovery from an accidental `DROP TABLE` is useful, but it's a different guarantee from a DR backup, which specifically has to survive the loss of the entire environment it came from — the region, the account, or the data center. If your only "backup" lives in the same account as the primary, it protects against operator mistakes but not against the disaster this topic is actually about.

---

## Common Mistakes

1. **Backing up to the same region or account as the primary.** A regional outage or a compromised account can destroy both the source and the only copy of the backup at once.
2. **Never testing the restore.** A backup job that always exits successfully is not evidence the data can be turned back into a running system — only a real restore is.
3. **Confusing backup frequency with RPO.** RPO also depends on the backup actually succeeding and being valid; a corrupted or partial backup silently produces a worse RPO than the schedule implies.
4. **No written runbook.** If the restore procedure lives only in one engineer's memory, it isn't a procedure — it's a single point of failure on top of the disaster you're recovering from.
5. **Not verifying the restored data.** Restoring a backup and seeing the process exit cleanly is not the same as confirming the data is complete and the application actually works against it.

---

## Apply it

1. Pick one small stateful component — a database or a config store — in a project you control, ideally in a sandbox or staging environment.
2. Write one target RPO and one target RTO for it, in plain language, based on how bad it would be to lose an hour of its data versus a day.
3. Set up (or confirm) an automated backup whose frequency matches your RPO target, stored somewhere independent of the primary.
4. Write the restore procedure as literal runnable commands, then execute it fully: start a timer the moment you declare the primary "lost," stop it once you've verified the restored system works.
5. Compare the measured RTO against your target, and write one sentence on whether the current backup frequency actually supports the RPO target you set.

## Verify your work

- You have a written target RPO and a written target RTO, stated in units of time, decided before you began.
- The backup runs automatically and is stored somewhere independent of the primary source.
- You performed a full restore, timed with a stopwatch or timestamps, producing a real measured RTO.
- You checked the restored data for completeness and correctness — not just that the restore command exited without error.

## Review questions

- What is the difference between what RPO measures and what RTO measures?
- Why does storing a backup in the same region as its primary defeat the purpose of the backup?
- What is the only reliable way to know whether your stated RTO is real rather than assumed?
- If a database backs up once every 24 hours, what is the worst-case RPO, and at what moment would that worst case occur?
