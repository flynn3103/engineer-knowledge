# Caching

> Covers Cache Aside, Cache Invalidation, Cache Stampede and Hot Keys, Eviction Policies, Refresh Ahead, Types of Caching, Write Behind, and Write Through.

## Topics

| Topic | What it covers |
|---|---|
| [Cache Aside](cache-aside/) | The application checks the cache first; on a miss, it reads the database itself and populates the cache. The most common caching pattern… |
| [Cache Invalidation](cache-invalidation/) | "There are only two hard things in Computer Science: cache invalidation and naming things." Deciding *when* a cached value is no longer… |
| [Cache Stampede and Hot Keys](cache-stampede-and-hot-keys/) | When a popular cache key expires, every one of its thousands of concurrent readers can simultaneously fall through to the database at once… |
| [Eviction Policies](eviction-policies/) | A cache is finite; the data you'd like to cache usually isn't. Eviction policies decide what gets thrown out when the cache is full — and… |
| [Refresh Ahead](refresh-ahead/) | Instead of waiting for a key to expire and forcing the next reader to eat a cache miss, proactively refresh hot keys shortly before their… |
| [Types of Caching](types-of-caching/) | The same cache-aside/write-through logic can live in wildly different places — inside a single process, in a shared cluster, in front of a… |
| [Write Behind](write-behind/) | Write to the cache immediately and acknowledge the caller — then flush to the durable store asynchronously, in batches. Maximizes write… |
| [Write Through](write-through/) | Every write goes to the cache and the database together, synchronously, so the cache is never stale for data written this way — at the cost… |
