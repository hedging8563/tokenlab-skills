# Video prompt families

Each section starts with the source. The "Models" line gives the family and its ID pattern. Find current IDs with `GET /v1/models?recommended_for=video` and pick the ones that match. "Contract" lines state what the TokenLab model contract lists. Check the live contract before you send a parameter. Numbers marked "maker" come from the model maker's docs and may differ from TokenLab limits.

General video rules:
- Text-to-video: write the full scene. Image-to-video: write only motion, camera, and a stability rule. The image already shows the scene.
- One clear action per shot. Slow, small, connected motion is more reliable than big, fast action.
- Write one camera move per shot. Stacked moves cause wobble.
- Show speed with physical signs (lean, spray, streaked background). Do not rely on "fast".
- Put dialogue in quotes and name the speaker each time. Put sound cues in their own sentence.
- Replace "cinematic", "epic", and "beautiful" with a visible detail.

## Seedance

Sources (maker prompt guides; the points below are a short subset, so read the guides for the full rules):
- https://docs.volcengine.com/docs/ark/seedance-2-0-prompt-guide
- https://docs.byteplus.com/en/docs/modelark/seedance-2-0-prompt-guide
- https://docs.byteplus.com/en/docs/ModelArk/2607689 (Seedance 2.5)

Models: Seedance 2.0 (base, fast, mini) and 2.5 (`seedance-2*`).

Structure that works:
- Formula: precise subject, action detail, scene, light and color tone, camera move, visual style, quality, constraints. Lock who does what first, then where, then how it is shot.
- For a complex video, write shots in time order. Per shot: who, where, what they do, how the camera moves. Add sound per shot if you want it.
- Write body parts, size, speed, and force of the action. Prefer slow, gentle, linked motion. Avoid big sprints, jumps, and rolls. Show emotion with body detail, not with "very sad".
- Refer to inputs as type plus number: "Image 1", "Video 1", "Audio 1", in the order you send them. Give each one a job: "Image 1 is the first frame, Image 2 sets the outfit, Video 1 sets the camera move".
- Edit a video: "Strictly edit Video 1: change <old trait> to <new trait>, keep everything else." To add, say what, when, and where. To delete, say what, and say what stays.
- Maker 2.5 notes: edit prompts need an edit word (edit, add, delete, replace). Extend prompts need an extend word (extend forward or backward, continue).
- The maker's older guides say negative prompt words do not work. Write wanted results in positive words.

Contract:
- Operations: `text-to-video`, `image-to-video`, `start-end-to-video`, `reference-to-video`, `video-to-video`, `video-extension`.
- Params: `prompt`, `duration`, `resolution`, `aspect_ratio` (includes `adaptive`), `generate_audio`, `output_audio`, `seed`, `return_last_frame`, `watermark`. Reference inputs: `image_urls`, `video_urls`, `audio_urls`, `reference_images`. Extension uses `task_id`.
- No `negative_prompt`. Seedance 2.5 does not list `seed`.

Example:
- "Shot 1 (0 to 4 s): a baker in a flour-dusted apron kneads dough on a wooden table, slow push-in, warm window light. Shot 2 (4 to 8 s): close-up of her hands shaping a loaf, steady camera. Sound: soft kitchen ambience, dough slaps."
- "Image 1 is the first frame. The woman turns her head slowly toward the window and smiles. Camera holds still. Her outfit and the room stay unchanged."

Pitfalls:
- Many inputs with no jobs make the model guess. Give each input one role.
- Big action in a short clip breaks. Split into shots.

## Kling

Sources:
- https://kling.ai/quickstart/klingai-video-3-model-user-guide
- https://kling.ai/blog/kling-ai-prompt-guide
- https://app.klingai.com/global/dev/document-api/apiReference/model/textToVideo (API reference)

Models: Kling 3.0 and Kling Omni video (`kling-*`).

