# Usage Notes

This reference file supports `tokenlab-api-integration`.

## When this skill is most useful

- A minimal runnable example using the fewest moving parts possible.
- The exact base URL, auth shape, install command, and environment variables required to run the example.
- A concise note on when to stay on the OpenAI-compatible path versus switching to a native Anthropic or Gemini route.
- A contract-aware path for non-chat APIs before choosing model-specific parameters.
- A concrete default model choice that is plausible on TokenLab, not a generic placeholder.

## Delivery hints

- Write from a developer point of view: concrete examples beat abstract feature lists.
- Keep claims precise and verifiable; avoid hype language and empty marketing modifiers.
- The next step after reading should be obvious: run the sample, switch the base URL, or inspect available models.
- OpenAI-compatible base URL: https://api.tokenlab.sh/v1
- Anthropic-native base URL: https://api.tokenlab.sh (no /v1 suffix)
- Gemini-native endpoint uses the same host: https://api.tokenlab.sh
- Machine-readable API overview: https://api.tokenlab.sh/llms.txt
- General model discovery: GET https://api.tokenlab.sh/v1/models
- Non-chat model shortlists: GET https://api.tokenlab.sh/v1/models?recommended_for=image|video|music|3d|tts|stt|embedding|rerank|translation
- Model-specific public contract: GET https://api.tokenlab.sh/v1/models/:model
- Pricing-only detail: GET https://api.tokenlab.sh/v1/models/:model/pricing
- When Claude or Gemini models are called through /v1/chat/completions, TokenLab may return X-TokenLab-Hint and X-TokenLab-Native-Endpoint headers recommending a native route. Treat the header as a recommendation that the agent should evaluate, not as a forced automatic switch.
- Claude native calls use `/v1/messages`. Gemini native calls use `/v1beta/models/{model}:generateContent`; when TokenLab returns `X-TokenLab-Native-Endpoint`, prefer the exact route in that header.
- For OpenAI-compatible examples, include one concrete default model such as `gpt-5.5`, `claude-sonnet-5`, `gemini-3.5-flash`, or another model verified through the current catalog.
- If the first model or endpoint guess is wrong, the response should guide the agent to self-correct instead of forcing a docs search first.
- For model_not_found, inspect did_you_mean, suggestions, and hint.
- For insufficient_balance, inspect balance_usd, estimated_cost_usd, suggestions, and hint before switching to a cheaper model.
- For rate_limit or temporary model availability, inspect retryable and retry_after before retrying.
- For non-chat contract errors, inspect supported_operations, supported_parameters, allowed_resolutions, allowed_durations, allowed_aspect_ratios, request_endpoint, request_shape_mode, status_mode, contract_scope, and recommended_request before changing the request.
- Use "hundreds of models" for platform-wide count claims unless you are quoting a current API response directly.
