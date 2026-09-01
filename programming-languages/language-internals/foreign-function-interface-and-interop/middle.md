# FFI and Interoperability — Middle

Use C-compatible layouts only where promised. Pin or copy objects when a moving collector could relocate them. Translate error codes at the boundary, and specify whether callbacks may arrive on foreign threads. Batch work to amortize crossing and marshalling costs.

## Test yourself

1. When must memory be pinned?
2. Why are coarse FFI calls preferable?
3. How do callbacks affect thread safety?

Continue to [`senior.md`](senior.md).
