from __future__ import annotations

from collections.abc import Collection
from collections.abc import Sequence
from pathlib import Path

from ..filepath2import_path import filepath2import_path
from .config import Config
from .constants.const_base import ConstBase
from .constants.previous_const import PreviousConst


def write_consts(
    consts_file_path: Path,
    consts: Sequence[ConstBase],
    moved_consts: Collection[PreviousConst],
    renamed_consts: Collection[PreviousConst],
    config: Config,
):
    if not consts:
        return
    consts_file_path.parent.mkdir(exist_ok=True, parents=True)
    name_translator = {
        const.const_name: const.previous_const_name for const in renamed_consts
    }
    moved_consts_str = ""
    if moved_consts:
        moved_consts_str = (
            "\n".join(
                f"from {filepath2import_path(const.written_filepath)} import {const.const_name}{config.const_name_suffix} as {const.previous_const_name}{config.const_name_suffix} "
                for const in moved_consts
            )
            + "\n_ = "
            + ", ".join(
                const.previous_const_name + config.const_name_suffix
                for const in moved_consts
            )
            + "\n"
        )
    contents = (
        "from typing import Final\nfrom typing import Literal\n"
        + moved_consts_str
        + "\n".join(
            frozenset(
                f'{name_translator.get(const.const_name, const.const_name)}{config.const_name_suffix}: Final[Literal["{const.value}"]] = "{const.value}"'
                for const in consts
                if const.const_name + config.const_name_suffix
            )
        )
    )
    contents = contents.replace('"\n"', '"\\n"')
    consts_file_path.write_text(contents)