Structure that works:
- Maker formula: subject, action, scene, camera, light, mood. Write like a scene direction.
- Order for a full prompt: setting and mood, then characters and looks, then actions in order with camera beside them, then dialogue.
- Camera words: push-in, pan, tilt, orbit, tracking, extreme close-up, medium close-up, establishing wide, low angle. For an unbroken take, say "one continuous take, no cuts".
- Multi-shot: the maker has auto (the model plans cuts) and custom (it follows your shots). For custom, write "Shot 1", "Shot 2", with framing, angle, and move for each. Maker API form: "shot n, m seconds, text;" with shot lengths that add up to the clip length (up to 6 shots; each shot text at most 512 characters).
- Dialogue: one character, one line, with the tone in brackets: `Clerk (dry, British accent): "We close in five."` Do not use pronouns for speakers.
- Image-to-video: write only how the scene changes. A start frame plus element references holds identity better than a start frame alone.
- Maker limit for the 3.0 API: the prompt can hold at most 3072 characters (2500 recommended). The 3.0 API has no separate negative field. Negative words go in the prompt.

Contract:
- Kling 3.0 (base): text-to-video and image-to-video; `prompt`, `duration` (3 to 15), `resolution` (720p, 1080p), `start_image`, `end_image`, `image_url`, `output_audio`.
- Kling 3.0 pro (`kling-video-3-0-*`): adds `negative_prompt`, `n`, `reference_images`, `video_urls`, `frames`, `end_image`.
- Kling Omni video: `reference-to-video` and `video-to-video`; `image_urls`, `video_urls`, `duration`, `resolution`, `aspect_ratio`, `output_audio`.
- Kling 3.0 (base) lists no `multi_shot` field. Write shots in the prompt and check that the result cuts as asked.

Example:
- "Wide shot of a foggy harbor at dawn, slow pan right. Cut to a close-up of a fisherman knotting rope, handheld. Cut to an over-the-shoulder view as his boat leaves the dock. Sound: gulls, creaking wood."

Pitfalls:
- A static camera plus a sweeping pan in one prompt conflict. Pick one.
- Vague speaker labels give garbled dialogue. Keep name, line, and tone together.
- Keep on-screen text short and exact.

## Veo

Sources:
- https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1
- https://ai.google.dev/gemini-api/docs/veo

Models: Veo 3.1 (base, fast, lite; `veo*`).

Structure that works:
- Maker formula: cinematography, subject, action, context, style and ambiance. Camera comes first because it carries tone.
- Camera vocabulary: dolly, tracking, crane, aerial, slow pan, POV; wide, close-up, extreme close-up, low angle, two-shot; shallow depth of field, macro, wide-angle, soft focus.
- Dialogue in quotes: `A woman says, "We have to leave now."` Sound effects with `SFX:`. Background sound with `Ambient noise:`.
- Timed shots in one clip: `[00:00-00:02] Medium shot ... [00:02-00:04] Reverse shot ...` with sound per segment.
- Say the wanted result, not "no X": "a desolate plain with no buildings" works better than "no man-made structures".
- Reference images (maker: up to 3 of a person, character, or product) keep looks stable across shots. Maker: such clips must be 8 seconds, and the Lite model does not support them.
- First and last frame: send both images, then write the move and sound between them.
- Extension (maker): each step adds about 7 seconds, from a recent Veo clip, 720p only, not on Lite.

Contract:
- Veo 3.1 and Veo 3.1 fast: `text-to-video`, `image-to-video`, `reference-to-video`, `start-end-to-video`, `video-extension`. Params: `prompt`, `duration` (4, 6, 8), `resolution` (720p, 1080p), `aspect_ratio` (9:16, 16:9), `generateAudio`, `output_audio`. Extension takes `task_id` or `origin_task_id`.
- Veo 3.1 lite: text-to-video and image-to-video only, `duration` 8 only.
- No `negative_prompt` is listed, though the maker API has one. Use positive wording.

Example:
- "Slow crane shot rises from a lone hiker to reveal a misty canyon at sunrise. Epic fantasy look, soft gold light. Ambient noise: wind. SFX: boots on gravel."

Pitfalls:
- The maker calls the camera the strongest lever for tone. Do not leave it out.
- Long speech does not fit 4 seconds. Match the line to the clip length.

## Hailuo and MiniMax video

