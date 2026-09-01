# FFI and Interoperability — Junior

An ABI defines calling convention, symbol names, register use, alignment, and data layout. FFI code must also define who owns memory and how errors cross the boundary. Prefer integers, byte buffers, and explicit lengths over runtime-specific objects.

## Test yourself

1. Who frees a returned buffer?
2. Why can struct padding differ?
3. Can an exception safely cross C code?

Continue to [`middle.md`](middle.md).
