from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from itertools import chain
from operator import attrgetter
from typing import Union

from libcst import Arg
from libcst import Attribute
from libcst import Call
from libcst import Expr
from libcst import FormattedString
from libcst import FormattedStringExpression
from libcst import Name
from libcst import SimpleString

from ..config import Config
from ..constants.previous_const import PreviousConst
from .transformer import Transformer


class MagicRemover(Transformer):
    def __init__(
        self,
        config: Config,
        cst_str2const: Mapping[Union["SimpleString", "FormattedString"], str],
        renamed_consts: Mapping[str, Sequence[PreviousConst]],
    ):
        super().__init__(config)
        self.renamed_consts = renamed_consts
        self.cst_str2const = cst_str2const
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
    ) -> Union["FormattedString", "Name"]:
        if not (const_name := self.cst_str2const.get(original_node)):
            return updated_node
        return Expr(
            Call(
                Attribute(value=Name(const_name), attr=Name("format")),
                args=list(
                    map(
                        Arg,
                        map(
                            attrgetter("expression"),
                            filter(
                                FormattedStringExpression.__instancecheck__,
                                updated_node.parts,
                            ),
                        ),
                    )
                ),
            )
        )
