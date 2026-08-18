import json
from pathlib import Path
from typing import Any

from ..assets.dat import DatFile
from ..formats.dat.data import DataTableBody
from ..formats.dat.format import SealDatFormat


def _scr_token(value: Any) -> str:
  """One pipe cell's text -- `None` (an absent/junk value) as empty, a
  nested list flattened with `,`, everything else via `str`."""
  if value is None:
    return ""
  if isinstance(value, (list, tuple)):
    return ",".join(_scr_token(v) for v in value)
  return str(value)


# `.dat` types written as pipe-delimited `.scr` text instead of JSON: the
# generic "Seal Online Data" config-table container, plus the four bespoke
# schema-driven types whose records are likewise flat positional-value rows
# (see `schemas/monster.py`, `item.py`, `quest.py`, `seller.py`). Shared with
# `EdtPipeline`, whose decrypted `.edt`/`.ed<n>` payloads are these same
# `.dat` types, just reached through the LCG cipher instead of loose disk
# bytes.
_SCR_TYPE_NAMES = {
  DataTableBody.type_name,  # "Seal Online Data"
  "SealOnline MonsterDataFile",
  "Seal Online ItemFile",
  "Seal Online QuestFile",
  "Seal Online SellerFile",
  "Seal Online Table1DataFile",
  "Seal Online MonsterAI",
}


def is_scr_type(type_name: str) -> bool:
  """Whether a decoded `.dat` type is written as `.scr` text (else JSON)."""
  return type_name in _SCR_TYPE_NAMES


def render_scr(dat: DatFile) -> str:
  """A decoded `.dat`'s elements as `.scr`-style pipe text: a leading count
  line, then one `|`-joined, `|`-terminated row per element."""
  lines = [str(len(dat.elements))]
  lines += [
    "|".join(_scr_token(v) for v in element.values()) + "|" for element in dat.elements
  ]
  return "\n".join(lines) + "\n"


class DatPipeline:
  """Decode a `.dat` and write a JSON summary (type, version, count, and
  any decoded elements). Until a body decoder is registered for the
  type+version, `elements` is empty and only the header is written.

  A type in `_SCR_TYPE_NAMES` -- the generic "Seal Online Data" container
  (`formats/dat/data.py:DataTableBody`, the config-table family:
  Attendance_Reward, Job_type, Option_*, Pet_*, ...) plus Monster, Item,
  QuestFile and Seller -- instead writes a pipe-delimited `.scr`-style text
  file, the same plain-text shape as `npc*.scr`/`drop*.scr`: a leading
  count line, then one `|`-joined, `|`-terminated row per element. These
  tables are flat positional-value rows -- the client's own `.scr`
  predecessors of the same tables carry no more structure than that (see
  e.g. `etc/Additonal_reward.scr` vs. `additonal_reward.dat`), so there is
  nothing binary-specific worth keeping as JSON.
  """

  def run(self, filepath: Path, output_dir: Path) -> None:
    if not filepath.is_file():
      raise Exception(f"File not found: {filepath}")

    dat = SealDatFormat().decode(filepath)

    if is_scr_type(dat.type_name):
      out = output_dir / f"{filepath.stem}.scr"
      out.write_text(render_scr(dat), encoding="utf-8")
      print(
        f"{filepath.name}: {dat.type_name} v{dat.version}, "
        f"{len(dat.elements)} element(s) -> .scr"
      )
      return

    summary = {
      "type": dat.type_name,
      "version": dat.version,
      "count": dat.count,
      "decoded": len(dat.elements),
      "elements": dat.elements,
    }
    out = output_dir / f"{filepath.stem}.dat.json"
    out.write_text(
      json.dumps(summary, indent=2, ensure_ascii=False, default=str),
      encoding="utf-8",
    )
    print(f"{filepath.name}: {dat.type_name} v{dat.version}, {dat.count} element(s)")
