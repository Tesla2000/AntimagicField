from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import libcst

from ..config import Config
from ..constants.const_base import ConstBase


@dataclass(slots=True)
class Const(ConstBase):
    string_node: libcst.SimpleString
    origin_filepath: Path
    _import_filepath: Optional[Path] = None
    _const_name: Optional[str] = None

    def get_import_filepath(self, config: Config) -> Path:
        if config.consts_location == "directory":
            if self._import_filepath:
                return self._import_filepath.absolute()
            return self.origin2import(self.origin_filepath, config).absolute()
        raise ValueError("var_location can only be folder for now")

    def set_import_path(self, path: Path):
        self._import_filepath = path.absolute()

    @staticmethod
    def origin2import(origin_filepath: Path, config: Config) -> Path:
        return Path(
            config.consts_location_name
        ) / origin_filepath.absolute().relative_to(Path().absolute())

    def is_path_relative(self, parent_path: Path) -> bool:
        return self.origin_filepath.absolute().is_relative_to(
            parent_path.absolute()
        )

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


_known_strings = {
    "\n": "NEWLINE",
    "": "EMPTY",
    "_": "UNDERSCORE",
    " ": "SPACE",
    '"': "DOUBLE_QUOTES",
    "'": "SINGLE_QUOTES",
}
