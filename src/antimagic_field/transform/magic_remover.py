from __future__ import annotations

from collections.abc import Mapping
from typing import Union

from libcst import Name
from libcst import SimpleString

from ..config import Config
from .transformer import Transformer


class MagicRemover(Transformer):
    def __init__(
        self, config: Config, simple_str2const: Mapping["SimpleString", str]
    ):
        super().__init__(config)
        self.simple_str2const = simple_str2const

    def leave_SimpleString(
        self, original_node: "SimpleString", updated_node: "SimpleString"
    ) -> Union["SimpleString", "Name"]:
        if not (const_name := self.simple_str2const.get(original_node)):
            return updated_node
        return Name(const_name)
