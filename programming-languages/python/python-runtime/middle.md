# Python Runtime — Middle

Write with CPython’s practical behavior in mind, while keeping correctness independent of implementation details.

- Names reference objects; assignment usually does not copy.
- Prefer iterators and generators for large streams.
- Understand shallow versus deep copies before mutating nested data.
- Use `with` for files, locks, and resources.
- Measure memory or CPU with a profiler; do not infer it from syntax.

Use `tracemalloc` for allocation investigations and `cProfile` for CPU hotspots. Optimize only after a representative measurement.
