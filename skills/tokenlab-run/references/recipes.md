# TokenLab request recipes

Each body is a starting point. Replace `MODEL_ID` with a live model ID for that operation: take it from the Models list of the outcome skill you run, or find it with `GET /v1/models?recommended_for=<scene>` (see `tokenlab-model-picker`). The family named above a body is the one it was written for; other families can use other fields. Check the model's `operation_constraints` before you send it. All create calls use `POST`, `Authorization: Bearer $TOKENLAB_API_KEY`, and `Content-Type: application/json` unless marked multipart.

## Images: `/v1/images/generations`

Text-to-image (written for FLUX.2):

```json
{"model": "MODEL_ID", "operation": "text-to-image", "prompt": "...", "n": 1}
```

Image-to-image or image-edit on a model whose contract maps the operation to `/v1/images/generations` (written for Nano Banana, then Bria background removal):

```json
{"model": "MODEL_ID", "operation": "image-to-image", "prompt": "...", "image_urls": ["https://..."], "aspect_ratio": "1:1"}
{"model": "MODEL_ID", "operation": "image-edit", "image_url": "https://..."}
```

Size fields differ by family. Some take `width` / `height`, some `size` (`1024x1024`), some `aspect_ratio` plus `resolution`. Use only what `supported_parameters` lists.

## Images: `/v1/images/edits`

Use this endpoint only when the contract maps `image-edit` to it (for example GPT Image, `stability-*`, some Gemini image models). JSON form (written for GPT Image):

```json
{"model": "MODEL_ID", "prompt": "...", "image_url": "https://...", "size": "1024x1024"}
```

Multipart form: `model`, `prompt`, one or more `image` files, optional `mask` PNG. For `file_id` input, upload with `POST /v1/files` (`purpose=user_data`, `model=<edit model>`) and send `{"images": [{"file_id": "file_..."}]}`.

## Video: `/v1/videos/generations` (always async)

Written for Grok Imagine video, except `start-end-to-video` and `reference-to-video` (any model that publishes them) and `motion-control` (Kling motion control):

```json
{"model": "MODEL_ID", "operation": "text-to-video", "prompt": "...", "duration": 2, "resolution": "480p", "aspect_ratio": "16:9"}
{"model": "MODEL_ID", "operation": "image-to-video", "prompt": "...", "image_url": "https://...", "duration": 2, "resolution": "480p"}
{"model": "MODEL_ID", "operation": "start-end-to-video", "prompt": "...", "start_image": "https://...", "end_image": "https://..."}
{"model": "MODEL_ID", "operation": "reference-to-video", "prompt": "...", "reference_images": ["https://..."]}
{"model": "MODEL_ID", "operation": "video-to-video", "prompt": "...", "video_url": "https://....mp4"}
{"model": "MODEL_ID", "operation": "video-extension", "prompt": "...", "task_id": "ldtask_..."}
{"model": "MODEL_ID", "operation": "motion-control", "image_url": "https://...", "video_url": "https://....mp4", "resolution": "720p"}
```

`duration` is the output length in seconds. Allowed values are per model and per operation.

## Music: `/v1/music/generations` (async)

```json
{"model": "MODEL_ID", "prompt": "...", "title": "...", "tags": "lo-fi, mellow"}
```

Suno-style models take `mv`, `action`, `make_instrumental`, and `audio_operation` fields. Use them only when the model's contract lists them.

## 3D: `/v1/3d/generations` (async, no `operation` field)

Written for Tripo:

```json
{"model": "MODEL_ID", "prompt": "a low-poly robot mascot"}
{"model": "MODEL_ID", "prompt": "the object in the photo", "image_url": "https://..."}
```

## Worlds: `/v1/worlds/generations` (async)

Written for Marble (draft tier):

```json
{"model": "MODEL_ID", "prompt": "a quiet coastal town at sunset"}
```

## Speech: `/v1/audio/speech` (returns audio bytes)

Written for Grok TTS. `voice` values are per model; take them from the contract.

```json
{"model": "MODEL_ID", "input": "Hello there.", "voice": "eve", "response_format": "mp3"}
```

## Transcription: `/v1/audio/transcriptions` (multipart)

Fields: `model`, `file` (max 25 MB), optional `language`, `response_format` (`json`, `text`, `srt`, `vtt`, `verbose_json` where the model supports them).

## Text translation: `/v1/translations`

Written for Doubao Seed translation:

```json
{"model": "MODEL_ID", "text": "...", "target_language": "es"}
```

## Decisions: `/v1/systemone` (sync)

Written for a System One model (`GET /v1/models?category=decision`):

```json
{"model": "MODEL_ID", "state": "...", "questions": {"refund": {"type": "noul", "instructions": "Is a refund requested?"}}}
```

## Tasks

- `GET {poll_url}` or `GET /v1/tasks/{id}`: status and result.
- `DELETE /v1/tasks/{id}`: cancel a queued task where supported.
