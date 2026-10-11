---
name: tokenlab-edit-image
description: "Make one targeted change to an existing image with TokenLab image models: add or remove an object, replace or recolor something, change the background, cut out the subject, or extend the frame. Use when the user says \"remove the person in the back\", \"make the car red\", \"change the background to a beach\", \"remove the background\", \"transparent PNG\", \"erase this\", \"fill this area\", or \"make it wider\". The rest of the image must stay the same. For a full product shoot from a packshot, use tokenlab-product-photography. For upscaling or fixing an old or blurry photo, use tokenlab-restore-and-upscale. For wrong or new text inside the image, use tokenlab-text-in-image. To keep a person the same across new scenes, use tokenlab-character-consistency."
license: MIT
metadata:
  category: image
---

# Edit Image

Change one thing in an existing image and keep everything else. Pick the model by the type of edit: a prompt-only edit, a masked edit, a cutout, a background swap, or a wider frame.

## Inputs to collect

- **Source image:** a public `https` URL or a TokenLab result URL. For a private local file, use multipart `image` or `POST /v1/files` (see `tokenlab-run`).
- **The change:** one clear instruction. Split a list of changes into separate calls.
- **What must stay:** the subject, face, product, text, framing, and light, unless the user wants them changed.
- **Mask**, if the user has one: the exact area to change.
- **Output:** aspect ratio or size, and whether the user needs a transparent background.

## Models

Confirm each pick with `tokenlab-model-picker` or `GET /v1/models/{model}` before you call it. Prices and supply change.

| Edit | Default | Alternatives | Fast / low-cost |
| --- | --- | --- | --- |
| Prompt-only edit: add, remove, replace, recolor, restyle | `nano-banana-2` (`operation: "image-edit"`, `image_urls`, on `/v1/images/generations`) | `flux-kontext-pro` (`/v1/images/edits`), `qwen-image-edit-2511`, `gpt-image-2` (`/v1/images/edits`) | `p-image-edit` |
| Masked edit (change only a marked area) | `ideogram-edit-v3-turbo` (`mask_url`) | `gpt-image-2` (`mask`), `stability-inpaint`, `flux-pro-1.0-fill` (both `/v1/images/edits`) | |
| Cut out the subject (transparent PNG) | `bria-rmbg-v2-0` (`operation: "image-edit"`) | | |
| New background, same subject | `ideogram-replace-background-v3-turbo` (`image_url` + `prompt`) | `ideogram-replace-background-v3` | |
| Extend the frame to a new size (outpaint) | `ideogram-reframe-v3-turbo` (`size` from its list, no prompt) | | |

`references/request-bodies.md` has a tested body for each row.

## Workflow

Run each call with `tokenlab-run` (contract → estimate → call → poll → result).

1. Read the contract for the model. Use `request_endpoint_by_operation["image-edit"]` for the endpoint. Many edit models use `/v1/images/generations` with `operation: "image-edit"`; others use `/v1/images/edits`. Note the image field (`image_url`, `image_urls`, or `image`) and the size field.
2. Estimate the cost from `GET /v1/models/{model}/pricing`: price per image times `n`. For `nano-banana-2` the price depends on `resolution`.
3. Write one edit instruction (see Technique). Send the source image URL in the field the contract lists. Send only listed fields.
4. Read the response. A sync response has `data[].url`. A response with `status: "pending"` and `poll_url` is a task: poll it every 5–10 s until `completed` or `failed`. The same model can answer either way, so handle both.
5. Compare the result with the source. If the change is wrong, rewrite the instruction and run again on the **original** source. If the change is right but incomplete, run the next edit on the **result** URL.
6. Return the result URL, the model, the task ID (if any), and the instruction you sent.

## Technique

- **Name the change, then name what stays.** Google's editing template for Gemini image models: "Using the provided image, change only the [element] to [new element]. Keep everything else in the image exactly the same, preserving the original style, lighting, and composition."
- **Point at the object by what it looks like and where it is.** "the white plate at the right edge of the desk", not "the thing on the right".
- **One edit per call.** Chain edits on result URLs. Each call is a new charge, so batch only edits that touch the same area.
- **Removals: say what fills the gap.** "Fill that area with the same walnut wood and wall."
- **Recolor: give the target color and the parts that keep their color.** "Change the mug body to deep forest green. Keep the clay base and the handle shape."
- **Use a mask when the area is small or the prompt-only edit drifts.** The mask convention is per model. For `gpt-image-2` on `/v1/images/edits`, fully transparent mask pixels mark the edit area, and the mask must have the same size as the image.
- **Cutouts need no prompt.** Send only the image to `bria-rmbg-v2-0`. In tests it returned an RGBA PNG.
- **Do not edit text here.** Models can change or misspell letters. Route text changes to `tokenlab-text-in-image`.

## Quality bar

- Only the requested area changed. Faces, products, logos, and text outside it match the source.
- Light, shadow direction, and perspective of the new content match the scene.
- No seams, smears, or repeated texture where an object was removed.
- Cutouts: clean edges, thin parts kept (handles, hair, straps), real transparency in the PNG.
- Output size and aspect ratio are what the user asked for.

## Related skills

- `tokenlab-run`: the call, poll, and result mechanics.
- `tokenlab-product-photography`: a full product shoot from one packshot.
- `tokenlab-restore-and-upscale`: sharper, larger, or repaired photos.
- `tokenlab-text-in-image`: add or fix words in an image.
- `tokenlab-character-consistency`: keep a person the same in a new scene.
