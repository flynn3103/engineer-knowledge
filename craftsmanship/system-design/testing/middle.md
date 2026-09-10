# Testing — Middle

Use integration tests for database, queue, filesystem, and framework behavior. Use consumer-driven contracts for independently deployed services. Acceptance and BDD examples align business rules; end-to-end tests validate a few critical journeys, not every branch.

Property-based tests explore invariants across generated inputs. Mutation testing checks whether assertions notice meaningful code changes. Snapshot tests work for reviewed, stable output but become weak when updated blindly.

## Test yourself

1. Which boundary needs a real dependency?
2. What does a contract test protect?
3. Name one useful domain property.
4. What does a surviving mutant reveal?

Continue to [`senior.md`](senior.md).
