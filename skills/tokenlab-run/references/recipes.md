# TokenLab request recipes

Each body is a starting point. Check the model's `operation_constraints` before you send it, and replace the model ID with one that is live today. All create calls use `POST`, `Authorization: Bearer $TOKENLAB_API_KEY`, and `Content-Type: application/json` unless marked multipart.

## Images: `/v1/images/generations`

Text-to-image:

```json
{"model": "flux-2-pro", "operation": "text-to-image", "prompt": "...", "n": 1}
```

Image-to-image or image-edit on a model whose contract maps the operation to `/v1/images/generations`:

```json
{"model": "nano-banana-2", "operation": "image-to-image", "prompt": "...", "image_urls": ["https://..."], "aspect_ratio": "1:1"}
{"model": "bria-rmbg-v2-0", "operation": "image-edit", "image_url": "https://..."}
```

Size fields differ by family. Some take `width` / `height`, some `size` (`1024x1024`), some `aspect_ratio` plus `resolution`. Use only what `supported_parameters` lists.

## Images: `/v1/images/edits`

Use this endpoint only when the contract maps `image-edit` to it (for example `gpt-image-2`, `stability-*`, some Gemini image models). JSON form:

```json
{"model": "gpt-image-2", "prompt": "...", "image_url": "https://...", "size": "1024x1024"}
```

Multipart form: `model`, `prompt`, one or more `image` files, optional `mask` PNG. For `file_id` input, upload with `POST /v1/files` (`purpose=user_data`, `model=<edit model>`) and send `{"images": [{"file_id": "file_..."}]}`.

## Video: `/v1/videos/generations` (always async)

```json
{"model": "grok-imagine-video", "operation": "text-to-video", "prompt": "...", "duration": 2, "resolution": "480p", "aspect_ratio": "16:9"}
{"model": "grok-imagine-video", "operation": "image-to-video", "prompt": "...", "image_url": "https://...", "duration": 2, "resolution": "480p"}
{"model": "<start-end model>", "operation": "start-end-to-video", "prompt": "...", "start_image": "https://...", "end_image": "https://..."}
{"model": "<reference model>", "operation": "reference-to-video", "prompt": "...", "reference_images": ["https://..."]}
{"model": "grok-imagine-video", "operation": "video-to-video", "prompt": "...", "video_url": "https://....mp4"}
{"model": "grok-imagine-video", "operation": "video-extension", "prompt": "...", "task_id": "ldtask_..."}
{"model": "kling-2.6-motion-control", "operation": "motion-control", "image_url": "https://...", "video_url": "https://....mp4", "resolution": "720p"}
```

`duration` is the output length in seconds. Allowed values are per model and per operation.

## Music: `/v1/music/generations` (async)

```json
{"model": "<music model>", "prompt": "...", "title": "...", "tags": "lo-fi, mellow"}
```

Suno-style models take `mv`, `action`, `make_instrumental`, and `audio_operation` fields. Use them only when the model's contract lists them.

## 3D: `/v1/3d/generations` (async, no `operation` field)

```json
{"model": "tripo-h3.1", "prompt": "a low-poly robot mascot"}
{"model": "tripo-h3.1", "prompt": "the object in the photo", "image_url": "https://..."}
```

## Worlds: `/v1/worlds/generations` (async)

```json
{"model": "marble-1.0-draft", "prompt": "a quiet coastal town at sunset"}
```

## Speech: `/v1/audio/speech` (returns audio bytes)

```json
{"model": "grok-tts", "input": "Hello there.", "voice": "eve", "response_format": "mp3"}
```

## Transcription: `/v1/audio/transcriptions` (multipart)

Fields: `model`, `file` (max 25 MB), optional `language`, `response_format` (`json`, `text`, `srt`, `vtt`, `verbose_json` where the model supports them).

## Text translation: `/v1/translations`

```json
{"model": "doubao-seed-translation", "text": "...", "target_language": "es"}
```

## Decisions: `/v1/systemone` (sync)

```json
{"model": "jev-1.13", "state": "...", "questions": {"refund": {"type": "noul", "instructions": "Is a refund requested?"}}}
```

## Tasks

- `GET {poll_url}` or `GET /v1/tasks/{id}`: status and result.
- `DELETE /v1/tasks/{id}`: cancel a queued task where supported.