Sources:
- https://platform.minimax.io/docs/api-reference/video-generation-i2v (camera commands, older models)
- https://platform.minimax.io/docs/guides/video-prompt (H3 examples; it is a gallery, not a formal guide)

Models: Hailuo H3, H3 max, and 2.3 (`hailuo-*`).

Structure that works:
- Hailuo 2.3 (maker docs): put camera commands in square brackets. The 15 commands are Truck left/right, Pan left/right, Push in, Pull out, Pedestal up/down, Tilt up/down, Zoom in/out, Shake, Tracking shot, Static shot. Join up to 3 in one bracket for a joint move: `[Pan left,Pedestal up]`. List brackets in order for a sequence. Plain words also work, but the maker says explicit commands are more exact. Maker limit: 2000 characters.
- Shape: `[Camera command] subject, visible action, setting, light and look`.
- Hailuo H3 (maker examples): start with length and aspect ratio, then the use, then a job for each reference image, then the core action, then camera, style, and sound. Use plain camera words (dolly in, track left, handheld, locked-off). The H3 maker pages do not list bracket commands, so do not assume they work.
- Say the edit rhythm and the feeling you want ("tight, punchy cuts", "slow and calm").

Contract:
- Hailuo H3: all of `text-to-video`, `image-to-video`, `start-end-to-video`, `reference-to-video`. Params: `prompt`, `negative_prompt`, `seed`, `duration` (6, 10), `resolution` (768p, 2k), `aspect_ratio` (16:9, adaptive). Reference-to-video takes one to five images. Video and audio references and 2K output are not supported for it.
- Hailuo H3 max: text-to-video, image-to-video, start-end-to-video; `duration` 5 to 15; `resolution` 480p, 768p.
- Hailuo 2.3: text-to-video and image-to-video; `duration` 6, 10; `resolution` 768p, 1080p. No `negative_prompt`.

Example:
- Hailuo 2.3: "[Push in] A ceramic cup of coffee on a stone table, steam rising, soft morning light from the left."
- Hailuo H3: "10s, 16:9. Image 1: the courier. Image 2: the rainy street at night. The courier jogs across the street, low-angle tracking shot, neon rim light, wet reflections. Sound: rain, footsteps."

Pitfalls:
- More than 3 camera commands in one bracket is outside the maker advice.
- Do not mix bracket commands into an H3 prompt unless a test shows they work.

## Wan

Source: https://www.alibabacloud.com/help/en/model-studio/text-to-video-prompt

Models: Wan 3.0, 3.0 prime, and 2.6 (`wan-*`).

Structure that works:
- Basic formula: subject, setting, movement. Advanced: add detail to each, then aesthetic control (light, shot size, angle, lens, camera move) and a style name.
- A prompt with no light, shot, or camera gets "a static camera in an undefined void" (maker words, paraphrased). Camera moves carry meaning: push-in is close or tense, pull-out shows scale, tracking walks beside the subject, orbit adds weight, fixed camera is calm.
- Image-to-video: write only motion (with speed words like "slowly") and camera, or "fixed camera".
- Sound (2.5 and later): give the voice line with emotion, tone, and pace; the sound effects with source and action; and the music style.
- Several speakers: one stable label per character, an action before each line, a distinct voice note, and a link word such as "Immediately".
- Multi-shot (2.6 and later): a short story summary, then numbered shots with time ranges, such as `Shot 1 [0-3 s]`. For a single shot on 2.7 and later, write "Generate single shot."
- Reference-to-video: Wan 3.0 style models call inputs "Image n" and "Video n", numbered by upload order, images and videos counted apart. Wan 2.6 uses `character1`, `character2` (up to 3). Quoted dialogue is kept. Write "No dialogue." or "No background music." to stop the model from adding them.
- The maker lists things to avoid: real people by name, scene cuts in one clip, exact readable text, long choreographed action, exact lip sync.

