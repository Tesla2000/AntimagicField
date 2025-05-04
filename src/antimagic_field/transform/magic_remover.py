from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from itertools import chain
from operator import attrgetter
from typing import Optional
from typing import Union

import libcst
from libcst import Arg
from libcst import Attribute
from libcst import BaseExpression
from libcst import Call
from libcst import Expr
from libcst import FormattedString
from libcst import FormattedStringExpression
from libcst import ImportAlias
from libcst import Name
from libcst import SimpleString

from ..config import Config
from ..constants.const import Const
from ..constants.previous_const import PreviousConst
from ..str_consts.src.antimagic_field.transform.magic_remover import EXPRESSION
from ..str_consts.src.antimagic_field.transform.magic_remover import FORMAT
from .transformer import Transformer


class MagicRemover(Transformer):
    _import_names: set[str]

    def __init__(
        self,
        config: Config,
        cst_str2const: Mapping[Union["SimpleString", "FormattedString"], str],
        renamed_consts: Mapping[str, Sequence[PreviousConst]],
        removed_values: Mapping[str, Const],
    ):
        super().__init__(config)
        self.removed_values = removed_values
        self.renamed_consts = renamed_consts
        self.cst_str2const = cst_str2const
        self._import_names = set()
        self.prev2new = {
            const.previous_const_name
            + self.config.const_name_suffix: (
                const.const_name + self.config.const_name_suffix
            )
            for const in chain.from_iterable(renamed_consts.values())
        }

    def leave_SimpleString(
        self, original_node: "SimpleString", updated_node: "SimpleString"
    ) -> Union["SimpleString", "Name"]:
        if not (const_name := self.cst_str2const.get(original_node)):
            return updated_node
        return Name(const_name)

    def leave_FormattedString(
        self, original_node: "FormattedString", updated_node: "FormattedString"
    ) -> Union["FormattedString", "Expr"]:
        if not (const_name := self.cst_str2const.get(original_node)):
            return updated_node
        return Expr(
            Call(
                Attribute(value=Name(const_name), attr=Name(FORMAT)),
                args=list(
                    map(
                        Arg,
                        map(
                            attrgetter(EXPRESSION),
                            filter(
                                FormattedStringExpression.__instancecheck__,
                                updated_node.parts,
                            ),
                        ),
                    )
                ),
            )
        )

    def visit_ImportAlias(self, node: "ImportAlias") -> Optional[bool]:
        class GetNames(libcst.CSTVisitor):
            def visit_Name(_, node: "Name") -> Optional[bool]:
                self._import_names.add(node)
                return super().visit_Name(node)

        node.visit(GetNames())
        return super().visit_ImportAlias(node)

    def leave_Name(
        self, original_node: "Name", updated_node: "Name"
    ) -> "BaseExpression":
        if original_node in self._import_names:
            return updated_node
        if value := self.removed_values.get(original_node.value):
            return SimpleString(
                value=f'"{value.value.replace('"', '\\"').replace("\n", "\\n")}"'
            )
        return updated_node
