# Audio prompt families: music and speech

Each section starts with the source. "Contract" lines state what the TokenLab model contract lists. Check the live contract before you send a parameter. Numbers marked "maker" come from the model maker's docs and may differ from TokenLab limits.

## Suno

Sources:
- https://help.suno.com/en/articles/5782977 (V4.5 prompts and the lyrics box; I saw only a search excerpt of this page)
- https://suno.com/hub/how-to-make-a-song and https://suno.com/hub/how-to-make-beats (maker hub pages; style prompt examples and structure tags)

No full official prompt manual was read. Treat the points below as maker hints from those pages.

Model: `suno-music`.

Structure that works:
- Two kinds of text. Style text says how the song sounds. Lyrics say what is sung. Do not mix them.
- Style text: genre (be specific), mood and energy, vocal type, key instruments, tempo or BPM, key if you know it. Maker example: "Bright pop track, 110 BPM, female vocals, big synth hook in the chorus, intimate piano in the verse."
- Vague style text ("a happy pop song") gives generic songs.
- Do not stack many genres. One or two related styles work better than five.
- Lyrics: use section tags on their own lines: `[Intro]`, `[Verse 1]`, `[Chorus]`, `[Bridge]`, `[Outro]`. Short, concrete images carry more than broad claims. Each line should move the scene forward.
- For beats and loops: order the style text as tempo, genre, rhythm style, instruments, mood. Name instruments directly.
- Leave the lyrics empty and add the instrumental option for a song with no vocals.

Contract:
- Fields listed: `prompt`, `tags`, `full_lyrics`, `title`, `negative_tags`, `make_instrumental`, `mv` (model version), `action`. For uploaded audio, `audio_operation` selects cover, extend, replace-section, add-instrumental, or stem separation. Each mode has required fields in the contract notes.
- The contract notes do not say which of `prompt`, `tags`, and `full_lyrics` holds style text and which holds lyrics. Read the contract and a sample request before you map your text.
- `negative_tags` is the negative control. Keep it short.
- `mv` selects the model version. The contract notes say some flows need it.

Example (style text):
- "Contemporary R&B, 92 BPM, warm soulful male lead, soft female backing vocals in the chorus, electric piano, deep bass, mellow swing drums, clean guitar riffs."
- Example (lyrics): `[Verse 1]` "Streetlights hum on the wet window glass" then `[Chorus]` "Take me home, take me home tonight".

Pitfalls:
- Style text and lyrics are separate. Put section tags in the lyrics, not in the style text.
- Stacked genres and vague words give generic songs.

## MiniMax music

Source: https://platform.minimax.io/docs/api-reference/music-generation

Model: `minimax-music-2.6`.

Structure that works:
- Style prompt: describe style, mood, and setting with short comma-separated terms. Maker example: genre, emotion, and scene together ("indie folk, introspective, a solitary walk, a coffee shop").
- Maker prompt limit: 2000 characters.
- Lyrics: one line per row. Maker structure tags: `[Intro]`, `[Verse]`, `[Pre Chorus]`, `[Chorus]`, `[Post Chorus]`, `[Bridge]`, `[Interlude]`, `[Hook]`, `[Build Up]`, `[Break]`, `[Transition]`, `[Solo]`, `[Inst]`, `[Outro]`. Maker lyrics limit for vocal tracks: 3500 characters.
- A song with no vocals needs the style prompt only.

Contract:
- Fields listed: `prompt`, `full_lyrics`, `negative_prompt`, `n`, `seed`, `output_format`.
- The maker has an instrumental switch and a lyrics writer. The contract lists neither. For no vocals, say "instrumental, no vocals" in the prompt and leave `full_lyrics` empty.

Example:
- Prompt: "Indie folk, introspective, slow tempo, fingerpicked acoustic guitar, soft brush drums, a solitary walk in autumn."
- Lyrics: `[Verse]` "Leaves on the path where we used to walk" then `[Chorus]` "I carry the light, I carry it home".

Pitfalls:
- Use only the maker's listed structure tags.
- The prompt is style, not a story. Keep the story in the lyrics.

## Stable Audio

Sources:
- https://kb.stability.ai/knowledge-base/stable-audio-3-prompt-guide
- https://github.com/Stability-AI/stable-audio-3/blob/main/docs/guides/prompting.md

Models: `stable-audio-3`, `stable-audio-3-small-music-text-to-audio`, `stable-audio-3-small-sfx-text-to-audio`, `stable-audio-3-small-sfx-base-text-to-audio`.

Structure that works:
- Music: genre first, then main instruments and rhythm, then mood, arrangement, and production feel. Add BPM. Era, place, a recording method, or a listening scene help ("the last song of a long night at a club").
- The model is meant for instrumentals. It may make wordless vocal sounds, not clear singing.
- Isolated parts: start with `TrackType: Instrument`, name the instrument, add genre, energy, and BPM. Add `Format: Duo` for two instruments. Playing technique, room, and mic position help.
- Samples and SFX: describe three things. The source (what makes the sound), the action (how it starts and how long it lasts), and the recording (room, mic, effects). Add `TrackType: SFX`.
- Maker: the small music model does not support SFX. Use a small SFX model or the full model.
- Pick a realistic length. SFX are short. Maker maximum: about 6 minutes 20 seconds on the medium model and 2 minutes on small.
- Results vary per run. Iterate.

