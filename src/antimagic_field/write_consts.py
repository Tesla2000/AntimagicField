from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from .config import Config
from .const import Const


def write_consts(
    consts_file_path: Path, consts: Sequence[Const], config: Config
):
    consts_file_path.parent.mkdir(exist_ok=True, parents=True)
    if consts_file_path.exists():
        contents = consts_file_path.read_text()
    else:
        contents = "from typing import Final\nfrom typing import Literal\n"
    current_consts = tuple(
        line.split(":")[0] for line in contents.splitlines() if ":" in line
    )
    contents += "\n".join(
        frozenset(
            f'{const.const_name}{config.const_name_suffix}: Final[Literal["{const.value}"]] = "{const.value}"'
            for const in consts
            if const.const_name + config.const_name_suffix
            not in current_consts
        )
    )
    contents = contents.replace('"\n"', '"\\n"')
    if contents:
        consts_file_path.write_text(contents)
