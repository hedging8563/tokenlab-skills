---
name: tokenlab-animate-image
description: "Turn one still image into a short video clip with TokenLab image-to-video models. Use when the user says \"animate this photo\", \"make this picture move\", \"bring this image to life\", \"turn this still into a video\", \"add motion to my artwork\", or \"make a living photo / cinemagraph\". The image becomes the first frame; the prompt describes the motion and the camera. For a clip that must end on a second image, use tokenlab-keyframe-transition. For a product ad, use tokenlab-product-ad-video. For a speaking face, use tokenlab-talking-avatar. For a person who copies the moves in another video, use tokenlab-motion-control."
license: MIT
metadata:
  category: video
---

# Animate Image

Turn one still into a short clip. The image is the first frame. The prompt says what moves, how the camera moves, and what you hear.

## Inputs to collect

- **Image:** a public `https` URL or a TokenLab result URL. Crop it to the target aspect ratio first. Many models follow the input image shape and ignore `aspect_ratio` for this operation.
- **Motion:** what moves, and how much ("hair moves in a light wind", "she turns her head and smiles").
- **Camera:** static, or one move (slow push-in, pan left, orbit).
- **Length and size:** seconds and resolution. Start short for a first test.
- **Sound:** with or without audio. Some models always add audio; some can be silent.

## Models

Confirm each pick with `tokenlab-model-picker` or `GET /v1/models/{model}` before you call it. Prices, durations, and supply change.

| Need | Default | Alternatives | Fast / low-cost |
| --- | --- | --- | --- |
| General image-to-video | `veo3.1-fast` (4, 6, or 8 s; 720p or 1080p; 9:16 or 16:9; audio always on) | `kling-v3.0` (3-15 s, 720p/1080p, `output_audio` on or off), `hailuo-h3` (6 or 10 s, 768p, native audio), `seedance-2.0` (4-15 s, 480p-4k, audio on by default), `wan-3.0` (2-30 s, 480p-1080p) | `grok-imagine-video` (1-15 s, 480p/720p), `viduq3-turbo` (540p-1080p), `hailuo-h3-max` (5-15 s, 480p/768p) |
| Silent loop or background plate | `pixverse-v6` (1-15 s, 360p-1080p, audio off by default) | `kling-v3.0` with `output_audio: false`, `viduq3-turbo` with `output_audio: false` | `pixverse-v6` at 360p or 540p |

All of these use `POST /v1/videos/generations` with `operation: "image-to-video"`. Most take the image in `image_url`; `viduq3-turbo` lists `image` and `start_image` instead. Send `output_audio` only when the operation lists it.

## Workflow

Run each call with `tokenlab-run` (contract → estimate → call → poll → result).

1. Read the contract: `python scripts/tokenlab_run.py contract MODEL --operation image-to-video`. Note `supported_parameters`, `allowed_durations`, `allowed_resolutions`, and `delivery`. Use only listed fields and values.
2. Estimate the cost: `python scripts/tokenlab_run.py price MODEL`. Most video models price per second, so multiply the per-second price for your resolution (and audio setting, if the price depends on it) by `duration`. Use the Official price as the upper bound. Tell the user the estimate before you start the job.
3. Write the prompt (see Technique) and build the body:

   ```json
   {"model": "grok-imagine-video", "operation": "image-to-video", "image_url": "https://...", "prompt": "She smiles, raises her right hand, and waves at the camera twice. Static camera, soft studio light.", "duration": 2, "resolution": "480p"}
   ```

4. Call and wait: `python scripts/tokenlab_run.py run /v1/videos/generations --json @body.json --wait`. Save the task ID before you poll. The helper polls every 5 s; keep the interval at 5-10 s.
5. If your wait times out, resume with `python scripts/tokenlab_run.py poll TASK_ID`. Never create a second task for the same request.
6. On `failed`, read `error_details.code` and `param`, fix the body, and ask the user before a paid retry.
7. Return the video URL (`video_url`, `video.url`, or `videos[]`), the model, the task ID, and the estimate.

## Technique

- **Describe the change, not the picture.** The model already sees the image. Spend the prompt on action, camera, and sound. "The waves roll in and foam over the rocks; slow pan right" beats a full description of the beach.
- **Prompt parts:** subject + action, then camera position or move, then composition, lens or focus, and ambiance. These are the parts Google lists for Veo prompts, and they work as a checklist for any model.
- **One main action per clip.** Short clips have room for one gesture or one camera move. Make a second clip for the next beat, or extend the clip with `tokenlab-extend-video`.
- **Keep identity.** Say what must not change: "keep her face, hair, and jacket exactly as in the image."
- **Sound on Veo.** Veo 3.1 always makes audio. Describe the sounds you want ("soft wind, distant gulls"). Put spoken words in quotes. If you say nothing, you still get audio.
- **Silent output.** Pick a model whose contract lists `output_audio` and send `false`. Do not send `output_audio` to a model that does not list it.
- **Aspect ratio.** Crop the image before you call. Image-to-video output on `grok-imagine-video` follows the input image shape.
- **Prompt is required on some models.** `hailuo-h3-max` needs a non-empty prompt for every operation.

## Quality bar

- The first frame matches the input image. Face, product, and text do not change shape or color.
- Motion is smooth and physically plausible. No melting hands, no jump cuts.
- Camera behavior matches the request (a static request stays static).
- Duration, resolution, and aspect ratio match what the user asked for.
- The user saw the cost estimate before the job, and the answer names the model and task ID.

## Related skills

- `tokenlab-run`: the call, poll, and result mechanics.
- `tokenlab-keyframe-transition`: set both the first and the last frame.
- `tokenlab-extend-video`: continue the clip past its last frame.
- `tokenlab-product-ad-video`: product shots and ad clips.
- `tokenlab-cinematic-video`: shots built from camera language.
- `tokenlab-prompting`: prompt craft per model family.
