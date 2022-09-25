#!/usr/bin/env python3
from __future__ import annotations

import sys
import os
from argparse import ArgumentParser
from abc import ABC, abstractmethod
from .nodes import \
        Generator, \
        SVG2PGFTransform, \
        SVGBboxProvider, \
        SVGElementContainerNode, \
        SVGElementNode, \
        SVGNode, \
        Bbox
from .templating import EnvironmentFactory
from .config import TomlConfigLoader, SVG2PGFOptions
from typing import Any, Iterator, Optional
from svgelements import SVG
from collections import namedtuple
import xml.etree.ElementTree

class NamedNodes:
    @classmethod
    def _select_nodes(cls, node: SVGElementNode) -> Iterator[SVGElementNode]:
        if node.id is not None:
            yield node
        if isinstance(node, SVGElementContainerNode):
            for child in node.children:
                for n in cls._select_nodes(child):
                    yield n

    def __init__(self, node: SVGElementNode):
        self._nodes = { n.id: n for n in self._select_nodes(node) }

class NamedFragments(NamedNodes):
    def __getitem__(self, key: str) -> Optional[str]:
        node = self._nodes[key]
        return "\n".join(node.generate())

NamedBbox = namedtuple('NamedBbox', ('xmin', 'ymin', 'xmax', 'ymax'))

class PGF:
    def __init__(self, node: SVGElementNode, indent: str = '  '):
        self.node = node
        self.indent = indent
        self.named_fragments = None

    @property
    def code(self) -> str:
        lines = self.node.generate(self.indent)
        string = "\n".join(lines)
        if string:
            string += "\n"
        return string

    @property
    def frags(self) -> NamedFragments:
        if self.named_fragments is None:
            self.named_fragments = NamedFragments(self.node)
        return self.named_fragments

    @property
    def bbox(self) -> Optional[NamedBbox]:
        if isinstance(self.node, SVGBboxProvider):
            bbox = self.node.svg_bbox()
        else:
            bbox = None

        if bbox is not None :
            if isinstance(self.node, SVG2PGFTransform):
                bbox = self.node.svg2pgf_bbox(bbox)
            bbox = NamedBbox(*bbox)
        return bbox



class App:
    def __init__(self, config_loader: Optional[TomlConfigLoader] = None) -> None:
        self.parser = self.create_argument_parser()
        if config_loader is None:
            config_loader = TomlConfigLoader()
        self.config_loader = config_loader

    def configure_argument_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument('input',
            metavar = 'FILE',
            nargs = '?',
            type = str,
            help = 'input file'
        )
        parser.add_argument('--template', '-t',
            metavar = 'FILE',
            type = str,
            help = 'template file'
        )
        parser.add_argument('--template-path', '-I',
            metavar = 'DIR',
            type = str,
            action = 'append',
            help = 'template search path'
        )
        parser.add_argument('--output', '-o',
            metavar = 'FILE',
            type = str,
            help = 'output file'
        )

    def create_argument_parser(self) -> ArgumentParser:
        parser = ArgumentParser(description = 'Covert SVG vector graphics to LaTeX/PGF code.')
        self.configure_argument_parser(parser)
        return parser

    def create_template_variables(self, root: SVGElementNode) -> dict[str,Any]:
        pgf = PGF(root)
        return { 'pgf' : pgf }

    def try_load_config_files(self) -> Optional[SVG2PGFOptions]:
        self.config_loader.context = ''
        options = self.config_loader.try_load_file('svg2pgf.toml')
        if options is not None:
            return options
        options = self.config_loader.try_load_file('.svg2pgf.toml')
        if options is not None:
            return options
        self.config_loader.context = 'tool.svg2pgf'
        return self.config_loader.try_load_file('pyproject.toml')

    def convert(self,
                node: SVGElementNode,
                template_file: Optional[str]=None,
                template_path: Optional[str|list[str]] = None
    ) -> str:
        if template_file is None:
            return "\n".join(node.generate()) + "\n"

        if template_path is None:
            template_path = ['templates']

        env = EnvironmentFactory(template_path).create_environment()
        variables = self.create_template_variables(node)
        template = env.get_template(template_file)
        return template.render(**variables)


    def run(self) -> int:
        arguments = self.parser.parse_args()
        config = self.try_load_config_files()

        if len(self.config_loader.log) > 0:
            sys.stderr.write("\n".join(self.config_loader.log))
            sys.stderr.write("\n")

        if self.config_loader.has_errors:
            return 1

        if arguments.input is None or arguments.input == '-':
            input_file = sys.stdin
        else:
            input_file = arguments.input

        try:
            svg = SVGNode.parse(input_file)
        except xml.etree.ElementTree.ParseError as e:
            sys.stderr.write(f"error: {e.msg}\n")
            return 1

        template_path = arguments.template_path or []
        if config is not None and 'template_path' in config:
            template_path.extend(config['template_path'])

        pgf = self.convert(svg, arguments.template, template_path)
        if arguments.output is None:
            sys.stdout.write(f"{pgf}\n")
        else:
            with open(arguments.output, 'w') as output:
                output.write(f"{pgf}\n")

        return 0

def main() -> int:
    return App().run()


if __name__ == '__main__':
    main()
