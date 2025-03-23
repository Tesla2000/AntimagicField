from __future__ import annotations

import json
import os
from collections.abc import Sequence
from functools import partial
from itertools import batched
from itertools import chain
from pathlib import Path

from libcst import parse_module
from litellm import completion
from more_itertools.more import map_reduce

from .config import Config
from .config import create_config_with_args
from .config import parse_arguments
from .constants.previous_const import PreviousConst
from .create_response_format import create_response_format
from .extract_constants import extract_constants
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
        filter(lambda path: path.suffix == ".py", paths)
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
        consts_file_path = Path(config.consts_location_name)
        predefined_constants: Sequence[PreviousConst] = tuple(
            chain.from_iterable(
                map(
                    partial(read_consts, config=config),
                    consts_file_path.rglob("*.py"),
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
    if duplicates and config.duplicates_solver == "ignore":
        consts = tuple(
            filter(lambda const: const.value not in duplicate_values, consts)
        )
    if ai_solved_constants := tuple(
        filter(lambda const: const.const_name is None, all_consts)
    ):
        unique_solved = {
            const.value: const for const in ai_solved_constants
        }.values()
        for solving_batch in batched(unique_solved, config.ai_solving_batch):
            solved_values = tuple(const.value for const in solving_batch)
            solutions = json.loads(
                completion(
                    config.ai_model,
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                f"Peak suitable constant names for the following string. Note constant names can't repeat and can't be in this set {frozenset(const.const_name for const in all_consts)}"
                            ),
                        }
                    ],
                    temperature=0.0,
                    response_format=create_response_format(solving_batch),
                ).choices[0]["message"]["content"]
            )
            for const in ai_solved_constants:
                if const.value in solved_values and (
                    solution := solutions.get(
                        f"string{solved_values.index(const.value) + 1}"
                    )
                ):
                    const.set_const_name(solution)
    if not consts:
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
        tuple(
            map(
                lambda const: const.set_const_name(None),
                filter(
                    lambda const: const.value in duplicate_values, all_consts
                ),
            )
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
            # predefined_constants,
            consts=grouped_consts.get(filepath, []),
            config=config,
        )
    return fail
