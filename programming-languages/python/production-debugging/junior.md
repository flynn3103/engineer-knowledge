# Python Production Debugging — Junior

Start from evidence, not a theory.

1. Capture the error, request ID, time, and affected version.
2. Reproduce the smallest safe example.
3. Read the complete traceback from the first relevant frame.
4. Add a test before fixing the defect.
5. Verify the fix with the same reproduction.

Use structured logs with meaningful fields; do not log secrets or raw personal data.
