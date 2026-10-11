# Image prompt families

Each section starts with the source. The "Models" line gives the family and its ID pattern. Find current IDs with `GET /v1/models?recommended_for=image` and pick the ones that match. "Contract" lines state what the TokenLab model contract lists. Check the live contract before you send a parameter. Numbers marked "maker" come from the model maker's own docs and may differ from TokenLab limits.

## FLUX

Sources:
- https://docs.bfl.ai/guides/prompting_guide_flux2 (FLUX.2 pro and max)
- https://docs.bfl.ai/flux_2/flux2_image_editing (editing and multi-reference)
- https://docs.bfl.ai/kontext/kontext_image_editing (FLUX.1 Kontext)

Models: FLUX.2 (`flux-2-*`: pro, max, flex, dev, Klein), FLUX.1 Kontext (`flux-kontext-*`), and FLUX1.1 pro (`flux-pro-*`).

Structure that works:
- Subject, then action, then style, then context, then small details. The maker says the model weights early words more.
- Length: 10 to 30 words for quick tests, 30 to 80 for most work, over 80 only for complex scenes.
- Write light as part of the context. Name the source and quality: "golden hour", "soft diffused softbox", "hard direct flash".
- For realism, name a camera, lens, and film look. This beats "professional photo".
- Colors: write "color #C92695" and tie each code to one object.
- Text in the image: put the words in quotes, say where they sit, and describe the font style and color.
- JSON prompts (scene, subjects, style, palette, lighting, camera) suit many-subject scenes and automated pipelines. Plain prose works as well for exploring.

Edits and references:
- Say the change in plain words. One prompt can mix a global change and an addition.
- Name inputs by number and give each one a job: "the product from image 1, the wood texture from image 2, apply the style of image 3 to the whole scene".
- Kontext: keep edits short and specific ("Change the car color to red"). Describe the new setting and leave the person's features out, so they carry over. For text edits write `Replace 'old' with 'new'`. Chain edits one step at a time.

Contract:
- FLUX.2 pro and the FLUX.2 Klein models (`flux-2-klein-*`) list `prompt`, `input_image`, `resolution`, `async`. No `negative_prompt`, no `seed`.
- FLUX.2 dev lists `negative_prompt`, `seed`, `steps`, `guidance_scale`, `cfg_scale`, `width`, `height`, `images`.
- FLUX1.1 pro ultra lists `aspect_ratio`, `image_prompt`, `raw`.
- The maker guide says FLUX.2 pro and max take no negative prompts. Phrase wishes in positive words. Use `negative_prompt` on FLUX.2 dev only as a light extra.

Examples:
- "Soaking wet tiger cub sheltering under a banana leaf in a rainy jungle, close-up photo, shallow depth of field, soft overcast light."
- Edit: "Keep the woman's face, hair, and pose from image 1. Put her in the cafe from image 2, warm window light from the left."

Pitfalls:
- Do not write "no blur". Write "sharp focus throughout".
- A hex code floating in the prompt gives random results. Attach it to an object.
- No official guide was read for FLUX1.1 pro. Use the general structure and test one call.

## Nano Banana and Gemini image

Source: https://ai.google.dev/gemini-api/docs/image-generation (prompt guide and templates).

Models: Nano Banana (2, 2.1, 2 lite, Pro) and Gemini image (`gemini-*-image`).

Structure that works:
- Write a full scene as sentences, not a keyword list. The maker examples give setting, subject, materials, light, composition, and mood.
- Photoreal template: shot type, subject, setting, then light, camera angle, and lens.
- Product mockup template: studio-lit photo, surface, light setup and its purpose, camera angle, the feature to show, where focus lands.
- Sticker or illustration: art style, subject and action, line and color traits, background.
- Text in images: say the image type, the exact words in quotes, the font style, and the color scheme. The maker advises its Pro image model for professional text assets.
- Negative space: one subject in one part of the frame, a large empty background, soft light. Good for banners with copy later.

Edits:
- Say what to add, remove, or change. Say how it must blend (same style, light, perspective).
- For a local change, add "keep everything else identical".
- The maker advises refining in steps, with the earlier result as the next input.
- Maker note: many reference images are allowed, with limits that vary by model (up to 14 objects on some). The TokenLab contract does not state a limit. Start with a few.

Contract:
- Nano Banana 2 and 2.1: `prompt`, `aspect_ratio`, `resolution` (1k, 2k, 4k), `size`, `response_format`, `async`; image inputs `image_url`, `image_urls`, `reference_image_urls`.
- Nano Banana 2 lite allows `resolution` 1k only.
- Nano Banana Pro and Gemini 3 Pro Image list fewer aspect ratios than Nano Banana 2. Read the list first.
- No `negative_prompt` on any of them.

