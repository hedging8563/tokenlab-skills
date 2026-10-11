# `suno-music` request shapes

All shapes go to `POST /v1/music/generations` and return a task. Check the live contract first: `GET /v1/models/suno-music`, then `operation_constraints[].supported_parameters` and `notes`. Prices differ by action; read `GET /v1/models/suno-music/pricing`.

## Generate a song

```json
{"model": "suno-music", "mv": "chirp-v5", "title": "Small Lights",
 "tags": "indie folk, acoustic guitar, warm female vocal, gentle",
 "prompt": "A short, gentle indie folk song about city lights coming on after rain. Simple verse and chorus."}
```

Live-checked on 2026-10-12: completed in about 34 s and returned `audio_url` (a 35 s MP3), `image_url` (cover art), `title`, and `audio_id`.

- `mv` is required for generation. Accepted values from the API reference: `chirp-v3-5`, `chirp-v4`, `chirp-v4-5`, `chirp-v4-5plus`, `chirp-v4-5all`, `chirp-v5`, `chirp-v5-5`.
- Add `make_instrumental: true` for no vocals.
- Add `negative_tags` for styles to avoid.
- `prompt` takes up to 5,000 characters; `tags` and `negative_tags` up to 1,000 each.

## Work on an existing track

Set `audio_operation` and the fields it needs. These rules come from the model contract notes.

| `audio_operation` | Source | Required fields |
| --- | --- | --- |
| `upload-cover` (default when `audio_url` is sent alone) | `audio_url` (public audio URL) | `mv`, `prompt` |
| `upload-extend` | `audio_url` | `mv`, `prompt`, `continue_at` > 0 |
| `add-instrumental` | `audio_url` | `mv`, `title`, `tags`, `negative_tags` |
| `replace-section` | `task_id` + `audio_id`, or `audio_url` + `mv` | `prompt`, `tags`, `title`, `infill_start_s`, `infill_end_s` (6–60 s apart), `full_lyrics` |
| `vocal-separate` | `task_id` + `audio_id` | |
| `multi-stem-separation` | `task_id` + `audio_id` | |
| `advanced-split` | `task_id` + `audio_id` | `stem_name` |

`task_id` is the TokenLab task ID of the source song (it must belong to your organization). `audio_id` is in that task's result. Keep both when you deliver a song the user may edit.

To continue a generated clip, the API reference also lists `continue_clip_id` with optional `continue_at`.

## Lyrics only

The API reference describes `action: "LYRICS"` without `mv` for models whose public operations include `lyrics`. Check `public_operations` before you use it; a music-only model does not gain lyrics support from this field.
