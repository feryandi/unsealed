# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Unsealed** is a Python CLI tool that decodes and encodes proprietary binary game files from *Seal Online* (an MMORPG). It reads game-specific formats (`.ms1`, `.act`, `.map`, `.men`, `.spr`, `.tex`) and converts them to standard formats (`.glb`/`.gltf` 3D models, `.png` textures). It also includes an interactive 3D viewer powered by pygame + OpenGL + imgui-bundle.

## Commands

### Setup
```bash
pip install -e ".[dev]"
# Viewer also requires:
pip install pygame PyOpenGL PyOpenGL_accelerate imgui-bundle
```

### Run the CLI tool
```bash
python -m unsealed
python -m unsealed -o output_dir
# Or, after installation:
unsealed -o output_dir
```

### Run the viewer
```bash
python -m unsealed.viewer
python -m unsealed.viewer path/to/file.ms1
```
Supported viewer file types: `.ms1`, `.act`, `.map`, `.tex`, `.te1`, `.men`, `.spr`

### Lint
```bash
ruff check src/
ruff format src/
```

### Tests
There are no automated tests yet. The `tests/input/` directory contains real game binary files used for manual verification. Test a specific file by running the tool and providing the file path interactively.

## Architecture

### Core Pattern: Format → Asset → Pipeline

Every conversion follows this three-layer pattern:

1. **Formats** (`src/unsealed/formats/`) — File I/O layer. Each format subpackage implements `BaseFormat[T]` with `decoder()` and `encoder()` methods. Decoders read binary game files into intermediate Asset objects; encoders write Asset objects to output files.

2. **Assets** (`src/unsealed/assets/`) — Intermediate representations. Pure Python data classes that are format-agnostic (e.g., `Model`, `Geometry`, `Mesh`, `Material`, `Animation`, `Skeleton`, `Blob`, `Shaders`). These decouple game-specific formats from output formats.

3. **Pipelines** (`src/unsealed/pipelines/`) — Orchestration layer. Each pipeline wires together multiple format decoders/encoders to process a complete asset (e.g., `ObjectPipeline` decodes `.ms1` + optional `.bn1`/`.an1`, then encodes to `.glb`).

### Entry point (CLI)
`src/unsealed/__main__.py` → `MainPipeline` → dispatches to the right sub-pipeline by file extension.

### Supported file type → pipeline mapping (CLI)
| Extension | Name | Pipeline |
|---|---|---|
| `.act` | Actor File | `ActorPipeline` → `.glb` |
| `.ms1` | Mesh File | `ObjectPipeline` → `.glb` |
| `.map` | Map File | `MapPipeline` → heightmap `.png` + extracted objects |
| `.men` | Menu File | `MenuPipeline` |
| `.tex` / `.te1` | Texture File | `TexturePipeline` → `.png` |

`.sha` (Q3-style shader text), `.mdt`, `.spr`, `.sfx`, `.mat`, `.bn1`, `.an1`, `.blob`, `.heightmap` have format decoders but are read indirectly by the pipelines above (e.g. `.bn1`/`.an1` co-locate with `.ms1`).

### Binary reading
All decoders use `utils/file.py:File` — a thin wrapper around `BytesIO` with typed read methods (`read_int`, `read_float`, `read_string`, `read_short`, etc.). Strings are decoded with fallback encodings: `euc_kr` → `windows-1252` → `utf-8` (the game uses Korean EUC-KR encoding).

### Format decoder conventions
- Decoders are instantiated with a `Path` and expose a `decode()` method.
- Many `.ms1` files have a mode flag at the start (`ukwn = 0/1/10`) that alters parsing behavior.
- `.ms1` mesh files optionally co-locate `.bn1` (bones/skeleton) and `.an1` (animation) files with the same stem.
- `.tex`/`.te1` textures are XOR-obfuscated; the decoder detects the embedded image type (DDS, JPG, BMP, TGA) and applies the appropriate key.
- `.sha` files contain Q3-style shader definitions (parsed by `viewer/shader/parser.py`); decoded to `assets/shader.py:Shaders`.
- `.spr` files are sprite atlases that reference one or more `.tex`/`.te1` source images plus a list of sub-rectangles; decoded by `formats/spr/decoder.py`. The viewer wraps this in `viewer/sprite_atlas.py` for a flatter, GPU-friendly representation.
- `.men` UI files reference a sibling `.spr` atlas (same stem) and place named sprite refs into pixel rectangles per UI element with per-state variants (`base/click/disabled/hover/focus`).

