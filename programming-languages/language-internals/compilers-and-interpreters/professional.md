# Compilers and Interpreters — Professional

LLVM lowers front-end IR into target-independent and target-specific passes; optimization remarks expose why transformations fired. HotSpot combines interpretation, C1, and C2 tiered compilation with profiling and deoptimization. V8 uses Ignition bytecode and TurboFan optimized code. CPython compiles AST to stack bytecode executed by its evaluation loop.

Operate compiler changes with build-time, startup, warmup, throughput, code-size, and crash-symbolization metrics. Runbooks need rollback and artifact provenance. Design reviews ask which semantics constrain optimization and how generated code is inspected.

Further reading: LLVM Language Reference, OpenJDK HotSpot sources, V8 Ignition/TurboFan docs, CPython `Python/compile.c` and `Python/bytecodes.c`.
