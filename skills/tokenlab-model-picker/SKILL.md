---
name: tokenlab-model-picker
description: "Pick TokenLab models for an outcome: map what the user wants (a product photo, an animated still, a voiceover, a 3D asset, a routing decision, a chat or coding agent) to a public operation, then to live model IDs from the catalog, with a default, an alternative, and a fast or low-cost option. Use when the user asks \"which model should I use\", \"what is the best model for video\", \"compare image models\", or when another tokenlab-* skill needs to confirm a model is live. To run the call, use tokenlab-run. For cost-aware fallback chains in production code, use tokenlab-cost-routing."
license: MIT
metadata:
  category: foundation
---

# TokenLab Model Picker

Turn an outcome into a short list of live TokenLab model IDs. Work in three steps: outcome → operation → model. Read live catalog signals every time; never answer from memory.

## What this skill should deliver

- The operation the outcome needs, and the endpoint for it.
- A shortlist with exact public model IDs: a default, an alternative, and a fast or low-cost option.
- Why each model fits, from contract and catalog signals.
- One command the user can rerun to refresh the list.
- A caveat for anything volatile: price, supply, or a benchmark claim.

## Step 1: outcome → operation

| Outcome | Operation | Outcome skill |
| --- | --- | --- |
| New image from text | `text-to-image` | `tokenlab-photoreal-stills`, `tokenlab-product-photography`, `tokenlab-text-in-image`, `tokenlab-logos-and-vectors` |
| Change an existing image | `image-edit`, `image-to-image` | `tokenlab-edit-image`, `tokenlab-restore-and-upscale`, `tokenlab-character-consistency` |
| Video from text | `text-to-video` | `tokenlab-cinematic-video` |
| Video from a still | `image-to-video` | `tokenlab-animate-image`, `tokenlab-product-ad-video`, `tokenlab-talking-avatar` |
| Video from reference images | `reference-to-video` | `tokenlab-character-consistency`, `tokenlab-product-ad-video` |
| Video between two frames | `start-end-to-video` | `tokenlab-keyframe-transition` |
| Change or continue a video | `video-to-video`, `video-extension` | `tokenlab-edit-video`, `tokenlab-extend-video` |
| Move a character like a reference clip | `motion-control` | `tokenlab-motion-control` |
| Speech from text / text from speech | `tts` / `stt` | `tokenlab-voiceover`, `tokenlab-transcribe-and-subtitle` |
| Song, instrumental, sound effect | `music` | `tokenlab-music` |
| 3D asset / explorable world | `text-to-3d`, `image-to-3d` / `world-generation` | `tokenlab-image-to-3d-asset`, `tokenlab-world-generation` |
| Typed yes/no, choice, or score | `systemone` | `tokenlab-decisions` |
| Text translation | `translation` | `tokenlab-transcribe-and-subtitle` |
| Chat, coding, agent loop | chat formats | `tokenlab-api-integration`, `tokenlab-native-endpoints` |

## Step 2: operation → candidates

- Scene shortlist: `GET https://api.tokenlab.sh/v1/models?recommended_for=<scene>`. Scenes: `image`, `video`, `music`, `3d`, `tts`, `stt`, `embedding`, `rerank`, `translation`, `decision`. If the API rejects a scene with `invalid_recommended_for`, use the category filter instead.
- Category filter: `GET /v1/models?category=<category>` (for example `category=decision`).
- Keep only models whose `tokenlab.public_contract_summary.public_operations` (or `public_contract`) includes the operation.
- A scene ranks models by their measured success rate in the last 24 hours, not by output quality. Read `tokenlab.agent_preferences.<scene>`: `preferred_rank`, `success_rate_24h`, `sample_count_24h`, and `status`. `status: "insufficient_samples"` means no ranking signal yet, not a bad model.
- Check supply per operation: `tokenlab.deliveryAvailability.operations[<op>]` shows whether Verified and Official supply exist.

## Step 3: candidates → shortlist

1. For each candidate, read `GET /v1/models/{model}` and confirm:
   - `lifecycle.stage` is `active`;
   - the operation, its endpoint in `request_endpoint_by_operation`, and the inputs the user has (image, video, audio, reference count);
   - the size, duration, and resolution limits the user needs, from `operation_constraints`.
2. Read `GET /v1/models/{model}/pricing` and compare cost per output unit (image, second, character, token, or request).
3. Pick the default for fit and reliability, an alternative with a different strength (quality, speed, or input type), and a fast or low-cost option. Use the outcome skill's model table as the starting list, then confirm it live.
4. Chat and coding: read `tokenlab.accepted_request_formats` to match the client's protocol (`openai_chat_completions`, `openai_responses`, `anthropic_messages`, `gemini_generate_content`).
5. Decisions: discover `category=decision` and confirm the `systemone` operation. A decision model returns typed answers; never select it as a chat model.

MCP equivalents: `list_models`, `get_model`, `get_model_pricing`, `compare_models`.

## Output format

- One sentence: the outcome, the operation, and your assumptions.
- A table: `Role` (default / alternative / fast), `Model ID`, `Why`, `Watch out`.
- One rerunnable command, for example `curl "https://api.tokenlab.sh/v1/models?recommended_for=video"`.
- One line on what to confirm before a paid call (price, supply, limits).

## Avoid

- Do not name a single universal best model, and do not hardcode one model as the only answer.
- Do not recommend a model that is absent from the live catalog or does not publish the operation.
- Do not infer an endpoint, field, or capability from a model name; read the contract.
- Do not invent prices, model counts, or benchmark results. A benchmark claim needs a cited source and date.
- Do not use physical route names or provider-prefixed names as model IDs.

## Edge cases

- The user asks for the cheapest: still state what the cheap model cannot do (inputs, length, resolution, audio).
- The catalog is unreachable: say so, and give the outcome skill's table as examples only, not as live truth.
- The user names a model: check that it publishes the operation; if not, say so and offer live alternatives.

## Related skills

- `tokenlab-run`: run the chosen model.
- `tokenlab-prompting`: prompt craft for the chosen family.
- `tokenlab-cost-routing`: fallback chains with live pricing.
