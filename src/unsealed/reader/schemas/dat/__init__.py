"""Declarative schemas for Seal Online `.dat` files.

`base.py` holds the dat schema vocabulary (byte leaf `DataType`s +
registration wrappers). Every other module declares ONE schema and
registers it into the shared `REGISTRY` (formats/records.py) on import,
so adding a table/type is adding one file here:

  * TYPE_NAME-dispatched self-describing types (item, monster, skill,
    buff, pet_food_table, quest, seller, mesh) call `register_type_schema`.
  * FILENAME-dispatched `Seal Online Data` container tables call
    `register_data_schema`.

Importing this package imports them all, so their registrations happen.
No decoder is involved -- the dat decoder later queries `REGISTRY`.
"""

from . import base  # noqa: F401  — vocabulary + register wrappers (import first)
from . import attendance_reward  # noqa: F401
from . import bonus_result  # noqa: F401
from . import buff  # noqa: F401
from . import combat_power  # noqa: F401
from . import compose_result_template  # noqa: F401
from . import compose_template  # noqa: F401
from . import costume_exchange  # noqa: F401
from . import exbox_exchange  # noqa: F401
from . import f_drop  # noqa: F401
from . import hard_constant  # noqa: F401
from . import harddungeondecomposition  # noqa: F401
from . import harddungeonpenalty_template  # noqa: F401
from . import hardfieldpenalty  # noqa: F401
from . import iopt_cost  # noqa: F401
from . import item  # noqa: F401
from . import item_data  # noqa: F401
from . import item_exchange  # noqa: F401
from . import item_string  # noqa: F401
from . import itemgrow_template  # noqa: F401
from . import job_type  # noqa: F401
from . import macro_constant  # noqa: F401
from . import mesh  # noqa: F401
from . import mission  # noqa: F401
from . import mix  # noqa: F401
from . import monster  # noqa: F401
from . import opt_gem_cmps  # noqa: F401
from . import opt_gem_cmps_rst_grp  # noqa: F401
from . import option_appearance  # noqa: F401
from . import option_bit  # noqa: F401
from . import option_cost  # noqa: F401
from . import option_grade  # noqa: F401
from . import option_value  # noqa: F401
from . import pet_breed  # noqa: F401
from . import pet_decomposition  # noqa: F401
from . import pet_fail  # noqa: F401
from . import pet_food  # noqa: F401
from . import pet_food_table  # noqa: F401
from . import pet_ingest_condition  # noqa: F401
from . import pet_material  # noqa: F401
from . import pet_smelting  # noqa: F401
from . import quest  # noqa: F401
from . import rank  # noqa: F401
from . import reward_time  # noqa: F401
from . import seller  # noqa: F401
from . import skill  # noqa: F401
from . import skill_opt_gem  # noqa: F401
from . import skill_opt_gem_equip  # noqa: F401
from . import skill_opt_id  # noqa: F401
from . import skill_opt_type_str  # noqa: F401
from . import stone_decomposition  # noqa: F401
from . import stone_levelstatus  # noqa: F401
from . import stone_optcost  # noqa: F401
from . import stone_statusgroup  # noqa: F401
from . import stone_step  # noqa: F401
from . import sub_g  # noqa: F401
from . import succession_condition  # noqa: F401
