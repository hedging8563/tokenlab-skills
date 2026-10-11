# TokenLab Decisions

- Category: `decision`
- License: MIT

Gets typed answers (yes/no probability, a choice, or a score) about text or JSON from a TokenLab System One decision model, for routing, gating, scoring, and triage. The skill writes the questions, calls `/v1/systemone` or the MCP `evaluate_decisions` tool, and keeps thresholds in your code.

Install:

```bash
npx skills add https://github.com/hedging8563/tokenlab-skills --skill tokenlab-decisions -y
```

Agents should use `SKILL.md`.
