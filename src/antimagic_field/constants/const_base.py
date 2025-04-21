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
from ..str_consts.src.antimagic_field import EMPTY
from ..str_consts.src.antimagic_field import SPACE
from ..str_consts.src.antimagic_field import UNDERSCORE
from ..str_consts.src.antimagic_field.constants.const_base import A_ZA_Z
from ..str_consts.src.antimagic_field.constants.const_base import S


class ConstBase(ABC):
    const_name: str
    value: str
    is_rstring: bool

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
        const_name = const_name.replace(UNDERSCORE, SPACE)
        const_name = EMPTY.join(
            filter(
                allowed_chars.__contains__,
                re.sub(
                    A_ZA_Z,
                    r"\1_\2",
                    re.sub(S, UNDERSCORE, const_name),
                ).upper(),
            )
        ).strip(UNDERSCORE)
        if (
            not EMPTY.join(
                filterfalse(string.hexdigits.__contains__, const_name)
            ).replace(UNDERSCORE, EMPTY)
            and max_n_parts is not None
        ):
            return None
        if const_name and const_name[0].isnumeric():
            num = re.findall(r"[\d,.]+", const_name)[0]
            const_name = re.sub(
                r"[\d,.]+_?",
                (
                    p.number_to_words(num, comma=EMPTY, andword=EMPTY)
                    + UNDERSCORE
                )
                .replace(",", EMPTY)
                .replace("-", UNDERSCORE)
                .upper(),
                const_name,
                1,
            ).replace(SPACE, UNDERSCORE)
        if const_name != UNDERSCORE.join(
            const_name.split(UNDERSCORE)[:max_n_parts]
        ):
            return None
        return re.sub(r"_+", UNDERSCORE, const_name)

    @property
    def defined_const_name(self):
        return self.const_name


allowed_chars = (*string.digits, *string.ascii_letters, UNDERSCORE)
p = inflect.engine()
