# TokenLab Extend Video

- Category: `video`
- License: MIT

Continues a video clip past its last frame. The skill picks the right extension input (a public video URL or a TokenLab task ID), checks the source clip, and uses `tokenlab-run` for the contract, cost estimate, call, and polling.

Install:

```bash
npx skills add https://github.com/hedging8563/tokenlab-skills --skill tokenlab-extend-video -y
```

Agents should use `SKILL.md`.
