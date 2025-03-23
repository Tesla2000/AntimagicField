from __future__ import annotations

from collections.abc import Collection
from collections.abc import Sequence
from pathlib import Path

from more_itertools import map_reduce

from .config import Config
from .constants.const import Const
from .constants.const_base import ConstBase


def group2files(
    all_consts: Collection[ConstBase], config: Config
) -> dict[Path, Sequence[ConstBase]]:
    for value, constants in map_reduce(
        all_consts, lambda const: const.value
    ).items():
        new_const = next(filter(Const.__instancecheck__, constants), None)
        if new_const is None:
            continue
        filepath: Path = new_const.origin_filepath
        while not all(
            const.is_path_relative(filepath)
            or const.is_path_relative(Const.origin2import(filepath, config))
            for const in constants
        ):
            filepath = filepath.parent
        if filepath.is_dir():
            filepath = filepath.joinpath("__init__.py")
        tuple(
            const.set_import_path(Const.origin2import(filepath, config))
            for const in constants
        )
    return map_reduce(
        all_consts, lambda const: const.get_import_filepath(config)
    )
