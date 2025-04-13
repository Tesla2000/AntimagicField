from __future__ import annotations

import os
from collections import Counter
from collections.abc import Collection
from collections.abc import Sequence
from functools import partial
from itertools import chain
from pathlib import Path
from typing import Optional

from libcst import parse_module
from more_itertools.more import map_reduce

from .ai_solve import ai_assign_names
from .ai_solve import ai_solve_duplicates
from .config import Config
from .config import create_config_with_args
from .config import parse_arguments
from .constants.const import Const
from .constants.const_base import ConstBase
from .constants.previous_const import PreviousConst
from .exceptions import FailedToSolveDuplicates
from .extract_constants import extract_constants
from .filepath2import_path import filepath2import_path
from .group2files import group2files
from .read_consts import read_consts
from .save2files import save2files
from .solve_duplicates import solve_duplicates
from .transaction import transation
from .transform.modify_file import modify_file


def main() -> int:
    """
    The `main` function processes a list of filenames from a configuration,
    filtering for Python files, and applies a modification function to each,
    returning a failure status indicating whether any modifications failed. It
    utilizes argument parsing and configuration creation to determine the files
    to be modified.
    :return: An integer indicating the success (0) or failure (1) of file
    modifications.
    """
    args = parse_arguments(Config)
    config = create_config_with_args(Config, args)
    os.chdir(config.root)
    with transation(
        chain.from_iterable(
            (
                config.pos_args,
                Path(config.root)
                .joinpath(config.consts_location_name)
                .rglob("*.py"),
            )
        )
    ):
        return _main(config)


def _main(config: Config):
    fail = 0
    paths = map(Path, config.pos_args)
    modified_files: Sequence[Path] = tuple(
        filter(
            lambda path: path.suffix == ".py"
            and (
                config.consts_location != "directory"
                or not path.is_relative_to(Path(config.consts_location_name))
            )
            and not config.is_excluded(path),
            paths,
        )
    )
    modules = {file: parse_module(file.read_text()) for file in modified_files}
    consts = tuple(
        chain.from_iterable(
            extract_constants(
                filepath=file, module=modules[file], config=config
            )
            for file in modified_files
        )
    )
    if config.consts_location == "directory":
        predefined_constants: Sequence[PreviousConst] = tuple(
            chain.from_iterable(
                map(
                    partial(read_consts, config=config),
                    Path(config.consts_location_name).rglob("*.py"),
                )
            )
        )
    else:
        raise ValueError("var_location can only be folder for now")
    if config.difficult_string_solver == "ignore":
        consts = tuple(
            filter(lambda const: const.const_name is not None, consts)
        )
    predefined_values = frozenset(
        const.value for const in predefined_constants
    )
    if config.difficult_string_solver == "exception" and (
        difficult_constants := tuple(
            filter(
                lambda const: const.const_name is None
                and const.value not in predefined_values,
                consts,
            )
        )
    ):
        for filepath, magical_strings in map_reduce(
            difficult_constants,
            lambda const: const.origin_filepath,
            lambda const: const.value,
        ):
            print(filepath, "found:", "\n".join(magical_strings))
        return 1
    all_consts = (*consts, *predefined_constants)
    duplicates = solve_duplicates(all_consts)
    duplicate_values = frozenset(chain.from_iterable(duplicates.values()))
    if duplicates and config.duplicates_solver == "exception":
        for filepath, magical_strings in map_reduce(
            filter(lambda const: const.value in duplicate_values, consts),
            lambda const: const.origin_filepath,
            lambda const: const.value,
        ):
            print(filepath, "found:", "\n".join(magical_strings))
        return 1
    const_names = set(const.const_name for const in all_consts)
    if unnamed_constants := tuple(
        filter(lambda const: const.const_name is None, all_consts)
    ):
        unique_unnamed = {
            const.value: const for const in unnamed_constants
        }.values()
        ai_assign_names(unique_unnamed, config, const_names, unnamed_constants)
    if not consts and not solve_duplicates(all_consts):
        return 0
    if config.modify is False and consts:
        for filepath, magical_strings in map_reduce(
            consts,
            lambda const: const.origin_filepath,
            lambda const: const.value,
        ):
            print(filepath, "found:", "\n".join(magical_strings))
        return 1
    if duplicates and config.duplicates_solver == "ai":
        try:
            ai_solve_duplicates(all_consts, config, const_names)
        except FailedToSolveDuplicates as e:
            print(
                f"Failed to solve for following duplicates {e.duplicate_values}"
            )
    elif config.duplicates_solver == "most_common":
        all_consts = _solve_duplicates_most_common(
            consts, predefined_constants
        )
    elif config.duplicates_solver == "ignore":
        all_consts = _solve_duplicates_ignore(consts, predefined_constants)
    consts = tuple(filter(Const.__instancecheck__, all_consts))
    predefined_constants = tuple(
        filter(PreviousConst.__instancecheck__, all_consts)
    )
    grouped_files = group2files(all_consts, config)
    file_switching_consts = map_reduce(
        filter(
            lambda const: all(
                (
                    const.previous_written_filepath,
                    const.written_filepath,
                    const.previous_written_filepath != const.written_filepath,
                )
            ),
            predefined_constants,
        ),
        lambda const: const.previous_written_filepath.absolute(),
    )
    renamed_consts = map_reduce(
        filter(
            lambda const: all(
                (
                    const.const_name,
                    const.previous_const_name,
                    const.const_name != const.previous_const_name,
                )
            ),
            predefined_constants,
        ),
        lambda const: (
            const.previous_written_filepath or const.written_filepath
        ).absolute(),
    )
    save2files(grouped_files, file_switching_consts, renamed_consts, config)
    grouped_consts = map_reduce(consts, lambda const: const.origin_filepath)
    for filepath in modified_files:
        fail |= modify_file(
            filepath,
            module=modules[filepath],
            consts=grouped_consts.get(filepath, []),
            renamed_consts={
                filepath2import_path(key): value
                for key, value in renamed_consts.items()
            },
            config=config,
        )
    return fail


