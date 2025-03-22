from __future__ import annotations

from collections.abc import Sequence
from itertools import chain
from itertools import filterfalse
from typing import Optional

from libcst import Annotation
from libcst import CSTNode
from libcst import Name
from libcst import SimpleString
from libcst import Subscript

from ..config import Config
from .transformer import Transformer


class MagicSeeker(Transformer):
    def __init__(self, config: Config):
        super().__init__(config)
        self._simple_strings: list["SimpleString"] = list()
        self._string_annotations: list["SimpleString"] = list()

    def visit_SimpleString(self, node: "SimpleString") -> Optional[bool]:
        self._simple_strings.append(node)
        return super().visit_SimpleString(node)

    def visit_Annotation(self, node: "Annotation") -> Optional[bool]:
        self._string_annotations.extend(
            self.get_magical_strings(node.annotation, self.config)
        )
        return super().visit_Annotation(node)

    def visit_Subscript(self, node: "Subscript") -> Optional[bool]:
        if (
            (value := node.value)
            and isinstance(value, Name)
            and value.value == "Literal"
        ):
            self._string_annotations.extend(
                chain.from_iterable(
                    self.get_magical_strings(child, self.config)
                    for child in node.children
                )
            )
        return super().visit_Subscript(node)

    @classmethod
    def get_magical_strings(
        cls, module: CSTNode, config: Config
    ) -> Sequence["SimpleString"]:
        seeker = cls(config)
        module.visit(seeker)
        if config.include_annotations:
            return seeker._simple_strings
        return tuple(
            filterfalse(
                seeker._string_annotations.__contains__, seeker._simple_strings
            )
        )
