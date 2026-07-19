"""Polymorph stat table (`polymorph.edt` -> `polymorph*.tsv`)."""

from ..formats.celltable import i32s
from ..formats.records import RecordSchema, register_schema

POLYMORPH_SCHEMA = RecordSchema(
  name="polymorph",
  columns=i32s(
    "index",  # 0-based row id; the polymorph item points here
    "creature_id",  # morph target ref -> polymorph-creature table
    "hp_bonus",  # flat max-HP added while morphed
    "ap_bonus",  # flat max-AP added while morphed
    "hit",  # accuracy
    "evasion",  # avoid
    "attack",  # physical attack (swaps with magic in phys/mag variant pairs)
    "attack_speed",  # aspd
    "magic",  # magic attack
    "defense",
    "critical",  # some tooltips render this as "special move"
    "move_speed",
  ),
)

register_schema("tsv", POLYMORPH_SCHEMA, patterns=(r"^polymorph",))
