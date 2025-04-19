from __future__ import annotations

from collections.abc import Sequence
from itertools import chain
from itertools import filterfalse
from typing import Optional
from typing import Union

from libcst import Annotation
from libcst import Assign
from libcst import Call
from libcst import ClassDef
from libcst import ConcatenatedString
from libcst import CSTNode
from libcst import Expr
from libcst import FormattedString
from libcst import FunctionDef
from libcst import Name
from libcst import SimpleStatementLine
from libcst import SimpleString
from libcst import Subscript

from ..config import Config
from .transformer import Visitor


class MagicSeeker(Visitor):
    def __init__(self, config: Config):
        super().__init__(config)
        self._simple_strings: list["SimpleString"] = list()
        self._simple_string_consts_assignment: list[
            Union["SimpleString", "FormattedString"]
        ] = list()
        self._string_annotations: list["SimpleString"] = list()
        self._typevar_strings: list["SimpleString"] = list()
        self._docstrings: list[Union["SimpleString", "FormattedString"]] = (
            list()
        )
        self._strings_in_concatenated: list[
            Union["SimpleString", "FormattedString"]
        ] = list()

    def visit_ClassDef_body(self, node: "ClassDef") -> None:
        doc = self._get_docstring(node)
        if doc:
            self._docstrings.append(doc)
        return super().visit_ClassDef_body(node)

    def visit_FunctionDef_body(self, node: "FunctionDef") -> None:
        doc = self._get_docstring(node)
        if doc:
            self._docstrings.append(doc)
        return super().visit_FunctionDef_body(node)

    def visit_Assign(self, node: "Assign") -> Optional[bool]:
        if (
            isinstance(name := node.targets[0].target, Name)
            and name.value.isupper()
            and isinstance(node.value, (SimpleString, FormattedString))
        ):
            self._simple_string_consts_assignment.append(node.value)
        return super().visit_Assign(node)

    def visit_SimpleString(self, node: "SimpleString") -> Optional[bool]:
        self._simple_strings.append(node)
        return super().visit_SimpleString(node)

    def visit_Annotation(self, node: "Annotation") -> Optional[bool]:
        self._string_annotations.extend(
            self.get_magical_strings(node.annotation, self.config)
        )
        return super().visit_Annotation(node)

    def visit_Call(self, node: "Call") -> Optional[bool]:
        if (
            isinstance(node.func, Name)
            and node.func.value == "TypeVar"
            and isinstance(node.args[0].value, SimpleString)
        ):
            self._typevar_strings.append(node.args[0].value)
        return super().visit_Call(node)

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

    def visit_ConcatenatedString(
        self, node: "ConcatenatedString"
    ) -> Optional[bool]:
        self._strings_in_concatenated.extend(
            chain.from_iterable(
                (
                    (
                        [node.left]
                        if isinstance(
                            node.left, (SimpleString, FormattedString)
                        )
                        else self.get_magical_strings(node.left, self.config)
                    ),
                    (
                        [node.right]
                        if isinstance(
                            node.right, (SimpleString, FormattedString)
                        )
                        else self.get_magical_strings(node.right, self.config)
                    ),
                )
            )
        )
        return super().visit_ConcatenatedString(node)

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
                (
                    seeker._string_annotations
                    + seeker._docstrings
                    + seeker._strings_in_concatenated
                    + seeker._typevar_strings
                    + seeker._simple_string_consts_assignment
                ).__contains__,
                seeker._simple_strings,
            )
        )

    def _get_docstring(
        self, node: Union["ClassDef", "FunctionDef"]
    ) -> Optional[Union["SimpleString", "FormattedString"]]:
        if (
            isinstance(
                line_statements := node.body.body[0], SimpleStatementLine
            )
            and isinstance(expr := line_statements.body[0], Expr)
            and isinstance(
                string := expr.value, (SimpleString, FormattedString)
            )
        ):
            return string
