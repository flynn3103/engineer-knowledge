# Data Representation and Numerics — Professional

IEEE 754 defines rounding modes, subnormals, signed zero, infinities, and NaNs; reproducibility depends on operation order and hardware/compiler rules. Apache Arrow uses typed columnar buffers and validity bitmaps for cache-friendly cross-language interchange. NaN-boxing encodes tags and payloads inside unused NaN patterns in dynamic runtimes. Protobuf fixes wire types but still requires field-number discipline.

Monitor conversion failures, overflow counters, corrupt payloads, and numerical drift. Further reading: IEEE 754, Unicode Standard Annexes, Arrow format specification, and Protobuf encoding guide.
