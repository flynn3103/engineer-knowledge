# Python Production Debugging — Middle

Make a service diagnosable before an incident.

- Log request or job IDs, operation, duration, and outcome.
- Emit metrics for rate, errors, latency, and saturation.
- Use traces to follow a request across HTTP, queues, and databases.
- Add health checks that reflect the ability to serve traffic.

When an alert fires, compare a failing request with a healthy one and change one variable at a time.
