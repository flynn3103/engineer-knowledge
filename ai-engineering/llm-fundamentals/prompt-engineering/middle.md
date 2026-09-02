# Prompt Engineering — Middle

<!-- level-focus -->
At middle level, focus on this question:

> When a product needs the same kind of prompt run across many different inputs, how do you build a template that stays consistent, stays maintainable, and earns its token cost — instead of a pile of near-duplicate inline strings?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Prompt Templates: Separating Scaffold From Content

A junior-level prompt is a single string, hand-written for one request. The moment a product needs to run "the same kind of prompt" against hundreds or thousands of different inputs — classify this ticket, summarize this document, extract these fields from this form — hand-writing a new string per request stops being viable, and copy-pasting the instruction into a dozen call sites with minor variations creates the exact problem code review exists to prevent: the same logic duplicated, drifting slightly out of sync every time someone edits one copy and not the others.

A **prompt template** separates the fixed instructional scaffold (the part that never changes) from the variable content (the part that changes per request), using ordinary string templating:

```python
from string import Template

TICKET_CLASSIFIER_TEMPLATE = Template("""\
You are classifying customer support tickets into exactly one category.

Categories: $categories

Respond with only the category name, nothing else.

Ticket:
$ticket_text
""")

prompt = TICKET_CLASSIFIER_TEMPLATE.substitute(
    categories="Billing, Shipping, Account Access, Product Defect, Refund Request, Technical Support, Feedback, Other",
    ticket_text=ticket.body,
)
```

(Jinja2 or an f-string-based template work the same way for this purpose — the mechanism matters less than the separation it enforces.)

Two concrete things this buys a product team that inline strings don't:

- **Consistency across requests.** Every call to the classifier renders from the same scaffold, so the instruction wording, the category list, and the output-format constraint are identical for every ticket, not subtly different depending on which call site wrote the string.
- **A single place to fix a wording bug.** If the classifier is misreading "Refund Request" tickets as "Billing" because the category description is ambiguous, the fix is one edit to `TICKET_CLASSIFIER_TEMPLATE`, not a search across every file that happened to inline a similar prompt.

## Core Concept 2 — Chain-of-Thought, and Keeping Reasoning Out of the Parsed Output

**Chain-of-thought prompting** asks the model to reason step-by-step before giving a final answer, rather than jumping straight to the answer. On multi-step reasoning tasks — arithmetic word problems, multi-hop questions, anything requiring the model to hold intermediate state — this measurably improves accuracy over asking for the answer directly, because it gives the model room to work through intermediate steps instead of pattern-matching straight to a guess.

```
A customer's subscription renews on the 15th. They cancel on the 3rd of the
following month. Our refund policy prorates unused days at the daily rate.
How many days should be refunded?

Think through this step by step, then give your final answer on its own
line as: ANSWER: <number>
```

The practical trap at middle level: chain-of-thought reasoning text is verbose, sometimes reveals uncertainty or an incorrect intermediate step that got corrected later, and is not what a downstream system — or a user-facing UI — should consume. The fix is separating the reasoning from the final answer via a structured output field, so the caller parses only the answer and the reasoning never leaks into what's shown or fed downstream:

```python
import re

def parse_response(text: str) -> int:
    match = re.search(r"ANSWER:\s*(\d+)", text)
    if not match:
        raise ValueError(f"No ANSWER field found in response: {text!r}")
    return int(match.group(1))
```

Or, more robustly, ask for a structured field directly (see Core Concept 4) so parsing isn't a regex over free text at all — the reasoning can go in one field and the answer in another, and only the answer field is read by the caller.

## Core Concept 3 — Role/Persona Prompting: When It Helps, When It's Cargo-Culted

Assigning the model a role — "You are an expert code reviewer with 15 years of experience in distributed systems" — is one of the most commonly copy-pasted prompt-engineering techniques, and one of the least consistently justified. It genuinely helps in a narrow set of cases: when the role plausibly shifts *what the model attends to or which register it writes in* — a persona like "You are a terse technical editor" can measurably change output length and word choice compared to no persona at all, because it's steering a real, observable dimension of the response.

It is cargo-culted the moment it's added out of habit with no way to tell whether it changed anything. "You are a world-class expert" prepended to a task the model already performs consistently without it is decoration, not engineering — if removing the persona line produces indistinguishable output on your actual task, it isn't earning the tokens it costs on every request. The test is the same as any other prompt change: compare output with and against the persona on a handful of real inputs before keeping it, not "it feels like it should help."

## Core Concept 4 — Output Format Constraints

Free-text output that you *hope* parses correctly downstream is a middle-level anti-pattern. The more reliable alternative is stating the exact output contract in the prompt — a JSON schema, a fixed set of labels, a word limit — and, where the API supports it, enforcing it structurally rather than just asking nicely:

```
Respond with only valid JSON matching this shape, nothing else:
{
  "category": "Billing" | "Shipping" | "Account Access" | "Product Defect" | "Refund Request" | "Technical Support" | "Feedback" | "Other",
  "confidence": <float between 0 and 1>
}
```

An explicit format constraint turns "does the output happen to be parseable" into "the output is contractually one of a known set of shapes" — the same shift from hoping a function's caller passes the right type to declaring and enforcing the type. Many current APIs support this as a first-class feature (JSON mode, structured output, function/tool-calling schemas) rather than a prompt-text convention alone; prefer the structural mechanism when the API offers one, and fall back to a strict textual format instruction plus defensive parsing when it doesn't.

## Core Concept 5 — Concrete Scenario: Building the Ticket Classifier

A product needs to classify support tickets into one of 8 categories. Walking through the build in order:

