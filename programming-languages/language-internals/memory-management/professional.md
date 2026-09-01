# Memory Management — Professional

CPython combines refcounting, cyclic GC, and `pymalloc` arenas. HotSpot G1 partitions heaps into regions and balances evacuation work against pause goals; ZGC uses colored pointers and concurrent relocation. Go’s concurrent mark-sweep collector controls CPU/heap trade-offs through pacing and memory limits. jemalloc exposes arenas and fragmentation statistics beneath native services.

Operate allocation bytes/op, live set, pause tails, promotion, fragmentation, native memory, and OOM events. Further reading: *Garbage Collection Handbook*, OpenJDK GC docs, Go GC guide, CPython `obmalloc.c`, and jemalloc internals.
