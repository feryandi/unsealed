# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the `unsealed-viewer` GUI (onefile).

Bundles the GLSL shader sources (loaded at runtime via
``Path(__file__).parent / "glsl"``) plus the binaries/data shipped by
pygame, PyOpenGL and imgui-bundle. Run from the repo root:

    pyinstaller src/unsealed/viewer/unsealed-viewer.spec

Paths are resolved relative to this spec's own directory (SPECPATH) so it
builds the same regardless of the working directory.
"""
import os

from PyInstaller.utils.hooks import collect_all, collect_submodules

_SRC = os.path.abspath(os.path.join(SPECPATH, "..", ".."))  # -> src/
_ICON = os.path.join(SPECPATH, "..", "icon.ico")  # src/unsealed/icon.ico

datas = []
binaries = []
# The reader's schema catalogue is imported dynamically (its __init__ walks
# the package), so static analysis misses it: name the modules explicitly or
# the frozen viewer ships an empty registry. See the reader's spec.
hiddenimports = collect_submodules("unsealed.reader.schemas")

# Grab everything (python modules, extension binaries, data) from the GPU stack.
for pkg in ("imgui_bundle", "OpenGL", "OpenGL_accelerate", "pygame"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

# GLSL shaders are read at runtime relative to the shaders module. Place them
# at the same package path inside the bundle so `Path(__file__).parent` finds
# them.
datas += [
    (os.path.join(SPECPATH, "rendering", "glsl"), "unsealed/viewer/rendering/glsl"),
    # App icon, resolved at runtime via unsealed.resources.icon_path().
    (_ICON, "unsealed"),
]

a = Analysis(
    [os.path.join(SPECPATH, "__main__.py")],
    pathex=[_SRC],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="unsealed-viewer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_ICON,
)
