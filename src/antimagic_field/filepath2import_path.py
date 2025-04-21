from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .str_consts.src.antimagic_field import EMPTY
from .str_consts.src.antimagic_field.filepath2import_path import INIT


def filepath2import_path(
    filepath: Path, project_root: Optional[Path | str] = None
) -> str:
    project_root = project_root or os.getcwd()
    return ".".join(
        filepath.absolute().relative_to(project_root).with_suffix(EMPTY).parts
    ).removesuffix(INIT)
