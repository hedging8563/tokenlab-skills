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

The hosted MCP entry is intentionally read-only and does not contain a TokenLab API key. The stdio entry defaults to the public `catalog` profile; set `TOKENLAB_MCP_TOOL_PROFILE=core` or `full` in the environment that launches Claude Code when the client should expose credentialed tools, then restart Claude Code. Set `TOKENLAB_API_KEY` separately for those calls; changing the profile does not change approvals or grant API permissions. The profile uses Claude Code's documented [environment-variable default syntax](https://code.claude.com/docs/en/mcp#environment-variable-expansion-in-mcpjson).

## Codex plugin installation

Codex CLI 0.149.0 can consume this marketplace:

```bash
codex plugin marketplace add hedging8563/tokenlab-skills
codex plugin add tokenlab@tokenlab-tools
```

The plugin and the standalone Skills installation above are alternative ways to load the same skills. Neither changes the client's default model provider. See the API integration skill's [Codex](skills/tokenlab-api-integration/references/codex_setup.md), [Claude Code](skills/tokenlab-api-integration/references/claude_setup.md), [OpenCode](skills/tokenlab-api-integration/references/opencode_setup.md), [Pi](skills/tokenlab-api-integration/references/pi_setup.md), and [Hermes](skills/tokenlab-api-integration/references/hermes_setup.md) setup references when you explicitly want TokenLab as a model provider.

## Update an existing installation

Plugin release **0.1.3** adds the reversible Hermes setup helper alongside Codex, Claude Code, OpenCode and Pi. `.claude-plugin/plugin.json` owns the plugin version. The marketplace's metadata version describes the marketplace manifest, not the installed plugin release. A Git push alone does not refresh a cached Claude plugin whose version remains unchanged; see [Claude's version rules](https://code.claude.com/docs/en/plugins-reference#version-management).

For a Claude Code plugin installation:

```text
/plugin marketplace update tokenlab-tools
/plugin update tokenlab@tokenlab-tools
```

Restart Claude Code after updating. For a Codex plugin installation, refresh the marketplace snapshot and install the updated version:

```bash
codex plugin marketplace upgrade tokenlab-tools
codex plugin add tokenlab@tokenlab-tools
codex plugin list --json
```

For skills installed through `npx skills`, update that skill in its original scope. The Skills CLI tracks source content independently of the plugin version:

```bash
# Run in the project where you installed the skill:
npx skills update tokenlab-api-integration --project

# Or, if it was installed globally:
npx skills update tokenlab-api-integration --global
```

Check that the installed API integration skill includes the required helper, including `scripts/configure_hermes.py` for Hermes, before following its setup reference. Other skill names can be updated individually using the same command.
