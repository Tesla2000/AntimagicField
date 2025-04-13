from __future__ import annotations

from collections.abc import Collection
from collections.abc import Mapping
from collections.abc import Sequence
from pathlib import Path

from libcst import Module
from more_itertools.more import map_reduce

from ..config import Config
from ..constants.const import Const
from ..constants.previous_const import PreviousConst
from ..filepath2import_path import filepath2import_path
from .magic_remover import MagicRemover


def modify_file(
    filepath: Path,
    consts: Collection[Const],
    module: Module,
    renamed_consts: Mapping[str, Sequence[PreviousConst]],
    config: Config,
) -> int:
    if not consts:
        return 0
    code = filepath.read_text()
    new_code = module.visit(
        MagicRemover(
            config,
            {
                const.string_node: const.const_name + config.const_name_suffix
                for const in consts
                if const.const_name
            },
            renamed_consts,
        )
    ).code
    before, annotations_import, rest = new_code.rpartition(
        "from __future__ import annotations\n"
    )
    new_code = (
        before
        + annotations_import
        + "".join(
            f"from {filepath2import_path(source)} import {', '.join(frozenset(map(lambda const: const.const_name + config.const_name_suffix, source_consts)))}\n"
            for source, source_consts in map_reduce(
                consts, lambda const: const.get_import_filepath(config)
            ).items()
        )
        + rest
    )
    if new_code != code:
        filepath.write_text(new_code)
        print(f"File {filepath} was modified")
        return 1
    return 0
