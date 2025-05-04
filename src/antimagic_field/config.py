from __future__ import annotations

import os
from argparse import Namespace
from pathlib import Path
from typing import Any
from typing import get_origin
from typing import Literal
from typing import Optional
from typing import Type

import toml  # type: ignore
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic import Field
from pydantic_core import PydanticUndefined

from .custom_argument_parser import CustomArgumentParser
from .str_consts.src.antimagic_field import DIRECTORY
from .str_consts.src.antimagic_field import EMPTY
from .str_consts.src.antimagic_field import MOST_COMMON
from .str_consts.src.antimagic_field import UNDERSCORE
from .str_consts.src.antimagic_field.config import ARGS
from .str_consts.src.antimagic_field.config import CONFIG_FILE
from .str_consts.src.antimagic_field.config import DEFAULT_FORMATTED
from .str_consts.src.antimagic_field.config import ENV
from .str_consts.src.antimagic_field.config import FORMATTED
from .str_consts.src.antimagic_field.config import GENERATED_CONSTANTS
from .str_consts.src.antimagic_field.config import POS_ARGS

load_dotenv()


class Config(BaseModel):
    _root: Path = Path(__file__).parent
    pos_args: list[str] = Field(default_factory=list)
    config_file: Optional[Path] = None
    consts_location: Literal["directory", "file", "local"] = DIRECTORY
    consts_location_name: str = GENERATED_CONSTANTS
    modify: bool = True
    include_annotations: bool = False
    const_name_suffix: str = ""
    exclude: str = EMPTY
    root: str = os.getcwd()
    duplicates_solver: Literal["exception", "ignore", "most_common"] = (
        MOST_COMMON
    )
    difficult_string_solver: Literal["exception", "ignore", "ai"] = "ai"
    ai_model: str = "anthropic/claude-3-5-sonnet-20240620"
    allowed_consts: str = r"[\s\S]*"
    ai_solving_batch: int = 30
    max_duplicates_solve_attempts: int = 3
    formatting: Optional[str] = None
    suppress_fail: bool = False
    env_file_path: Path = Path(ENV)

    def __init__(self, /, **data: Any):
        super().__init__(**data)
        if self.formatting and "{filepaths}" not in self.formatting:
            raise ValueError(
                "{filepaths}" + " placeholder must be included in --formatting"
            )
        load_dotenv(self._env_path)

    @property
    def _env_path(self) -> Path:
        if self.env_file_path.is_absolute():
            return self.env_file_path
        return self.root / self.env_file_path

    def is_excluded(self, path: Path) -> bool:
        return bool(self.exclude) and any(
            map(
                path.absolute().is_relative_to,
                map(Path.absolute, map(Path, self.exclude.split(","))),
            )
        )


def parse_arguments(config_class: Type[Config]) -> Namespace:
    parser = CustomArgumentParser(
        description="Configure the application settings."
    )

    for name, value in config_class.model_fields.items():
        if name.startswith(UNDERSCORE):
            continue
        annotation = value.annotation
        if len(args := getattr(annotation, ARGS, [])) > 1:
            annotation = next(filter(None, args))
        if get_origin(value.annotation) == Literal:
            annotation = str
        parser.add_argument(
            FORMATTED.format(name) if name != POS_ARGS else name,
            type=annotation,
            default=value.default,
            help=DEFAULT_FORMATTED.format(value),
        )

    return parser.parse_args()


def create_config_with_args(
    config_class: Type[Config], args: Namespace
) -> Config:
    arg_dict = {
        name: getattr(args, name)
        for name in config_class.model_fields
        if hasattr(args, name) and getattr(args, name) != PydanticUndefined
    }
    if arg_dict.get(CONFIG_FILE) and Path(arg_dict[CONFIG_FILE]).exists():
        config = config_class(
            **{
                **arg_dict,
                **toml.load(arg_dict.get(CONFIG_FILE)),
            }
        )
    else:
        config = config_class(**arg_dict)
    for variable in config.model_fields:
        value = getattr(config, variable)
        if (
            isinstance(value, Path)
            and value.suffix == EMPTY
            and not value.exists()
        ):
            value.mkdir(parents=True)
    return config