Contract:
- `stable-audio-3`: `prompt`, `duration`, `output_format` (mp3, wav), `seed`, `steps`, `cfg_scale`, `model`.
- The three `stable-audio-3-small-*` models: `prompt`, `duration`, `seconds`, `seed`, `steps`, `guidance_scale`, `negative_prompt`.
- The maker guide does not cover negative prompts. Use `negative_prompt` only as a light extra.

Examples:
- Music: "Detroit-influenced techno, stripped-back arrangement, metallic percussion, deep sub bass, raw analog synths, 130 BPM."
- SFX: "TrackType: SFX. Heavy wooden door slams in a stone hall, long reverb tail, close mic, 3 seconds."

Pitfalls:
- Pick a realistic length for the sound. The maker says realistic lengths give better results.
- Do not ask for sung lyrics. The model makes instrumentals.

## TTS voices

The script is the prompt. Write it the way it should sound. Pick the voice and speed with parameters, not with prose.

General rules:
- Spell out numbers, dates, units, and symbols the way they should be said, unless the model handles them well. Small and fast models misread them most (maker advice for ElevenLabs).
- Use normal punctuation for rhythm. Commas and full stops set pace.
- For a long script, split it by paragraph. Generate each part, then join.
- Test a short sample of the voice before the full script.

### Grok voices

Source: https://docs.x.ai/developers/model-capabilities/audio/text-to-speech

Model: `grok-tts`.

- Voices in the contract: `eve`, `ara`, `rex`, `sal`, `leo`. The maker page does not describe them. Listen to a sample of each before you choose.
- Maker tags: inline tags like `[pause]`, `[long-pause]`, `[laugh]`; wrapping tags like `<whisper>...</whisper>`, `<slow>`, `<soft>`. Put them where the expression would happen, wrap whole phrases, and do not stack many. Nesting works: `<slow><soft>Goodnight, sleep well.</soft></slow>`.
- Maker: any built-in voice can speak any supported language.
- Contract: `input`, `voice`, `response_format` (`mp3`). No speed field.

### MiniMax speech

Source: https://platform.minimax.io/docs/api-reference/speech-t2a-http

Models: `speech-2.8-hd`, `speech-2.8-turbo`, `minimax-speech-2-8`.

- `voice_id` picks the voice; `speed` sets pace (maker range 0.5 to 2, default 1). Contract default voice: `male-qn-qingse`. `speech-2.8-hd` also lists English voice names such as `English_expressive_narrator` and `English_Whispering_girl`.
- Pause marker in the text (maker): `<#1.5#>` for a 1.5 second pause. Put it between speech, not at an edge, and not twice in a row. Range 0.01 to 99.99.
- Interjection tags in the text (maker, 2.8 models): `(laughs)`, `(sighs)`, `(breath)`, `(gasps)`. Test each one.
- Maker input limit: under 10,000 characters per call.
- Contract: `speech-2.8-hd` and `speech-2.8-turbo` list `input`, `voice`, `voice_id`, `speed`, `response_format`. They do not list `emotion`, `vol`, or `pitch`, so set mood with the script and the voice choice. `minimax-speech-2-8` lists `language_code` and `n` and no `speed`.

### ElevenLabs

Source: https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices

Model: `eleven-v4-turbo`.

- v3 and v4 take audio tags in square brackets for delivery, such as emotion, whisper, or a laugh. Describe the voice quality in the tag so it is not read as a sound effect, for example `[low, gravelly voice]`. Match tags to the voice. Test rare tags.
- Ellipses add a pause and weight. Capital letters add stress. Natural speech punctuation sets the rhythm.
- SSML break tags are for older models. Do not use them on v3 or v4.
- v4 reads IPA between slashes for hard words. Use it only on words that need it.
- For a long piece, make short segments and join them.
- Contract: `input`, `voice`, `language_code`, `seed`, `response_format`. No `speed` field is listed (the maker's speed control is a voice setting, not in the contract).

### CosyVoice

Source: https://www.alibabacloud.com/help/en/model-studio/introduction-to-cosyvoice-ssml-markup-language (SSML) and https://www.alibabacloud.com/help/en/model-studio/cosyvoice-voice-list (instructions).

Model: `cosyvoice-v3.5-plus`.

- Maker: SSML tags in the text can set rate, tone, pauses, and volume, but only for some voices. The maker also has an `instruction` field with a strict Chinese format. The TokenLab contract lists neither an SSML switch nor an instruction field.
- Contract: `input`, `voice`, `speed`, `response_format`. Use `speed` and the voice choice. Do not rely on SSML in `input` until a short test shows it works.

### Qwen3 TTS

Source: https://www.alibabacloud.com/help/en/model-studio/qwen-tts

Model: `qwen3-tts-flash`.

- The maker says style instructions belong to the separate instruct model, not to the plain flash model. The contract has no instruction field.
- Contract: `input`, `voice` (default `Cherry`), `language_code`, `speed`, `response_format`. Output is WAV whatever you ask. Set `language_code` to the language of the text for correct sound.
- Pick the voice first. Then tune `speed`.

Example scripts:
- Calm narration: "Welcome back. Today, we walk through three simple steps. First, open the app."
- Grok: "<soft>It was a quiet night.</soft> [pause] Then the phone rang."
- ElevenLabs: "[whispering] Do not wake the others... [softly] we leave at dawn."

Pitfalls:
- A tag from one family does nothing, or is read aloud, in another. Use the tag style of the chosen family only.
- Long scripts in one call get uneven pace. Split them.
