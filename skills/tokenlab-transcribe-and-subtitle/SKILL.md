---
name: tokenlab-transcribe-and-subtitle
description: "Turn audio or video into a transcript, SRT or VTT subtitles, and translated subtitles with TokenLab speech-to-text and text translation models. Use when the user says \"transcribe this recording\", \"make subtitles for my video\", \"I need an SRT file\", \"caption this podcast\", \"what does this audio say\", or \"translate these subtitles into Spanish\". Gets timed segments, builds SRT/VTT, and translates cue by cue so timings stay. To turn a script into speech, use tokenlab-voiceover. For a talking video from a script, use tokenlab-talking-avatar."
license: MIT
metadata:
  category: audio
---

# Transcribe and Subtitle

Turn speech into text you can ship: a clean transcript, timed SRT or VTT subtitles, and the same subtitles in other languages. Transcription and text translation are two different endpoints and two different models.

## Inputs to collect

- **Audio or video file:** flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, or webm. Max 25 MB per request.
- **Spoken language,** if known (ISO-639-1, for example `en`, `zh`, `ja`).
- **Output:** plain transcript, SRT, VTT, or word timings.
- **Subtitle rules:** max characters per line (42 is a common default), and target languages.
- **Terms to spell right:** names, brands, and jargon.

## Models

Confirm each pick with `tokenlab-model-picker` or `GET /v1/models/{model}` before you call it. Prices and supply change. Find current models with `GET /v1/models?recommended_for=stt` and `GET /v1/models?recommended_for=translation`.

| Stage | Default | Alternatives | Fast / low-cost |
| --- | --- | --- | --- |
| Timed transcript for subtitles | `whisper-large-v3-turbo` (`response_format: "verbose_json"`, `timestamp_granularities[]=word`) | `whisper-large-v3` | `whisper-large-v3-turbo` |
| Plain transcript (no timings needed) | `qwen3-asr-flash` (`language`, `prompt`, `response_format`: `json`, `text`, `verbose_json`) | `fun-asr` (can return a task), `grok-stt`, `fish-transcribe-1` (`json` only) | `whisper-large-v3-turbo` |
| Translate transcript or cue text | `doubao-seed-translation` on `/v1/translations` (`text`, `target_language`, `source_language`) | A chat model, when you need tone or glossary control | |

Do not use `/v1/audio/translations` for this skill. Translate the text with `/v1/translations` instead.

## Workflow

Run each call with `tokenlab-run` (contract → estimate → call → poll → result).

1. Read the contracts: `python scripts/tokenlab_run.py contract whisper-large-v3-turbo --operation stt` and `contract doubao-seed-translation --operation translation`.
2. Check the file. If it is over 25 MB, cut it into parts at silences, or extract a mono audio track from the video (for example `ffmpeg -i in.mp4 -vn -ac 1 -b:a 64k out.mp3`). Keep each part's start offset.
3. Estimate. Speech-to-text prices per second of audio; some models bill a minimum length per request (read `minimumUnitCount` in `GET /v1/models/{model}/pricing`). Example: a 5.5 s clip on a 10 s minimum is billed as 10 s × (price per second). Translation prices per token.
4. Transcribe with timings. Multipart upload:
   `python scripts/tokenlab_run.py run /v1/audio/transcriptions --form model=whisper-large-v3-turbo --form response_format=verbose_json --form 'timestamp_granularities[]=word' --form language=en --file file=@clip.mp3 > transcript.json`
   The response can be the transcript or a task (`status` + `poll_url`). If it is a task, poll it.
5. Build subtitles from the timings: `python scripts/subtitles.py transcript.json --format srt --max-chars 42 > clip.en.srt` (or `--format vtt`). This works even when a model cannot return SRT or VTT itself. Add each part's start offset if you split the file.
6. Translate cue by cue, so each cue keeps its time:
   - `python scripts/subtitles.py transcript.json --max-chars 42 --text-only > cues.en.txt`
   - Send the lines as `text` to `/v1/translations` with `target_language`. Write the returned `text` to `cues.es.txt`.
   - `python scripts/subtitles.py transcript.json --max-chars 42 --texts cues.es.txt > clip.es.srt`
   If the line count does not match, translate in smaller batches or one cue per request.
7. Return the transcript text, the subtitle files, the models, and the request IDs.

## Technique

- **Ask for `verbose_json`.** It returns `segments` with `start` and `end`, and word timings when you ask for them. Build SRT/VTT from that. Direct `response_format=srt` or `vtt` is documented for Whisper, but if it fails, the `verbose_json` path still works.
- **Whisper fields.** The Whisper model contracts list only `file` and `language`, but the transcription API reference documents `response_format` and `timestamp_granularities` for Whisper, and both work today. If a call returns `400 unsupported_parameter`, drop them and fall back to plain `json` text.
- **Send `language` when you know it.** It avoids a wrong-language guess on short or noisy clips.
- **Use `prompt` for spelling** on models that list it (`qwen3-asr-flash`): put names and terms in it, for example "TokenLab, Kubernetes, Dr. Okafor".
- **Not every `verbose_json` has timings.** Some models return only `text`, `language`, and `duration`. Use a Whisper model when you need segments.
- **Cue length:** about 42 characters per line and one or two lines per cue reads well. `--max-chars` splits long segments on word timings.
- **Translate text, not files.** Send cue lines, not the SRT with timestamps; the translator can merge or drop lines. Keep the line count equal to the cue count.
- **Clean audio wins.** Mono, normal level, and little music under the voice give better text than any setting.

## Quality bar

- The transcript matches the audio; names and terms are spelled right.
- Subtitle times line up with speech, with no overlaps and no cue longer than the line limit.
- Translated subtitles have the same cue count and times as the source.
- The final answer lists files, models, request IDs, and any parts you split.

## Related skills

- `tokenlab-run`: the call, poll, and result mechanics.
- `tokenlab-voiceover`: speech audio from a script.
- `tokenlab-talking-avatar`: a speaking video from a portrait and audio.
- `tokenlab-api-integration`: put this flow into application code.
