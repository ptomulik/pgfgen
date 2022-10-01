"""Provides templating engine based on jinja2"""

from __future__ import annotations

from jinja2 import Environment
from jinja2 import FileSystemLoader

from collections import namedtuple
from argparse import Namespace

from typing import Iterator
from typing import Optional
from typing import final

from .svg.nodes import SVG2PGFTransform
from .svg.nodes import SVGBboxProvider
from .svg.nodes import SVGElementContainerNode
from .svg.nodes import SVGElementNode
from .svg.nodes import SVGNode

from .svg.generator import GeneratorNodeVisitor as SvgToPgfGenerator

from svgelements import Color
from svgelements import Matrix
from svgelements import DEFAULT_PPI

from .defaults import BLOCK_START_STRING
from .defaults import BLOCK_END_STRING
from .defaults import VARIABLE_START_STRING
from .defaults import VARIABLE_END_STRING
from .defaults import COMMENT_START_STRING
from .defaults import COMMENT_END_STRING
from .defaults import TRIM_BLOCKS
from .defaults import AUTOESCAPE
from .defaults import TEMPLATE_PATH
from .defaults import SVG_PATH

from .exceptions import SvgFileNotFound

from .types import SearchPath
from .types import PGFGenOptions
from .types import PGFGenOptionKey
from .types import SupportsAppend

from .util import find_in_search_path


@final
class EnvironmentFactory:
    @staticmethod
    def create(
        arguments: Namespace, options: Optional[PGFGenOptions] = None
    ) -> EnvironmentFactory:
        template_path = EnvironmentFactory._compose_search_paths(
            arguments.template_path, options, "template_path", TEMPLATE_PATH
        )
        svg_path = EnvironmentFactory._compose_search_paths(
            arguments.svg_path, options, "svg_path", SVG_PATH
        )
        return EnvironmentFactory(template_path=template_path, svg_path=svg_path)

    @staticmethod
    def _compose_search_paths(
        searchpath: Optional[SearchPath],
        options: Optional[PGFGenOptions],
        key: PGFGenOptionKey,
        default: SearchPath,
    ) -> SearchPath:
        if options is not None and key in options:
            if searchpath is None:
                searchpath = options[key]
            else:
                searchpath.extend(options[key])
        if searchpath is None:
            searchpath = default
        return searchpath

    def __init__(self, template_path: SearchPath, svg_path: SearchPath):
        self.template_path = template_path
        self.svg_path = svg_path

    def get_environment(self) -> Environment:
        variables = {
            "loadsvg": SvgFileLoader(self.svg_path),
            "svgtopgf": SvgToPgf,
        }
        env = Environment(
            block_start_string=BLOCK_START_STRING,
            block_end_string=BLOCK_END_STRING,
            variable_start_string=VARIABLE_START_STRING,
            variable_end_string=VARIABLE_END_STRING,
            comment_start_string=COMMENT_START_STRING,
            comment_end_string=COMMENT_END_STRING,
            trim_blocks=TRIM_BLOCKS,
            autoescape=AUTOESCAPE,
            loader=FileSystemLoader(self.template_path),
        )
        env.globals.update(variables)
        return env


class SvgFileLoader:
    def __init__(self, searchpath: Optional[SearchPath] = None):
        if searchpath is None:
            searchpath = SVG_PATH
        self.searchpath = searchpath

    def __call__(
        self,
        name: str,
        reify: bool = True,
        ppi: Optional[int] = DEFAULT_PPI,
        width: Optional[int] = None,
        height: Optional[int] = None,
        color: str | Color = "black",
        transform: Optional[str | Matrix] = None,
        context: Optional[SupportsAppend] = None,
        parse_display_none: bool = False,
    ) -> SVGNode:
        file = find_in_search_path(self.searchpath, name)
        if file is None:
            raise SvgFileNotFound(name)
        return SVGNode.parse(
            file,
            reify=reify,
            ppi=ppi,
            width=width,
            height=height,
            color=color,
            transform=transform,
            context=context,
            parse_display_none=parse_display_none,
        )


class SvgNamedFragments:
    def __init__(self, node: SVGElementNode, indent: str = "  "):
        self._nodes = {n.id: n for n in _svg_select_named_nodes(node)}
        self.indent = indent

    def __getitem__(self, key: str) -> str:
        generator = SvgToPgfGenerator(self.indent)
        self._nodes[key].accept_visitor(generator)
        return "\n".join(generator.lines)


def _svg_select_named_nodes(node: SVGElementNode) -> Iterator[SVGElementNode]:
    if node.id is not None:
        yield node
    if isinstance(node, SVGElementContainerNode):
        for child in node.children:
            for n in _svg_select_named_nodes(child):
                yield n


NamedBbox = namedtuple("NamedBbox", ("xmin", "ymin", "xmax", "ymax"))


class SvgToPgf:
    """Provides access to LaTeX/PGF drawing code and metadata generated out of
    a parsed SVG file. Attributes, that may be costly, get lazy-evaluated."""

    def __init__(self, node: SVGElementNode, indent: str = "  "):
        self.node = node
        self.indent = indent
        self.named_fragments: Optional[SvgNamedFragments] = None

    @property
    def code(self) -> str:
        """Whole drawing as LaTeX/PGF code."""
        generator = SvgToPgfGenerator(self.indent)
        self.node.accept_visitor(generator)
        return "\n".join(generator.lines)

    @property
    def frags(self) -> SvgNamedFragments:
        """Parts of drawing resulted from named fragments fo SVG tree."""
        if self.named_fragments is None:
            self.named_fragments = SvgNamedFragments(self.node, self.indent)
        return self.named_fragments

    @property
    def bbox(self) -> Optional[NamedBbox]:
        """Bounding box for the whole drawing."""
        if isinstance(self.node, SVGBboxProvider):
            bbox = self.node.svg_bbox()
        else:
            bbox = None

        if bbox is not None:
            if isinstance(self.node, SVG2PGFTransform):
                bbox = self.node.svg2pgf_bbox(bbox)
            bbox = NamedBbox(*bbox)
        return bbox
