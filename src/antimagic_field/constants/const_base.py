from __future__ import annotations

import re
import string
from abc import ABC
from abc import abstractmethod
from itertools import filterfalse
from pathlib import Path
from typing import Optional

import inflect

from ..config import Config


class ConstBase(ABC):
    const_name: str
    value: str

    @abstractmethod
    def set_const_name(self, const_name: Optional[str], suffix: str):
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
    def _format_const_name(
        const_name: str, max_n_parts: Optional[int] = 3
    ) -> Optional[str]:
        const_name = const_name.replace("_", " ")
        const_name = "".join(
            filter(
                allowed_chars.__contains__,
                re.sub(r"[\s-]+", "_", const_name).upper().lstrip("_"),
            )
        )
        if (
            not "".join(
                filterfalse(string.hexdigits.__contains__, const_name)
            ).replace("_", "")
            and max_n_parts is not None
        ):
            return None
        if const_name[0].isnumeric():
            num = re.findall(r"[\d,.]+", const_name)[0]
            const_name = re.sub(
                r"[\d,.]+_?",
                (p.number_to_words(num, comma="", andword="") + "_")
                .replace(",", "")
                .replace("-", "_")
                .upper(),
                const_name,
                1,
            ).replace(" ", "_")
        if const_name != "_".join(const_name.split("_")[:max_n_parts]):
            return None
        return re.sub(r"_+", "_", const_name)


allowed_chars = (*string.digits, *string.ascii_letters, "_")
p = inflect.engine()
