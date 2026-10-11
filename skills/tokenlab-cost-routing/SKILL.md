---
name: tokenlab-cost-routing
description: "Design cost, latency, and fallback policy for TokenLab requests in production: a primary, balanced, fast, and budget route per workload, per-request cost estimates from live pricing, Verified or Official delivery choices, and rules for when a fallback is allowed. Use when the user asks \"how do I cut my TokenLab bill\", \"build a fallback chain\", \"route cheap vs quality\", or \"what will this workload cost per month\". To find which models fit a task, use tokenlab-model-picker. To run one request, use tokenlab-run."
license: MIT
metadata:
  category: coding
---

# TokenLab Cost Routing

Turn a workload into a routing policy: which route serves which request, what each request costs, and when a fallback may run. Model discovery belongs to `tokenlab-model-picker`; this skill decides cost, latency, and fallback rules on top of its shortlist.

## What this skill delivers

- One sentence with the workload, volume, and assumptions.
- A route table with roles: primary, balanced, fast, budget.
- A cost estimate per request and per month from live pricing, with units shown.
- A delivery choice per route (Auto, Verified, or Official).
- Fallback rules: which errors trigger a fallback, and which changes need user approval.

## Inputs to collect

- Workload: chat, coding agent, image, video, audio, embedding, rerank, translation, or decisions.
- Volume and size: requests per day, tokens, images, seconds, or characters per request.
- Quality floor, latency target, and budget ceiling.
- Hard requirements: native protocol, tools, structured output, media inputs, audio, resolution.

## Workflow

1. Get the candidates from `tokenlab-model-picker` for the workload's operation or protocol. Keep only models that meet the hard requirements.
2. Read `GET /v1/models/{model}/pricing` for each candidate. Note `pricing_unit` and the price structure (entries, formulas, unit variants, minimum units, credits). `platform` is the Verified price; `official` is the Official price; a missing Verified price means no Verified supply, not free.
3. Estimate cost per request: quantity × unit price. For chat, include input, output, and cache reads or writes. For media, use the seconds, images, or characters the workload really sends. Show the formula.
4. Assign roles: primary (meets the quality floor), balanced, fast (lowest latency that still meets the floor), and budget.
5. Choose delivery per route. `Auto` (default) tries Verified, then runs Official once if Verified has no supply or fails before output, and holds the higher price until the run ends. `X-TokenLab-Delivery-Policy: verified` or `official` pins one option; that request fails with no charge when the option has no supply.
6. Write the fallback rules (below) and the refresh plan: when the table was checked and how to re-check it.

## Fallback rules

- Fall back on `429` after `Retry-After`, on retryable `5xx`, and on `503 all_channels_failed` / `delivery_tier_unavailable` with `retryable: false` (do not repeat the same request; move to the next route).
- Do not fall back on `400` contract errors, `401`/`403`, or `402 insufficient_balance`; fix the request, key, or balance.
- Never fall back after streaming output started or after an async task was accepted. That would duplicate the work and the charge.
- A fallback must keep the request semantics: protocol, tools, structured output, media inputs, safety settings. If the next route cannot, stop and ask.
- Paid media (video, 3D, worlds, music) fallbacks need explicit user approval; each retry is a new charge.
- Decision models (`systemone`) are never in a chat fallback chain. Compare decision routes on measured task error on the user's labeled cases; a zero output price does not mean zero output tokens.

## Output format

| Route role | Model ID | Endpoint | Est. cost per request | Delivery | Fall back when |
| --- | --- | --- | --- | --- | --- |

Then: the pricing commands used, the monthly estimate with assumptions, and one implementation note on retries, rate limits, and approval when quality drops.

## Quality bar

- Every price comes from the pricing API at a stated time, with units and the formula shown.
- No route drops a hard requirement; each trade-off (quality, latency, features) is named.
- Fallback triggers are specific error codes, and no rule can duplicate a paid generation.
- The table says how to refresh it; nothing is presented as permanent.

## Avoid

- Do not invent prices, discounts, or model counts.
- Do not expose TokenLab internal routing or supplier details.
- Do not switch a user's chosen model without saying why.

## Related skills

- `tokenlab-model-picker`: the candidate shortlist.
- `tokenlab-run`: estimate and run one request.
- `tokenlab-api-integration`: put the routing policy into code.
