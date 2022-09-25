from __future__ import annotations

from typing import Optional, TypedDict
from jinja2 import Environment, FileSystemLoader
import tomli

from .defaults import BLOCK_START_STRING
from .defaults import BLOCK_END_STRING
from .defaults import VARIABLE_START_STRING
from .defaults import VARIABLE_END_STRING
from .defaults import COMMENT_START_STRING
from .defaults import COMMENT_END_STRING
from .defaults import TRIM_BLOCKS
from .defaults import AUTOESCAPE


class EnvironmentFactory:
    def __init__(self, template_path: str|list[str]):
        self.template_path = template_path

    def create_environment(self) -> Environment:
        return Environment(
            block_start_string = BLOCK_START_STRING,
            block_end_string = BLOCK_END_STRING,
            variable_start_string = VARIABLE_START_STRING,
            variable_end_string = VARIABLE_END_STRING,
            comment_start_string = COMMENT_START_STRING,
            comment_end_string = COMMENT_END_STRING,
            trim_blocks = TRIM_BLOCKS,
            autoescape = AUTOESCAPE,
            loader = FileSystemLoader(self.template_path)
        )
