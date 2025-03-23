from __future__ import annotations

from collections.abc import Collection
from typing import Type

from pydantic import BaseModel
from pydantic import create_model
from pydantic import Field

from src.antimagic_field.constants.const import Const


def create_response_format(consts: Collection[Const]) -> Type[BaseModel]:
    return create_model(
        "FieldNames",
        __doc__="Descriptions contain values of constants that the names should be assigned to",
        **{
            f"string{index}": (str, Field(description=const.value))
            for index, const in enumerate(consts, 1)
        },
    )
