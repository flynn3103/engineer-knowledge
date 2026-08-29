# Off-heap / Native Memory — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Off-heap / Native Memory** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### Two worlds of memory

Picture your process's memory split into two territories:

```
+-------------------------------------------------------+
|                  Your process (one OS process)        |
|                                                       |
|   +------------------+        +--------------------+  |
|   |  MANAGED HEAP    |        |  OFF-HEAP / NATIVE |  |
|   |  (GC owns this)  |        |  (you own this)    |  |
|   |                  |        |                    |  |
|   |  objects, arrays |        |  malloc/mmap blocks|  |
|   |  GC scans + frees|        |  GC ignores it     |  |
|   |  capped by -Xmx  |        |  you must free it  |  |
|   +------------------+        +--------------------+  |
|                                                       |
|   Both count toward RSS (what the OS sees you using)  |
+-------------------------------------------------------+
```

Both regions live inside the *same* process and both consume real RAM. The difference is **who is responsible for them**.

### Why leave the managed heap at all?

A garbage collector is wonderful, but it is not free. Three foundational reasons push data off-heap:

1. **GC pressure.** Every object on the managed heap is something the GC must eventually look at. A 10 GB in-memory cache means 10 GB the GC has to scan and reason about, which lengthens pauses. Move that cache off-heap and the GC sees almost nothing — the cache is invisible to it. This is the single biggest motivator for JVM off-heap caches.

2. **Talking to the outside world.** When you do file I/O, network I/O, or call into a C library, the OS and native code want a stable block of memory at a fixed address. The GC likes to *move* objects around. Off-heap memory never moves, so it is safe to hand to the OS.

3. **Precise control.** Sometimes you want to free memory *the instant* you are done with it, not "eventually, whenever the GC gets around to it." Off-heap gives you that exact control — at the cost of having to remember to do it.

### The fundamental trade

> **The GC will not free what it cannot see. Off-heap memory is invisible to the GC. Therefore off-heap memory must be freed by you.**

This one sentence is the source of nearly every off-heap bug, every "my Java process is using 8 GB but the heap is only 2 GB" incident, and every container that gets killed by the kernel for reasons the application logs never explain.

---

## Code Examples

### Managed heap (the familiar world) — Java

```java
// Lives on the GC heap. You never free it.
byte[] data = new byte[1024];
data[0] = 42;
// When `data` becomes unreachable, the GC reclaims it. Done.
```

### Off-heap (the new world) — Java DirectByteBuffer

```java
import java.nio.ByteBuffer;

// allocateDirect asks the OS for native memory, NOT the GC heap.
ByteBuffer buf = ByteBuffer.allocateDirect(1024); // 1 KB off-heap
buf.put(0, (byte) 42);
byte b = buf.get(0); // read it back like an array

// These 1024 bytes do NOT count against -Xmx.
// They DO count against RSS — the OS sees them.
// They are freed only when `buf` (a tiny wrapper object) is GC'd. (More on
// why that is a problem at higher tiers.)
```

The key idea for a junior: `new byte[1024]` and `ByteBuffer.allocateDirect(1024)` both give you 1 KB to use, but they live in different worlds with different rules.

### Off-heap — Go (asking the OS directly via mmap)

```go
package main

import (
	"fmt"
	"syscall"
)

func main() {
	// mmap asks the OS for a 4 KB region OUTSIDE the Go GC heap.
	mem, err := syscall.Mmap(-1, 0, 4096,
		syscall.PROT_READ|syscall.PROT_WRITE,
		syscall.MAP_ANON|syscall.MAP_PRIVATE)
	if err != nil {
		panic(err)
	}

	mem[0] = 42 // use it like a normal byte slice
	fmt.Println(mem[0])

	// The Go GC does NOT manage this. We must hand it back ourselves:
	if err := syscall.Munmap(mem); err != nil {
		panic(err)
	}
}
```

Notice the explicit `Munmap`. In normal Go you never free anything; here you must.

---

## Best Practices

- **Default to the managed heap.** Off-heap is a specialized tool. Most code should never touch it. Use it when you have evidence (GC pauses, interop needs, sizes too big to manage on-heap).
- **Always pair an allocation with a free.** The instant you write an off-heap allocation, write its release. Treat them like opening and closing a bracket.
- **Prefer high-level wrappers.** Use `DirectByteBuffer`, a library's pooled buffers, or modern safe APIs rather than raw pointer arithmetic. They make the "must free" obligation harder to forget.
- **Know your two numbers.** Get used to checking both the heap size *and* the process RSS. When they diverge, off-heap is usually involved.

---

## Edge Cases & Pitfalls

- **"The heap looks fine but the process keeps growing."** Classic off-heap leak. The heap dump is clean because the leak is in territory the dump never inspects.
- **Freeing twice ("double free").** Releasing the same off-heap block twice is a corruption bug, not a no-op. Free exactly once.
- **Use-after-free.** Reading off-heap memory after you freed it gives garbage or crashes the process. There is no GC keeping it alive for you.
- **Assuming `-Xmx` protects you.** It only caps the managed heap. The OS can still run the process out of physical memory through off-heap growth, and on a container the *kernel* kills the process (OOM-kill) with no graceful error.

---

## Apply it

1. Choose one small, known input for **Off-heap / Native Memory**.
2. Predict the output or observable behavior.
3. Run the smallest example or probe that exercises the concept.
4. Change one input to trigger a failure or boundary case.
5. Explain the evidence using the guide's vocabulary.

## Verify your work

- Record the exact input, command or code path, and output.
- Repeat the probe and confirm the result is consistent.
- Show one expected success and one expected failure.
- Resolve any difference between the prediction and the evidence.

## Review questions

- What problem does Off-heap / Native Memory solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
