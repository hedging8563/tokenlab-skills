# Question design for System One

Four common patterns. Each shows the questions and the code that acts on them. Thresholds are examples; tune them on labeled cases.

## Routing: pick one path

```json
{"route": {"type": "choice", "instructions": "Which queue should handle this request?",
  "criteria": {"billing": "Charges, invoices, refunds", "technical": "Errors, bugs, API problems",
               "account": "Login, access, profile", "other": null}}}
```

```python
queue = answers["route"]["choice"]
if answers["route"].get("confidence", 1) < 0.6:
    queue = "human-triage"
```

Give a catch-all option (`other`) so the model is not forced into a wrong queue.

## Gating: allow or stop one action

```json
{"safe_to_send": {"type": "noul", "instructions": "Is this reply safe to send to the customer without review?",
  "criteria": {"true": "Polite, on topic, makes no promises about money or dates.",
               "false": "Rude, off topic, or promises money, refunds, or dates."}}}
```

```python
if answers["safe_to_send"]["noul"] >= 0.9:
    send(reply)
else:
    hold_for_review(reply)
```

For a gate before a costly or risky action, use a high threshold and a safe default (hold, not send).

## Scoring: rank or sort

```json
{"lead_fit": {"type": "score", "instructions": "How well does this lead fit our product?",
  "criteria": ["No fit", "Weak fit", "Some fit", "Good fit", "Ideal fit"]}}
```

`score` is a number from 0 to 4 here and can be a fraction. Sort on it, or bucket it: `>= 3` goes to sales.

## Triage: several questions, one call

```json
{"state": {"ticket": "...", "plan": "pro", "open_tickets": 2},
 "questions": {
   "refund_requested": {"type": "noul", "instructions": "Does the customer ask for money back?"},
   "team": {"type": "choice", "instructions": "Which team owns this?", "criteria": {"billing": null, "technical": null, "sales": null}},
   "urgency": {"type": "score", "instructions": "How urgent is it?", "criteria": ["Routine", "Money or access affected", "Outage or safety issue"]}}}
```

One call answers all three. The response keeps your names under `answers`.

## Agent branches

Inside an agent loop, put the agent's current step in `state` (goal, last tool result, open items) and ask one `choice` question: "What should the agent do next?" with options such as `call_tool`, `ask_user`, `finish`. The agent code switches on the choice. The agent's main chat model stays separate.

## Rules from the contract

- Request fields: exactly `model`, `state`, `questions`. Other keys are rejected (`Unrecognized key(s)`).
- `state` and each `instructions`: a string, a JSON object, or a JSON array.
- `noul` `criteria` (optional): an object with both `true` and `false`.
- `choice` `criteria`: 1–255 options; each value is guidance or `null`.
- `score` `criteria`: an ordered array of 2–10 levels.
- `questions` must not be empty.

## Checking before use

1. Collect 20–50 real cases with the right answer.
2. Run them once. Save the answers.
3. For each threshold, count false positives and false negatives at a few values (0.5, 0.7, 0.9).
4. Pick the threshold that matches the cost of each error. Re-check when you change questions or models.
