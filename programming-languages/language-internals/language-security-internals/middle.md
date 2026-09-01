# Language Security Internals — Middle

ASLR randomizes locations; DEP/NX blocks execution from data pages; stack canaries detect some overwrites; control-flow integrity limits indirect branches. Sandboxes restrict syscalls and resources. Capability designs grant explicit authority instead of ambient access.

## Test yourself

1. Why is ASLR insufficient alone?
2. What does CFI protect?
3. How does capability security reduce authority?

Continue to [`senior.md`](senior.md).
