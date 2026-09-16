# TokenLab API Integration

- Category: `coding`
- License: MIT

Canonical coding skill for TokenLab Chat, Responses, Anthropic Messages, Gemini, image, video, music, 3D, audio, files, embeddings, rerank, translation, and asynchronous tasks.

Install non-interactively:

```bash
npx skills add https://github.com/hedging8563/tokenlab-skills --skill tokenlab-api-integration -y
```

The skill uses live public model discovery and `GET /v1/models/{id}` request-format contracts instead of model-name guesses. It includes runnable integration templates, sync-or-async media handling, bounded task polling, cancellation propagation, and structured error recovery.

`search_api.py --detail MODEL_ID --json` includes the published `request_contract`, preserving operation endpoints, request shapes, task status modes, and parameter constraints. The `--client` option selects chat protocol compatibility; media API endpoints come from the operation contract.

Files:

- `SKILL.md`: endpoint selection and implementation rules
- `references/integration_examples.md`: runnable JavaScript, Python, Go, PHP, and cURL patterns
- `scripts/search_api.py`: standard-library, read-only live model discovery
- `scripts/configure_codex.py`: Python 3.11+ Codex profile preview, incremental setup and restoration; no extra dependencies
- `references/codex_setup.md`: configuration commands, credential boundaries and verified systems
- `scripts/configure_claude.py`: explicit Claude Code session launcher setup and restoration; preserves saved accounts, defaults and permissions
- `references/claude_setup.md`: session authentication, supported commands, conflicts and actual-client verification scope
- `scripts/setup_files.py`: shared atomic file operations for the two configuration helpers
- `agents/openai.yaml`: agent-facing display metadata
