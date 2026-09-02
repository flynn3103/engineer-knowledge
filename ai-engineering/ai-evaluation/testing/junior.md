# Testing — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Can you write a unit test for prompt-construction and routing logic that never calls a real model — mocking the model client and asserting only the deterministic parts: the rendered prompt, the selected tool schema, the chosen model and parameters?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — What's Actually Deterministic in an LLM Call

You already know how to unit test ordinary code: given an input, assert an exact expected output. That breaks the moment a real model call is in the path — the same prompt can produce different wording on different runs, so asserting exact output text makes the test flaky by construction, not by accident.

The fix is not to give up on unit testing this code. It's to notice that most of the code around a model call is *not* the model call:

- **Prompt construction** — filling a template with structured input. Deterministic: same input always produces the same rendered string.
- **Routing** — choosing which model, which temperature, which tool schema to use based on the input (for example, a cheap model for simple categories, a stronger one for complex ones). Deterministic: same input always produces the same routing decision.
- **The model call itself** — sending the built request to the LLM and getting a response back. Non-deterministic: same input can produce different output text even at low temperature.

A unit test at this level tests the first two and mocks the third out of existence.

## Core Concept 2 — Mock at the Client Boundary

**Mocking** means replacing a real dependency with a fake stand-in that returns a fixed, predictable value instead of doing the real (slow, non-deterministic, costly) work. For LLM code, the right seam to mock is the **model client** — the object or function that actually sends the request over the network — not some internal helper function a layer above it.

Mock too shallow (an internal function that just calls the client) and the test still doesn't reflect the real integration seam. Mock too deep (stub out your own routing logic) and you're no longer testing the code you meant to test — you've replaced the thing under test, not its dependency.

## Core Concept 3 — Worked Example

A support-ticket triage service builds a request from a template and routes it to a model and tool schema based on the ticket's category:

```python
# app/triage.py
PROMPT_TEMPLATES = {
    "billing": "You are a billing support agent.\nSubject: {subject}\nBody: {body}",
    "bug_report": "You are a bug-triage agent.\nSubject: {subject}\nBody: {body}",
}

MODEL_ROUTES = {
    "billing": {"model": "small-fast-model", "temperature": 0.0},
    "bug_report": {"model": "large-reasoning-model", "temperature": 0.2},
}

TOOL_SCHEMAS = {
    "billing": [{"name": "issue_refund", "parameters": {"amount": "number", "reason": "string"}}],
    "bug_report": [{"name": "file_bug", "parameters": {"severity": "string", "summary": "string"}}],
}

def build_request(ticket: dict) -> dict:
    category = ticket["category"]
    template = PROMPT_TEMPLATES[category]
    route = MODEL_ROUTES[category]
    return {
        "prompt": template.format(subject=ticket["subject"], body=ticket["body"]),
        "model": route["model"],
        "temperature": route["temperature"],
        "tools": TOOL_SCHEMAS[category],
    }

def handle_ticket(ticket: dict, llm_client) -> str:
    request = build_request(ticket)
    return llm_client.call(**request)
```

The test mocks `llm_client` and asserts on the request that was built, never on what a real model would say:

```python
# tests/test_triage.py
from unittest.mock import MagicMock
from app.triage import build_request, handle_ticket

def test_build_request_renders_billing_prompt_and_routes_correctly():
    ticket = {"category": "billing", "subject": "Overcharged", "body": "Charged twice for one order"}

    request = build_request(ticket)

    assert "Overcharged" in request["prompt"]
    assert "Charged twice for one order" in request["prompt"]
    assert request["model"] == "small-fast-model"
    assert request["temperature"] == 0.0
    assert request["tools"][0]["name"] == "issue_refund"

def test_handle_ticket_never_calls_a_real_model():
    mock_client = MagicMock()
    mock_client.call.return_value = "mocked response"
    ticket = {"category": "bug_report", "subject": "Crash on save", "body": "App crashes when saving"}

    result = handle_ticket(ticket, mock_client)

    mock_client.call.assert_called_once()
    sent = mock_client.call.call_args.kwargs
    assert sent["model"] == "large-reasoning-model"
    assert sent["tools"][0]["name"] == "file_bug"
    assert result == "mocked response"   # the mock's value, not a real model's — this line proves nothing about model quality
```

Nothing in either test depends on what a model would actually generate. `test_build_request_...` never touches the network at all — `build_request` is pure. `test_handle_ticket_...` swaps in `MagicMock()` for the client, so `llm_client.call` never leaves the process. Both tests run in milliseconds, need no API key, and fail only when the deterministic code — the template, the routing table, the schema — actually breaks.

## Core Concept 4 — What Never Belongs in This Kind of Test

A unit test at this level should never assert:

- The literal text a model would generate (`assert response == "I'm sorry to hear that..."`) — that's not determined by the code under test, it's determined by the model.
- That a real network call succeeded — that belongs in an integration or end-to-end test, not a unit test (see `middle.md` and `senior.md`).
- Anything that requires an API key or network access to run — if a test can't run offline, it isn't a unit test.

## Common Mistakes

1. **Asserting exact model output text.** The test passes today and fails next week when the model provider updates the model behind the same name, or even just returns different phrasing on a re-run — for a reason that has nothing to do with a bug in your code.
2. **Skipping the mock and calling a real model "just for this one test."** It works until the test suite needs a valid API key to run in CI, costs money on every run, and occasionally fails for reasons unrelated to the code (rate limits, transient network errors).
3. **Only asserting on the prompt text, never on the model or tool selection.** A routing bug — the wrong model or the wrong tool schema selected for a category — passes silently if the test never looks at `request["model"]` or `request["tools"]`.
4. **Mocking too deep.** Replacing your own `build_request` function with a mock, instead of mocking the LLM client, means the test no longer exercises the logic it was meant to verify.
5. **Eyeballing `print()` output instead of asserting in code.** A rendered prompt that "looks right" in a manual run gives no repeatable signal — the next person to touch the template has nothing to run and no fast feedback.

## Apply it

1. Take a function in your own codebase (or write a small one) that builds an LLM request from a template and structured input, with at least two different categories that route to different models or tool schemas.
2. Write a mock LLM client — a simple stand-in object with a `.call()` method that returns a fixed value.
3. Write two tests: one asserting the rendered prompt contains the input's key fields, and one asserting the correct model and tool schema were selected for a *different* category than the first test used.
4. Run the suite with no network access and no API key configured, and confirm both tests still pass.
5. Deliberately swap two entries in the routing table and confirm the corresponding test fails — this proves the test is actually checking the routing logic, not just running without error.

## Verify your work

- Tests pass with no network access and no valid API key present.
- No assertion in the suite contains literal text you expect a model to generate.
- Changing the *wording* of a prompt template (without removing a required field) doesn't break the test; removing a required field does.
- Swapping a routing entry (wrong model or wrong tool schema for a category) makes the corresponding test fail.
- Each test runs in well under a second.

## Review questions

- Why does asserting exact model output text make a test fail for reasons that have nothing to do with a bug in your code?
- What is the "client boundary," and why is it the right seam to mock instead of mocking your own routing function?
- Give an example of a routing bug that a test asserting only on prompt text would miss, but a test asserting on `model` and `tools` would catch.
- What has to be true about a test for it to count as a real unit test rather than an integration test in disguise?

---

*Part of [Testing](README.md) → [AI Evaluation](../README.md). Continue to [middle.md](middle.md).*