### GLTF output
`GltfEncoder` in `formats/gltf/encoder.py` builds a GLTF 2.0 JSON dict from a `Model` asset. Encoding order matters: skeleton → materials → meshes → animations. Buffers are embedded as base64 data URIs. `GlbFormat` wraps `GltfEncoder` and writes both `.gltf` (JSON) and `.glb` (binary) outputs.

---

## Viewer Architecture

### Entry point
`src/unsealed/viewer/__main__.py` → `ViewerApp.run()` — pygame + OpenGL 3.3 Core + imgui-bundle.

### Layer overview
```
viewer/
├── __main__.py             — entry point; starts ViewerApp
├── sprite_atlas.py         — atlas-aware .spr decode shared by men + spr modes
│
├── modes/                  — pluggable per-format Mode plugins
│   ├── base.py             — Mode Protocol, BaseMode ABC, MODES registry,
│   │                         for_path() / for_scene(), AnimationPolicy.
│   │                         Re-exports RenderExtension / RenderPhase from
│   │                         rendering/extension.py for convenience.
│   ├── context.py          — ModeContext: explicit Mode↔Host snapshot/API
│   ├── __init__.py         — auto-registers ModelMode, MapMode, ImageMode,
│   │                         SprMode, MenMode
│   ├── model/              — .ms1, .act  → ModelScene + OrbitCamera +
│   │                         InfiniteGridExtension (FORWARD_OPAQUE)
│   ├── map/                — .map → MapScene + MapCamera + SkyExtension
│   │                         (BACKGROUND) + TerrainExtension (FORWARD_OPAQUE)
│   │                         + sky.py / terrain.py renderers
│   ├── image/              — .tex, .te1 → ImageScene + ImageCamera +
│   │                         ImageExtension (BACKGROUND, full-screen quad)
│   ├── spr/                — .spr → SprScene + SprCamera + SprExtension
│   └── men/                — .men → MenScene + MenCamera + MenExtension
│
├── app/
│   ├── viewer_app.py       — ViewerApp (pygame loop, drives AppWorld)
│   ├── world.py            — AppWorld (component registry + system dispatch +
│   │                         mode-specific state helpers used by draw_hud)
│   ├── context.py          — ViewerContext.load() uses modes.for_path()
│   ├── constants.py
│   ├── components/         — pure @dataclass state (animation, input, render,
│   │                         scene, window)
│   └── systems/            — AnimationSystem, InputSystem, LoadSystem,
│                             UpdateSystem (no HudSystem — imgui replaces it)
│
├── scenes/                 — shared data classes (CPU-side, no GL)
│   ├── viewer_scene.py     — ViewerScene base (in scenes/scene.py actually)
│   ├── three_dimensional_scene.py — TDS(ViewerScene): meshes (flat) +
│   │                         entities (grouped). Base for ModelScene / MapScene.
│   ├── entity.py           — AnimatedEntity: meshes + skeleton + animation_groups
│   └── scene.py            — ViewerMesh (geometry only — no anim fields),
│                             ViewerPrimitive, ViewerQ3Stage, ViewerSkeleton,
│                             ViewerBone, ViewerAnimationGroup,
│                             ViewerBoneAnimation, ViewerKeyframe.
│                             Also _STRIDE_PLAIN / _STRIDE_SKINNED.
│
├── camera/
│   ├── base.py             — Camera base (concrete cameras live in
│   │                         modes/<m>/camera.py — OrbitCamera, MapCamera,
│   │                         ImageCamera, SprCamera, MenCamera)
│   └── __init__.py         — exports Camera, compute_bounds
│
├── animation/
│   ├── evaluator.py        — Animator, NodeAnimator
│   └── sampling.py         — keyframe interpolation helpers
│
├── shader/
│   └── parser.py           — Q3-style .sha shader parser
│
└── rendering/              — mode-agnostic core (no isinstance(scene, X) anywhere)
    ├── renderer.py         — Renderer drives core passes + iterates mode
    │                         RenderExtensions by RenderPhase
    ├── extension.py        — RenderPhase enum + RenderExtension Protocol
    │                         (lives here so renderer doesn't import modes/)
    ├── imgui_renderer.py   — ImGuiRenderer: imgui-bundle pygame backend
    │                         wrapper (init / process_event / new_frame /
    │                         render / shutdown / on_resize / want_capture_*)
    ├── math_utils.py       — ray_aabb_in_world, unproject_ray (CPU picking)
    ├── shaders.py          — GLSL loader (reads .glsl files from glsl/)
    ├── glsl/               — Actual GLSL source files (mesh / skin / inst /
    │                         wire / sel / img / terrain / sky / q3stage /
    │                         hud / gbuffer / lighting)
    ├── types.py            — ShaderVariant, DrawCommand, RenderContext
    ├── registry.py         — RenderRegistry
    ├── components.py       — GpuBufferComp, MaterialComp, TransformComp,
    │                         BoundsComp
    └── passes/             — GBufferPass, LightingPass, OverlayPass,
                              ForwardPass, Q3StagePass
```

