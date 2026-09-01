# Object-Oriented Design — Middle

High cohesion keeps related behavior together; low coupling limits knowledge between collaborators. Connascence asks what must change together and how strongly. Keep strong forms local and prefer weaker forms across boundaries.

Use SOLID diagnostically:

- SRP: one coherent reason to change;
- OCP: stable variation points, not speculative extension;
- LSP: substitutions preserve caller expectations;
- ISP: consumers depend on focused capabilities;
- DIP: policy does not depend directly on volatile detail.

Apply tell-don’t-ask, command-query separation, and the Law of Demeter to reduce navigation and external decision logic. Watch for feature envy, primitive obsession, data clumps, god classes, and shotgun surgery.

## Test yourself

1. Which change reason reveals low cohesion?
2. How can an implementation violate LSP?
3. Where should an interface be owned?
4. What navigation chain reveals missing responsibility?

Continue to [`senior.md`](senior.md).