Contract:
- Wan 3.0 and 3.0 prime: `text-to-video`, `image-to-video`, `reference-to-video`, `start-end-to-video`. Params: `prompt`, `duration` (2 to 30), `resolution`, `aspect_ratio`, `start_image`, `end_image`, `image_urls`, `video_urls`, `audio_urls`, `reference_images`. No `negative_prompt`.
- Wan 2.6: `text-to-video`, `image-to-video`; `duration` 2, 5, 10, 15; params `audio`, `output_audio`, `reference_urls`. No `negative_prompt`.
- The maker docs do not describe a negative prompt for the video guide. Do not send one.

Example:
- "Warm tones, side light, low-angle medium shot, slow push-in. A fisherman in a yellow raincoat hauls a net on a rocking deck at dawn. Waves crash, gulls cry, a soft cello plays. No dialogue."

Pitfalls:
- Pronouns in a two-person scene swap the voices. Use labels.
- A scene cut inside one single-shot prompt is not reliable.

## PixVerse

Source: https://pixverse.ai/en/blog/ai-video-prompt-guide-7-tested-fixes (maker blog; no formal docs page found).

Models: PixVerse V6 and C1 (`pixverse-*`).

Structure that works:
- Keep it to about 50 to 80 words, with the main action first.
- Three sentences: (1) subject, one action, location; (2) one camera move plus a specific style, lens, light, or composition cue; (3) what stays stable, what is absent, and sound.
- Drop "cinematic" and "epic". Name light, lens, composition, palette, or camera path.
- One camera move per prompt. Add at most one texture cue (for example slight handheld feel).
- No fake negative words ("no jitter"). Say "hands move naturally".
- Do not say "fast". Show speed with spray, lean, or streaks.
- Image-to-video: do not re-describe the image. Write motion, camera, and a stability rule.

Contract:
- PixVerse V6 and C1: `text-to-video`, `image-to-video`, `start-end-to-video`, `reference-to-video`. Params: `prompt`, `duration` (1 to 15), `resolution` (360p to 1080p), `aspect_ratio`, `output_audio`; image and video inputs. No `negative_prompt`.

Example:
- "An old fisherman coils wet rope on a wooden dock at dawn. Slow lateral tracking shot, soft pink backlight, 35mm lens feel, mist over grey water. His hands move naturally, the dock stays level, no text on screen. Sound: lapping waves, creaking planks."

Pitfalls:
- A long prompt buries the main action.
- Several camera moves in one clip give jitter.

## Grok Imagine

Sources (API docs only; no dedicated prompting guide found):
- https://docs.x.ai/developers/model-capabilities/video/generation
- https://docs.x.ai/developers/model-capabilities/video/reference-to-video

Models: Grok Imagine video and Grok Imagine video 1.5.

Conservative advice:
- The maker says the 1.5 models make a first frame from your text, then animate it. So describe a strong still frame first, then one action and one camera move.
- A prompt is needed only for text-to-video. With an image, write what changes: the action, the camera, the mood. Do not repeat what the image shows.
- Audio is on by default and can include speech and effects. Ask for sounds in the prompt. The 1.5 models make lip-synced speech from quoted lines.
- For reference-to-video the maker tags inputs by zero-based position: `<IMAGE_0>`, `<IMAGE_1>`, and voices `<AUDIO_0>`. A pinned first image takes `<IMAGE_0>`. Give each tag one job and keep the character count low.
- Detailed scenes take longer. Over-long prompts return an error.

Contract:
- Grok Imagine video (base): `text-to-video`, `image-to-video`, `reference-to-video`, `video-to-video`, `video-extension`. Params: `prompt`, `duration` (1 to 15), `resolution` (480p, 720p), `aspect_ratio`. Extension takes `task_id`, `extend_at`, `extend_times`.
- Grok Imagine video 1.5: `text-to-video` and `image-to-video` only, with `generate_audio`, `resolution` up to 1080p. The contract does not list reference-to-video or first and last frame for 1.5.
- No `negative_prompt`.

Example:
- "A street vendor lifts the lid off a steaming pot at dusk, steam fills the frame. Slow dolly forward. Sound: sizzle, distant traffic. She says, "Fresh and hot.""

Pitfalls:
- Long scene lists slow the job and may fail. Keep one scene.
- Do not use maker tag syntax unless the contract operation lists reference inputs.
