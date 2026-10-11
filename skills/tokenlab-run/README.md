# TokenLab Run

- Category: `foundation`
- License: MIT

The execution contract that every TokenLab outcome skill uses: read the model contract, pick the operation, estimate the cost, provide inputs, call the endpoint, wait for async tasks, and read the result URLs.

Install:

```bash
npx skills add https://github.com/hedging8563/tokenlab-skills --skill tokenlab-run -y
```

Files:

- `SKILL.md`: the procedure, error table, and quality bar
- `references/recipes.md`: starting request bodies per endpoint family
- `scripts/tokenlab_run.py`: standard-library CLI with `contract`, `price`, `run --wait`, `poll`, `cancel`, and `upload`
- `agents/openai.yaml`: agent-facing display metadata
