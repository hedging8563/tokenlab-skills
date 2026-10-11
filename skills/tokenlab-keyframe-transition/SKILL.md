---
name: tokenlab-keyframe-transition
description: "Make a video that starts on one image and ends on another with TokenLab start-end-to-video models. Use when the user says \"go from this frame to that frame\", \"first frame and last frame\", \"morph A into B\", \"transition between these two images\", \"before and after video\", \"start and end keyframes\", or \"make these two shots connect\". The model fills in the motion between the two frames. For one image with free motion, use tokenlab-animate-image. To continue an existing clip, use tokenlab-extend-video. To make the end frame by editing the start frame, use tokenlab-edit-image first."
license: MIT
metadata:
  category: video
---

# Keyframe Transition

Give the model a first frame and a last frame. It generates the motion between them. Good for before/after reveals, product state changes, and joining two shots.

## Inputs to collect

- **Start image** and **end image:** public `https` URLs or TokenLab result URLs. Same aspect ratio and similar size.
- **What happens between them:** the action, the camera move, and the pace.
- **Length and size:** seconds and resolution.
- **Sound:** with or without audio.

If the user has only the start image, make the end image by editing it with `tokenlab-edit-image`. Change only what should change, so everything else stays in place.

## Models

Confirm each pick with `tokenlab-model-picker` or `GET /v1/models/{model}` before you call it. Prices, durations, and supply change.

| Need | Default | Alternatives | Fast / low-cost |
| --- | --- | --- | --- |
| First and last frame (`start-end-to-video`, `start_image` + `end_image`) | `veo3.1-fast` (4, 6, or 8 s; 720p/1080p; 9:16 or 16:9; audio always on; Verified delivery only for this operation) | `seedance-2.0` (4-15 s, 480p-4k), `wan-3.0` (2-30 s, 480p-1080p), `hailuo-h3-max` (5-15 s, 480p/768p, prompt required), `veo3.1` | `viduq3-turbo` (540p-1080p, `output_audio` on or off), `pixverse-v6` (1-15 s, 360p-1080p, silent by default) |

All use `POST /v1/videos/generations` with `operation: "start-end-to-video"`, `start_image`, and `end_image`. Send `output_audio` only when the operation lists it.

## Workflow

Run each call with `tokenlab-run` (contract → estimate → call → poll → result).

1. Read the contract: `python scripts/tokenlab_run.py contract MODEL --operation start-end-to-video`. Note durations, resolutions, aspect ratios, and `delivery`. If `delivery` shows only `verified`, a request pinned to Official cannot run.
2. Check the two frames: same aspect ratio and close in size. Fix them before you pay for a video.
3. Estimate the cost: `python scripts/tokenlab_run.py price MODEL`, then per-second price × `duration`. Use the Official price as the upper bound. Tell the user the estimate.
4. Build the body:

   ```json
   {"model": "viduq3-turbo", "operation": "start-end-to-video", "start_image": "https://...empty-mug.jpg", "end_image": "https://...full-mug.jpg", "prompt": "Hot black coffee pours into the empty white mug from above until it is full, then soft steam rises. Static camera, same morning window light.", "duration": 2, "resolution": "540p", "output_audio": false}
   ```

5. Call and wait: `python scripts/tokenlab_run.py run /v1/videos/generations --json @body.json --wait`. Save the task ID. Poll every 5-10 s.
6. If a wait times out, resume with `python scripts/tokenlab_run.py poll TASK_ID`. Never create a duplicate task.
7. Return the video URL, the model, the task ID, and the estimate.

## Technique

- **Match the frames.** Same aspect ratio, framing, and light give a smooth result. Vidu's API requires the start and end frame resolutions to be within a ratio of 0.8 to 1.25. Treat that as a safe rule for every model.
- **Make B from A.** Edit the start frame to get the end frame (same scene, one change). Two unrelated images force the model to invent a cut or a morph.
- **Describe the path, not the frames.** The model sees both images. Write what happens between them: "the lid opens and steam rises", "the camera pulls back to show the whole room".
- **One change per clip.** A single pour, turn, or reveal works best. Chain more clips for more changes.
- **Give it time.** Large changes need more seconds. Keep 2-4 s for small changes and 6-8 s for big moves.
- **Lock the camera when the subject moves.** "Static camera" keeps the frames aligned; add one camera move only when the frames differ by viewpoint.
- **Prompt rules.** `hailuo-h3-max` needs a non-empty prompt for every operation. `wan-3.0` does not take driving audio in first/last-frame mode.
- **Sound.** Veo models always add audio; describe it. For silent output, pick a model that lists `output_audio` and send `false`.

## Quality bar

- The first frame matches the start image and the last frame matches the end image.
- The motion between them is continuous: no hard cut, no flash, no face morph unless the user asked for one.
- Subject identity, product shape, and text stay stable through the clip.
- Duration, resolution, and aspect ratio match the request; the user saw the estimate first.

## Related skills

- `tokenlab-run`: the call, poll, and result mechanics.
- `tokenlab-edit-image`: make the end frame from the start frame.
- `tokenlab-animate-image`: one image, free motion.
- `tokenlab-extend-video`: continue a clip past its last frame.
- `tokenlab-cinematic-video`: camera language for each shot.
