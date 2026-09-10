# Security at Scale — Middle

Use STRIDE to examine spoofing, tampering, repudiation, disclosure, denial, and privilege escalation. OAuth 2 delegates authorization; OIDC adds identity; JWT is a token format, not an access-control design.

Use KMS envelope encryption, automated certificate rotation, rate limits, WAF controls, and scoped service identities. Test key expiry, revocation, clock skew, and dependency compromise.

## Test yourself

1. Which trust boundary needs a threat model?
2. Why is JWT validation insufficient for authorization?
3. How does envelope encryption work?
4. Which abuse limit protects expensive work?

Continue to [`senior.md`](senior.md).
