# Interfaces — Hands-On Tasks

> **Topic:** [Interfaces](../README.md)

---

## Warm-Up

1. Define a small `Shape` interface with an `Area() float64` method; implement it for `Circle` and `Rectangle` without either type mentioning `Shape` explicitly. Write a function that takes a `[]Shape` and returns the total area.
2. Reproduce the nil-interface gotcha: write a function returning a typed `nil` pointer as an `error`, and show `err == nil` is `false`. Fix it to return literal `nil`.
3. Write a function using a type switch to handle `string`, `int`, and a custom struct differently, with a `default` case.

## Core

4. Define a `Notifier` interface with a `Notify(msg string) error` method. Write a `Service` that depends on `Notifier` via constructor injection, and a hand-written fake `Notifier` (no mocking library) for a test that verifies `Service` calls `Notify` with the expected message.
5. Build a `Clock` interface wrapping `time.Now()`. Write a function that checks whether a token has expired, injecting a `fixedClock` in a test to deterministically test both the "expired" and "not expired" branches.
6. Compose two small interfaces (`Reader` and `Closer`, your own definitions) into a `ReadCloser` via embedding, and implement a type that satisfies the composed interface.

## Advanced

7. Write a generic `Filter[T any](items []T, pred func(T) bool) []T` function, then write a second generic `Sum[T Number](items []T) T` with a numeric constraint. Explain in writing why `Sum` needs a constraint but `Filter` doesn't.
8. Take an interface with 6+ methods (invent one, e.g. a "God" `Repository` interface) used by two different consumers that each only call 2 methods. Refactor into two narrow, per-consumer interfaces, and show both are satisfied by the same concrete implementation simultaneously.
9. Simulate the "can't add a method to a shared interface" scenario: define a `Store` interface with two independent fake implementations (pretend they're two teams' services). Add a new capability via a new `TTLStore` interface embedding `Store`, and show the original two implementations remain unaffected.

## Capstone

10. Design and implement a small plugin-style system: a `Plugin` interface with `Name() string` and `Run(ctx context.Context, input string) (string, error)`, a registry that accepts any number of `Plugin` implementations, and at least 3 different concrete plugins. Write a test using a hand-written fake plugin that returns a controllable error, verifying the registry handles a failing plugin without affecting the others.

## If you can do all of these, you have the middle level

You can design consumer-driven interfaces, use dependency injection with hand-written fakes instead of a mocking framework, choose correctly between generics and interfaces, and avoid the nil-interface and pointer-receiver method-set traps.

---

## Related Topics

- [Junior](junior.md) · [Middle](middle.md) · [Senior](senior.md) · [Professional](professional.md) · [Interview](interview.md)
