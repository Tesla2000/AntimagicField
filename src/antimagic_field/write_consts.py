from __future__ import annotations

from collections.abc import Collection
from collections.abc import Sequence
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

from .config import Config
from .constants.const_base import ConstBase
from .constants.previous_const import PreviousConst
from .filepath2import_path import filepath2import_path


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
    moved_consts_str = ""
    code = consts_file_path.read_text() if consts_file_path.exists() else ""
    previous_moved_consts = []
    module = libcst.parse_module(code)

    class PreviousImportsExtractor(libcst.CSTVisitor):
        def visit_Assign(self, node: "Assign") -> Optional[bool]:
            if len(node.targets) != 1 or node.targets[0].target.value != "_":
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
                f"from {'.'.join(map(attrgetter('value'), filter(Name.__instancecheck__, node.module.children + [node.module])))} import {alias.name.value}"
                for alias in filter(ImportAlias.__instancecheck__, node.names)
                if alias.name.value in previous_moved_consts
            )
            return super().visit_ImportFrom(node)

    module.visit(ImportsExtractor())
    if moved_consts or previous_moved_consts_imports:
        moved_consts_str = (
            "\n".join(
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
            + ", ".join(
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
            + "\n"
        )
    names = tuple(
        name_translator.get(const.const_name, const.const_name)
        + config.const_name_suffix
        for const in consts
    )
    contents = (
        "from typing import Final\nfrom typing import Literal\n"
        + moved_consts_str
        + "\n".join(
            sorted(
                frozenset(
                    f'{name}: Final[Literal["{('\n' in (value := const.value)) * '""'}{value.replace('"', r"\"")}{('\n' in value) * '""'}"]] = "{('\n' in value) * '""'}{value.replace('"', r"\"")}{('\n' in value) * '""'}"'
                    for name, const in zip(names, consts)
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
                and node.targets[0].target.value not in (*names, "_")
            ):
                previous_assignments.append("\n" + Module([node]).code)
            return super().visit_Assign(node)

    module.visit(PreviousAssignmentExtractor())
    contents = contents.replace('"\n"', '"\\n"')
    contents += "".join(
        filterfalse(
            previous_assignments.__contains__,
            (
                f"\n{key}{config.const_name_suffix} = {value}{config.const_name_suffix}"
                for key, value in name_translator.items()
            ),
        )
    )
    contents += "".join(previous_assignments)
    consts_file_path.write_text(contents)