### Mode plugin
Each scene-type family lives in its own `modes/<name>/` directory with `scene.py`, `pipeline.py`, `camera.py`, `extensions.py`, `mode.py`. To add a new format:
1. Create the directory; subclass `BaseMode` setting `name`, `extensions`, `scene_type`, and (optional) `animation_policy`.
2. Implement `decode(path, shader_cache)`, `make_camera(scene, w, h)`, `draw_hud(world)`, plus any `on_*` event handlers you need.
3. Build any draw-time extras as `RenderExtension` classes in `extensions.py` and return them from `render_extensions()` — **the same instances every call** (the renderer caches them at startup).
4. `register(NewMode())` in `modes/__init__.py`. The core viewer needs no edits.

**Circular-import discipline:** the renderer never imports `..modes`. `RenderPhase` and the `RenderExtension` protocol live in `rendering/extension.py` (a leaf module); `modes/base.py` re-exports them for mode code's convenience. `AppWorld.register_render_extensions()` walks `MODES`, dedupes by `id(ext)`, and hands the union to `Renderer.register_extensions()`. `Renderer.load_scene(scene, active_extensions)` takes the active mode's extensions as a parameter — the renderer never asks `modes/` who's active.

### HUD — immediate-mode imgui, no panel framework
Every `Mode` implements `draw_hud(world: AppWorld)`. Inside it the mode calls `imgui.begin(...)`, emits widgets, and mutates `AppWorld` state directly on click (`world.anim_toggle_play()`, `world.toggle_q3()`, `world.select_men_element(...)`, etc.). There is **no action-dispatch layer** and **no HudPanel/HudButton/HudAction types** — those were replaced by imgui-bundle. `ViewerApp.run()` calls `world.imgui.new_frame()` → `mode.draw_hud(world)` → `world.imgui.render()` each frame; when no scene is loaded, an inline `_draw_welcome(world)` runs instead.

`InputSystem` feeds every pygame event to imgui first and drops mouse/key events when `imgui.want_capture_mouse` / `want_capture_keyboard` is set — that's what keeps a drag-over-a-panel from also panning the scene.

### ModeContext — explicit Mode↔Host API
Mode event handlers (`on_key`, `on_mouse_*`, `on_scroll`) and special operations (`inject_model`) receive a `ModeContext` (`modes/context.py`) — a per-call snapshot of camera, window size, input state, animation component, selection, etc., plus mutator methods (`set_capture`, `set_lmb_down`, `pick`, `anim_toggle_play`, `open_inject_dialog`, …). `AppWorld.mode_context()` builds a fresh instance per event. Modes read the snapshot fields and call the methods for state changes — they never reach into `AppWorld` directly from a handler.

