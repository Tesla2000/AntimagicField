from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import inflect
import libcst


@dataclass(slots=True)
class Const:
    string_node: libcst.SimpleString
    _const_name: Optional[str] = None

    @property
    def value(self) -> str:
        return self.string_node.evaluated_value

    @property
    def const_name(self) -> Optional[str]:
        if self._const_name is not None:
            return self._const_name
        string = self.string_node.evaluated_value
        if string in _known_strings:
            return _known_strings[string]
        if (
            all(map(str.isalnum, string.replace("_", "")))
            and len(string.split()) == 1
        ):
            if string[0].isnumeric():
                num = re.findall(r"\d+", string)[0]
                string = re.sub(
                    r"\d+_?",
                    p.number_to_words(num, comma="", andword="") + "_",
                    string,
                    1,
                ).replace(" ", "_")
            return string.replace("-", "_").upper()
        return None

    @const_name.setter
    def const_name(self, const_name: Optional[str]):
        self._const_name = const_name


p = inflect.engine()


_known_strings = {
    "\n": "NEWLINE",
    "": "EMPTY",
    "_": "UNDERSCORE",
    " ": "SPACE",
}
