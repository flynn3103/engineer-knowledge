# Python Data and Distributed Systems — Junior

Database calls can fail, time out, and return more data than expected.

- Use parameterized queries or a trusted ORM API.
- Close connections with a context manager or managed session.
- Fetch only needed columns and page large results.
- Wrap related writes in a transaction.
- Never assume a network call happens exactly once.

Write integration tests against a real compatible database when behavior matters.
