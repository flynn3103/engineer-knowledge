# Compilers and Interpreters — Middle

Front ends produce a typed or validated representation. Lowering converts rich constructs into simpler IR operations. Control-flow graphs expose branches; SSA gives each value one definition, enabling constant propagation, dead-code elimination, and data-flow analysis.

Walk one function from AST to IR, then compare optimized output. Optimization is constrained by exceptions, overflow, aliasing, and observable side effects.

## Test yourself

1. Why use several IR levels?
2. What makes dead-code removal unsafe?
3. How does SSA help analysis?

Continue to [`senior.md`](senior.md).
