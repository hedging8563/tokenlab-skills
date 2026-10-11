---
name: tokenlab-openai-compatible-migration
description: "Move an existing OpenAI-compatible app, SDK wrapper, LiteLLM or LangChain config, or OpenRouter setup to TokenLab with the smallest diff: change the base URL and key variable, map model IDs from the live catalog, keep native semantics, and keep a rollback. Use when the user says \"switch my app to TokenLab\", \"replace OpenAI/OpenRouter with TokenLab\", or \"what do I change in my config\". For new code from scratch, use tokenlab-api-integration. For Responses, Messages, or Gemini-native behavior, use tokenlab-native-endpoints."
license: MIT
metadata:
  category: coding
---

# TokenLab OpenAI-Compatible Migration

Move an existing integration to TokenLab without changing how it works. Change configuration first; change code only where the old provider's model IDs or endpoints have no direct match.

## What this skill delivers

- A minimal diff or config block.
- The TokenLab base URL and key variable.
- A model mapping from the live catalog, with each mapped ID confirmed.
- A note for each call that needs a native endpoint instead of chat.
- A smoke test command and a one-line rollback.

## Inputs to collect

- Where the provider is configured: environment variables, SDK constructors, config files.
- Every model ID in use, and which endpoint family each one calls (chat, Responses, embeddings, images, audio).
- Provider-specific headers or fields the app sends.

## Models

<!-- tokenlab:models:start -->
<!-- Generated from the live catalog by scripts/sync_models.py. Do not edit; change preferredModels in catalog.json. -->

| Operation | Model | Pick | Use |
| --- | --- | --- | --- |
| `chat` | `gpt-5.6-luna` | default | Example for Chat Completions |

This list refreshes daily from the live catalog. Preferred models come first; otherwise models are ranked by their 24-hour success rate. Before a call, confirm the model with `GET /v1/models/{model}` and read its price from `GET /v1/models/{model}/pricing`.
<!-- tokenlab:models:end -->

The model above is only an example for a smoke test. Map each model the app uses with `tokenlab-model-picker`; never assume a name match.

## Migration targets

| Client | Base URL | Path | Key |
| --- | --- | --- | --- |
| OpenAI-compatible SDK | `https://api.tokenlab.sh/v1` | `/chat/completions` | `Authorization: Bearer $TOKENLAB_API_KEY` |
| Anthropic SDK | `https://api.tokenlab.sh` | `/v1/messages` | key in the SDK |
| Gemini SDK | `https://api.tokenlab.sh` | `/v1beta/models/{model}:generateContent` | key in the SDK |

## Workflow

1. Find the provider configuration, key variables, and model IDs.
2. Change the base URL and the key variable. Keep the SDK, client shape, and request code as they are.
3. Map each model ID: look it up in `GET /v1/models` (or through `tokenlab-model-picker`), then confirm the endpoint in `GET /v1/models/{model}` (`accepted_request_formats` for chat; `public_operations` for media). Report any model with no clear match and let the user choose.
4. Keep native semantics: calls that use Responses, Anthropic Messages, Gemini parts, tools, media, audio, embeddings, rerank, or translation stay on their own endpoints.
5. Run the smoke test:

   ```bash
   curl https://api.tokenlab.sh/v1/chat/completions \
     -H "Authorization: Bearer $TOKENLAB_API_KEY" -H "Content-Type: application/json" \
     -d '{"model": "MODEL_ID", "messages": [{"role": "user", "content": "Reply with OK."}]}'
   ```

6. Write the rollback line: the old base URL and key variable.

## Rules

- Do not rewrite the SDK architecture when a base URL change is enough.
- Do not flatten Anthropic or Gemini payloads into chat unless the user accepts the behavior change.
- Do not change a model silently; an OpenRouter slug or another provider's name maps only after a catalog check.
- Keep only headers that TokenLab documents or the app still needs.
- Never put keys in source files or prompts.
- Apps with separate base URLs for chat, embeddings, and media: migrate one family at a time.

## Quality bar

- The diff touches configuration first; every code change has a reason.
- Every mapped model ID exists in the live catalog and declares the endpoint the app calls.
- The smoke test passes on a real response, and the rollback restores the old provider.

## Related skills

- `tokenlab-model-picker`: map and confirm model IDs.
- `tokenlab-native-endpoints`: calls that need a native protocol.
- `tokenlab-api-integration`: new code and client setup.