1. **Start with the template and zero-shot instructions** (Core Concept 1), rendering the ticket text and the category list as variables. Run it against a labeled validation set — a set of tickets with a human-assigned correct category — and measure accuracy.
2. **Identify the categories the model actually confuses**, from the validation results, not from guessing. Suppose the confusion matrix shows "Refund Request" tickets are frequently misclassified as "Billing" — both mention money, and the instruction alone doesn't state the distinguishing signal (the customer is asking for money back, not being charged incorrectly).
3. **Add 2–3 few-shot examples targeting exactly that confusion** — one clear "Billing" example, one clear "Refund Request" example, and one borderline one that shows how to resolve the ambiguity — rather than adding examples for every category, most of which the model already gets right.
4. **Add the explicit output-format constraint** from Core Concept 4, so the category name comes back as one of exactly 8 known strings instead of a free-text label that might be "refund" one time and "Refund Request" another.
5. **Re-run against the same validation set** and compare accuracy before and after each change, isolating which change (few-shot examples vs. format constraint) moved the number.

## Core Concept 6 — Under- and Over-Application

Few-shot examples cost tokens on **every single request**, not once. For a classifier running against thousands of tickets a day, 3 few-shot examples averaging 40 tokens each adds roughly 120 tokens to every call — real, recurring cost and latency, not a one-time price. That cost is worth paying only for genuinely ambiguous formatting or judgment calls the model doesn't reliably get right zero-shot. Adding few-shot examples to a category the model already classifies at high accuracy zero-shot is pure overhead: it doesn't move accuracy on that category and pays the token cost on every request regardless.

The signals in both directions:

- **Under-applying:** a task with a specific, non-obvious output format or a judgment call the model keeps getting wrong, still running zero-shot — accuracy on the validation set is measurably below where a handful of targeted examples would put it.
- **Over-applying:** few-shot examples included for categories or tasks where zero-shot accuracy is already high — removing them changes token cost but not accuracy.

## Verification: Beyond Spot Checks

A handful of manual spot checks ("I tried three tickets and they looked right") does not verify a template used against thousands of future inputs — it verifies three inputs. The middle-level bar is testing the template against a labeled validation set and measuring accuracy as a number:

```python
correct = 0
for ticket, expected_category in validation_set:
    prompt = TICKET_CLASSIFIER_TEMPLATE.substitute(
        categories=CATEGORY_LIST, ticket_text=ticket.body
    )
    result = parse_response(call_model(prompt))
    if result["category"] == expected_category:
        correct += 1

accuracy = correct / len(validation_set)
print(f"Accuracy: {accuracy:.1%} on {len(validation_set)} tickets")
```

This does two things a spot check can't: it gives a number you can compare before and after a template change (did adding few-shot examples actually move accuracy, or just add tokens), and it exposes exactly which categories the errors cluster in, which is what makes step 2 of Core Concept 5 possible at all.

## Common Mistakes

| Mistake | Why it hurts | Fix |
|---|---|---|
| Inline prompt strings duplicated across call sites | A wording fix has to be found and applied in every copy, and copies drift out of sync | One template, one place to edit, referenced everywhere it's used |
| Letting chain-of-thought reasoning text leak into the parsed or displayed output | Verbose, sometimes-uncertain reasoning ends up shown to a user or fed downstream as if it were the answer | Separate reasoning from the final answer with a structured field or explicit delimiter, and parse only the answer |
| Adding a persona/role with no before/after comparison | Tokens spent every request with no verified effect | Compare output with and without the persona on real inputs before keeping it |
| Hoping free-text output happens to parse | Downstream parsing breaks unpredictably as output format drifts | State an explicit format constraint; use structured output mode where the API supports it |
| Adding few-shot examples to every category instead of the confused ones | Token cost on every request with no accuracy gain on categories already handled well | Target examples at the specific confusions a validation run surfaces |
| Verifying with a handful of manual spot checks | Three inputs looking right says nothing about the other thousands | Measure accuracy against a labeled validation set |

## Apply it

1. Take a classification or extraction task with a fixed, known set of output categories (support tickets, product reviews, form fields — real or representative sample data).
2. Build a template with variables for the input content and the category list, and render it with a real templating mechanism (not string concatenation).
3. Run it zero-shot against a labeled validation set of at least 20–30 examples and record accuracy.
4. From the errors, identify which specific categories are confused for which other categories, add 2–3 few-shot examples targeting exactly that confusion, and add an explicit output-format constraint.
5. Re-run against the same validation set and report the accuracy delta, attributing the change to the specific edit that caused it.

## Verify your work

- The template's fixed scaffold and variable content are cleanly separated — a wording change requires editing one place, not several call sites.
- If the task involves multi-step reasoning, the reasoning text is demonstrably kept out of the parsed/displayed answer (show the parsing code or the structured field).
- You have a before/after accuracy number from a labeled validation set, not a description of a few examples that "looked good."
- You can name the specific confusion (category X mistaken for category Y) that your few-shot examples were chosen to fix.
- You can state, for any few-shot examples you kept, why removing them would measurably hurt accuracy on this specific task — not just that examples "generally help."

## Review questions

- What specifically does separating a prompt into a template with variables buy you that a set of near-duplicate inline strings doesn't?
- Why does chain-of-thought reasoning need to be kept separate from the answer a downstream system parses, rather than just appended to a longer response?
- What would tell you that a role/persona addition to a prompt is cargo-culted rather than earning its cost?
- Why is a handful of manual spot checks insufficient to verify a prompt template, and what replaces it?
- Given a task where the model already classifies 7 of 8 categories at high accuracy zero-shot and confuses only 2 of them, where specifically should few-shot examples go, and why not everywhere?
