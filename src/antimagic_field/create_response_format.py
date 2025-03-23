from __future__ import annotations

from collections.abc import Collection
from typing import Type

from pydantic import BaseModel
from pydantic import create_model

from src.antimagic_field.constants.const import Const


def create_response_format(consts: Collection[Const]) -> Type[BaseModel]:
    return create_model(
        "FieldNames", **{const.value: (str, ...) for const in consts}
    )
