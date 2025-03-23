from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from pathlib import Path

from .config import Config
from .constants.const_base import ConstBase
from .constants.previous_const import PreviousConst
from .write_consts import write_consts


def save2files(
    grouped_consts: Mapping[Path, Sequence[ConstBase]],
    file_switching_consts: Mapping[Path, Sequence[PreviousConst]],
    renamed_consts: Mapping[Path, Sequence[PreviousConst]],
    config: Config,
):
    for path, consts in grouped_consts.items():
        write_consts(
            path,
            consts,
            file_switching_consts.get(path, []),
            renamed_consts.get(path, []),
            config,
        )
