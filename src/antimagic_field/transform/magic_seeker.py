from __future__ import annotations

from collections.abc import Sequence
from itertools import chain
from itertools import filterfalse
from typing import Optional
from typing import Union

from libcst import Annotation
from libcst import Assign
from libcst import BaseSmallStatement
from libcst import BaseStatement
from libcst import BaseSuite
from libcst import Call
from libcst import ClassDef
from libcst import ConcatenatedString
from libcst import CSTNode
from libcst import Expr
from libcst import FormattedString
from libcst import FunctionDef
from libcst import Module
from libcst import Name
from libcst import SimpleStatementLine
from libcst import SimpleString
from libcst import Subscript

from ..config import Config
from ..str_consts.src.antimagic_field.transform.magic_seeker import LITERAL
from ..str_consts.src.antimagic_field.transform.magic_seeker import TYPE_VAR
from .transformer import Visitor


class MagicSeeker(Visitor):
    def __init__(self, config: Config):
        super().__init__(config)
        self._simple_strings: list["SimpleString"] = list()
        self._formated_strings: list["FormattedString"] = list()
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
        self._docstrings.extend(self._get_docstrings(node.body))
        return super().visit_ClassDef_body(node)

    def visit_FunctionDef_body(self, node: "FunctionDef") -> None:
        self._docstrings.extend(self._get_docstrings(node.body))
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

    def visit_FormattedString(self, node: "FormattedString") -> Optional[bool]:
        self._formated_strings.append(node)
        return super().visit_FormattedString(node)

    def visit_Annotation(self, node: "Annotation") -> Optional[bool]:
        self._string_annotations.extend(
            self.get_magical_strings(node.annotation, self.config)
        )
        return super().visit_Annotation(node)

    def visit_Call(self, node: "Call") -> Optional[bool]:
        if (
            isinstance(node.func, Name)
            and node.func.value == TYPE_VAR
            and isinstance(node.args[0].value, SimpleString)
        ):
            self._typevar_strings.append(node.args[0].value)
        return super().visit_Call(node)

    def visit_Subscript(self, node: "Subscript") -> Optional[bool]:
        if (
            (value := node.value)
            and isinstance(value, Name)
            and value.value == LITERAL
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
    ) -> Sequence[Union["SimpleString", "FormattedString"]]:
        seeker = cls(config)
        if isinstance(module, Module):
            seeker._docstrings.extend(seeker._get_docstrings(module))
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
                seeker._simple_strings + seeker._formated_strings,
            )
        )

    @classmethod
    def _get_docstrings(
        cls,
        node: "BaseSuite",
    ) -> tuple[Union["SimpleString", "FormattedString"], ...]:
        return tuple(filter(None, map(cls._get_docstring, node.body)))

    @staticmethod
    def _get_docstring(
        line_statement: Union["BaseStatement", "BaseSmallStatement"],
    ) -> Optional[Union["SimpleString", "FormattedString"]]:
        if not isinstance(line_statement, SimpleStatementLine):
            return None
        expr = line_statement.body[0]
        if not isinstance(expr, Expr):
            return None
        string = expr.value
        if not isinstance(string, (SimpleString, FormattedString)):
            return None
        return string
