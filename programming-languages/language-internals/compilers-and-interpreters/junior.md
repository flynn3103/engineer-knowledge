# Compilers and Interpreters — Junior

Lexing groups characters into tokens; parsing builds structure; semantic analysis resolves names and types. An interpreter may walk the AST or execute bytecode. A compiler may emit bytecode, native code, or another language.

The naive model “compiled versus interpreted” breaks for CPython, Java, and JavaScript because each compiles to an intermediate form before a VM executes or further compiles it.

## Test yourself

1. Is missing `)` a syntax or semantic error?
2. What information does an AST omit?
3. Why is bytecode useful?

Continue to [`middle.md`](middle.md).
