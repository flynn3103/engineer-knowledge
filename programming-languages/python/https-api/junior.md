# Python HTTP APIs — Junior

An HTTP endpoint has a clear input, output, and status code.

- Validate request data before business logic.
- Return a consistent JSON shape.
- Use `201` for a created resource, `204` for no body, `404` when absent, and `400` for invalid input.
- Do not return raw exception messages to clients.

Test the endpoint through HTTP, not only its helper function.
