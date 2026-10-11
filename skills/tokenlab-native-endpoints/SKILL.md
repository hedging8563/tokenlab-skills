---
name: tokenlab-native-endpoints
description: "Call TokenLab through a model's native protocol instead of OpenAI-compatible chat: OpenAI Responses, Anthropic Messages, Gemini generateContent, or System One decisions. Use when the user needs provider-native features (Responses state, Claude thinking or tool blocks, Gemini parts), when a response carries an X-TokenLab-Native-Endpoint hint, or when the user asks \"should I use /v1/messages or /v1/chat/completions\". For media and audio calls, use tokenlab-run and the outcome skills. For full application code and client setup, use tokenlab-api-integration."
license: MIT
metadata:
  category: coding
---

# TokenLab Native Endpoints

Choose the native endpoint that a model declares, and keep that protocol's request semantics. OpenAI-compatible chat stays the simple default when no native feature is needed.

## What this skill delivers

- The chosen endpoint and the contract field that allows it.
- One runnable cURL or SDK block with the right base URL and auth header.
- When OpenAI-compatible chat is still the simpler path.
- A recovery note: which contract to read when the call fails.

## Inputs to collect

- The model ID, and the client or SDK the caller uses.
- The native feature the caller needs: Responses items and state, Claude thinking, tool use or cache blocks, Gemini parts and generation config, or typed decisions.
- Any `X-TokenLab-Hint` or `X-TokenLab-Native-Endpoint` header from an earlier response.

## Models

<!-- tokenlab:models:start -->
<!-- Generated from the live catalog by scripts/sync_models.py. Do not edit; change preferredModels in catalog.json. -->

| Operation | Model | Pick | Use |
| --- | --- | --- | --- |
| `chat` | `gpt-5.6-sol` | default | Example for Responses |
| `chat` | `claude-sonnet-4-6` | alternative | Example for Anthropic Messages |
| `chat` | `gemini-3.5-flash` | alternative | Example for Gemini generateContent |
| `systemone` | `jev-1.13` | default | Example for System One decisions |

This list refreshes daily from the live catalog. Preferred models come first; otherwise models are ranked by their 24-hour success rate. Before a call, confirm the model with `GET /v1/models/{model}` and read its price from `GET /v1/models/{model}/pricing`.
<!-- tokenlab:models:end -->

These are examples per protocol. For another model, read `tokenlab.accepted_request_formats` in `GET /v1/models/{model}`; it lists the chat protocols that model accepts.

## Endpoint families

| Contract value | Endpoint | Base URL for SDKs |
| --- | --- | --- |
| `openai_chat_completions` | `POST /v1/chat/completions` | `https://api.tokenlab.sh/v1` |
| `openai_responses` | `POST /v1/responses` | `https://api.tokenlab.sh/v1` |
| `anthropic_messages` | `POST /v1/messages` | `https://api.tokenlab.sh` (the SDK adds `/v1`) |
| `gemini_generate_content` | `POST /v1beta/models/{model}:generateContent` (`:streamGenerateContent` for SSE) | `https://api.tokenlab.sh` |
| `systemone` (operation) | `POST /v1/systemone` | HTTP JSON, or MCP `evaluate_decisions` |

Auth is `Authorization: Bearer $TOKENLAB_API_KEY`; native SDKs may send the key in their own header.

## Workflow

1. Read `GET /v1/models/{model}`. Chat protocols are in `tokenlab.accepted_request_formats`. Decisions are in `public_contract.public_operations` (`systemone`) with `request_endpoint_by_operation`.
2. Start with OpenAI-compatible chat unless the caller needs a native feature or the model does not declare chat.
3. If an earlier response has `X-TokenLab-Native-Endpoint`, treat it as routing evidence and prefer that exact route.
4. Build the request in the native shape and send it. Keep the request ID from `x-request-id`.
5. On a contract error, read the error's structured fields and the model contract, and fix the request. Do not flatten it into another protocol.

```bash
curl https://api.tokenlab.sh/v1/messages \
  -H "Authorization: Bearer $TOKENLAB_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{"model": "MODEL_ID", "max_tokens": 256, "messages": [{"role": "user", "content": "Reply with OK."}]}'
```

Take `MODEL_ID` from the Models list above, or from any model whose contract declares `anthropic_messages`.

## Rules

- Keep Anthropic Messages semantics on `/v1/messages`: system blocks, thinking blocks and signatures, tool use and tool results, and cache control.
- Keep Gemini content parts, roles, tools, and `generationConfig` on the Gemini route when the caller needs them.
- Responses is not Chat with another name. Use it only when the model declares `openai_responses` and the client implements Responses.
- System One takes only `model`, `state`, and named `questions` (`noul`, `choice`, `score`) and returns typed answers. It has no messages, streaming, tools, or batch. Never configure a decision model as a chat model, and never treat an answer as permission to act. Discover decision models with `GET /v1/models?category=decision` (or `recommended_for=decision`). Details: `tokenlab-decisions`.
- Do not remove unsupported fields just to pass validation when that changes output, safety, billing, or response guarantees.
- Do not expose private TokenLab routing details.
- The TokenLab MCP server uses the `core` profile by default, which has `create_response`, `create_anthropic_message`, `create_gemini_content`, `create_chat_completion`, and `evaluate_decisions`.

## Quality bar

- The endpoint matches a declared contract value, and the cited field is named.
- Native fields survive the round trip; nothing was flattened without the user's consent.
- When the user's explicit need conflicts with an endpoint hint, the trade-off is stated and the user confirms.

## Related skills

- `tokenlab-api-integration`: application code and client setup.
- `tokenlab-decisions`: question design and thresholds for System One.
- `tokenlab-model-picker`: choose the model.
- `tokenlab-run`: media, audio, 3D, and decision calls.
