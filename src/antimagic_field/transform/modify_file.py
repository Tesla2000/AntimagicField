from __future__ import annotations

from itertools import chain
from operator import attrgetter
from pathlib import Path

import libcst as cst
from more_itertools.more import map_reduce

from ...filepath2import_path import filepath2import_path
from ..config import Config
from ..const import Const
from ..write_consts import write_consts
from .magic_remover import MagicRemover
from .magic_seeker import MagicSeeker


def modify_file(filepath: Path, config: Config) -> int:
    code = filepath.read_text()
    module = cst.parse_module(code)
    magical_strings = MagicSeeker.get_magical_strings(module, config)
    if config.modify is False and magical_strings:
        print(filepath, "found:", "\n".join(magical_strings))
        return 1
    consts = tuple(map(Const, magical_strings))
    consts = tuple(filter(lambda const: const.const_name is not None, consts))
    duplicates = dict(
        (const_name, values)
        for const_name, values in map_reduce(
            consts,
            lambda const: const.const_name,
            lambda const: const.value,
            frozenset,
        ).items()
        if len(values) > 1
    )
    if duplicates and config.raise_on_duplicates:
        raise ValueError(
            str(filepath)
            + "\n"
            + "\n".join(
                f"{' '.join(sorted(values))} causes occurrence of duplicates"
                for const_name, values in duplicates.items()
            )
        )
    if duplicates:
        values = frozenset(chain.from_iterable(duplicates.values()))
        consts = tuple(filter(lambda const: const.value not in values, consts))
    if not consts:
        return 0
    if config.var_location == "directory":
        consts_file_path = Path(
            config.var_location_name
        ) / filepath.absolute().relative_to(Path().absolute())
    else:
        raise ValueError("var_location can only be folder for now")
    write_consts(consts_file_path, consts, config)
    new_code = module.visit(
        MagicRemover(
            config,
            {
                const.string_node: const.const_name + config.const_name_suffix
                for const in consts
                if const.const_name
            },
        )
    ).code
    before, annotations_import, rest = new_code.rpartition(
        "from __future__ import annotations\n"
    )
    new_code = (
        before
        + annotations_import
        + f"from {filepath2import_path(consts_file_path)} import {', '.join(frozenset(map(lambda const_name: const_name + config.const_name_suffix, map(attrgetter("const_name"), consts))))}\n"
        + rest
    )
    if new_code != code:
        filepath.write_text(new_code)
        print(f"File {filepath} was modified")
        return 1
    return 0
