# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the released `unsealed-reader-gui` app (onedir).

This is the ONLY reader binary shipped in releases: the full reader —
its decoders (numpy/scipy/pillow/pygltflib) plus the PySide6/Qt UI. The
entry is the reader's `__main__.py`, so the exe launches the GUI by
default AND runs the `decode` subcommand (it's built windowless for a
clean GUI; `__main__.run()` reattaches to the parent console when
invoked with a subcommand so that CLI output stays visible).
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

_SRC = os.path.abspath(os.path.join(SPECPATH, "..", ".."))  # -> src/
_ICON = os.path.join(SPECPATH, "..", "icon.ico")  # src/unsealed/icon.ico
_LOGO = os.path.join(SPECPATH, "..", "logo.png")  # src/unsealed/logo.png
_VENDOR = os.path.join(SPECPATH, "vendor", "bkcrack")


def _host_bkcrack_asset():
    """The single bkcrack binary matching the build host (or None)."""
    import platform

    system, machine = platform.system(), platform.machine().lower()
    if system == "Windows":
        return "bkcrack-windows-x86_64.exe"
    if system == "Darwin":
        return "bkcrack-macos-" + ("arm64" if machine in ("arm64", "aarch64") else "x86_64")
    if system == "Linux":
        return "bkcrack-linux-" + ("aarch64" if machine in ("aarch64", "arm64") else "x86_64")
    return None


# Bundle bkcrack (zlib-licensed) so cross-platform, memory-dump-free .spak
# key recovery works. The binaries are fetched, not committed to git -- run
#   python -m unsealed.reader.vendor.fetch
# before packaging (the release workflow does this). Only the host build is
# bundled: shipping other OSes' password-cracker binaries would add dead
# weight and needless AV noise. Its license notice always ships. The dest
# dir mirrors what unsealed.reader.vendor.bkcrack_path() expects.
_VENDOR_DEST = "unsealed/reader/vendor/bkcrack"
_bkcrack_datas = [(os.path.join(_VENDOR, "LICENSE.txt"), _VENDOR_DEST)]
_host_asset = _host_bkcrack_asset()
_host_path = os.path.join(_VENDOR, _host_asset) if _host_asset else None
if _host_path and os.path.isfile(_host_path):
    _bkcrack_datas.append((_host_path, _VENDOR_DEST))
else:
    print(
        "WARNING: bkcrack binary not found -- automatic known-plaintext .spak "
        "key recovery will be unavailable in this build. Run "
        "'python -m unsealed.reader.vendor.fetch' before pyinstaller."
    )

hiddenimports = []

a = Analysis(
    [os.path.join(SPECPATH, "__main__.py")],
    pathex=[_SRC],
    binaries=[],
    # Icon + welcome-screen logo, resolved at runtime via
    # unsealed.resources (icon_path / logo_path); plus the vendored bkcrack.
    datas=[(_ICON, "unsealed"), (_LOGO, "unsealed")] + _bkcrack_datas,
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
        # scipy (~55 MB) is no longer used: utils/matrix.py does its one
        # matrix->quaternion in numpy now (verified equal to scipy to
        # machine epsilon), so exclude it and its heavy friends outright.
        "scipy",
        "pandas",
        "matplotlib",
        # This GUI imports only QtCore/QtGui/QtWidgets (verified). Drop the
        # heavyweight Qt modules PyInstaller's PySide6 hook bundles by
        # default -- WebEngine alone is a whole Chromium (~130 MB), and
        # Quick/QML, 3D, Multimedia, Charts, Pdf, Sql, … are all unused.
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineQuick",
        "PySide6.QtWebChannel",
        "PySide6.QtWebSockets",
        "PySide6.QtQuick",
        "PySide6.QtQuick3D",
        "PySide6.QtQuickWidgets",
        "PySide6.QtQuickControls2",
        "PySide6.QtQml",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DRender",
        "PySide6.Qt3DInput",
        "PySide6.Qt3DLogic",
        "PySide6.Qt3DAnimation",
        "PySide6.Qt3DExtras",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtGraphs",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "PySide6.QtSensors",
        "PySide6.QtPositioning",
        "PySide6.QtLocation",
        "PySide6.QtBluetooth",
        "PySide6.QtNfc",
        "PySide6.QtSerialPort",
        "PySide6.QtSql",
        "PySide6.QtTest",
        "PySide6.QtDesigner",
        "PySide6.QtHelp",
        "PySide6.QtScxml",
        "PySide6.QtRemoteObjects",
        "PySide6.QtSpatialAudio",
        "PySide6.QtTextToSpeech",
    ],
    noarchive=False,
)

# Belt-and-suspenders trim: even with the modules excluded above, the
# PySide6 hook can still copy their Qt DLLs/plugins (pulled as transitive
# deps) plus Qt's bundled UI translations (~40-50 MB of .qm). Prune them
# from the collected tables. Scoped to Qt payload via ``_is_qt`` so no
# non-Qt binary/data is ever touched; the kept core is Qt6Core/Gui/Widgets
# + the platform/imageformat/style plugins the app actually needs.
_QT_HEAVY = (
    "webengine", "quick", "qml", "3dcore", "3drender", "3dinput",
    "3dlogic", "3danimation", "3dextras", "multimedia", "charts",
    "datavisualization", "qtgraphs", "pdf", "sensors", "positioning",
    "location", "bluetooth", "nfc", "serialport", "sql", "qttest",
    "designer", "scxml", "remoteobjects", "spatialaudio", "texttospeech",
)


def _keep_qt(dest):
    """False for a heavy/unused Qt file (else keep). ``dest`` is a bundle path."""
    p = dest.replace("\\", "/").lower()
    # English-only app: Qt's own translations aren't needed.
    if p.endswith(".qm") and "translations" in p:
        return False
    is_qt = (
        "pyside6" in p or "/qt6" in p or p.startswith("qt6") or "shiboken6" in p
    )
    if not is_qt:
        return True
    return not any(tok in p for tok in _QT_HEAVY)


a.binaries = [b for b in a.binaries if _keep_qt(b[0])]
a.datas = [d for d in a.datas if _keep_qt(d[0])]

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
    icon=_ICON,
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
