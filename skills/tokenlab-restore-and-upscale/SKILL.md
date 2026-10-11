---
name: tokenlab-restore-and-upscale
description: "Make an image larger and sharper, or repair an old, scratched, faded, or blurry photo, with TokenLab image models. Use when the user says \"upscale this\", \"make it 4K\", \"increase the resolution\", \"this is too small to print\", \"sharpen this photo\", \"fix my old family photo\", \"remove the scratches\", or \"restore this picture\". Upscale models keep the content and add pixels; a repair step uses an edit model first. To change, add, or remove content, use tokenlab-edit-image. To make a new realistic photo, use tokenlab-photoreal-stills. For a product shot on a new background, use tokenlab-product-photography."
license: MIT
metadata:
  category: image
---

# Restore and Upscale

Make a photo bigger and cleaner without changing what it shows. Upscale and repair are separate steps with separate models: repair first, then upscale the repaired result.

## Inputs to collect

- **Source image:** a public `https` URL or a TokenLab result URL.
- **Goal:** larger only, larger and sharper, or repair (scratches, tears, fading, noise, blur) and then larger.
- **Target size:** the pixel size or print size the user needs. This decides the upscale factor.
- **Faithfulness:** must faces, text, and fine patterns stay exactly as they are, or may the model add plausible detail?

## Models

Confirm each pick with `tokenlab-model-picker` or `GET /v1/models/{model}` before you call it. Prices and supply change.

| Stage | Default | Alternatives | Fast / low-cost |
| --- | --- | --- | --- |
| Upscale | `stability-upscale-fast` (`/v1/images/edits`, image only) | `topaz-labs-wonder-3-5`, `bria-image-increase-resolution` (both `operation: "image-edit"` on `/v1/images/generations`), `stability-upscale-conservative` (`prompt`, `creativity`; `/v1/images/edits`) | `p-image-upscale` (`operation: "image-edit"`) |
| Repair damage, fading, or blur before the upscale | `nano-banana-2` (`operation: "image-edit"`, `image_urls`) | `flux-kontext-pro` (`/v1/images/edits`) | `p-image-edit` |

Observed on 2026-10-12 with a 1024 × 1024 input: `stability-upscale-fast` returned 4096 × 4096, and `p-image-upscale` returned 2048 × 2048. Neither contract has a scale field. Check the output size of each new model with one test call before you promise a size.

## Workflow

Run each call with `tokenlab-run` (contract → estimate → call → poll → result).

1. Read the contract for each model. Use `request_endpoint_by_operation["image-edit"]` for the endpoint. Send only the listed fields. The upscale models have no prompt, except `stability-upscale-conservative`.
2. Estimate the cost from `GET /v1/models/{model}/pricing`. Upscalers here are priced per image. Add the repair step if you run one.
3. **Repair (only if needed).** Send the source to the edit model with one repair instruction (see Technique). Check that faces and text did not change.
4. **Upscale.** Send the repaired result URL (or the source) to the upscaler:
   - `/v1/images/generations` models: `{"model": "p-image-upscale", "operation": "image-edit", "image_url": "SRC"}`.
   - `/v1/images/edits` models: `{"model": "stability-upscale-fast", "image_url": "SRC"}` (JSON `image_url` or multipart `image`).
5. Read the response. A sync response has `data[].url`. A response with `status: "pending"` and `poll_url` is a task: poll it every 5–10 s until `completed` or `failed`.
6. Download the result and check its pixel size and detail at 100% zoom. If the size is still too small, upscale the result once more, then check again.
7. Return the result URL, the final pixel size, the model per stage, and the task IDs.

## Technique

- **Repair before you upscale.** An upscaler makes scratches, noise, and JPEG blocks larger too.
- **One repair instruction, with a keep list.** "Remove the scratches, dust, and the tear on the left. Keep the faces, the clothing, and the composition exactly the same. Do not add color." Ask for color only when the user wants colorization.
- **Faithful versus creative.** `stability-upscale-fast` and `p-image-upscale` take no prompt, so they cannot be steered toward new content. Use `stability-upscale-conservative` with a short `prompt` that describes the photo when the input is soft and you want the model to rebuild detail. Read its contract for the `creativity` field before you set it.
- **Do not chain many passes.** Each pass can add artificial texture. Two passes is a practical upper limit. Compare against the source after each one.
- **Keep the source.** Give the user the original URL with the result so they can compare.

## Quality bar

- The result shows the same people, objects, and text as the source. No new features, no changed faces, no rewritten letters.
- The pixel size meets the user's target.
- Edges are sharp, with no halos, plastic skin, or repeated texture.
- Repairs removed the damage and left the rest of the photo as it was.

## Related skills

- `tokenlab-run`: the call, poll, and result mechanics.
- `tokenlab-edit-image`: change, add, or remove content.
- `tokenlab-photoreal-stills`: a new realistic photo from a brief.
- `tokenlab-product-photography`: product shots on new backgrounds.
