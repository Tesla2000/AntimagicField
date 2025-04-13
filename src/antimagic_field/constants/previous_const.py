from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..config import Config
from .const_base import ConstBase


@dataclass(slots=True)
class PreviousConst(ConstBase):
    const_name: str
    value: str
    written_filepath: Path
    previous_written_filepath: Optional[Path] = None
    previous_const_name: Optional[str] = None

    def set_const_name(self, const_name: str, suffix: str = ""):
        self.previous_const_name = self.const_name
        self.const_name = self._format_const_name(const_name)
        if self.const_name:
            self.const_name += suffix

    def set_import_path(self, path: Path):
        self.previous_written_filepath = self.written_filepath
        self.written_filepath = path

    def is_path_relative(self, parent_path: Path) -> bool:
        return self.written_filepath.is_relative_to(parent_path)

    def get_import_filepath(self, _: Config) -> Path:
        return self.written_filepath.absolute()

    @property
    def defined_const_name(self):
        return self.const_name or self.previous_const_name
