"""SpakWorkspace — on-demand (lazy) mount of a .spak for the viewer.

The game client never extracts an archive: it reads the directory once,
then decrypts a single entry only when something needs it, pulling just
that file plus whatever it references (a model's textures/bones/anims, a
map's objects, …). This mirrors that: the entry list is available
instantly for browsing, and opening a file materializes only that file
and its dependency *closure* to a temp directory, leaving the rest of
the archive untouched.

Like the client, it also mounts the *sibling* archives in the same game
install (the other ``<root>/*/*.SPAK``) as a resolution fallback: a map
in ``map.SPAK`` references effect shaders that live in ``sfx.SPAK`` /
``skill.SPAK``, so dependencies are resolved across all archives even
though only the opened archive is browsed.

The decoders are filesystem-based and resolve siblings/textures/objects
by name in the same directory, so materializing the closure into one temp
dir lets them run unmodified — identical to the loose-files-on-disk case.
"""

from __future__ import annotations

import atexit
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from typing import Dict, FrozenSet, List, Set, Tuple

from ...formats.spak.decoder import SpakArchive

_TEX_EXTS = (".tex", ".te1", ".dds", ".png", ".jpg", ".bmp")


def _join(adir: str, base: str) -> str:
  base = base.replace("\\", "/")
  return f"{adir}/{base}" if adir else base


