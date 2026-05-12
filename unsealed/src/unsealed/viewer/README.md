# Unsealed Viewer

An interactive 3-D viewer for Seal Online game files. Loads `.ms1`, `.act`,
`.map`, `.tex`, and `.te1` files directly without first converting them to
glTF — useful for inspecting models, animations, maps, and textures.

## Install

The viewer requires extra dependencies on top of the base CLI. Install them
in one of two ways:

```bash
# A. Install with the optional 'viewer' extra (recommended)
pip install -e ".[viewer]"

# B. Or install dependencies directly
pip install pygame PyOpenGL PyOpenGL_accelerate moderngl imgui-bundle
```

OpenGL 3.3 Core is required.

## Run

```bash
# Open the welcome screen, then choose a file via File > Open
python -m unsealed.viewer

# Or load a file directly
python -m unsealed.viewer path/to/file.ms1
python -m unsealed.viewer path/to/file.map
python -m unsealed.viewer path/to/file.tex
```

Supported extensions: `.ms1`, `.act`, `.map`, `.tex`, `.te1`.

If a `.sha` (Q3-style shader) file lives next to the target file, the viewer
loads it automatically.

## Controls

### Model / actor scene (`.ms1`, `.act`)

| Key / mouse        | Action                                  |
|--------------------|-----------------------------------------|
| RMB drag           | Orbit (mouse locked)                    |
| LMB drag           | Orbit (mouse free)                      |
| MMB drag           | Pan                                     |
| Scroll             | Zoom                                    |
| W                  | Toggle wireframe                        |
| Space              | Play / pause animation                  |
| Backspace          | Stop animation                          |
| Up / Down arrows   | Cycle animations                        |
| Left / Right       | Scrub animation by 0.05 s (when paused) |
| O                  | Open file dialog                        |
| Esc                | Quit (or release mouse capture)         |

### Map scene (`.map`)

| Key / mouse  | Action                       |
|--------------|------------------------------|
| LMB drag     | Pan                          |
| MMB drag     | Pan (grab feel)              |
| RMB drag     | Orbit (yaw + pitch)          |
| WASD / Arrows| Pan with keyboard            |
| Scroll       | Zoom                         |
| LMB click    | Select / deselect object     |
| O            | Open file                    |
| Esc          | Quit                         |

### Image scene (`.tex`, `.te1`)

| Key / mouse | Action     |
|-------------|------------|
| Drag        | Pan        |
| Scroll      | Zoom       |
| O           | Open file  |
| Esc         | Quit       |

## Architecture (one-page tour)

```
viewer/
├── __main__.py        — entry point; checks deps, starts ViewerApp
├── app/
│   ├── viewer_app.py  — pygame loop, owns AppWorld, drives the renderer
│   ├── world.py       — AppWorld: holds all components/systems
│   ├── context.py     — ViewerContext: scene + camera + config per file
│   ├── components/    — pure @dataclass state (animation, input, render, scene, window)
│   ├── systems/       — stateless logic (animation, hud, input, load, update)
│   └── panels/        — cross-mode HUD panels (welcome only; mode-specific in modes/&lt;m&gt;/panels.py)
│
├── scenes/            — file-decoded CPU data (no GL)
├── animation/         — Animator + NodeAnimator + keyframe sampling
├── camera/            — OrbitCamera / MapCamera / ImageCamera
├── pipeline/          — file → ViewerScene converters
├── shader/            — Q3-style .sha parser
└── rendering/
    ├── renderer.py    — orchestrator (also owns inline command building, GPU upload, ray picking)
    ├── shaders.py     — GLSL loader + ShaderProgram wrapper
    ├── types.py       — DrawCommand, RenderContext, HudButton, HudPanel, VertexLayout
    ├── registry.py    — entity_id → GPU components
    ├── components.py  — GPU buffer / material / transform / bounds
    ├── hud.py         — HudRenderer
    ├── sky.py / terrain.py — forward renderers (map mode)
    ├── passes/        — gbuffer, lighting, overlay
    └── glsl/          — shader source files
```

### Frame pipeline (`Renderer.render`)

1. **G-Buffer** — opaque geometry → albedo + normal MRT
2. **Lighting** — fullscreen deferred Blinn-Phong
3. **Depth blit** — G-Buffer depth → default FBO
4. **Sky** (map only) — sky dome at depth 1
5. **Terrain** (map only) — forward pass
6. **Q3 stages** — multi-stage Q3-style shader forward pass
7. **Transparent** — primitives with `alpha < 1` (additive blend)
8. **Overlay** — wireframe + selection highlight
9. **HUD** — ImGui panels (rendered last by the app loop)

### File loading flow

`AppWorld.load(path)` →
1. `LoadSystem` loads `.sha` shaders from `path.parent` (cached per dir).
2. `ViewerContext.load(...)` picks a pipeline by extension and decodes the
   file into a `ViewerScene` subclass.
3. `Renderer.load_scene(scene)` uploads the scene to GPU.
4. `AnimationSystem.load(...)` initialises animators (model & map paths).

## Troubleshooting

- **"Missing required packages"** — install the `viewer` extra:
  `pip install -e ".[viewer]"`.
- **Black window, no models** — check the terminal log; failed file
  decoding is printed there.
- **Map objects missing** — try toggling the Q3 shader pass with the
  *Shader: ON/OFF* button.
- **Animation looks wrong** — confirm the matching `.bn1` and `.an1` files
  live next to the `.ms1`.