Examples:
- "A photo of a matte black ceramic mug on a concrete bench. Three-point softbox light, 85mm lens, sharp focus on the rim, 4:5."
- Edit: "Using the supplied photo, replace only the blue sofa with a brown leather chesterfield. Keep the room, light, and shadows unchanged."

Pitfalls:
- Keyword lists give flat results. Use sentences.
- Lowercase `1k` is the TokenLab contract spelling. Use the contract value, not the maker's.
- Do not ask for long paragraphs of text in one image. Short lines render better.

## GPT image

Sources:
- https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide
- https://developers.openai.com/api/docs/guides/image-generation

Models: GPT Image (`gpt-image-*`). The contract lines below were read on GPT Image 2.

Structure that works:
- Order: scene or background, subject, key details, constraints.
- Say the use: "ad", "infographic", "UI mock". It sets the polish level.
- For a long prompt, use short labeled lines. Refine one change at a time.
- Name materials, shapes, and textures. Use "photorealistic" for photos. Treat camera specs as hints.
- Text: exact words in quotes or CAPS, font style, size, color, place. Spell odd words letter by letter. Add "no other text".
- Start with low quality for drafts. Use medium or high for small text, dense diagrams, close portraits, and identity edits.

Edits and identity:
- "Change only X, keep everything else the same." Repeat the keep list on each retry.
- Lock face, skin tone, body shape, pose, hair, and expression. Allow only the target change (for example clothing).
- Ask for a real fit (folds, drape) and matching light so edits do not look pasted.
- Label each input image by number and role.

Contract:
- `quality`: `auto`, `low`, `medium`, `high`. `background`: `auto` or `opaque`. The contract says transparent backgrounds are not supported. The maker guide describes transparency for some builds, so follow the contract.
- `size` is `auto` or WIDTHxHEIGHT. Both sides must be multiples of 16, the long edge at most 3840, the ratio at most 3:1, total pixels between 655,360 and 8,294,400.
- Edits go to `/v1/images/edits`. Up to 16 source images. A mask applies to the first image. The contract has no `input_fidelity`.
- No `negative_prompt`.

Examples:
- "Poster for a summer sale, verbatim headline "SUMMER SALE", bold sans-serif, centered at the top, white on navy. No other text."
- "Replace only the sofa with a green velvet one. Keep light, shadows, camera angle, and all other objects."

Pitfalls:
- Moody scenes (night, rain, neon) need extra detail on air and scale, or the image turns flat and real.
- Exact layout placement is not reliable. Say it once, then check.
- Recurring characters can drift. Use an anchor image.

## Seedream

Sources:
- https://docs.byteplus.com/en/docs/modelark/seedream-4-0-5-0-prompt-guide (the maker prompt guide; the page body did not load for me, so the points below come from search excerpts of the maker docs and are partial)
- https://docs.byteplus.com/en/docs/ModelArk/1541523 (image API reference)

Models: Seedream 5.0 (base, pro, lite, flash) and 4.5 (`seedream-*`).

Structure that works:
- Describe subject, action, and setting in plain, connected prose. Add style, color, light, or composition when they matter. Avoid keyword piles.
- Newer versions need less description than older ones. Short and exact beats many adjectives.
- Say what the image is for ("a logo for a gaming company", "a poster").
- Put every word that must appear in the image in double quotes.
- With input images, say "Figure 1", "Figure 2" and state what must stay unchanged.
- Maker limit: at most 300 Chinese characters or 600 English words. Long prompts make the model drop details.
- Size: set a resolution level and describe the shape in words, or set exact size. Do not do both (maker).

Contract:
- Seedream 5.0 and 4.5: text-to-image on `/v1/images/generations`; image-to-image on `/v1/images/edits`. Params include `prompt`, `aspect_ratio`, `resolution`, `size`, `quality`, `n`, `response_format`.
- Seedream 5.0 pro: `resolution` is required (1k or 2k). Image-to-image goes to `/v1/images/generations`.
- Seedream 5.0 lite lists `prompt`, `image`, `image_url`, `n`, `response_format`, `async`.
- No `negative_prompt`.

Examples:
- "A ceramic coffee cup on a wooden table by a rainy window, soft morning light, shallow depth of field, calm mood. Square product tile."
- Edit: "Put the dress from Figure 2 on the woman in Figure 1. Keep her face, pose, and background unchanged."

Pitfalls:
- Do not write both an exact size and a size description that disagree.
- Crowded scenes lose items. State the spatial relation of each key object.

## Recraft

Source: https://www.recraft.ai/docs/prompt-engineering-guide/prompting-with-recraft-v4

