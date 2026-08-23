# Interfaces — Interview Prep

> **Topic:** [Interfaces](../README.md)

---

## Conceptual / Foundational

**Q: How does Go decide if a type satisfies an interface?**
A: Structurally and implicitly — if the type (or its pointer) has all the methods in the interface's method set, it satisfies it automatically. No explicit `implements` declaration.

**Q: What is the empty interface, and when would you use it?**
A: `interface{}` (alias `any`) has zero methods, so every type satisfies it. Used when a function genuinely must accept any type (e.g. `fmt.Println`), typically requiring a type assertion or type switch to do anything type-specific afterward. Since Go 1.18, generics are often a better-typed alternative.

**Q: Why does a `nil` pointer stored in an interface not equal `nil`?**
A: An interface value is `nil` only when both its dynamic type and value are nil. A typed `nil` pointer (`var p *T = nil` assigned to an interface) has a non-nil *type* component, so `iface == nil` is false even though the underlying pointer is nil.

## Tricky / Trap Questions

**Q: A struct has a method with a pointer receiver. Does the value type satisfy an interface requiring that method?**
A: No — only `*T` is in the method set for a pointer-receiver method; `T` (the value) is not, unless the value is addressable and Go can take its address automatically (which it can for a local addressable variable calling the method directly, but not for interface satisfaction).

**Q: What's the difference between `v, ok := x.(T)` and `v := x.(T)`?**
A: The two-value form never panics; `ok` is `false` on a failed assertion. The single-value form panics if `x`'s dynamic type isn't `T`.

**Q: When should you use generics instead of an interface?**
A: When the function needs the *same concrete type* in and out (e.g. `Max[T Ordered](a, b T) T`), or needs type-specific operations (`+`, `<`) that an interface's dynamic dispatch can't express type-safely. Interfaces are for describing behavior across genuinely different concrete types; generics are for one algorithm parameterized over a type.

## System / Design Scenarios

**Q: You need to add a `SetWithTTL` capability to a `Store` interface implemented by a dozen services. How do you avoid breaking everyone?**
A: Don't add the method to `Store`. Create a new `TTLStore` interface that embeds `Store` and adds the method; only the one consumer that needs TTL support has to implement the wider interface.

**Q: Design a testable component that depends on the current time.**
A: Wrap `time.Now()` behind a one-method `Clock` interface; inject a `realClock` in production and a `fixedClock` in tests, making time-dependent logic deterministic to test.

## Behavioral / Experience

**Q: Tell me about an interface you designed that had to evolve. What would you do differently?**
A: (Tailor to experience — strong answers describe recognizing a breaking-change risk and choosing to add a new interface rather than widen an existing one, or recognizing an interface was defined too early with no real second implementation.)

---

## Cheat Sheet

```
Implicit satisfaction  → no "implements" keyword; structural typing
Pointer vs value method set → pointer-receiver methods only in *T's method set
Empty interface (any)  → accepts anything, loses static type info
Type assertion (safe)  → v, ok := x.(T)
Nil interface gotcha   → typed nil pointer in an interface != nil interface
Generics vs interfaces → same type in/out => generics; behavior across types => interfaces
```

---

## Related Topics

- [Junior](junior.md) · [Middle](middle.md) · [Senior](senior.md) · [Professional](professional.md) · [Tasks](tasks.md)
