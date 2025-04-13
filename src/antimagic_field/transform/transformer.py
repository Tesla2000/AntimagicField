from __future__ import annotations

import libcst as cst

from ..config import Config


class Transformer(cst.CSTTransformer):
    def __init__(self, config: Config):
        super().__init__()
        self.config = config


class Visitor(cst.CSTVisitor):
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
