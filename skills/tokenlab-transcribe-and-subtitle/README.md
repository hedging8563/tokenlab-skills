# TokenLab Transcribe and Subtitle

- Category: `audio`
- License: MIT

Turns audio or video into a transcript, SRT or VTT subtitles, and translated subtitles. The skill gets timed segments from a live TokenLab speech-to-text model, builds subtitle files with `scripts/subtitles.py`, translates cue by cue on `/v1/translations`, and uses `tokenlab-run` for the calls.

Install:

```bash
npx skills add https://github.com/hedging8563/tokenlab-skills --skill tokenlab-transcribe-and-subtitle -y
```

Agents should use `SKILL.md`.
