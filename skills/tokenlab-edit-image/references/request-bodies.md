# Edit request bodies

Each body is a starting point. Take `MODEL_ID` from the Models list in `SKILL.md` for the `image-edit` operation and the family named above the body. Read the model contract first and send only fields in its `supported_parameters`. Replace `SRC` with the source image URL. "Live-tested" means the body returned an image on 2026-10-12.

## Prompt-only edits

Nano Banana on `/v1/images/generations` (live-tested; sync response):

```json
{"model": "MODEL_ID", "operation": "image-edit",
 "prompt": "Remove the white plate at the right edge of the desk. Fill that area with the same walnut wood and wall. Keep the mug, the light, and the framing exactly the same.",
 "image_urls": ["SRC"], "aspect_ratio": "1:1", "resolution": "1k"}
```

- `resolution`: `1k`, `2k`, or `4k`. The price is per image and goes up with `resolution`.
- `aspect_ratio`: a value from the contract's allowed list. Match the source to avoid a crop.
- The sync response can include both `data[].url` and `data[].b64_json`. Keep the URL.

P-Image edit on `/v1/images/generations` (live-tested; returned a task):

```json
{"model": "MODEL_ID", "operation": "image-edit",
 "prompt": "Change the mug color to deep forest green. Keep the handle shape, the walnut desk, the light, and the camera angle the same.",
 "image_url": "SRC", "n": 1}
```

FLUX Kontext on `/v1/images/edits` (live-tested with JSON `image_url`; returned a task):

```json
{"model": "MODEL_ID", "operation": "image-edit",
 "prompt": "Change the mug color to matte black. Keep everything else the same.",
 "image_url": "SRC"}
```

GPT Image on `/v1/images/edits` (from the contract; token-priced, so estimate from the pricing entries before you call):

```json
{"model": "MODEL_ID", "prompt": "...", "image_url": "SRC", "size": "1024x1024", "quality": "low"}
```

- `background` accepts `auto` or `opaque` only. No transparent output.
- Up to 16 source images. A `mask` applies to the first image.

## Masked edits

Ideogram edit on `/v1/images/generations` (from the contract; not live-tested):

```json
{"model": "MODEL_ID", "operation": "image-edit", "prompt": "...", "image_url": "SRC", "mask_url": "MASK"}
```

The Stability inpaint model and FLUX Fill use `/v1/images/edits` with `image`, `mask`, and `prompt`. Read each contract and the model maker's mask rules before you build the mask.

## Cutout

Bria background removal on `/v1/images/generations` (live-tested; returned a task; result is an RGBA PNG):

```json
{"model": "MODEL_ID", "operation": "image-edit", "image_url": "SRC"}
```

## Background replace and reframe

Ideogram replace-background (from the contract; `operation` is required):

```json
{"model": "MODEL_ID", "operation": "image-edit", "image_url": "SRC", "prompt": "on a sunny beach at noon, soft sand, blue sky"}
```

Ideogram reframe (from the contract; `operation` is required; `size` must be one of the sizes in its contract, such as `1344x768`, `1024x1024`, or `768x1344`):

```json
{"model": "MODEL_ID", "operation": "image-edit", "image_url": "SRC", "size": "1344x768"}
```
