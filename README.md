# TokenLab Skills

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
