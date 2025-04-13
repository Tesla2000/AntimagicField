from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from itertools import chain
from typing import Union

from libcst import Name
from libcst import SimpleString

from ..config import Config
from ..constants.previous_const import PreviousConst
from .transformer import Transformer


class MagicRemover(Transformer):
    def __init__(
        self,
        config: Config,
        simple_str2const: Mapping["SimpleString", str],
        renamed_consts: Mapping[str, Sequence[PreviousConst]],
    ):
        super().__init__(config)
        self.renamed_consts = renamed_consts
        self.simple_str2const = simple_str2const
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
        if not (const_name := self.simple_str2const.get(original_node)):
            return updated_node
        return Name(const_name)
