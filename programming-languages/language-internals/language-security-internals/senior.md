# Language Security Internals — Senior

Design defense in depth across compiler hardening, runtime checks, process isolation, syscall policy, dependency integrity, and incident detection. Side channels cross ordinary permission boundaries through timing, caches, and speculative execution, so sensitive code needs data-independent behavior and measured mitigations.

Inventory every native and unsafe boundary. Define the blast radius if it fails, apply least privilege, and make security-relevant runtime events observable.

## Test yourself

1. Which isolation layer contains native memory corruption?
2. What trust boundary does a Spectre-style attack cross?
3. How would you measure the cost and effectiveness of a mitigation?

Continue to [`professional.md`](professional.md).
