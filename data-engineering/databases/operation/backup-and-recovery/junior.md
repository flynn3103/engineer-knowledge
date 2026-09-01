# Backup & Recovery — Junior

<!-- level-focus -->
At junior level, focus on this question:

> What's the difference between a full and an incremental backup, and why not
> just take a full backup every time?

---

## Full backups

A **full backup** copies the entire database's data at a point in time — the
most complete, simplest thing to restore from (just load it back), but also
the slowest to take and the most storage-hungry, especially if you keep
several.

```mermaid
flowchart LR
    Sun["Sunday: full backup\n(500 GB)"]
    Mon["Monday: full backup\n(500 GB again)"]
    Tue["Tuesday: full backup\n(500 GB again)"]
    Sun --- Mon --- Tue
```

Taking a full backup every day means storing (and copying) the entire
dataset every single day — most of which hasn't changed since yesterday.

## Incremental backups

An **incremental backup** captures only what's **changed since the last
backup** (full or incremental), which is dramatically smaller and faster to
take for a large, slowly-changing dataset.

```mermaid
flowchart LR
    Full["Sunday: FULL backup\n(500 GB)"] --> Inc1["Monday: INCREMENTAL\n(only changes: 5 GB)"]
    Inc1 --> Inc2["Tuesday: INCREMENTAL\n(only changes: 4 GB)"]
```

The trade-off: **restoring** now requires the full backup plus every
incremental since it, applied in order — more steps, more places something
could go wrong, and typically a slower restore than a single full backup
would give you.

| | Full backup | Incremental backup |
|---|---|---|
| Backup time/storage | High, every time | Low, after the first full |
| Restore time | Fast — one file to load | Slower — full + chain of incrementals, applied in sequence |
| Failure surface | One backup to trust | Every incremental in the chain must be intact |

> 🎓 **Takeaway:** full backups are simple and safe to restore from but
> expensive to take repeatedly; incremental backups are cheap to take but
> require a longer, more fragile chain to restore. Most real systems combine
> both — a periodic full backup, with incrementals in between (this is
> `middle.md`'s subject, taken to its logical extreme with continuous logs).

## Test yourself

1. If Tuesday's incremental backup is corrupted, what happens to your ability
   to restore to Wednesday, even if Wednesday's own incremental is fine?
2. Why does an incremental backup strategy need at least one full backup to
   ever be useful?
3. For a database that changes very little day-to-day (mostly reference
   data), would full or incremental backups make more sense as the primary
   strategy? Why?

Continue to [`middle.md`](middle.md).
