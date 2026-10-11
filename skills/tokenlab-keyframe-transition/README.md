# TokenLab Keyframe Transition

- Category: `video`
- License: MIT

Makes a video that starts on one image and ends on another. The skill checks the two frames, picks a live TokenLab start-end-to-video model, and uses `tokenlab-run` for the contract, cost estimate, call, and polling.

Install:

```bash
npx skills add https://github.com/hedging8563/tokenlab-skills --skill tokenlab-keyframe-transition -y
```

Agents should use `SKILL.md`.
