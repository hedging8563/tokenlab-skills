---
name: tokenlab-voiceover
description: "Turn a script into natural speech audio with a chosen voice, using TokenLab text-to-speech models. Use when the user says \"read this script aloud\", \"make a voiceover for my video\", \"narrate this\", \"text to speech\", \"give this a male / female / calm voice\", \"podcast intro audio\", or \"voice for my app\". Picks a model and voice from the live contract, splits long scripts, and returns audio files. For a face that speaks the audio, use tokenlab-talking-avatar. For subtitles or a transcript of existing audio, use tokenlab-transcribe-and-subtitle. For songs or sung vocals, use tokenlab-music."
license: MIT
metadata:
  category: audio
---

# Voiceover

Turn a written script into clean speech audio. The speech endpoint is synchronous and returns audio bytes, so there is no task to poll. The work is choosing the voice, shaping the script, and splitting long text.

## Inputs to collect

- **Script:** the exact words. Ask before you rewrite them.
- **Voice:** gender, age, tone (calm, upbeat, authoritative), and accent. Or a voice ID the user already likes.
- **Language** of the script.
- **Use:** video narration, app prompts, ads, audiobook, or phone audio. This decides pace and file format.
- **Format:** `mp3` for most uses, `wav` or `flac` for editing, when the model offers them.

## Models

Confirm each pick with `tokenlab-model-picker` or `GET /v1/models/{model}` before you call it. Prices and supply change. Find current speech models with `GET /v1/models?recommended_for=tts`.

| Need | Default | Alternatives | Fast / low-cost |
| --- | --- | --- | --- |
| General narration and app voice | `grok-tts` (`voice`: `eve`, `ara`, `rex`, `sal`, `leo`; `mp3`) | `eleven-v4-turbo` (`voice`, `language_code`, `seed`), `cosyvoice-v3.5-plus` (`voice`, `speed`) | `qwen3-tts-flash` (named voices, WAV output) |
| Large voice library, speed control | `speech-2.8-hd` (`voice` from a long published list, or `voice_id`; `speed`; `mp3`, `wav`, `flac`, `pcm`) | `speech-2.8-turbo` (`voice_id`, `speed`, same formats) | `speech-2.8-turbo` |
| Many short lines at a flat per-request price | `kling-tts` (`input`, `voice_id`) | | |

Most speech models price per input character. `kling-tts` prices per request. Read `pricing_unit` before you estimate.

## Workflow

Run each call with `tokenlab-run` (contract → estimate → call → poll → result).

1. Read the contract: `python scripts/tokenlab_run.py contract MODEL --operation tts`. Note `supported_parameters` and `parameter_options` (voice names, `response_format` values). Send only listed fields. `grok-tts` takes `input`, `voice`, `response_format`.
2. Pick the voice from `parameter_options.voice`. If the model lists no voice options, use the voice from `recommended_request`, or ask the user for a `voice_id`. Do not invent voice names.
3. Estimate: count the characters in `input` and multiply by the per-character price from `GET /v1/models/{model}/pricing`. Per-character prices are quoted per 1M characters. Example: 78 characters × (price per 1M characters) / 1,000,000.
4. Split scripts longer than 4,096 characters (the endpoint limit) at paragraph or sentence breaks. Use one voice and the same settings for every part. Join the files in order.
5. Call `POST /v1/audio/speech` and save the bytes: `python scripts/tokenlab_run.py run /v1/audio/speech --json @body.json --out line01.mp3`. Allow a client timeout of at least 120 s for long input. Keep the `x-request-id`.
6. Check the file: it plays, its length fits the script, and the format is what you asked for. Some models return one fixed format; trust the response `Content-Type` over the requested format.
7. Return the file paths, model, voice, and character count. TTS has no result URL; store the files yourself.

## Technique

- **Punctuation sets the pace.** Commas, periods, and question marks guide timing and tone. "That's amazing!" sounds excited; "That's amazing." sounds flat. Paragraph breaks give natural pauses.
- **`grok-tts` speech tags.** Inline tags go where the sound would happen: `[pause]`, `[long-pause]`, `[laugh]`. Wrapping tags change a span: `<whisper>...</whisper>`, `<slow>...</slow>`, `<soft>...</soft>`. Tags are not read aloud. Punctuation plus one inline tag sounds more natural than a stack of inline tags. Wrapping tags can nest: `<slow><soft>Goodnight.</soft></slow>`. These tags are for `grok-tts`; check the model maker's guide before you use tags on another model.
- **Write numbers and names the way they are said.** "twenty twenty-six", "four point five". Test hard names on a short line first.
- **Speed:** use `speed` only where the contract lists it (`speech-2.8-*`, `cosyvoice-v3.5-plus`, `qwen3-tts-flash`). Keep it near 1 for narration.
- **One voice per character.** For dialogue, give each speaker a fixed voice and render line by line. Keep a table of line → voice → file.
- **Short test first.** Render one sentence in two or three voices, let the user pick, then render the full script.

See `references/voices.md` for the voice fields per model and how to pick one.

## Quality bar

- Every word of the script is spoken, in order, with no added words.
- One voice and one speed across all parts of one narration.
- No clicks or long silences at the joins between parts.
- Names, numbers, and brand terms are said correctly.
- The user got the estimate before a long script, and the final answer names the model, voice, and files.

## Related skills

- `tokenlab-run`: the call and result mechanics.
- `tokenlab-talking-avatar`: put the voiceover on a speaking face.
- `tokenlab-transcribe-and-subtitle`: subtitle the finished voiceover.
- `tokenlab-music`: background music or a song under the voice.
- `tokenlab-prompting`: prompt craft per model family.
