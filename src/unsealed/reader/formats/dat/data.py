"""Generic "Seal Online Data" table body decoder.

A large family of small config/lookup tables (Attendance_Reward,
Job_type, Option_*, Pet_*, Stone_*, Compose_*, etc. — 46 files in the
sample dump) all share ONE container header instead of a bespoke type
name. Layout (v1), after the shared 64-byte header + int32 count:

    int32   field_count    declared LOGICAL fields per row
    row[count]             each `width` int32 cells (little-endian)

`field_count` is NOT a reliable read stride: it counts logical fields,
which diverges from the int32-cell width whenever a file packs wide
fields (Mission has an i64 field: 15 fields / 16 cells). So the row width
in cells is resolved per-file, known up front because the schema is keyed
by FILENAME:

  * tagged file   -> `schema.total_cells` (authoritative: the schema
                     knows every field's cell width, incl. i64/strings)
  * untagged file -> the file-size cell grid, (size - 72) / count / 4,
                     i.e. a uniform int32 row

Each file's COLUMNS mean different things, so a per-file `RecordSchema`
(see `schemas/dat/`) names/types the columns; an untagged file gets a
synthesized `generic_schema(width)` of `field_0..field_N` int32 columns
(width from the file size) so it still decodes to named rows.
`field_count` is kept in `unknown` for reference only.
"""

from ...assets.dat import DatFile
from ...formats.records import schema_for_filename
from ...schemas.dat.base import generic_schema
from ...utils.file import File
from .registry import DatBody, register

_HEADER_AND_COUNT = 68  # 64-byte header + int32 count


class DataTableBody(DatBody):
  type_name = "Seal Online Data"
  # Any version — the container (count + field_count + fixed-width rows)
  # is version-agnostic. Only v1 (the config tables) has ever been seen
  # in a sample.
  versions = ()

  def decode(self, file: File, dat: DatFile) -> None:
    dat.unknown["field_count"] = file.read_int()  # declared logical fields

    if dat.count <= 0:
      dat.elements = []
      return

    # The schema is known here (keyed by filename+version). Untagged files
    # fall back to a uniform int32 grid sized from the file. Either way the
    # record layout is a `RecordSchema`, so reading is one code path.
    schema = schema_for_filename("dat", dat.source_name, dat.version)
    if schema is None:
      body = file.size - (_HEADER_AND_COUNT + 4)
      schema = generic_schema(body // dat.count // 4)
    dat.unknown["schema"] = schema.name
    dat.unknown["row_width"] = schema.total_cells

    dat.elements = [schema.read_record(file, idx) for idx in range(dat.count)]


register(DataTableBody())