### File loading flow
1. `LoadSystem.load(path, world)` — called on startup or file-open dialog.
2. Loads `.sha` shaders from the file's parent directory into `world.shader_cache` (cached per directory).
3. `ViewerContext.load(path, …)` — `modes.for_path()` → `mode.decode()` → `mode.make_camera()`.
4. `Renderer.load_scene(scene, mode.render_extensions())` — uploads CPU data to GPU (VBOs, textures → `RenderRegistry`), runs `ext.free_scene()` on the previously-active set, then `ext.upload(scene)` on the new set.
5. `AnimationSystem.load(component, scene)` — builds `EntityAnimState`s and applies the active mode's `AnimationPolicy`.

### ECS pattern (AppWorld)
- **Components** (`app/components/`) — pure `@dataclass` state, no methods.
- **Systems** (`app/systems/`) — stateless classes; methods take components/world as arguments.
- **AppWorld** — owns one instance of each component and system; exposes public state-mutating helpers (`anim_toggle_play`, `anim_select`, `toggle_q3`, `select_shader`, `select_spr_entry`, `toggle_men_hide`, `set_men_state`, `select_men_element`, `pick_at`, `open_inject_dialog`, …) so `Mode.draw_hud` can mutate state inline on widget clicks.

### Render pipeline order
Core passes run unconditionally (when there are meshes); mode-supplied `RenderExtension`s plug in at named phases. The renderer pre-mirrors `proj` on the X axis once and passes the mirrored matrix to every pass and extension.

1. G-Buffer pass (`GBufferPass`) — opaque geometry → albedo + normal MRT
2. Lighting pass (`LightingPass`) — fullscreen deferred Blinn-Phong quad
3. Depth blit — G-Buffer depth → default FBO
4. `RenderPhase.BACKGROUND` — extensions (sky, 2-D image quad)
5. `RenderPhase.FORWARD_OPAQUE` — extensions (terrain, infinite grid)
6. `RenderPhase.FORWARD_Q3` — extensions, then core `Q3StagePass` (gated on `ctx.q3_enabled`)
7. `RenderPhase.TRANSPARENT` — extensions, then core `ForwardPass` (alpha < 1)
8. `RenderPhase.OVERLAY` — extensions, then core wireframe / selection highlight via `OverlayPass`

Extensions still run at BACKGROUND and FORWARD_OPAQUE when the registry is empty (a `.map` with zero baked objects still shows sky + terrain; image / spr / men modes draw nothing else).

### RenderExtension lifecycle
- `Renderer.init()` — compiles all built-in programs and passes.
- `Renderer.register_extensions(exts)` — called once by `AppWorld.register_render_extensions()` with the deduped union of `mode.render_extensions()` from every registered Mode; the renderer calls `ext.init()` here.
- `Renderer.load_scene(scene, active_exts)` — `ext.free_scene()` on the previously-active set, then `ext.upload(scene)` on the new active set.
- `Renderer.render(ctx)` — `_run_phase(phase, ctx, view, proj)` iterates `_active_extensions` matching each phase, between core passes.
- `Renderer.cleanup()` — `ext.dispose()` on every registered extension.

### Adding a mode-specific render pass
1. Write a class implementing the `RenderExtension` protocol: a class attr `phase: RenderPhase` and methods `init() / upload(scene) / render(ctx, view, proj) / free_scene() / dispose()`. (See `viewer/modes/map/extensions.py` for the canonical Sky/Terrain pair, or `viewer/modes/model/extensions.py:InfiniteGridExtension` for a minimal example.)
2. In your `Mode.__init__`, store the extension instance(s) and return them from `render_extensions()` — same instances every call.
3. Done — the renderer compiles your shaders at startup, uploads your scene state on each load, and calls your `render()` at the declared phase.

