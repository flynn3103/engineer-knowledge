# Data Representation and Numerics — Middle

Endianness controls byte order, while a protocol defines field order and width. Floating-point comparison needs a domain tolerance, not a universal epsilon. Unicode normalization can make visually identical strings contain different code points. Object layouts add headers, alignment, padding, and sometimes boxing.

Define serialization contracts explicitly and round-trip boundary fixtures across languages.

## Test yourself

1. Where should byte order be decided?
2. Why does normalization affect identifiers?
3. What cost does boxing add?

Continue to [`senior.md`](senior.md).
