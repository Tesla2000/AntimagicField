from __future__ import annotations

from collections.abc import Collection
from collections.abc import Iterable
from collections.abc import Sequence

from more_itertools import map_reduce

from .constants.const_base import ConstBase


def solve_duplicates(
    constants: Collection[ConstBase],
) -> dict[str, Sequence[str]]:
    duplicates = _get_duplicates(constants)
    for const_name, values in tuple(duplicates.items()):
        values = tuple(frozenset(values))
        if len(values) > 2:
            continue
        for i in (0, 1):
            first, second = i, not i
            if values[first].capitalize() == values[second]:
                tuple(
                    const.set_const_name(const.const_name, "_LOWERCASE")
                    for const in constants
                    if const.value == values[first]
                )
                tuple(
                    const.set_const_name(const.const_name, "_CAPITALIZED")
                    for const in constants
                    if const.value == values[second]
                )
                del duplicates[const_name]
                break
            if values[first].upper() == values[second]:
                tuple(
                    const.set_const_name(const.const_name, "_LOWERCASE")
                    for const in constants
                    if const.value == values[first]
                )
                tuple(
                    const.set_const_name(const.const_name, "_UPPERCASE")
                    for const in constants
                    if const.value == values[second]
                )
                del duplicates[const_name]
                break
    return duplicates


def _get_duplicates(
    constants: Iterable[ConstBase],
) -> dict[str, Sequence[str]]:
    return {
        const_name: values
        for const_name, values in map_reduce(
            constants,
            lambda const: const.const_name,
            lambda const: const.value,
        ).items()
        if len(frozenset(values)) > 1 and const_name is not None
    }
