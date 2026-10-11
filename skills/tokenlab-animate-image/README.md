# TokenLab Animate Image

- Category: `video`
- License: MIT

Turns one still image into a short video clip. The skill picks a live TokenLab image-to-video model, writes a motion-first prompt, and uses `tokenlab-run` for the contract, cost estimate, call, and polling.

Install:

```bash
npx skills add https://github.com/hedging8563/tokenlab-skills --skill tokenlab-animate-image -y
```

Agents should use `SKILL.md`.
