---
name: tokenlab-world-generation
description: "Turn a text description, one or more images, a panorama, or a video into an explorable 3D world (a Marble world you can walk through, plus splat and mesh files) with TokenLab world models. Use when the user says \"make a 3D world\", \"explorable scene of a tea room\", \"walkable environment for my game\", \"turn this photo into a 3D space\", \"virtual set\", or \"360 scene\". Drafts cheap first, then makes the final world, and returns the viewer link and files. For one downloadable object instead of a place, use tokenlab-image-to-3d-asset. For a flat image of a scene, use tokenlab-photoreal-stills."
license: MIT
metadata:
  category: 3d
---

# World Generation

Make an explorable 3D place from a description, images, or a video. The result is a world viewer link plus downloadable Gaussian splats (`.spz`), a collider mesh (`.glb`), and a thumbnail. World jobs are async and paid per request.

## Inputs to collect

- **Source:** text only, one image, up to 4 images of the same place, a panorama, or a video. Images and video as public `https` URLs.
- **The place:** indoor or outdoor, size, layout, key objects, light, time of day, and style.
- **Use:** quick look, game or film set, or a shared viewer link. This decides draft vs final model.
- **Sharing:** whether the world should be public. Leave `permission` out unless the user asks.

## Models

Confirm each pick with `tokenlab-model-picker` or `GET /v1/models/{model}` before you call it. Prices and supply change. World models appear in `GET /v1/models?recommended_for=3d` with the `world-generation` operation.

| Need | Default | Alternatives | Fast / low-cost |
| --- | --- | --- | --- |
| Draft a layout or idea | `marble-1.0-draft` | | `marble-1.0-draft` |
| Final world | `marble-1.1` | `marble-1.0` | `marble-1.0-draft` |
| Large outdoor or large indoor space | `marble-1.1-plus` (bigger world, more credits) | `marble-1.1` | |

All four take the same fields: `prompt`, `image`, `image_url`, `images`, `video_url`, `is_pano`, `seed`, `display_name`, `tags`, `permission`, and the native `world_prompt` object.

## Workflow

Run each call with `tokenlab-run` (contract → estimate → call → poll → result).

1. Read the contract: `python scripts/tokenlab_run.py contract marble-1.0-draft --operation world-generation`. Send only listed fields.
2. Estimate with `GET /v1/models/{model}/pricing`. World models charge credits per request, shown as a USD range in `pricing_summary`; `pricing_details.worldLabs` lists credits per input type and the USD price per credit. Example: `marble-1.0-draft` from text or one image = (credits for that input type) × (USD per credit). Use `official_max_price` as the upper bound and tell the user before you start.
3. Draft first. Run `marble-1.0-draft` with the brief. Show the viewer link and thumbnail. Change the brief until the layout is right.
4. Make the final world with `marble-1.1` (or `marble-1.1-plus` for large spaces), same brief, after the user agrees to the price.
5. Call and wait: `python scripts/tokenlab_run.py run /v1/worlds/generations --json @body.json --wait --interval 10`. Save the task `id` and `poll_url` (`/v1/worlds/generations/{id}`) first. A draft took about 40 s in testing; World Labs says a standard world takes about 5 minutes. On a timeout, resume with `poll TASK_ID`.
6. Read the result:
   - `world_marble_url`: the world viewer link to open and explore.
   - `assets.splats.spz_urls`: splats at `100k`, `500k`, and `full_res`.
   - `glb_url`: the collider mesh (low detail; for physics and walking, not for looks).
   - `thumbnail_url`, `caption`, and `pano_url` when present. A completed task does not always have every asset.
   - `cost.total_credits`: generation usage in credits, not a currency amount.
7. Download the files the user needs; media-result URLs stay valid for 30 days. Return the viewer link, file URLs, model, and task ID.

Body examples:

```json
{"model": "marble-1.0-draft", "prompt": "A small Japanese tea room at dusk: tatami floor, low wooden table, paper sliding doors glowing with warm lamp light, a garden with a stone lantern visible through an open door.", "display_name": "Tea room draft"}
{"model": "marble-1.1", "image_url": "https://...", "prompt": "Extend this cafe interior into a full room with the same style."}
```

## Technique

- **Describe a place, not a story.** Space type, layout, key objects and where they are, materials, light and time of day, and style. One place per world.
- **Images:** text is optional with an image; without it, a caption is made for you. Use `jpg`, `png`, or `webp`.
- **Panoramas:** set `is_pano: true` when the image is a real 360 panorama, `false` for a wide normal photo. The default is `auto`.
- **Several images of one place:** send up to 4 in `images`. For more control, use `world_prompt` with `type: "multi-image"` and an azimuth per image (0 front, 90 right, 180 back, 270 left).
- **Video:** a walk-through clip in `mp4`, `mov`, or `mkv` via `video_url`.
- **`seed`** (0–4294967295): keep it fixed while you change the prompt, so you compare prompt changes and not random changes.
- **Metadata:** `display_name` up to 64 characters; `tags` up to 10, each up to 32 characters.

## Quality bar

- The world shows the requested place, layout, and light, and the user can open the viewer link.
- The user saw the draft and the price before the final world.
- Files the user asked for (splats, mesh, pano) are present, or the answer says which were not returned.
- The final answer has the viewer link, file URLs, model, task ID, and credits used.

## Related skills

- `tokenlab-run`: the call, poll, and result mechanics.
- `tokenlab-image-to-3d-asset`: one downloadable object instead of a place.
- `tokenlab-photoreal-stills`: a reference image to start a world from.
- `tokenlab-api-integration`: put world creation into an app (MCP `create_world` and `get_world_status` need the `full` profile).
