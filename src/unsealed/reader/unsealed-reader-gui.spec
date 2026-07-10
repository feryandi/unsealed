# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the released `unsealed-reader-gui` app (onedir).

This is the ONLY reader binary shipped in releases: the full reader —
its decoders (numpy/scipy/pillow/pygltflib) plus the PySide6/Qt UI. The
entry is the reader's `__main__.py`, so the exe launches the GUI by
default AND runs the `decode` / `recover-key` subcommands (it's built
windowless for a clean GUI; `__main__.run()` reattaches to the parent
console when invoked with a subcommand so that CLI output stays visible).
Run from the repo root:

    pyinstaller src/unsealed/reader/unsealed-reader-gui.spec

Deliberately **onedir**, not onefile: PySide6/Qt is LGPLv3 and must be
*dynamically* linked, so the Qt `.dll`s/plugins ship as separate files
next to the exe (a user can inspect/replace them). PyInstaller's built-in
PySide6 hook collects the Qt runtime + platform plugins; UPX is disabled
because it can corrupt the Qt DLLs. The viewer's GPU stack is excluded —
the reader never imports the viewer, so this bundle stays free of
pygame/OpenGL/imgui.

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
        # The reader never imports the viewer, so keep the GPU stack out.
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
    [],
    exclude_binaries=True,  # onedir: binaries/datas go in the COLLECT below
    name="unsealed-reader-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX can corrupt Qt DLLs
    console=False,  # windowed GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="unsealed-reader-gui",
)
