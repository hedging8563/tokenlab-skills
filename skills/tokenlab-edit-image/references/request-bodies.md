# Edit request bodies

Each body is a starting point. Read the model contract first and send only fields in its `supported_parameters`. Replace `SRC` with the source image URL. "Live-tested" means the body returned an image on 2026-10-12.

## Prompt-only edits

`nano-banana-2` on `/v1/images/generations` (live-tested; sync response):

```json
{"model": "nano-banana-2", "operation": "image-edit",
 "prompt": "Remove the white plate at the right edge of the desk. Fill that area with the same walnut wood and wall. Keep the mug, the light, and the framing exactly the same.",
 "image_urls": ["SRC"], "aspect_ratio": "1:1", "resolution": "1k"}
```

- `resolution`: `1k`, `2k`, or `4k`. The price is per image and goes up with `resolution`.
- `aspect_ratio`: a value from the contract's allowed list. Match the source to avoid a crop.
- The sync response can include both `data[].url` and `data[].b64_json`. Keep the URL.

`p-image-edit` on `/v1/images/generations` (live-tested; returned a task):

```json
{"model": "p-image-edit", "operation": "image-edit",
 "prompt": "Change the mug color to deep forest green. Keep the handle shape, the walnut desk, the light, and the camera angle the same.",
 "image_url": "SRC", "n": 1}
```

`flux-kontext-pro` on `/v1/images/edits` (live-tested with JSON `image_url`; returned a task):

```json
{"model": "flux-kontext-pro", "operation": "image-edit",
 "prompt": "Change the mug color to matte black. Keep everything else the same.",
 "image_url": "SRC"}
```

`gpt-image-2` on `/v1/images/edits` (from the contract; token-priced, so estimate from the pricing entries before you call):

```json
{"model": "gpt-image-2", "prompt": "...", "image_url": "SRC", "size": "1024x1024", "quality": "low"}
```

- `background` accepts `auto` or `opaque` only. No transparent output.
- Up to 16 source images. A `mask` applies to the first image.

## Masked edits

`ideogram-edit-v3-turbo` on `/v1/images/generations` (from the contract; not live-tested):

```json
{"model": "ideogram-edit-v3-turbo", "operation": "image-edit", "prompt": "...", "image_url": "SRC", "mask_url": "MASK"}
```

`stability-inpaint` and `flux-pro-1.0-fill` use `/v1/images/edits` with `image`, `mask`, and `prompt`. Read each contract and the model maker's mask rules before you build the mask.

## Cutout

`bria-rmbg-v2-0` on `/v1/images/generations` (live-tested; returned a task; result is an RGBA PNG):

```json
{"model": "bria-rmbg-v2-0", "operation": "image-edit", "image_url": "SRC"}
```

## Background replace and reframe

`ideogram-replace-background-v3-turbo` (from the contract; `operation` is required):

```json
{"model": "ideogram-replace-background-v3-turbo", "operation": "image-edit", "image_url": "SRC", "prompt": "on a sunny beach at noon, soft sand, blue sky"}
```

`ideogram-reframe-v3-turbo` (from the contract; `operation` is required; `size` must be one of the sizes in its contract, such as `1344x768`, `1024x1024`, or `768x1344`):

```json
{"model": "ideogram-reframe-v3-turbo", "operation": "image-edit", "image_url": "SRC", "size": "1344x768"}
```
