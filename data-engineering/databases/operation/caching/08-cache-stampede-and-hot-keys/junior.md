# Cache Stampede & Hot Keys — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Why is a hot key's expiry uniquely dangerous, when a cold key's expiry is a
> non-event?

---

## Not all cache misses are equal

A cold key (requested rarely) expiring is harmless: the next, single request
for it pays one cache-miss database round trip, exactly as designed in
[Cache-Aside](../01-cache-aside/README.md). A **hot key** — one being read by
thousands of concurrent requests per second, like a homepage's "trending
now" list or a viral post's like count — behaves completely differently when
it expires.

```mermaid
sequenceDiagram
    participant R1 as Reader 1
    participant R2 as Reader 2
    participant R3 as Reader 3
    participant Cache
    participant DB
    Note over Cache: Hot key expires at t=0
    R1->>Cache: GET key (t=0.001)
    Cache-->>R1: MISS
    R2->>Cache: GET key (t=0.001)
    Cache-->>R2: MISS
    R3->>Cache: GET key (t=0.001)
    Cache-->>R3: MISS
    Note over R1,R3: All three (of thousands) independently\ndecide to query the database
    R1->>DB: expensive query
    R2->>DB: SAME expensive query
    R3->>DB: SAME expensive query
    Note over DB: Thousands of IDENTICAL queries\nhit the database in the same instant
```

Every one of the key's concurrent readers gets a miss at the same instant,
and — following the standard cache-aside pattern from `junior.md` of that
topic — every single one of them independently queries the database and
tries to repopulate the cache. This is called a **cache stampede**, **dogpile
effect**, or **thundering herd**: one expired key turns into thousands of
simultaneous, completely redundant database queries, which can overwhelm a
database that was otherwise comfortably handling load.

> 🎓 **Takeaway:** the danger of a stampede scales with how popular the key
> is, not with how expensive the query behind it is (though an expensive
> query makes it worse). A cheap query run 10,000 times simultaneously is
> still 10,000x the load the cache was supposed to be absorbing.

## Test yourself

1. Why doesn't a cold key (read once every few minutes) ever cause a
   stampede, even with the exact same cache-aside code?
2. If a stampede happens, what's the difference between "the database is
   slow because of the stampede" and "the database is slow because the query
   itself is slow"?
3. Estimate the database load multiplier for a key normally read once per
   TTL cycle by 5,000 concurrent users, if it stampedes on every expiry.

Continue to [`middle.md`](middle.md).
