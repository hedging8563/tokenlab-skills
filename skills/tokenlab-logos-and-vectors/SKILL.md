---
name: tokenlab-logos-and-vectors
description: "Make logo marks, app icons, badges, and flat vector-style graphics, then convert them to SVG, with TokenLab image models. Use when the user says \"design a logo\", \"make an icon for my app\", \"simple mark for my brand\", \"flat illustration\", \"I need this as an SVG\", \"vectorize this logo\", or \"turn this PNG into a vector\". The skill makes a raster mark first, then vectorizes it. For a poster or label with readable words, use tokenlab-text-in-image. For a realistic photo, use tokenlab-photoreal-stills. To change an existing raster image, use tokenlab-edit-image."
license: MIT
metadata:
  category: image
---

# Logos and Vectors

Make a simple mark or icon and deliver it as an SVG. The text-to-image models here return raster images (PNG or JPEG). A second step turns the chosen raster into an SVG.

## Inputs to collect

- **Brand name and what it does:** one line.
- **Mark type:** symbol only, symbol plus name, or name only (wordmark).
- **Style:** flat, geometric, line, rounded, hand-drawn; number of colors and the colors (hex if the user has them).
- **Use:** app icon, favicon, website header, print. Small uses need fewer, thicker shapes.
- **Existing raster logo**, if the task is vectorize-only: a public `https` URL or a TokenLab result URL.

## Models

Confirm each pick with `tokenlab-model-picker` or `GET /v1/models/{model}` before you call it. Prices and supply change.

| Stage | Default | Alternatives | Fast / low-cost |
| --- | --- | --- | --- |
| Mark or icon (text-to-image, raster) | `recraft-v4.1` (`size` `1024x1024` only, `n` 1) | `recraft-v4.1-pro` (`size` `2048x2048` only), `ideogram-4-5` for marks with words | `recraft-v4.1-flash` |
| Raster to SVG (image-edit) | `recraft-vectorize` (`operation: "image-edit"`, `image_url`) | `picsart-image-vectorizer` | |

All use `/v1/images/generations`.

## Workflow

Run each call with `tokenlab-run` (contract → estimate → call → poll → result).

1. Read the contract for each model. Each Recraft text-to-image model lists one `size` value and `n` `1` only: `1024x1024` for `recraft-v4.1` and `recraft-v4.1-flash`, `2048x2048` for `recraft-v4.1-pro`.
2. Estimate the cost from `GET /v1/models/{model}/pricing`: marks times the price per image, plus one vectorize call per chosen mark.
3. **Marks.** Generate 3–4 options, one call each, with different shape ideas (see Technique). Send `operation: "text-to-image"`, the model's one `size` value, and `n: 1`.
4. Read each response. A sync response has `data[].url`. A response with `status: "pending"` and `poll_url` is a task: poll it every 5–10 s until `completed` or `failed`.
5. Let the user pick one mark. Vectorize only the pick.
6. **SVG.** Send `{"model": "recraft-vectorize", "operation": "image-edit", "image_url": "MARK_URL"}`. Do not send `output_format: "svg"`; it returns `400` (the field accepts only `png`, `jpeg`, `webp`). Leave `output_format` out.
7. Download the result and check the file. In tests, both vectorizers returned real SVG (`Content-Type: image/svg+xml`) although the result URL ends in `.png`. Save it with a `.svg` name.
8. Return the SVG file or URL, the raster URL, the model per stage, and the task IDs.

## Technique

- **Say "flat vector logo mark" first.** Recraft's own API example uses the style cue "flat vector" in the prompt.
- **Few shapes, few colors.** "A simple rounded bread loaf made of two solid colors, warm orange and dark brown." Simple shapes vectorize into clean paths; gradients, shadows, and texture turn into hundreds of small shapes.
- **Plain white background, centered, no text.** Add "No text, no gradients, no shadows" unless the user wants a wordmark.
- **Words in a logo:** make the wordmark with `tokenlab-text-in-image` (quoted text, letter style described), check the spelling, then vectorize that result.
- **The background becomes a shape.** Both vectorizers put the white background into the SVG as a full-size filled path. Delete that path (or set it to `none`) when the user needs a transparent mark.
- **Check small sizes.** Look at the mark at 32 px. If it turns into a blob, ask for fewer, thicker shapes.

## Quality bar

- The mark reads clearly at 32 px and at full size.
- Only the colors the user asked for, as flat fills.
- The SVG opens in a browser, has a small number of paths, and has no raster image embedded.
- Any words are spelled right.
- The mark does not copy a known brand's logo.

## Related skills

- `tokenlab-run`: the call, poll, and result mechanics.
- `tokenlab-text-in-image`: wordmarks and posters with exact text.
- `tokenlab-edit-image`: change an existing raster image.
- `tokenlab-photoreal-stills`: realistic photos.