### Scene types and their cameras
| Scene class | File types | Camera |
|---|---|---|
| `ModelScene` | `.ms1`, `.act` | `OrbitCamera` |
| `MapScene` | `.map` | `MapCamera` |
| `ImageScene` | `.tex`, `.te1` | `ImageCamera` |
| `SprScene` | `.spr` | `SprCamera` |
| `MenScene` | `.men` | `MenCamera` |

`ModelScene` and `MapScene` both subclass `ThreeDimensionalScene` (`meshes` + `entities`). `ImageScene` / `SprScene` / `MenScene` are 2-D and don't populate the renderer's mesh registry — their `RenderExtension` does all drawing.

### Model-in-map injection
A model file can be injected into a loaded `.map` at runtime, becoming one more `AnimatedEntity` that animates + renders like any baked-in object. Press `I` while a map is loaded → file picker → on confirm, model spawns at the camera's terrain-clamped target. Entry points: `ModeContext.open_inject_dialog()` (from `MapMode.on_key`) → `AppWorld.open_inject_dialog()` → `MapMode.inject_model(path, mctx)`. Internally: decode via `ModelMode().decode()`, set each mesh's `instance_matrices` to a single translation at `cam.target`, append meshes + entity to the map scene, then `Renderer.load_scene(map_scene, mode.render_extensions())` + `AppWorld.reload_animation(map_scene)`.

### AnimationPolicy — mode-driven load behavior
`Mode.animation_policy: AnimationPolicy` (frozen dataclass, `has_primary` / `auto_play_all`) tells `AnimationSystem.load` how to treat fresh entities. ModelMode → `has_primary=True` (UI-controlled, paused). MapMode → `auto_play_all=True` (every enabled entity plays on its own clock, no primary). New modes default to neither (no playback, no UI). This replaced per-mode `isinstance` branches in `AnimationSystem.load`.

### Animation ECS (entity-based, single path)
- **`AnimatedEntity`** (`scenes/entity.py`) — `name`, `meshes: list[ViewerMesh]`, `skeleton`, `animation_groups`, `source_file`. ModelScene has 1 entity (the whole file); MapScene has 1 entity per object file.
- **`EntityAnimState`** (`app/components/animation.py`) — per-entity playback (`enabled/group_idx/time/playing/duration/animator/bone_matrices/node_animators/node_matrices`).
- **`AnimationComponent`** — `states: list[EntityAnimState]` (parallel to `scene.entities`), `primary_entity: Optional[int]` (UI target; set by `AnimationPolicy.has_primary`), plus renderer-facing flat dicts `bone_matrices/node_matrices` keyed by global mesh idx.
- **`AnimationSystem.update`** is a single loop over `scene.entities` — no `isinstance(scene, …)` branches.
- UI sites access `anim.primary` (the controllable state) and `scene.entities[anim.primary_entity]` (its entity).
- Gate the `Animator` (bone-skinning) path on `entity.skeleton is not None AND any(m.is_skinned for m in entity.meshes)`. A file with a dummy skeleton but no physique data still needs `NodeAnimator`s for its node-transform tracks.
- **Node animation**: `NodeAnimator` uses the mesh's local matrix as bind pose; renderer computes `uModel = inst_mat @ animated_world`.

### Picking (CPU ray-cast)
`Renderer.pick(mx, my, w, h, view, proj)` unprojects a ray and intersects it against per-entity AABBs (folding `inst_mats_cpu` per instance). Used by `MapMode` on click for object selection. `MenMode` does its own 2-D rectangle picking inside `_pick_element` — no GL involved.

### Sprite atlas decoding
`viewer/sprite_atlas.py` provides `SpriteAtlas` (one decoded source `.tex` as an HxWx4 numpy array) and `SpriteRef` (sub-rectangle into an atlas). `SprMode` and `MenMode` both consume this — one GL texture per atlas, sprite selection switches UVs only, never re-uploads pixels. The pipeline uses a `ThreadPoolExecutor` to decode atlases in parallel.
