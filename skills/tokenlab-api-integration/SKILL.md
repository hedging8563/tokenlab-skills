---
name: tokenlab-api-integration
description: Integrates TokenLab chat, image, audio, video, and other API families into code with runnable examples, model discovery, public contract checks, and agent-first recovery paths. Use when the user wants to add TokenLab APIs to an app or script.
license: MIT
metadata:
  category: coding
---

# TokenLab API Integration

Built for runnable integration work for TokenLab chat, image, audio, video, and other API families across coding agents.

## What this skill should deliver

- A minimal runnable example using the fewest moving parts possible.
- The exact base URL, auth shape, install command, and environment variables required to run the example.
- A concise note on when to stay on the OpenAI-compatible path versus switching to a native Anthropic or Gemini route.
- For non-chat APIs, a model discovery or contract check before hardcoding request shape details.
- A concrete default model choice that is plausible on TokenLab, not a generic placeholder.
- A short explanation of the agent-first recovery path when the model, endpoint, or route guess is wrong.

## Preferred approach

1. Clarify the user's goal, inputs, and required deliverable.
2. Read [references/usage-notes.md](references/usage-notes.md) before acting.
3. Produce one concrete output before adding explanation.
4. Use the following operating rules:

- Start with the smallest working example before introducing abstractions or helper layers.
- State the base URL explicitly and keep the environment setup copy-pasteable.
- When model selection is open, show how to discover models through `/v1/models` or `https://api.tokenlab.sh/llms.txt` instead of hardcoding one option.
- For non-chat model selection, prefer `GET /v1/models?recommended_for=<scene>` where `<scene>` is one of `image`, `video`, `music`, `3d`, `tts`, `stt`, `embedding`, `rerank`, or `translation`.
- Before retrying a failed non-chat request, read `GET /v1/models/:model` and align with the public contract, including `supported_operations`, `supported_parameters`, `request_endpoint`, `request_shape_mode`, and `recommended_request`.
- Use native Anthropic or Gemini examples only when the request explicitly needs provider-specific behavior.

## Output format

- One short intro sentence explaining what the example does.
- One runnable code block only.
- One shell setup block showing both dependency install and the exact environment variable export.
- One short model discovery note.
- One short routing note explaining when to stay on the OpenAI-compatible path and when a response header or provider-specific feature suggests a native Anthropic or Gemini route.

## Avoid

- Do not return pseudo-code when runnable code is expected.
- Do not hide required environment variables, auth headers, or base URLs.
- Do not over-claim pricing, speed, or compatibility without grounding it in a concrete example or source.
- Do not claim an exact platform-wide model count; say "hundreds of models" unless the current API response is being quoted directly.
- Do not silently drop unsupported non-chat fields. If removing a field would change user intent, safety, billing, or response guarantees, surface the contract error and fail closed.

## Inputs

- Natural-language user request
- Referenced files or URLs
- Existing project context, if available

## Outputs

- A concrete deliverable, recommendation, or implementation result
- Short notes on assumptions, caveats, or next actions when needed

## Edge Cases

- If required inputs are missing, state exactly what is missing.
- If the request only partially matches this skill, handle the matching portion and clearly scope the rest.
- If a risk, safety, or compliance concern appears, surface it before producing the final output.