def _solve_duplicates_most_common(
    consts: Collection[Const], predefined_consts: Collection[PreviousConst]
) -> Sequence[ConstBase]:
    all_consts = *consts, *predefined_consts
    duplicates = solve_duplicates(all_consts)
    value2const_name = _assign_command_names(duplicates, predefined_consts)
    tuple(
        map(
            lambda const: const.set_const_name(
                value2const_name.get(const.value), max_n_parts=None
            ),
            filter(lambda const: const.value in value2const_name, consts),
        )
    )
    consts = tuple(
        filter(
            lambda const: value2const_name.get(const.value, const.const_name)
            is not None,
            consts,
        )
    )
    return *consts, *predefined_consts


def _assign_command_names(
    duplicates: dict[str, Sequence[str]],
    predefined_consts: Collection[PreviousConst],
) -> dict[str, Optional[str]]:
    value2const_name = {}
    value2const_name_predefined = {
        const.value: const.const_name for const in predefined_consts
    }
    for key, values in duplicates.items():
        counter = Counter(values)
        for value in frozenset(values):
            value2const_name[value] = None
        if predefined_value := next(
            filter(None, map(value2const_name_predefined.get, values)), None
        ):
            value2const_name[predefined_value] = key
        else:
            value2const_name[max(values, key=counter.get)] = key
    return value2const_name


def _solve_duplicates_ignore(
    consts: Collection[Const], predefined_consts: Collection[PreviousConst]
) -> Sequence[ConstBase]:
    all_consts = *consts, *predefined_consts
    duplicates = solve_duplicates(all_consts)
    duplicate_values = frozenset(chain.from_iterable(duplicates.values()))
    tuple(
        map(
            lambda const: const.set_const_name(None),
            filter(lambda const: const.value in duplicate_values, consts),
        )
    )
    consts = tuple(
        filter(lambda const: const.value not in duplicate_values, consts)
    )
    return *consts, *predefined_consts
