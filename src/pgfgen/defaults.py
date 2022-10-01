"""Provides defaults to other modules"""

from __future__ import annotations

BLOCK_START_STRING = r"(@"
BLOCK_END_STRING = r"@)"
VARIABLE_START_STRING = r"(("
VARIABLE_END_STRING = r"))"
COMMENT_START_STRING = r"(#"
COMMENT_END_STRING = r"#)"
TRIM_BLOCKS = True
AUTOESCAPE = False
TEMPLATE_PATH = ["."]
SVG_PATH = TEMPLATE_PATH
