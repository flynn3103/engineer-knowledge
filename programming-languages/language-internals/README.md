# Language Internals

> Predict what code becomes, how values are represented, which runtime owns execution, and where cross-language contracts can fail.

Do not read this track as an encyclopedia. Start with a question from a real program, run a small experiment, and stop when the evidence explains the behavior.

## Learning path

| Stage | Section | Question it helps answer |
|---|---|---|
| 1 | [Evaluation and Execution Models](evaluation-and-execution-models/README.md) | When and in what order does work happen? |
| 2 | [Type Systems](type-systems/README.md) | Which states and operations can the program express? |
| 3 | [Data Representation and Numerics](data-representation-and-numerics/README.md) | How do values become bits, and where is information lost? |
| 4 | [Memory Management](memory-management/README.md) | Who allocates, owns, retains, and releases memory? |
| 5 | [Compilers and Interpreters](compilers-and-interpreters/README.md) | How does source become executable behavior? |
| 6 | [Runtime Systems](runtime-systems/README.md) | Which services does the runtime provide while code executes? |
| 7 | [Metaprogramming](metaprogramming/README.md) | When should programs inspect or generate programs? |
| 8 | [Foreign Functions and Interoperability](foreign-function-interface-and-interop/README.md) | Which ABI, ownership, and representation rules cross languages? |
| 9 | [Language Security Internals](language-security-internals/README.md) | Which mechanisms prevent memory and control-flow abuse? |
| 10 | [Choosing a Language](choosing-a-language/README.md) | Which evidence justifies adoption, migration, or rejection? |

## Investigation loop

1. Reduce the behavior to the smallest program that still reproduces it.
2. Predict evaluation order, types, representation, allocation, and output.
3. Inspect compiler output, runtime traces, memory profiles, or generated code.
4. Change one language feature or runtime condition.
5. Explain both results with one bounded rule.

If the rule cannot predict a second case, it is still a story—not yet a useful mental model.

Part of the [Programming Languages](../README.md) roadmap.
