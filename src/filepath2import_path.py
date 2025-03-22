from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def filepath2import_path(
    filepath: Path, project_root: Optional[Path | str] = None
) -> str:
    project_root = project_root or os.getcwd()
    return ".".join(
        filepath.absolute().relative_to(project_root).with_suffix("").parts
    )
