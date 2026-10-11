---
name: tokenlab-api-integration
description: "Write runnable application code that calls TokenLab (formerly LemonData): Chat Completions, Responses, Anthropic Messages, Gemini, images, video, music, 3D, worlds, speech, transcription, files, embeddings, rerank, translation, System One decisions, and async tasks, in Python, JavaScript, Go, PHP, or cURL. Also sets up Codex, Claude Code, OpenCode, Pi, or Hermes to use TokenLab as the model provider. Use when the user says \"integrate TokenLab\", \"add a TokenLab call to my app\", \"use TokenLab in Codex or Claude Code\", or \"handle TokenLab async tasks in code\". To run one request now, use tokenlab-run. To choose models, use tokenlab-model-picker. To move an existing OpenAI-compatible app, use tokenlab-openai-compatible-migration."
license: MIT
metadata:
  category: coding
---

# TokenLab API Integration

Put TokenLab into application code or a client configuration. The code reads the live model contract, uses the endpoint that the contract declares, handles sync and async results, and keeps request semantics intact.

## What this skill delivers

1. The endpoint and the contract field that justifies it (never a guess from a model name).
2. Runnable code with install commands, environment variables, timeouts, cancellation, and error handling.
3. For non-chat work: live model discovery, then create, wait, and a terminal result.
4. One minimal check command that proves the business result, not only HTTP 200.
5. For client setup: a preview, an explicit apply step, and a restore path.

## Inputs to collect

- Task type, input and output media, and whether the caller needs sync, streaming, or async results.
- The protocol the caller already speaks (OpenAI Chat, OpenAI Responses, Anthropic Messages, Gemini, or plain HTTP).
- Language and framework, and where the key lives (`TOKENLAB_API_KEY` or a secret store).
- For client setup: the client, its version, and the model the user chose.

## Models

<!-- tokenlab:models:start -->
<!-- Generated from the live catalog by scripts/sync_models.py. Do not edit; change preferredModels in catalog.json. -->

| Operation | Model | Pick | Use |
| --- | --- | --- | --- |
| `chat` | `gpt-5.6-luna` | default | Example for Chat Completions clients (OpenCode, Pi, Hermes) |
| `chat` | `gpt-5.6-sol` | alternative | Example for Responses clients (Codex) |
| `chat` | `claude-sonnet-4-6` | alternative | Example for Messages clients (Claude Code) |

This list refreshes daily from the live catalog. Preferred models come first; otherwise models are ranked by their 24-hour success rate. Before a call, confirm the model with `GET /v1/models/{model}` and read its price from `GET /v1/models/{model}/pricing`.
<!-- tokenlab:models:end -->

These are example chat models for client setup. The user chooses the model; check that it declares the client's protocol in `tokenlab.accepted_request_formats` before you write it into a configuration. For non-chat work, discover models with `tokenlab-model-picker` or `GET /v1/models?recommended_for=<scene>`.

## Public roots

- API root: `https://api.tokenlab.sh`. OpenAI-compatible base URL: `https://api.tokenlab.sh/v1`.
- Anthropic SDK base URL: `https://api.tokenlab.sh` (do not add `/v1`).
- Docs: `https://tokenlab.sh/docs`. OpenAPI: `https://tokenlab.sh/docs/openapi.json`.
- Catalog: `GET /v1/models`; contract: `GET /v1/models/{model}`; prices: `GET /v1/models/{model}/pricing`.
- Auth: `Authorization: Bearer $TOKENLAB_API_KEY`, or the native SDK's own key header.

## Workflow

1. Read the model contract with the read-only helper:

   ```bash
   python skills/tokenlab-api-integration/scripts/search_api.py --category video --limit 20
   python skills/tokenlab-api-integration/scripts/search_api.py --detail MODEL_ID --json
   ```

2. Chat: pick the endpoint from `tokenlab.accepted_request_formats` (table below). Non-chat and decisions: pick it from `public_contract.public_operations` and `request_endpoint_by_operation`. A decision model can have no chat format; do not reject its declared `systemone` operation for that reason.
3. Send only the request shape of that endpoint. Do not mix Responses, Messages, Gemini, and Chat fields.
4. Write the code from [references/integration_examples.md](references/integration_examples.md): key from the environment, timeouts, cancellation, async waiting, and structured errors.
5. Give the user one check command and say what result counts as success.

Do not deploy, write production keys, or send paid generation requests unless the user asks.

## Protocol selection

