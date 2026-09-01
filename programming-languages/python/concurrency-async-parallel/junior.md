# Python Concurrency — Junior

Concurrency helps a program wait for more than one thing; it does not automatically make code faster.

- Use plain synchronous code first.
- Use `async def` only with `await`-compatible I/O.
- Never call blocking I/O or CPU-heavy work directly inside an async handler.
- Protect shared mutable state and keep tasks small.

Use timeouts and tests that prove cancellation and failure behavior.
