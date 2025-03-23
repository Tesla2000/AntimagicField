from __future__ import annotations

import re
import string
from abc import ABC
from abc import abstractmethod
from pathlib import Path
from typing import Optional

import inflect

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

    @staticmethod
    def _format_const_name(const_name: str):
        const_name = "".join(
            filter(
                allowed_chars.__contains__,
                const_name.replace(" ", "_")
                .replace("-", "_")
                .upper()
                .lstrip("_"),
            )
        )
        if const_name[0].isnumeric():
            num = re.findall(r"\d+", const_name)[0]
            const_name = re.sub(
                r"\d+_?",
                p.number_to_words(num, comma="", andword="") + "_",
                const_name,
                1,
            ).replace(" ", "_")
        return const_name


allowed_chars = (*string.digits, *string.ascii_letters, "_")
p = inflect.engine()
