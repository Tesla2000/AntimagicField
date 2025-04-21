from __future__ import annotations

from libcst import FormattedString
from libcst import FormattedStringExpression
from libcst import FormattedStringText

from ..str_consts.src.antimagic_field import EMPTY


def formated_string2string(formated_string: FormattedString) -> str:
    return EMPTY.join(map(_part2string, formated_string.parts))


def _part2string(part: FormattedStringText | FormattedStringExpression):
    if isinstance(part, FormattedStringText):
        return part.value
    if isinstance(part, FormattedStringExpression):
        return (
            "{"
            + (
                ":" + part.format_spec[0].value
                if part.format_spec
                and isinstance(part.format_spec[0], FormattedStringText)
                else EMPTY
            )
            + "}"
        )
    raise ValueError()
