# TokenLab Voiceover

- Category: `audio`
- License: MIT

Turns a script into natural speech audio with a chosen voice. The skill picks a live TokenLab speech model and voice from the model contract, splits long scripts, and uses `tokenlab-run` for the calls.

Install:

```bash
npx skills add https://github.com/hedging8563/tokenlab-skills --skill tokenlab-voiceover -y
```

Agents should use `SKILL.md`.