Models: Recraft V4.1 (base, pro, utility, flash; `recraft-*`).

Structure that works:
- Short prompts (about 3 to 6 words) let the model make design choices. Use them to explore, then make variants.
- For a set art direction, use a structured order: subject and scene, background, framing and pose, physical details, other subjects and where they sit, light, camera and depth, mood.
- Earlier items weigh more. Subject first keeps content in front. Style first keeps the visual language in front.
- Vector and logo work: name the graphic type, shape logic (geometry, symmetry, silhouette), a strict palette, one line weight, layout, and exclusions. Skip texture and material words.
- Typography: put every text string in quotes, then describe the system: headline size and place, second-level hierarchy, color blocking, surface.
- Posters: describe each visual layer, then how layers overlap. Give a grid, margins, and relative text sizes.
- 3D: define form, materials, light, camera, and color, or the result is loose.

Contract:
- Recraft V4.1 lists `prompt`, `n`, `size`, `response_format`. The listed `n` is 1 and the listed `size` is `1024x1024`. The pro, utility, and flash models list the same four fields. Read the contract for other sizes before you plan a layout.
- No `negative_prompt`. The maker examples state exclusions inside the prompt ("flat color, no gradients, no texture").

Examples:
- "Minimal fox logo, geometric shapes, centered, flat two-color palette (deep green and cream), uniform line weight, no gradients, no text."
- "Poster, top-centered headline "NIGHT MARKET" large, small subtitle below, warm lantern photo behind, 12-column grid, wide margins."

Pitfalls:
- Dramatic adjectives add noise. Use concrete details.
- Unquoted text gets paraphrased.

## Qwen image

Source: https://www.alibabacloud.com/help/en/model-studio/qwen-image-api (API reference with prompt notes). The maker's detailed prompt guide is a separate page that I did not read.

Models: Qwen Image 3.0, 2.0, 2.0 pro, and Qwen Image Edit (`qwen-image-*`).

Structure that works:
- Describe content, style, and composition. Chinese and English both work.
- For text: for each string, give the exact words in quotes, its role (title, subtitle, speech bubble, footer), its place ("at the top"), and the font style and color ("bold blue cartoon font").
- The maker says the 2.0 family handles multi-line and paragraph text, and the Pro models render text more professionally.
- Maker limits for the 2.0 family: about 1,300 tokens per prompt, and text over the limit is cut. Stay well below.
- Maker feature: `prompt_extend` rewrites your prompt. Turn it off when you need exact control. The TokenLab contract does not list it.

Contract:
- Qwen Image 3.0: `prompt`, `image`, `image_url`, `image_urls`, `mask`, `reference_image_urls`, `n`, `resolution` (1k, 2k), `size`, `response_format`. No `negative_prompt`.
- Qwen Image 2.0: `prompt`, `image_url`, `n`, `resolution`, `size`, `response_format`.
- Qwen Image Edit 2511 (edit only): `negative_prompt`, `cfg_scale`, `guidance_scale`, `seed`, `steps`, `image`, `image_url`, `image_urls`, `images`, `width`, `height`.

Example:
- "A cafe menu board. Title "TODAY'S BREW" at the top in white chalk lettering. Three lines below, left aligned: "Latte 4.5", "Mocha 5.0", "Tea 3.0". Dark green board, warm light."

Pitfalls:
- A comma list of adjectives gives generic images and garbled letters. Give exact strings and places.
- Keep each text block short.

## Ideogram

Sources: no official prompting guide found. The maker API reference (https://developer.ideogram.ai/) covers parameters only, so the advice below is general.

Models: Ideogram 4.5 and the Ideogram V3 generate models (`ideogram-*`).

Conservative advice:
- Use Ideogram when the picture needs readable text. Put the exact words in quotes and say where each line sits.
- Keep each text line short. Say the surface (sign, label, poster) and the font style.
- Describe subject, setting, light, and style in short sentences.

Contract:
- Ideogram V3 generate text-to-image lists `prompt`, `aspect_ratio`, `negative_prompt`, `expand_prompt`, `n`, `seed`, `response_format`. `expand_prompt` may rewrite your prompt. Read its contract description before you rely on exact wording.
- Ideogram 4.5 lists `prompt`, `quality` (`low`, `medium`, `high`), `width`, `height`, `n`, `seed`, `output_format`, and for edits `image`, `image_url`, `image_urls`, `mask`. No `negative_prompt`.

Example:
- "Storefront sign above a bakery door, hand-painted cream letters on dark green, reads "OLD MILL BAKERY", warm evening light, 3:2."

Pitfalls:
- Long copy fails. Use a headline and a short line.
- Test the exact spelling. Re-run with a new `seed` before you rewrite the prompt.
