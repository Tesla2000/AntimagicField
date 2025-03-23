from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from pathlib import Path
from typing import Optional

from ..config import Config


class ConstBase(ABC):
    const_name: str
    value: str

    @abstractmethod
    def set_const_name(self, const_name: Optional[str]):
        pass

    @abstractmethod
    def is_path_relative(self, parent_path: Path) -> bool:
        pass

    @abstractmethod
    def set_import_path(self, path: Path):
        pass

    @abstractmethod
    def get_import_filepath(self, config: Config) -> Path:
        pass
