from __future__ import annotations

from collections.abc import Collection
from collections.abc import Sequence
from itertools import chain
from itertools import filterfalse
from operator import attrgetter
from pathlib import Path
from typing import Optional

import libcst
from libcst import Assign
from libcst import ImportAlias
from libcst import ImportFrom
from libcst import Module
from libcst import Name
from more_itertools import map_reduce

from .config import Config
from .constants.const_base import ConstBase
from .constants.previous_const import PreviousConst
from .filepath2import_path import filepath2import_path
from .str_consts.src.antimagic_field import COMA_SPACE
from .str_consts.src.antimagic_field import DOUBLE_QUOTES
from .str_consts.src.antimagic_field import EMPTY
from .str_consts.src.antimagic_field import NEWLINE
from .str_consts.src.antimagic_field import R
from .str_consts.src.antimagic_field import UNDERSCORE
from .str_consts.src.antimagic_field.write_consts import N
from .str_consts.src.antimagic_field.write_consts import VALUE


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
        const.previous_const_name: const.const_name for const in renamed_consts
    }
    moved_consts_str = EMPTY
    code = consts_file_path.read_text() if consts_file_path.exists() else EMPTY
    previous_moved_consts = []
    module = libcst.parse_module(code)

    class PreviousImportsExtractor(libcst.CSTVisitor):
        def visit_Assign(self, node: "Assign") -> Optional[bool]:
            if (
                len(node.targets) != 1
                or node.targets[0].target.value != UNDERSCORE
            ):
                return super().visit_Assign(node)
            node.value.visit(ElementVisitor())
            return super().visit_Assign(node)

    class ElementVisitor(libcst.CSTVisitor):
        def visit_Name(self, node: "Name") -> Optional[bool]:
            previous_moved_consts.append(node.value)
            return super().visit_Name(node)

    module.visit(PreviousImportsExtractor())
    previous_moved_consts_imports = []

    class ImportsExtractor(libcst.CSTVisitor):
        def visit_ImportFrom(self, node: "ImportFrom") -> Optional[bool]:
            previous_moved_consts_imports.extend(
                f"from {'.'.join(map(attrgetter(VALUE), filter(Name.__instancecheck__, node.module.children + [node.module])))} import {alias.name.value}"
                for alias in filter(ImportAlias.__instancecheck__, node.names)
                if alias.name.value in previous_moved_consts
            )
            return super().visit_ImportFrom(node)

    module.visit(ImportsExtractor())
    if moved_consts or previous_moved_consts_imports:
        moved_consts_str = (
            NEWLINE.join(
                sorted(
                    {
                        *tuple(
                            f"from {filepath2import_path(const.written_filepath)} import {const.const_name}{config.const_name_suffix}"
                            for const in moved_consts
                        ),
                        *previous_moved_consts_imports,
                    }
                )
            )
            + "\n_ = "
            + COMA_SPACE.join(
                sorted(
                    {
                        *tuple(
                            const.defined_const_name + config.const_name_suffix
                            for const in moved_consts
                            if const.defined_const_name not in name_translator
                        ),
                        *previous_moved_consts,
                    }
                )
            )
            + NEWLINE
        )
    names = tuple(
        name_translator.get(const.const_name, const.const_name)
        + config.const_name_suffix
        for const in consts
    )
    duplicate_const_groups = tuple(
        values
        for _, values in map_reduce(consts, lambda const: const.value).items()
        if len(values) > 1
    )
    duplicate_consts = tuple(chain.from_iterable(duplicate_const_groups))
    contents = (
        "from typing import Final\n"
        + moved_consts_str
        + NEWLINE.join(
            sorted(
                frozenset(
                    _line(name, const)
                    for name, const in zip(names, consts)
                    if const not in duplicate_consts
                ).union(
                    _line(
                        name_translator.get(
                            consts[0].const_name, consts[0].const_name
                        )
                        + config.const_name_suffix,
                        consts[0],
                    )
                    for consts in duplicate_const_groups
                )
            )
        )
    )

    previous_assignments = []

    class PreviousAssignmentExtractor(libcst.CSTVisitor):
        def visit_Assign(self, node: "Assign") -> Optional[bool]:
            if (
                len(node.targets) == 1
                and isinstance(node.children[1], Name)
                and isinstance(node.targets[0].target, Name)
                and node.targets[0].target.value not in (*names, UNDERSCORE)
                and node.targets[0].target.value != node.children[1].value
            ):
                previous_assignments.append(NEWLINE + Module([node]).code)
            return super().visit_Assign(node)

    module.visit(PreviousAssignmentExtractor())
    contents = contents.replace('"\n"', N)
    contents += EMPTY.join(
        filterfalse(
            previous_assignments.__contains__,
            chain.from_iterable(
                (
                    (
                        f"\n{key}{config.const_name_suffix} = {value}{config.const_name_suffix}"
                        for key, value in name_translator.items()
                        if key != value
                    ),
                    (
                        f"\n{const.const_name}{config.const_name_suffix} = {consts[0].const_name}{config.const_name_suffix}"
                        for consts in duplicate_const_groups
                        for const in consts[1:]
                        if f"{const.const_name}{config.const_name_suffix}"
                        != f"{consts[0].const_name}{config.const_name_suffix}"
                    ),
                )
            ),
        )
    )
    contents += EMPTY.join(previous_assignments)
    consts_file_path.write_text(contents)


def _line(name: str, const: ConstBase) -> str:
    return f'{name}: Final[str] = {R * const.is_rstring}"{(NEWLINE in (value := const.value)) * '""'}{value.replace(DOUBLE_QUOTES, r"\"")}{(NEWLINE in value) * '""'}"'
