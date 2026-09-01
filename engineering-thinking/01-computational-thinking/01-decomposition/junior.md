# Decomposition - Junior

Decomposition turns one large problem into small results you can understand, build, and verify.

## Use it when

- A ticket feels vague or too large.
- You cannot tell where a bug lives.
- You cannot estimate or test the work confidently.

## The method

1. **State the outcome.** Write one sentence about what the user or system can do.
   - Example: "A user uploads an image and sees it as their profile picture."
2. **List inputs, outputs, and failures.** Ask what enters the flow, what must be produced, and what can go wrong.
3. **Write the main actions as verbs.** For an image upload: receive, validate, resize, upload, save, display.
4. **Split vague actions again.** "Validate" becomes: check file exists, type is allowed, and size is allowed.
5. **Show dependencies.** Validate before resize; upload before saving its URL; stop with a clear error on failure.
6. **Build and verify one result at a time.** Test each boundary before relying on the whole flow.

## Make each part actionable

A part is ready when you can:

- Explain its purpose in one sentence.
- Name it clearly.
- State what it receives and returns.
- Verify it without running the full feature.
- Say when it is finished.

Prefer precise work items:

| Vague | Actionable |
|---|---|
| Handle image | Check image type |
| Build checkout | Calculate order total |
| Fix login | Reproduce expired-session failure |
| Improve performance | Measure checkout response time |

## Turn parts into code

Keep the top-level flow readable and give helpers one job:

```python
def set_profile_picture(user, uploaded_file):
    validate_image(uploaded_file)
    image_url = upload_image(make_thumbnail(uploaded_file))
    save_profile_picture(user, image_url)
    return image_url
```

- Split by **action** for most features: validate -> calculate -> save -> notify.
- Split by **data** when the same work runs independently on many chunks, such as CSV partitions.
- Do not split every line. Split where a rule, purpose, or reason to change is independent.

## Debug with decomposition

Draw the data path, then inspect one boundary at a time:

1. Can the stored image be opened?
2. Is its URL correct in the database?
3. Does the API return that URL?
4. Does the browser receive and render it?

Each answer eliminates part of the search area. Start with a cheap check near the middle when possible.

## Avoid these mistakes

- Splitting by frontend, backend, and database before understanding the user flow.
- Leaving pieces vague, such as "handle payment."
- Creating a function that needs every dependency and owns many responsibilities.
- Forgetting failure, retry, and user-facing error paths.
- Continuing to split after each piece is clear and testable.

## Planning template

```markdown
## Outcome
What should the user or system do?

## Inputs and outputs
What enters and leaves the flow?

## Steps, dependencies, and failures
What happens, in what order, and what can fail?

## Verification
How will we prove each part and the complete flow work?
```

## Checklist

- [ ] The outcome is one clear sentence.
- [ ] Inputs, outputs, dependencies, and failure paths are known.
- [ ] Each step is a clear, testable result.
- [ ] The complete flow is still visible.

> Do not solve the entire problem in your head. Find the next small, clear result; solve and verify it; then connect it to the rest.

## Check your understanding

1. What makes a decomposition useful rather than merely more detailed?
2. When should you split work by action versus data?
3. How can boundaries narrow a debugging search?
