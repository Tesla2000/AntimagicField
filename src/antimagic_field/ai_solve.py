from __future__ import annotations

import json
import sys
from collections.abc import Collection
from collections.abc import Iterable
from itertools import chain
from typing import Type

from more_itertools import batched
from pydantic import BaseModel
from pydantic import create_model
from pydantic import Field

from .config import Config
from .constants.const import Const
from .constants.const_base import ConstBase
from .exceptions import FailedToSolveDuplicates
from .solve_duplicates import solve_duplicates
from .str_consts.src.antimagic_field import EMPTY
from .str_consts.src.antimagic_field.ai_solve import CONTENT
from .str_consts.src.antimagic_field.ai_solve import FIELD_NAMES
from .str_consts.src.antimagic_field.ai_solve import MESSAGE
from .str_consts.src.antimagic_field.ai_solve import ROLE
from .str_consts.src.antimagic_field.ai_solve import STRING_FORMATTED
from .str_consts.src.antimagic_field.ai_solve import USER


def ai_solve_duplicates(
    all_consts: Collection[ConstBase], config: Config, const_names: set[str]
):
    n_duplicates = sys.maxsize
    while True:
        duplicates = solve_duplicates(all_consts)
        if not duplicates:
            return
        duplicate_values = frozenset(chain.from_iterable(duplicates.values()))
        if len(duplicates) >= n_duplicates:
            raise FailedToSolveDuplicates(duplicate_values)
        n_duplicates = len(duplicates)
        duplicate_constants = tuple(
            sorted(
                filter(
                    lambda const: const.value in duplicate_values, all_consts
                ),
                key=lambda const: const.const_name,
            )
        )
        ai_assign_names(duplicate_constants, config, const_names, all_consts)


def ai_assign_names(
    unique_unnamed: Collection[Const],
    config: Config,
    const_names: set[str],
    all_constants: Collection[ConstBase],
):
    tuple(
        _ai_assign_names(solving_batch, config, const_names, all_constants)
        for solving_batch in batched(unique_unnamed, config.ai_solving_batch)
    )


def _ai_assign_names(
    solving_batch: Collection[Const],
    config: Config,
    const_names: set[str],
    all_constants: Iterable[ConstBase],
):
    from litellm import completion

    solved_values = tuple(const.value for const in solving_batch)
    solutions = json.loads(
        completion(
            config.ai_model,
            messages=[
                {
                    ROLE: USER,
                    CONTENT: (
                        "Peak suitable constant names for the following string. "
                        "Constant names must be uppercase ascii strings with "
                        "words connected by _ with no more than 5 words. "
                        "Constant name shouldn't start with digits and "
                        "mustn't contain special characters. You mustn't use the same name twice."
                    ),
                }
            ],
            temperature=0.0,
            response_format=_create_response_format(solving_batch),
        ).choices[0][MESSAGE][CONTENT]
    )
    for const in filter(Const.__instancecheck__, all_constants):
        if const.value in solved_values and (
            solution := solutions.get(
                STRING_FORMATTED.format(solved_values.index(const.value) + 1)
            )
        ):
            const.set_const_name(solution, EMPTY, None)
            const_names.add(const.const_name)


def _create_response_format(consts: Collection[Const]) -> Type[BaseModel]:
    return create_model(
        FIELD_NAMES,
        __doc__="Descriptions contain values of constants that the names should be assigned to",
        **{
            STRING_FORMATTED.format(index): (
                str,
                Field(description=const.value),
            )
            for index, const in enumerate(consts, 1)
        },
    )