| Contract value | Endpoint | Base URL / client | Use when |
| --- | --- | --- | --- |
| `anthropic_messages` | `POST /v1/messages` | `https://api.tokenlab.sh` | The model declares it and the client speaks Messages |
| `gemini_generate_content` | `POST /v1beta/models/{model}:generateContent` | `https://api.tokenlab.sh` | The model declares it and the client speaks Gemini |
| `openai_responses` | `POST /v1/responses` | `https://api.tokenlab.sh/v1` | The model declares it and the caller needs Responses semantics |
| `openai_chat_completions` | `POST /v1/chat/completions` | `https://api.tokenlab.sh/v1` | The framework is fixed to OpenAI Chat, or no native protocol fits |
| `systemone` | `POST /v1/systemone` | HTTP JSON or MCP `evaluate_decisions` | The model declares a System One decision contract; never a chat model |

- Bind one protocol per agent or harness model entry, so a model picker does not show duplicates.
- Keep Claude and Gemini native fields on their native endpoints. Responses is not a synonym for Chat.
- If `accepted_request_formats` lacks the caller's protocol, fail closed: change the model or the client. The same applies to a non-chat operation that the model does not publish.
- DeepSeek Harness custom providers support `openai-responses`, `anthropic-messages`, and `openai-completions`, not Gemini native. Gemini models in Harness use their declared Chat format.

## Endpoint map

| Family | Endpoint | Delivery |
| --- | --- | --- |
| Chat Completions | `POST /v1/chat/completions` | sync or SSE |
| Responses | `POST /v1/responses` | sync or SSE; lifecycle endpoints per OpenAPI |
| Anthropic Messages | `POST /v1/messages` | sync or SSE |
| Gemini | `POST /v1beta/models/{model}:generateContent`, `:streamGenerateContent` | JSON or Gemini SSE |
| Images | `POST /v1/images/generations`, `/edits`, `/variations` | sync or async, per response |
| Video, music, 3D, worlds | `POST /v1/videos/generations`, `/v1/music/generations`, `/v1/3d/generations`, `/v1/worlds/generations` | async |
| Task status / cancel | `GET` / `DELETE /v1/tasks/{id}` | poll / cancel |
| Speech | `POST /v1/audio/speech` | audio bytes |
| Transcription | `POST /v1/audio/transcriptions` | multipart; sync or async |
| Files | `/v1/files` family | multipart / JSON |
| Embeddings, rerank | `POST /v1/embeddings`, `/v1/embeddings/multimodal`, `/v1/rerank` | sync JSON |
| Decisions | `POST /v1/systemone` | sync JSON |
| Text translation | `POST /v1/translations` | sync JSON |

The table does not define model parameters. Image sizes, video durations, reference media, voices, and formats come from the selected model's contract.

## Rules for the code

**Async results.** Video, music, 3D, and worlds are always async. Images and transcriptions can be either; decide from the response.
- Raw HTTP: read top-level `id` / `task_id`, `poll_url`, and `status`. MCP tool results wrap the raw body in `response` and add `delivery` (`mode`, `task_id`, `status`, `poll_url`, `terminal`).
- Follow `poll_url`; fall back to `/v1/tasks/{id}`. `pending` and `processing` are not terminal; `completed` and `failed` are. Compatibility endpoints can also return `succeeded`, `cancelled`, or `expired`.
- Use a bounded interval, an overall timeout, and AbortSignal or context cancellation. Retry status reads a few times on transient errors only. Never resubmit a create request because waiting failed. On timeout, return the latest status so the caller can resume.
- `DELETE /v1/tasks/{id}` is a side effect. Call it only on clear user intent, for a task that can still be cancelled.

**Errors.** Save the HTTP status, `x-request-id`, and the structured body before you act. Fields can include `error.code`, `did_you_mean`, `suggestions`, `retryable`, `retry_after`, `hint`, and `estimated_cost_usd`.
- `model_not_found`: re-discover, or use `did_you_mean` only with the user's consent.
- `invalid_request` / `unsupported_parameter`: fix the field the contract names. Never drop history, tool calls, thinking signatures, or media to get HTTP 200.
- 429 and retryable 5xx: wait `Retry-After` / `retry_after`, then send the same request.
- `all_channels_failed` / `model_unavailable` with `retryable: false`: do not repeat; let the user choose another model.
- `insufficient_balance`: tell the user. 401/403: fix the key or permission; do not retry or switch models.