class SpakWorkspace:
  """A lazily-materialized view of a .spak archive (+ its siblings)."""

  def __init__(self, spak_path: Path) -> None:
    self.path = spak_path
    self.mount = Path(tempfile.mkdtemp(prefix="unsealed_spak_"))
    atexit.register(self.close)

    # The opened archive (browsed) plus sibling archives in the same
    # install (dependency-resolution fallback only).
    self.archive = SpakArchive(spak_path)
    self.archives: List[SpakArchive] = [self.archive]
    self._open_siblings(spak_path)

    self._names: List[str] = self.archive.names()  # browsed = opened archive
    # name (lowercased) -> (archive, cased-name). The opened archive is
    # indexed first so it wins on any cross-archive name collision.
    self._by_name: Dict[str, Tuple[SpakArchive, str]] = {}
    for arc in self.archives:
      for n in arc.names():
        self._by_name.setdefault(n.lower(), (arc, n))

    self._materialized: Set[str] = set()
    self._closured: Set[str] = set()
    self._shader_caches: Dict[str, dict] = {}

    # Q3 shader definitions (*.shader) are globbed as a set by
    # load_shaders(dir); they are few and may live in sibling archives
    # (sfx/skill), so materialize them all up front. This also keeps the
    # per-directory shader cache correct even though the mount path never
    # changes as more files are materialized.
    for key, (_arc, name) in self._by_name.items():
      if key.endswith(".shader"):
        self._materialize(name)

  def _open_siblings(self, spak_path: Path) -> None:
    """Open the other ``<root>/*/*.SPAK`` archives (best-effort)."""
    primary = spak_path.resolve()
    root = primary.parent.parent
    if not root.is_dir():
      return
    for sp in sorted(root.glob("*/*.SPAK")):
      if sp.resolve() == primary:
        continue
      try:
        self.archives.append(SpakArchive(sp))
      except Exception as e:
        print(f"[spak] skip sibling {sp.name}: {e}")

  # ── public API ────────────────────────────────────────────────────────────

  def viewable_entries(self, exts: FrozenSet[str]) -> List[PurePosixPath]:
    """Entry names whose extension is viewable — instant, no decryption."""
    return sorted(
      PurePosixPath(n) for n in self._names if PurePosixPath(n).suffix.lower() in exts
    )

  def prepare(self, rel) -> Path:
    """Materialize `rel` and its dependency closure; return its real path."""
    name = self._resolve(str(rel).replace("\\", "/"))
    if name is not None:
      self._closure(name)
      return self.mount / name
    return self.mount / str(rel)

  def close(self) -> None:
    for arc in self.archives:
      try:
        arc.close()
      except Exception:
        pass
    shutil.rmtree(self.mount, ignore_errors=True)

  # ── materialization ─────────────────────────────────────────────────────────

  def _materialize(self, name: str) -> None:
    """Decrypt + write one entry to the temp mount (idempotent).

    The entry may come from the opened archive or any sibling archive.
    """
    found = self._by_name.get(name.lower())
    if found is None:
      return
    arc, actual = found
    if actual.lower() in self._materialized:
      return
    dest = self.mount / actual
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(arc.read(actual))
    self._materialized.add(actual.lower())

  def _materialize_texture(self, adir: str, ref: str) -> None:
    if not ref:
      return
    ref = ref.replace("\\", "/")
    self._materialize(_join(adir, ref))
    # Try the .tex/.te1/… variants in the ref's own (possibly nested) dir.
    refp = PurePosixPath(ref)
    refdir = _join(adir, str(refp.parent)) if str(refp.parent) != "." else adir
    for ext in _TEX_EXTS:
      self._materialize(_join(refdir, refp.stem + ext))

  # ── dependency closure (per format) ─────────────────────────────────────────

  def _closure(self, name: str) -> None:
    if name.lower() in self._closured:
      return
    self._closured.add(name.lower())

    self._materialize(name)
    adir = self._dir_of(name)
    ext = PurePosixPath(name).suffix.lower()
    real = self.mount / name

    try:
      if ext == ".ms1":
        self._ms1_closure(name, real, adir)
      elif ext == ".act":
        self._act_closure(real, adir)
      elif ext == ".spr":
        self._spr_closure(real, adir)
      elif ext == ".men":
        self._men_closure(real, adir)
      elif ext == ".map":
        self._map_closure(name, real, adir)
    except Exception as e:
      # Best-effort: a discovery failure just means fewer prefetched
      # deps (a missing texture renders untextured, as it would today).
      print(f"[spak] closure for {name!r} partial: {e}")

  def _ms1_closure(self, name: str, real: Path, adir: str) -> None:
    stem = PurePosixPath(name).stem
    # The ms1 decoder reads these same-stem siblings (with_suffix).
    self._materialize(_join(adir, stem + ".bn1"))
    self._materialize(_join(adir, stem + ".an1"))
    self._materialize(_join(adir, stem + ".sha"))

    from ...formats.ms1.format import SealMeshFormat

    model = SealMeshFormat().decode(real)
    if model.geometry is None:
      return
    # Plain material textures …
    for mat in model.geometry.materials:
      for m in [mat, *mat.sub_materials]:
        self._materialize_texture(adir, m.bitmap or "")
    # … plus textures referenced inside the Q3 shaders this model uses.
    self._materialize_shader_textures(model, adir)

  def _materialize_shader_textures(self, model, adir: str) -> None:
    """Pull textures named by the .shader stages the model's materials map to."""
    cache = self._shaders_for_dir(adir)
    if not cache:
      return

    names: Set[str] = set()
    if model.shaders:  # .sha mapping: material_name -> shader_name
      for s in model.shaders.shaders:
        names.add(s.shader_name)
        for ss in s.sub_shaders:
          names.add(ss.shader_name)
    for mat in model.geometry.materials:  # ms1-embedded shader names
      for m in [mat, *mat.sub_materials]:
        if m.shader_name:
          names.add(m.shader_name)

    for nm in names:
      shader = cache.get(PurePosixPath(nm).stem.lower()) if nm else None
      if shader is None:
        continue
      for stage in shader.stages:
        if stage.map_texture:
          self._materialize_texture(adir, stage.map_texture)
        for tex in stage.anim_textures:
          self._materialize_texture(adir, tex)

  def _shaders_for_dir(self, adir: str) -> dict:
    """Parsed *.shader cache for an archive directory (memoized)."""
    if adir not in self._shader_caches:
      from ..shader import load_shaders

      self._shader_caches[adir] = load_shaders(self.mount / adir if adir else self.mount)
    return self._shader_caches[adir]

  def _act_closure(self, real: Path, adir: str) -> None:
    from ...formats.act.decoder import SealActorDecoder

    actor = SealActorDecoder(real).decode()
    if actor is None:
      return
    ms1_base = PurePosixPath(actor.filename.replace("\\", "/")).stem + ".ms1"
    ms1_name = self._resolve(_join(adir, ms1_base))
    if ms1_name is not None:
      self._closure(ms1_name)
    for action in actor.actions:
      self._materialize(_join(adir, action.filename + ".an1"))

  def _spr_closure(self, real: Path, adir: str) -> None:
    from ...formats.spr.decoder import SealSprDecoder

    for ref_filename, _quads in SealSprDecoder(real).decode():
      self._materialize_texture(adir, ref_filename)

  def _men_closure(self, real: Path, adir: str) -> None:
    import contextlib
    import io
    import json

    from ...formats.men.decoder import SealMenDecoder

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
      raw = SealMenDecoder(real).decode()
    parsed = json.loads(raw) if isinstance(raw, str) else (raw or {})
    spr_name = parsed.get("spr") or ""
    if not spr_name:
      return
    spr_resolved = self._resolve(_join(adir, spr_name))
    if spr_resolved is not None:
      self._closure(spr_resolved)

  def _map_closure(self, name: str, real: Path, adir: str) -> None:
    stem = PurePosixPath(name).stem
    self._materialize(_join(adir, stem + ".mdt"))

    from ...formats.map.format import SealMapFormat

    terrain = SealMapFormat().decode(real)
    for tex in terrain.textures:
      self._materialize_texture(adir, tex)
    if terrain.lightmap:
      self._materialize_texture(adir, terrain.lightmap)

    # Object meshes referenced by the map (+ a sky dome, if present).
    self._materialize(_join(adir, "sky.ms1"))
    for filename in [*terrain.object_files, "sky.ms1"]:
      obj_stem = PurePosixPath(filename.replace("\\", "/")).stem
      obj_name = self._resolve(_join(adir, filename)) or self._resolve(
        _join(adir, obj_stem + ".ms1")
      )
      if obj_name is not None:
        self._closure(obj_name)

  # ── helpers ──────────────────────────────────────────────────────────────────

  def _resolve(self, name: str) -> str | None:
    """Return the canonical (cased) entry name, or None if absent."""
    found = self._by_name.get(name.replace("\\", "/").lower())
    return found[1] if found is not None else None

  @staticmethod
  def _dir_of(name: str) -> str:
    parent = PurePosixPath(name).parent
    return "" if str(parent) == "." else str(parent)
