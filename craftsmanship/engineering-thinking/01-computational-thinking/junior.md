# Computational Thinking — Junior

**Your question:** How do I break down a big feature request into small, testable pieces?

The phrase “add profile picture upload” is too vague to code safely. It hides file validation, resizing, storage, database updates, and display logic. If you code from the phrase alone, failures scatter across concerns and become hard to debug.

## The method: Decompose into observable outcomes

Instead of tasks, write **outcomes**—things you can verify without completing the feature:

**Bad (activities):** upload file → validate → store → update database → display  
**Good (outcomes):**
- File type is JPG, PNG, or WebP (reject others immediately)
- File size ≤ 5 MB (reject oversized files with clear error)
- Image stored in /uploads with unique name
- User.profile_image_url points to the stored file
- API response includes new image URL and timestamp
- Old image is removed from storage (optional: defer)

### How to apply it

1. Read the feature request word-by-word. For each concept, ask: “How will I know this worked?”
2. Write 5–8 outcomes. Each should:
   - Be checkable with inputs and expected outputs
   - Be achievable in one code change or one test
   - Have a single reason to fail
3. Check for missing outcomes: authorization, errors, edge cases, cleanup
4. Draw dependencies—which outcome must happen first?

### A concrete example

**Request:** Users can upload a profile picture

**Outcomes in order:**
1. Validate: MIME type in [image/jpeg, image/png, image/webp] → reject with code 400 if not
2. Validate: file size ≤ 5MB → reject with code 413 if not
3. Resize: convert to 256×256 → store in /uploads with hash-based filename
4. Update: set user.profile_image_url to /uploads/{hash}.jpg
5. Return: 200 response with { image_url, uploaded_at } JSON
6. Display: fetch and render image in UI with fallback avatar

Each outcome is testable alone:
- Test 1: send PNG file → expect 200, size recorded
- Test 2: send 20MB file → expect 413, database unchanged
- Test 3: check database after valid upload → user.profile_image_url matches stored path

## Recognize and name patterns

Repeated logic is a signal to standardize:
- “Validate file type” appears twice → extract as reusable check
- “Reject with error code” appears in multiple places → standardize response format

**But first:** name what's actually the same and what differs. File validation checks MIME type; data validation checks range. Don't merge them into a generic `validate()` function—keep concerns separate.

## Choose the smallest useful abstraction

An abstraction **hides irrelevant detail**. Ask: “Does the caller need to know this?”

- ✓ Good: `ImageStore.save(bytes) -> url` (caller shouldn't know if storage is local or S3)
- ✗ Poor: `Utils.process(data)` (unclear what it does; hides everything)
- ✗ Poor: `FileValidator.validate(file)` returning a boolean (doesn't say why it failed)

A minimal abstraction:
- Has a clear name (the single responsibility)
- Accepts concrete inputs (not generic objects)
- Returns a clear result or raises named exceptions
- Is testable without touching external systems

## Common beginner mistakes

| Mistake | Why it hurts | How to fix |
|---|---|---|
| “Implement feature X” → split into 50 tasks | Tasks are too interdependent to verify alone | Split by outcomes instead; one outcome = one testable result |
| Hide all error details in a generic exception | Caller can't diagnose failure | Raise specific exceptions (FileTooLarge, UnsupportedType) |
| Create a utility function after seeing two uses | Premature abstraction hides intent | Wait until the third use and first understand what's actually the same |
| Merge validation logic across domains | Validation rules diverge later, causing bugs | Keep validators separate by concern |

## Hands-on exercise

Take one ticket from your backlog. Write:
1. The desired result (1 sentence)
2. Five smaller, observable outcomes
3. Which outcome has no dependency (start there)
4. How you'd test outcome #1 without finishing outcome #5
5. One edge case (oversized file, missing field, race condition)

Stop if any outcome cannot be tested. Split it again.

## Verify your thinking

- [ ] Can you test outcome #1 without writing code for outcome #2?
- [ ] Does each outcome have exactly one input and output you can name?
- [ ] Can you explain why the order of outcomes matters?
- [ ] Can you name three ways outcome #3 could fail?
- [ ] Would a new team member understand what each outcome means?

Continue to [`middle.md`](middle.md).
