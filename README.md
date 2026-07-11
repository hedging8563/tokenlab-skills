# TokenLab Skills

[![Validate skills](https://github.com/hedging8563/tokenlab-skills/actions/workflows/validate.yml/badge.svg)](https://github.com/hedging8563/tokenlab-skills/actions/workflows/validate.yml)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-111827)](https://agentskills.io/specification)

This repository contains public agent skills released by TokenLab.

## Repository contents

- `skills/tokenlab-api-integration/` - Build runnable TokenLab API integrations.
- `skills/tokenlab-cost-routing/` - Choose TokenLab models with cost, latency, and fallback constraints.
- `skills/tokenlab-model-picker/` - Choose TokenLab models from public catalog signals.
- `skills/tokenlab-native-endpoints/` - Use TokenLab native Responses, Anthropic Messages, and Gemini routes.
- `skills/tokenlab-openai-compatible-migration/` - Migrate OpenAI-compatible apps and SDKs to TokenLab safely.
- Distribution-facing README and license information

Older generated skills, skills-factory outputs, and sync artifacts are intentionally not part of this repository. TokenLab ships only maintained, documented skills here.

## Skill format

Published skills follow the Agent Skills specification and use `SKILL.md` as the agent-facing entry point.

- Spec: https://agentskills.io/specification
- Canonical repo: https://github.com/hedging8563/tokenlab-skills

## Recommended install

```bash
npx skills add https://github.com/hedging8563/tokenlab-skills --skill tokenlab-api-integration -y
npx skills add https://github.com/hedging8563/tokenlab-skills --skill tokenlab-cost-routing -y
npx skills add https://github.com/hedging8563/tokenlab-skills --skill tokenlab-model-picker -y
npx skills add https://github.com/hedging8563/tokenlab-skills --skill tokenlab-native-endpoints -y
npx skills add https://github.com/hedging8563/tokenlab-skills --skill tokenlab-openai-compatible-migration -y
```

## Claude Code Plugin Marketplace

This repository is also a Claude Code plugin marketplace. It bundles the five maintained skills with two optional TokenLab MCP connections:

- `tokenlab-stdio` runs the published `@tokenlabai/mcp-server` locally over stdio. Public catalog tools work without a key; set `TOKENLAB_API_KEY` only when credentialed tools are needed.
- `tokenlab-hosted-model-explorer` connects to the public hosted Model Explorer over Streamable HTTP. It exposes read-only model discovery, comparison, and endpoint-example tools.

Add and install it from Claude Code:

```text
/plugin marketplace add hedging8563/tokenlab-skills
/plugin install tokenlab@tokenlab-tools
```

The installed skill names are namespaced as `/tokenlab:tokenlab-api-integration`, `/tokenlab:tokenlab-cost-routing`, `/tokenlab:tokenlab-model-picker`, `/tokenlab:tokenlab-native-endpoints`, and `/tokenlab:tokenlab-openai-compatible-migration`.

The hosted MCP entry is intentionally read-only and does not contain a TokenLab API key. The stdio entry defaults to the public `catalog` profile; set `TOKENLAB_MCP_TOOL_PROFILE=core` or `full` in the local environment when the client should expose credentialed tools.
