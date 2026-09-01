# Data Representation and Numerics — Senior

Representation failures become data corruption: schema evolution changes widths, NaN breaks ordering, decimal scales drift, or native structs cross an ABI with different padding. Use versioned schemas, canonical encodings, range validation, checksums, and compatibility fixtures.

Measure cache locality and vectorization before adopting packed or columnar layouts; misalignment and conversion may erase gains.

## Test yourself

1. How does NaN affect sorting?
2. Why is dumping a native struct unsafe as a wire format?
3. How do you migrate decimal scale?

Continue to [`professional.md`](professional.md).
