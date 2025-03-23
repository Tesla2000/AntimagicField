from __future__ import annotations

from pathlib import Path
from typing import Optional

import libcst
from libcst import AnnAssign
from libcst import Assign
from libcst import Name
from libcst import SimpleString

from .config import Config
from .constants.previous_const import PreviousConst


def read_consts(consts_file_path: Path, config: Config) -> list[PreviousConst]:
    if not consts_file_path.exists():
        return []
    visitor = _ConstantsGetter(consts_file_path, config)
    libcst.parse_module(consts_file_path.read_text()).visit(visitor)
    return visitor.consts


class _ConstantsGetter(libcst.CSTTransformer):
    def __init__(self, filepath: Path, config: Config):
        super().__init__()
        self.config = config
        self.filepath = filepath
        self.consts = []

    def visit_Assign(self, node: "Assign") -> Optional[bool]:
        if (
            len(node.targets) == 1
            and isinstance((target := node.targets[0].target), Name)
            and isinstance(node.value, SimpleString)
        ):
            self.consts.append(
                PreviousConst(
                    target.value.removesuffix(self.config.const_name_suffix),
                    node.value.evaluated_value,
                    self.filepath,
                )
            )
        return super().visit_Assign(node)

    def visit_AnnAssign(self, node: "AnnAssign") -> Optional[bool]:
        if isinstance((target := node.target), Name) and isinstance(
            node.value, SimpleString
        ):
            self.consts.append(
                PreviousConst(
                    target.value.removesuffix(self.config.const_name_suffix),
                    node.value.evaluated_value,
                    self.filepath,
                )
            )
        return super().visit_AnnAssign(node)
