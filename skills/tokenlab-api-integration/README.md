# TokenLab API Integration

- Category: `coding`
- License: MIT

Canonical coding skill for TokenLab Chat, Responses, Anthropic Messages, Gemini, image, video, music, 3D, audio, files, embeddings, rerank, translation, and asynchronous tasks.

Install non-interactively:

```bash
npx skills add https://github.com/hedging8563/tokenlab-skills --skill tokenlab-api-integration -y
```

The skill uses live public model discovery and `GET /v1/models/{id}` request-format contracts instead of model-name guesses. It includes runnable integration templates, sync-or-async media handling, bounded task polling, cancellation propagation, and structured error recovery.

Files:

- `SKILL.md`: endpoint selection and implementation rules
- `references/integration_examples.md`: runnable JavaScript, Python, Go, PHP, and cURL patterns
- `scripts/search_api.py`: standard-library, read-only live model discovery
- `agents/openai.yaml`: agent-facing display metadata
