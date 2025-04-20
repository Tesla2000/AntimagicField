from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

import libcst

from ..config import Config
from ..constants.const_base import ConstBase
from ..utils.formated_string2string import formated_string2string


@dataclass(slots=True)
class Const(ConstBase):
    string_node: libcst.SimpleString | libcst.FormattedString
    origin_filepath: Path
    _import_filepath: Optional[Path] = None
    _const_name: Optional[str] = None

    def get_import_filepath(self, config: Config) -> Path:
        if config.consts_location == "directory":
            if self._import_filepath:
                return self._import_filepath.absolute()
            return origin2import(self.origin_filepath, config).absolute()
        raise ValueError("var_location can only be folder for now")

    def set_import_path(self, path: Path):
        self._import_filepath = path.absolute()

    def is_path_relative(self, parent_path: Path) -> bool:
        return self.origin_filepath.absolute().is_relative_to(
            parent_path.absolute()
        )

    @property
    def is_rstring(self) -> bool:
        return self.string_node.prefix == "r"

    @property
    def value(self) -> str:
        if isinstance(self.string_node, libcst.SimpleString):
            return self.string_node.evaluated_value
        if isinstance(self.string_node, libcst.FormattedString):
            return formated_string2string(self.string_node)
        raise ValueError()

    @property
    def const_name(self) -> Optional[str]:
        if self._const_name is not None:
            return self._const_name
        string = self.value
        if isinstance(self.string_node, libcst.FormattedString):
            string += "_formatted"
        if string in _known_strings:
            return _known_strings[string]
        return self._format_const_name(string)

    def set_const_name(
        self,
        const_name: Optional[str],
        suffix: str = "",
        max_n_parts: Optional[int] = 3,
    ):
        if const_name is None:
            self._const_name = const_name
        else:
            self._const_name = self._format_const_name(const_name, max_n_parts)
            if self._const_name:
                self._const_name += suffix


def origin2import(origin_filepath: Path, config: Config) -> Path:
    return _origin2import(origin_filepath, config.consts_location_name)


@lru_cache
def _origin2import(origin_filepath: Path, consts_location_name: str) -> Path:
    return Path(consts_location_name) / origin_filepath.absolute().relative_to(
        Path().absolute()
    )


_known_strings = {
    "\n": "NEWLINE",
    "*": "STAR",
    ", ": "COMA_SPACE",
    "?": "QUESTION_MARK",
    "": "EMPTY",
    "_": "UNDERSCORE",
    " ": "SPACE",
    '"': "DOUBLE_QUOTES",
    "'": "SINGLE_QUOTES",
}
