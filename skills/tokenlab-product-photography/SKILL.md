---
name: tokenlab-product-photography
description: "Turn a product photo or a text brief into studio, lifestyle, or hero images for a store, catalog, or ad with TokenLab image models. Use when the user says \"make this a product photo\", \"put my product on a white background\", \"lifestyle shot of this bottle\", \"hero image for the launch\", \"packshot\", or \"e-commerce photos\". Usually a short pipeline: generate or restage the shot, cut the background, then place it in a new scene. For realistic photos with no product focus, use tokenlab-photoreal-stills. For text on packaging or posters, use tokenlab-text-in-image. For a single edit to an existing photo, use tokenlab-edit-image."
license: MIT
metadata:
  category: image
---

# Product Photography

Make catalog-, ad-, or hero-ready product images from a plain photo or a written brief. Each stage uses a different model, so route by stage, not by one favorite model.

## Inputs to collect

- **Product image**, if the user has one: a public `https` URL or a TokenLab result URL. Skip for a from-scratch brief.
- **Look:** studio (seamless or white sweep), lifestyle (a real setting), or hero (dramatic, ad-grade).
- **Background result:** keep, cut out, or replace with a named scene.
- **Format:** aspect ratio per channel (1:1 marketplace, 4:5 social feed, 9:16 story, 16:9 banner) and image count.
- **Hard rules:** product shape, colors, and on-pack text must not change. Add no logos, awards, or claims the user did not supply.

## Models

Confirm each pick with `tokenlab-model-picker` or `GET /v1/models/{model}` before you call it. Prices and supply change.

| Stage | Default | Alternatives | Fast / low-cost |
| --- | --- | --- | --- |
| Restage an existing product photo (image-to-image) | `nano-banana-2` (`operation: "image-to-image"`, `image_urls`) | `seedream-5.0` (image-to-image on `/v1/images/edits`), `flux-2-pro` (image-edit) | `nano-banana-2-lite` |
| Generate a shot from a brief (text-to-image) | `flux-2-pro` | `seedream-5.0`, `nano-banana-2`, `recraft-v4.1-utility` for flat catalog mockups | `p-image`, `flux-2-klein-9b` |
| Cut out the background | `bria-rmbg-v2-0` (`operation: "image-edit"`) | | |
| Replace the background in place | `ideogram-replace-background-v3-turbo` (`image_url` + `prompt`) | `ideogram-replace-background-v3` | |

## Workflow

Run each call with `tokenlab-run` (contract → estimate → call → poll → result).

1. Read the contract for each model you plan to use. Note the endpoint for the operation, the size fields (`aspect_ratio` + `resolution`, `size`, or `width` / `height`), and the image input field (`image_url`, `image_urls`, or `image`).
2. **Stage 1: a clean subject.** If the user has a good product photo, keep it. Otherwise generate one with a text-to-image model. Brief it like a photographer (see Technique). Image responses can be sync or async; follow `poll_url` when `status` is `pending`.
3. **Stage 2: the scene.**
   - Studio on white or transparent: send the subject to `bria-rmbg-v2-0` with `operation: "image-edit"` and `image_url`.
   - New background, same product: send the subject URL and a scene prompt to `ideogram-replace-background-v3-turbo`, or restage it with `nano-banana-2` image-to-image.
4. **Stage 3: variants.** Re-run only the weak stage, one aspect ratio per call. Keep the stage-1 URL as the anchor so the product stays the same.
5. Check the result against the Quality bar. Return the result URLs, the model per stage, and the task IDs.

## Technique

- **Brief order:** product, surface, light, lens or angle, background, mood. Example: "matte black wireless earbuds case on raw concrete, one soft key light from upper left, 45-degree top-down view, plain warm grey background, premium tech look."
- **Light is the main lever.** State direction and quality: "large softbox from the left, white bounce card on the right", "low warm sun from behind", "hard single spotlight from above".
- **Lens words change depth.** "100mm macro, shallow depth of field" for texture close-ups; "35mm, eye level" for lifestyle context.
- **Restage, do not regenerate.** When the product is right but the scene is wrong, use image-to-image or background replacement with the product photo as input. A fresh generation can change the product.
- **Protect the product in the prompt.** In image-to-image, say what must stay: "keep the bottle shape, label, and cap exactly as in the reference; change only the background to ..."
- **Ground the product.** A missing or wrong-direction contact shadow is the usual tell of a pasted product. Ask for "soft contact shadow under the product, light from the left" when you restage.
- **Copy on pack:** do not ask a general model to write label text. Keep the original label from the photo, or route to `tokenlab-text-in-image`.

## Quality bar

- Product shape, color, proportions, and label match the input.
- Light direction is consistent between product, shadow, and scene.
- Clean edges after a cutout: no halo, no lost thin parts (straps, cables, glass rims).
- Correct aspect ratio for each channel, and no invented text, logos, or badges.

## Related skills

- `tokenlab-run`: the call, poll, and result mechanics.
- `tokenlab-edit-image`: one targeted change to an existing photo.
- `tokenlab-text-in-image`: packaging and poster copy.
- `tokenlab-product-ad-video`: turn the final still into an ad clip.
- `tokenlab-prompting`: prompt craft per model family.
