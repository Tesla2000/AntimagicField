from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from typing import get_origin
from typing import Literal
from typing import Optional
from typing import Type

import toml
from dotenv import load_dotenv
from litellm.litellm_core_utils.get_supported_openai_params import (
    get_supported_openai_params,
)
from pydantic import BaseModel
from pydantic import Field
from pydantic_core import PydanticUndefined

from .custom_argument_parser import CustomArgumentParser

load_dotenv()


class Config(BaseModel):
    _root: Path = Path(__file__).parent
    pos_args: list[str] = Field(default_factory=list)
    config_file: Optional[Path] = None
    consts_location: Literal["directory", "file", "local"] = "directory"
    consts_location_name: str = "generated_constants"
    modify: bool = True
    include_annotations: bool = False
    const_name_suffix: str = "_CONST"
    root: str = os.getcwd()
    duplicates_solver: Literal["exception", "ignore", "ai"] = "ignore"
    difficult_string_solver: Literal["exception", "ignore", "ai"] = "ignore"
    ai_model: str = "gpt-4o-mini"
    env_file_path: Path = Path(".env")

    def __init__(self, /, **data: Any):
        super().__init__(**data)
        params = get_supported_openai_params(model=self.ai_model)
        assert (
            "response_format" in params
        ), f"Model must support response format. {self.ai_model} doesn't"
        load_dotenv(self._env_path)

    @property
    def _env_path(self) -> Path:
        if self.env_file_path.is_absolute():
            return self.env_file_path
        return self.root / self.env_file_path


def parse_arguments(config_class: Type[Config]):
    parser = CustomArgumentParser(
        description="Configure the application settings."
    )

    for name, value in config_class.model_fields.items():
        if name.startswith("_"):
            continue
        annotation = value.annotation
        if len(getattr(value.annotation, "__args__", [])) > 1:
            annotation = next(filter(None, value.annotation.__args__))
        if get_origin(value.annotation) == Literal:
            annotation = str
        parser.add_argument(
            f"--{name}" if name != "pos_args" else name,
            type=annotation,
            default=value.default,
            help=f"Default: {value}",
        )

    return parser.parse_args()


def create_config_with_args(config_class: Type[Config], args) -> Config:
    arg_dict = {
        name: getattr(args, name)
        for name in config_class.model_fields
        if hasattr(args, name) and getattr(args, name) != PydanticUndefined
    }
    if arg_dict.get("config_file") and Path(arg_dict["config_file"]).exists():
        config = config_class(
            **{
                **arg_dict,
                **toml.load(arg_dict.get("config_file")),
            }
        )
    else:
        config = config_class(**arg_dict)
    for variable in config.model_fields:
        value = getattr(config, variable)
        if (
            isinstance(value, Path)
            and value.suffix == ""
            and not value.exists()
        ):
            value.mkdir(parents=True)
    return config
