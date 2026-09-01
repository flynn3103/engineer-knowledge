# Evaluation and Execution Models — Professional

CPython’s bytecode evaluator, HotSpot tiered compilation, V8 Ignition/TurboFan, and GHC’s graph-reduction runtime demonstrate different cost placement. HotSpot and V8 speculate then deoptimize; GHC evaluates thunks and must control space leaks; async runtimes such as Tokio and asyncio schedule resumable state machines.

Operational reviews require startup, warmup, code cache, deoptimization, scheduler latency, and retained-thunk evidence. Further reading: runtime source trees, Peyton Jones on STG, and JVM/V8 compilation documentation.
