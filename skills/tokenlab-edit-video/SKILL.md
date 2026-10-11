---
name: tokenlab-edit-video
description: "Restyle or change an existing video clip with a text prompt using TokenLab video-to-video models. Use when the user says \"make this video look like anime / watercolor / claymation\", \"change the background in this clip\", \"restyle my video\", \"replace the outfit in this video\", \"make it night instead of day\", or \"edit this clip with a prompt\". The motion and timing come from the source clip; the prompt changes the look or content. To make the clip longer, use tokenlab-extend-video. To move a new character with the motion of this clip, use tokenlab-motion-control. To edit a still image, use tokenlab-edit-image."
license: MIT
metadata:
  category: video
---

# Edit Video

Change an existing clip with a prompt. The source keeps the motion, timing, and framing. The prompt says what to change and what to keep.

## Inputs to collect

- **Source clip:** a public `https` `.mp4` URL or a TokenLab result URL. Know its length and resolution (`ffprobe`).
- **The change:** a style ("watercolor animation"), a scene change ("make it night, wet streets"), or an object change ("the jacket is red leather").
- **What must stay:** pose, motion, framing, faces, product shape.
- **Reference images** (optional): a style or object to copy, on models that take them.

## Models

Confirm each pick with `tokenlab-model-picker` or `GET /v1/models/{model}` before you call it. Prices, limits, and supply change.

| Need | Default | Alternatives | Fast / low-cost |
| --- | --- | --- | --- |
| Prompt-only restyle or change of a short clip | `grok-imagine-video` (`prompt` + `video_url` only; output keeps the source length, at most 8.7 s, and at most 720p) | `kling-omni-video` (`video_url` plus optional `image_urls` references; `duration`, `aspect_ratio`, `resolution`; `output_audio` must be `false`), `seedance-2.0` (`video_url` plus image, video, and audio references; 480p-4k) | `flux-video-edit` (source up to 15 s, 720p, and 50 MiB; send `duration` = source length) |
| Change guided by reference images | `kling-omni-video` | `happyhorse-1.0` (`video_url` + `reference_images`; 720p/1080p; output capped at 15 s; do not send `output_audio`), `seedance-2.0` | |

All use `POST /v1/videos/generations` with `operation: "video-to-video"`. Seedance may reject a source clip that shows a realistic person.

## Workflow

Run each call with `tokenlab-run` (contract → estimate → call → poll → result).

1. Read the contract: `python scripts/tokenlab_run.py contract MODEL --operation video-to-video`. Note `supported_parameters`, `notes`, and `delivery`. Send only listed fields. `grok-imagine-video` does not use `duration`, `resolution`, or `aspect_ratio` for this operation; leave them out.
2. Check the source against the model's limits (`grok-imagine-video`: 8.7 s output cap; `flux-video-edit`: 15 s, 720p, 50 MiB; `happyhorse-1.0`: 15 s output cap). Trim the clip to the shot you need first.
3. Estimate the cost: `python scripts/tokenlab_run.py price MODEL`, then per-second price × output seconds. On these models the output length follows the source. `grok-imagine-video` holds the cost of its 8.7 s maximum up front and charges the delivered length. Use the Official price as the upper bound. Tell the user the estimate.
4. Build the body:

   ```json
   {"model": "grok-imagine-video", "operation": "video-to-video", "video_url": "https://....mp4", "prompt": "Turn the scene into a hand-drawn watercolor animation. Keep her pose, motion, and framing."}
   ```

   ```json
   {"model": "flux-video-edit", "operation": "video-to-video", "video_url": "https://....mp4", "prompt": "...", "duration": 2}
   ```

5. Call and wait: `python scripts/tokenlab_run.py run /v1/videos/generations --json @body.json --wait`. Save the task ID. Poll every 5-10 s.
6. If a wait times out, resume with `python scripts/tokenlab_run.py poll TASK_ID`. Never create a duplicate task.
7. Compare the result with the source (first frame, last frame, and one middle frame). Return the video URL, the model, the task ID, and the estimate.

## Technique

- **Say what changes and what stays.** "Change X to Y. Keep the pose, camera move, and framing." Models keep more of the source when you name it.
- **One change per pass.** Style first, then an object change in a second pass. Two big changes at once drift more.
- **Style words that travel well:** a medium ("watercolor", "claymation", "pencil sketch", "anime cel shading"), a palette ("muted teal and orange"), and a light change ("golden hour", "neon night").
- **Short, clean sources.** Trim to the shot you need. Hard cuts inside the source often break the edit.
- **Source audio.** Edits can keep the source soundtrack. Do not expect the edit to remove or replace sound; use an editor for audio.
- **Duration on `flux-video-edit`.** Send `duration` equal to the source length in seconds. It sets the first hold; the final charge follows the delivered clip.
- **Reference images.** On `kling-omni-video` and `happyhorse-1.0`, add a reference image for a precise look or object instead of a long description.

## Quality bar

- Motion, timing, and framing match the source.
- The requested change shows in every frame, with no flicker between styles.
- Faces, hands, and products keep their shape; nothing the user asked to keep has changed.
- The output length matches the source (within the model's cap); the user saw the estimate first.

## Related skills

- `tokenlab-run`: the call, poll, and result mechanics.
- `tokenlab-extend-video`: continue the clip instead of changing it.
- `tokenlab-motion-control`: put a new character into this clip's motion.
- `tokenlab-edit-image`: edit a single frame or still.
