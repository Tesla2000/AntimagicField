from __future__ import annotations

from collections.abc import Sequence
from functools import partial
from pathlib import Path

from libcst import Module

from .config import Config
from .constants.const import Const
from .transform.magic_seeker import MagicSeeker


def extract_constants(
    filepath: Path, module: Module, config: Config
) -> Sequence[Const]:
    magical_strings = MagicSeeker.get_magical_strings(module, config)
    return tuple(
        map(partial(Const, origin_filepath=filepath), magical_strings)
    )
