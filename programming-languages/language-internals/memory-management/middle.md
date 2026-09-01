# Memory Management — Middle

Reference counting reclaims promptly but needs cycle handling. Tracing collectors mark from roots and reclaim the rest; generational collectors optimize for short-lived objects. Allocators use arenas, size classes, and caches. Escape analysis may remove heap allocations.

Measure allocation rate, live set, pause distribution, and RSS separately.

## Test yourself

1. Why do cycles defeat plain refcounts?
2. What is the generational hypothesis?
3. Why can RSS exceed managed heap?

Continue to [`senior.md`](senior.md).
