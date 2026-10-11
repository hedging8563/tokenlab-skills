# Voice fields per speech model family

Read the live contract before you trust this table: `GET /v1/models/{model}`, then `tokenlab.public_contract.operation_constraints[].parameter_options`. Voice lists change.

| Family | Voice field | Where the voice list is | Other fields in the contract | Output |
| --- | --- | --- | --- | --- |
| Grok TTS | `voice` | `parameter_options.voice`: `eve`, `ara`, `rex`, `sal`, `leo` | `response_format` | `mp3` |
| MiniMax Speech 2.8 HD | `voice` or `voice_id` | `parameter_options.voice` (a long list, for example `English_expressive_narrator`, `English_CalmWoman`, `English_Trustworth_Man`) | `speed`, `response_format` | `mp3`, `wav`, `flac`, `pcm` |
| MiniMax Speech 2.8 Turbo | `voice_id` (or `voice`) | No list in the contract. `recommended_request` uses `male-qn-qingse` | `speed`, `response_format`, `stream_format: "audio"` | `mp3`, `wav`, `pcm`, `flac` |
| ElevenLabs | `voice` | No list in the contract. Ask the user for a voice ID | `language_code`, `seed`, `response_format` | per contract |
| CosyVoice | `voice` | No list in the contract | `speed`, `response_format` (`recommended_request` uses `mp3`) | per contract |
| Qwen TTS Flash | `voice` | `parameter_options.voice` (for example `Cherry`, `Serena`, `Ethan`); default `Cherry` | `language_code`, `speed` | WAV only; `response_format` does not transcode |
| Kling TTS | `voice_id` | No list in the contract | | per contract |

## How to pick a voice

1. Read the use: narration, app prompt, ad, or character line.
2. Shortlist two or three voices whose names or the user's notes fit the tone.
3. Render the same short line (one or two sentences) in each.
4. Let the user choose. Keep model + voice + speed fixed for the rest of the project.

## A known-good body

Live-checked on 2026-10-12 with Grok TTS. Take `MODEL_ID` from the Models list in `SKILL.md` (the Grok TTS entry).

```json
{"model": "MODEL_ID", "input": "Welcome to TokenLab. This short clip tests speech, subtitles, and translation.", "voice": "eve", "response_format": "mp3"}
```

It returned a 5.5 s MP3 (24 kHz mono) in under 2 s.

## Long scripts

- The speech endpoint takes at most 4,096 characters in `input`.
- Split at paragraph breaks first, then at sentence ends. Never split inside a sentence.
- Name the parts in order (`part01.mp3`, `part02.mp3`, ...) and join them with a short pause.
- If the user may edit lines later, keep one file per line so you re-render only the changed lines.
