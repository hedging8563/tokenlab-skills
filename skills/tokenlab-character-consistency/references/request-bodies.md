# Character consistency request bodies

Each body is a starting point. Read the model contract first and send only fields in its `supported_parameters`. "Live-tested" means the body returned a result on 2026-10-12.

## Anchor image

`p-image` on `/v1/images/generations` (live-tested; returned a task). `width` and `height` are listed in the contract, but a 768 × 768 request returned 1024 × 1024.

```json
{"model": "p-image", "operation": "text-to-image",
 "prompt": "Head-and-shoulders portrait photo of a woman in her thirties with short curly red hair, green eyes, light freckles, wearing a mustard yellow knit sweater. Plain light grey background, soft window light from the left, 85mm lens, eye level.",
 "n": 1}
```

## New scene from the anchor

`nano-banana-2` on `/v1/images/generations` (live-tested; sync response, 928 × 1152 for `4:5` at `1k`):

```json
{"model": "nano-banana-2", "operation": "image-to-image",
 "prompt": "The same woman from the reference image: same face, same short curly red hair, same green eyes and freckles, same mustard yellow knit sweater. She now sits at a cafe table by a window, laughing, holding a coffee cup with both hands. Three-quarter view, warm afternoon light.",
 "image_urls": ["ANCHOR"], "aspect_ratio": "4:5", "resolution": "1k"}
```

`ideogram-character-v3` (from the contract; not live-tested). `operation` is required and `reference_image_urls` takes one item:

```json
{"model": "ideogram-character-v3", "operation": "text-to-image", "prompt": "...", "reference_image_urls": ["ANCHOR"], "aspect_ratio": "4:5"}
```

## Clip from references

`grok-imagine-video` on `/v1/videos/generations` (live-tested; task finished in about 100 s; 480 × 480, about 1 s). This operation is priced per second plus a small charge per reference image.

```json
{"model": "grok-imagine-video", "operation": "reference-to-video",
 "prompt": "The woman from the reference images turns her head toward the camera and smiles. Same face, same red curly hair, same mustard sweater. Static camera.",
 "reference_images": ["ANCHOR", "SCENE_1"], "duration": 1, "resolution": "480p", "aspect_ratio": "1:1"}
```

Allowed for this operation: `duration` 1–10, `resolution` `480p` or `720p`, and the aspect ratios in the contract.
