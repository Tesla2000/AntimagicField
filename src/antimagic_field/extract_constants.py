from __future__ import annotations

from collections.abc import Sequence
from functools import partial
from pathlib import Path

from libcst import Module

from .config import Config
from .transform.magic_seeker import MagicSeeker
from src.antimagic_field.constants.const import Const


def extract_constants(
    filepath: Path, module: Module, config: Config
) -> Sequence[Const]:
    magical_strings = MagicSeeker.get_magical_strings(module, config)
    return tuple(
        map(partial(Const, origin_filepath=filepath), magical_strings)
    )
