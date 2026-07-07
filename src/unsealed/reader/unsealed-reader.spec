# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the `unsealed-reader` CLI (onefile).

Reader is pure-Python + numpy/scipy/pillow/pygltflib — no viewer deps, no
bundled data files. Run from the repo root:

    pyinstaller src/unsealed/reader/unsealed-reader.spec

Paths are resolved relative to this spec's own directory (SPECPATH) so it
builds the same regardless of the working directory.
"""
import os

from PyInstaller.utils.hooks import collect_submodules

_SRC = os.path.abspath(os.path.join(SPECPATH, "..", ".."))  # -> src/

# scipy pulls in submodules dynamically; make sure they're all collected.
hiddenimports = collect_submodules("scipy")

a = Analysis(
    [os.path.join(SPECPATH, "__main__.py")],
    pathex=[_SRC],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Keep the reader lean: never bundle the viewer's GPU stack.
        "pygame",
        "OpenGL",
        "OpenGL_accelerate",
        "imgui_bundle",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="unsealed-reader",
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
)
