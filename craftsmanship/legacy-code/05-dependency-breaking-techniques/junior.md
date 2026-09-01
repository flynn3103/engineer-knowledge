# Dependency-Breaking Techniques — Junior

A dependency is anything your code needs in order to run: a database, clock, file, network client, global variable, or another class. Break a dependency when it prevents you from testing or understanding the change.

## Start with the smallest move

- Pass a value instead of reading global state.
- Pass a collaborator instead of creating it inside the function.
- Extract a small function around hard-to-reach logic.
- Wrap a library call in an adapter you own.

```python
def welcome(name: str, send) -> None:
    send(f"Welcome, {name}!")

def test_welcome_sends_a_message():
    sent = []
    welcome("Ada", sent.append)
    assert sent == ["Welcome, Ada!"]
```

The function parameter is the seam. The test uses `sent.append`; production can pass a mailer function.

## Safe sequence

1. Characterize the existing behavior.
2. Change one dependency at a time.
3. Keep old callers working if you can.
4. Test through the new seam.
5. Make the requested behavior change only after the safety net is green.

Do not rewrite a whole module just to avoid one dependency. Create only the space needed for the current change.
