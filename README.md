# TokenLab Skills

[![Validate skills](https://github.com/hedging8563/tokenlab-skills/actions/workflows/validate.yml/badge.svg)](https://github.com/hedging8563/tokenlab-skills/actions/workflows/validate.yml)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-111827)](https://agentskills.io/specification)

Agent Skills for [TokenLab](https://tokenlab.sh). Each skill is a recipe for one outcome: a product photo, an animated still, a voiceover, a 3D asset, a typed decision. The agent loads a skill from its `description`, follows the workflow, and calls the TokenLab API over HTTP or MCP. It reads the live model catalog at run time, so the skill stays correct when models change.

## How the skills fit together

- **Foundation skills** do the shared work:
  - `tokenlab-run`: the execution contract. Read the model contract, estimate the cost, provide inputs, call, wait for the task, and read the result.
  - `tokenlab-model-picker`: map an outcome to an operation and to live model IDs.
  - `tokenlab-prompting`: prompt craft per model family.
- **Outcome skills** (image, video, audio, 3D, decisions) name default models, a workflow, technique, and a quality bar. They call `tokenlab-run` for the mechanics.
- **Integration skills** put TokenLab into application code: SDK setup, native endpoints, cost routing, and migration from other OpenAI-compatible providers.

Install `tokenlab-run` together with any outcome skill. The plugin installs all of them.

## Catalog

`catalog.json` owns the skill list, groups, order, operations, and preferred models. `skills.sh.json` and this section are generated from it with `python3 scripts/sync_catalog.py`.

## Model defaults refresh daily

Skills do not hard-code model IDs in their text. Each skill's `## Models` section holds a block that `scripts/sync_models.py` generates from the live catalog (`GET https://api.tokenlab.sh/v1/models`, no key needed):

1. The skill's `preferredModels` from `catalog.json` that are live and support the operation come first.
2. If none is live, the top three models that `recommended_for=<scene>` ranks by 24-hour success rate take their place, plus one low-cost option. When the API does not offer a scene yet (for example `decision`), the `category=<scene>` list is used instead.

The script also writes `generated/availability.json`: for each skill, `status` (`available`, or `unavailable` when no live model supports any of its operations), the current `models`, and `checkedAt`. Capability-specific operations (for example background removal, vectorizing, avatars, upscaling, motion control) set `rankedFallback` to `false` in `catalog.json`: when their preferred models are gone, the skill shows the operation as unavailable instead of a general model. Deprecated and preview models are never listed.

The [Sync model defaults](.github/workflows/sync-models.yml) workflow runs it daily:

- If a catalog read fails or the catalog lists fewer than 200 models, it stops and writes nothing.
- A small change (at most 3 skills, and at most 2 that become unavailable) gets a patch version, passes the tests and skill validation, and is pushed to `main`. Plugin and Skills CLI users get it on their next update.
- A larger change opens a pull request for review instead.

<!-- catalog:start -->

**Foundation** - Run any TokenLab request correctly, pick the model, and write the prompt.

- [`tokenlab-run`](skills/tokenlab-run/) - The execution contract: contract, estimate, upload, call, poll, read results.
- [`tokenlab-model-picker`](skills/tokenlab-model-picker/) - Pick the model for an outcome from live catalog signals.
- [`tokenlab-prompting`](skills/tokenlab-prompting/) - Prompt craft per model family for image, video, music, and speech.

**Image** - Create and edit images: product shots, edits, upscales, text, characters, photoreal stills, and logos.

- [`tokenlab-product-photography`](skills/tokenlab-product-photography/) - Packshot to studio, lifestyle, and hero shots.
- [`tokenlab-edit-image`](skills/tokenlab-edit-image/) - Add, remove, replace, recolor, and cut out backgrounds.
- [`tokenlab-restore-and-upscale`](skills/tokenlab-restore-and-upscale/) - Upscale, sharpen, and restore old or low-resolution photos.
- [`tokenlab-text-in-image`](skills/tokenlab-text-in-image/) - Posters, packaging, and UI mockups with exact, legible text.
- [`tokenlab-character-consistency`](skills/tokenlab-character-consistency/) - Keep one character or product the same across images and clips.
- [`tokenlab-photoreal-stills`](skills/tokenlab-photoreal-stills/) - Realistic photos of people, places, food, and scenes.
- [`tokenlab-logos-and-vectors`](skills/tokenlab-logos-and-vectors/) - Logos, icons, and flat marks, with SVG vectorizing.

**Video** - Animate stills, make ads and cinematic shots, control frames and motion, extend and edit clips.

- [`tokenlab-animate-image`](skills/tokenlab-animate-image/) - Turn a still image into a short video clip.
- [`tokenlab-product-ad-video`](skills/tokenlab-product-ad-video/) - Product image or brief to a short ad clip.
- [`tokenlab-keyframe-transition`](skills/tokenlab-keyframe-transition/) - Video that moves from a first frame to a last frame.
- [`tokenlab-extend-video`](skills/tokenlab-extend-video/) - Continue a clip past its last frame.
- [`tokenlab-edit-video`](skills/tokenlab-edit-video/) - Restyle or change an existing clip with a prompt.
- [`tokenlab-motion-control`](skills/tokenlab-motion-control/) - Move a character image with the motion of a reference video.
- [`tokenlab-talking-avatar`](skills/tokenlab-talking-avatar/) - Portrait plus script or audio to a talking-head video.
- [`tokenlab-cinematic-video`](skills/tokenlab-cinematic-video/) - Text or image to cinematic shots with camera language.

**Audio** - Voiceover, transcripts and subtitles, and music.

- [`tokenlab-voiceover`](skills/tokenlab-voiceover/) - Script to natural speech audio with a chosen voice.
- [`tokenlab-transcribe-and-subtitle`](skills/tokenlab-transcribe-and-subtitle/) - Audio or video to transcripts, SRT/VTT subtitles, and translations.
- [`tokenlab-music`](skills/tokenlab-music/) - Songs, instrumentals, and sound effects from a brief.

**3D and worlds** - Downloadable 3D assets and explorable worlds.

- [`tokenlab-image-to-3d-asset`](skills/tokenlab-image-to-3d-asset/) - Image or text to a downloadable 3D model (GLB and more).
- [`tokenlab-world-generation`](skills/tokenlab-world-generation/) - Text, image, or video to an explorable 3D world.

**Decisions** - Typed yes/no, choice, and score answers for agent branches.

- [`tokenlab-decisions`](skills/tokenlab-decisions/) - Typed yes/no, choice, and score answers with System One.

**Integration** - Put TokenLab into apps, native endpoints, cost routes, and OpenAI-compatible migrations.

- [`tokenlab-api-integration`](skills/tokenlab-api-integration/) - Runnable TokenLab code for chat, native, media, and async tasks.
- [`tokenlab-native-endpoints`](skills/tokenlab-native-endpoints/) - Use Responses, Messages, Gemini, and System One native routes.
- [`tokenlab-cost-routing`](skills/tokenlab-cost-routing/) - Cost-aware model routes and fallback chains from live pricing.
- [`tokenlab-openai-compatible-migration`](skills/tokenlab-openai-compatible-migration/) - Move OpenAI-compatible apps to TokenLab with a minimal diff.

<!-- catalog:end -->

## Install

### Claude Code plugin marketplace

```text
/plugin marketplace add hedging8563/tokenlab-skills
/plugin install tokenlab@tokenlab-tools
```

Installed skill names are namespaced, for example `/tokenlab:tokenlab-product-photography`.

### Codex plugin

Codex CLI 0.149.0 can consume this marketplace:

```bash
codex plugin marketplace add hedging8563/tokenlab-skills
codex plugin add tokenlab@tokenlab-tools
```

### Skills CLI (any agent)

Install one skill at a time:

```bash
npx skills add https://github.com/hedging8563/tokenlab-skills --skill tokenlab-run -y
npx skills add https://github.com/hedging8563/tokenlab-skills --skill tokenlab-product-photography -y
```

Use any id from the catalog above.

### Copy the folders

The skills follow the open [Agent Skills specification](https://agentskills.io/specification). Clone the repository and copy the `skills/<id>/` folders into the directory your agent loads skills from (for example `.claude/skills/` or `.agents/skills/`).

```bash
git clone https://github.com/hedging8563/tokenlab-skills.git
```

## API key and MCP servers

Media, audio, 3D, and decision calls need a TokenLab API key in `TOKENLAB_API_KEY`. Model discovery and pricing work without a key.

The plugin bundles two optional MCP connections:

- `tokenlab-stdio` runs the published `@tokenlabai/mcp-server` over stdio. It uses the `core` tool profile by default, so outcome skills can call `create_image`, `create_video`, `create_music`, `create_3d_model`, `create_speech`, `evaluate_decisions`, `get_task_status`, and the other credentialed tools. Set `TOKENLAB_API_KEY` for those calls. Set `TOKENLAB_MCP_TOOL_PROFILE=catalog` for read-only model discovery, or `full` for world generation, webhooks, and batch tools. Restart Claude Code after you change it. The profile uses Claude Code's [environment-variable default syntax](https://code.claude.com/docs/en/mcp#environment-variable-expansion-in-mcpjson). Changing the profile does not grant API permissions.
- `tokenlab-hosted-model-explorer` connects to the public hosted Model Explorer over Streamable HTTP. It is read-only and holds no API key.

The plugin and the Skills CLI are alternative ways to load the same skills. Neither changes the client's default model provider. To use TokenLab as a model provider, see the API integration skill's [Codex](skills/tokenlab-api-integration/references/codex_setup.md), [Claude Code](skills/tokenlab-api-integration/references/claude_setup.md), [OpenCode](skills/tokenlab-api-integration/references/opencode_setup.md), [Pi](skills/tokenlab-api-integration/references/pi_setup.md), and [Hermes](skills/tokenlab-api-integration/references/hermes_setup.md) setup references.

## Update an existing installation

Release **0.2.0** adds the foundation skills, 21 outcome skills for image, video, audio, 3D, and decisions, `catalog.json`, and `skills.sh.json`. The stdio MCP server now defaults to the `core` profile instead of `catalog`. The five earlier skill ids are unchanged.

`.claude-plugin/plugin.json` owns the plugin version. A Git push alone does not refresh a cached Claude plugin whose version is unchanged; see [Claude's version rules](https://code.claude.com/docs/en/plugins-reference#version-management).

For a Claude Code plugin installation:

```text
/plugin marketplace update tokenlab-tools
/plugin update tokenlab@tokenlab-tools
```

Restart Claude Code after updating. For a Codex plugin installation:

```bash
codex plugin marketplace upgrade tokenlab-tools
codex plugin add tokenlab@tokenlab-tools
codex plugin list --json
```

For skills installed with `npx skills`, update each skill in its original scope:

```bash
# In the project where you installed the skill:
npx skills update tokenlab-api-integration --project

# Or, if it was installed globally:
npx skills update tokenlab-api-integration --global
```

## Repository rules

- Each folder in `skills/` has a `SKILL.md` whose `name` equals the folder name.
- Outcome skills use the `tokenlab-` prefix so they never replace another vendor's skill with the same name.
- Exact model IDs appear only in the generated model block. To change a default, edit `preferredModels` in `catalog.json` and run `python3 scripts/sync_models.py`. Skills state no prices; the agent reads prices from the pricing API.
- `python3 -m unittest discover -s tests` checks the catalog, generated files, model blocks, versions, and helper scripts.