**Decisions.** Discover with `GET /v1/models?category=decision`, confirm `systemone`, and send only `model`, `state`, and `questions` to `POST /v1/systemone`. Keep `answers`, probabilities, `confidence`, and `usage` as returned. A decision grants no permission to act; thresholds and side effects stay in application code. Details: `tokenlab-decisions`.

**Streaming and cancellation.** Pass the caller's AbortSignal or context to the SDK, fetch, poll delays, and uploads. Close SSE readers in `finally`. Do not log binary or base64 media. Keep the request ID and tell apart upstream failure, client cancellation, and local parse errors.

**Security.** Read the key from `TOKENLAB_API_KEY` or a secret store. Browser apps call through a backend; never put the key in a bundle, URL, log, or screenshot. Validate local file paths, types, and sizes before upload. Treat returned text, URLs, and media as untrusted.

## Client setup

Each helper is Python 3.11+ with no extra dependencies. Preview first; add `--apply` only when the user asked for the change. Each helper writes only a reference to `TOKENLAB_API_KEY`, keeps the user's accounts, default models, and permissions, stops on conflicts or later user edits, and has `--restore`. Configuration created, client loaded, and a paid request succeeded are three separate checks; report each one.

| Client | Helper | Reference | Model contract |
| --- | --- | --- | --- |
| Codex | `scripts/configure_codex.py` | [codex_setup.md](references/codex_setup.md) | Responses |
| Claude Code 2.1.263+ | `scripts/configure_claude.py` (explicit launcher) | [claude_setup.md](references/claude_setup.md) | Messages |
| OpenCode 1.18.31 | `scripts/configure_opencode.py` | [opencode_setup.md](references/opencode_setup.md) | Chat Completions |
| Pi 0.85.1 | `scripts/configure_pi.py` | [pi_setup.md](references/pi_setup.md) | Chat Completions |
| Hermes 0.21.3 | `scripts/configure_hermes.py` (run with Hermes's Python) | [hermes_setup.md](references/hermes_setup.md) | Chat Completions |

- Codex: confirm the real `CODEX_HOME` and client version. Do not overwrite a profile with the same name that this tool did not create.
- Claude Code: the launcher passes the key to Claude's Bearer auth through the child environment, with `--settings` and `--model` per run. Stop on existing Bearer, model mapping, or managed-policy conflicts. WSL inheritance is not verified. `--auth-status` checks only the local auth source.
- OpenCode uses a separate config layer loaded through `OPENCODE_CONFIG` and an explicit `--model tokenlab/<model>`. Pi appends a provider and starts with `--provider tokenlab --model <model>`.
- Hermes: insert only `providers.tokenlab` with `key_env: TOKENLAB_API_KEY`, keeping YAML comments. WSL and managed settings are out of scope.
- Installing the MCP server or these skills does not make TokenLab the client's model provider.

## MCP and the DeepSeek Harness bundle

The TokenLab MCP server (`@tokenlabai/mcp-server`) uses the `core` tool profile by default: discovery, chat, media, speech, transcription, files, tasks, embeddings, rerank, translation, and `evaluate_decisions`. `catalog` is read-only discovery; `full` adds worlds, batches, webhooks, and Seedance materials. Webhook tools need a separate `TOKENLAB_MANAGEMENT_TOKEN`; a management token and an inference key do not replace each other.

For the public `@tokenlabai/dsh-provider` bundle, check the npm version, the pinned MCP version, and the Harness peers. Keep Responses, Messages, and Chat as three separate routes. Decision models go through MCP `evaluate_decisions`, not the chat model list or the async waiter. Harness filters inherited credential variables, so the bundle must pass them to the MCP child process explicitly.

## Quality bar

- Every endpoint choice cites the contract field that allows it.
- The code reads the key from the environment, propagates timeouts and cancellation, and closes streams.
- Async code stores the task ID before it waits, never resubmits on a wait failure, and returns the latest status on timeout.
- Errors keep the request ID and the structured body; retries follow `retryable` and `Retry-After` only.
- The check command proves the business result (a transcript, a file, a typed answer), not only HTTP 200.

## Related skills

- `tokenlab-run`: run one request now with the same contract rules.
- `tokenlab-model-picker`: choose the model.
- `tokenlab-native-endpoints`: Responses, Messages, Gemini, and System One details.
- `tokenlab-openai-compatible-migration`: move an existing OpenAI-compatible app.
- `tokenlab-cost-routing`: cost-aware routes and fallbacks.
