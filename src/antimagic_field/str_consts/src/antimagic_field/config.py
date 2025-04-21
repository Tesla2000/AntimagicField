from __future__ import annotations

from typing import Final
from typing import Literal

ARGS: Final[Literal["__args__"]] = "__args__"
CONFIG_FILE: Final[Literal["config_file"]] = "config_file"
CONST: Final[Literal["_CONST"]] = "_CONST"
DEFAULT_FORMATTED: Final[Literal["Default: {}"]] = "Default: {}"
ENV: Final[Literal[".env"]] = ".env"
FORMATTED: Final[Literal["--{}"]] = "--{}"
GENERATED_CONSTANTS: Final[Literal["generated_constants"]] = (
    "generated_constants"
)
POS_ARGS: Final[Literal["pos_args"]] = "pos_args"
