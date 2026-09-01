# Runtime Systems — Middle

Dispatch may be direct, virtual-table based, interface-table based, or dynamically cached. Loaders resolve symbols and initialize modules. JITs profile call sites, inline stable targets, and retain metadata for deoptimization. GC coordinates with stacks and safepoints to find roots.

## Test yourself

1. What makes an inline cache monomorphic?
2. Why must GC understand stack maps?
3. Which side effects make module initialization risky?

Continue to [`senior.md`](senior.md).
