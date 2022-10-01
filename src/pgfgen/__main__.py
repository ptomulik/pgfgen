#!/usr/bin/env python3
from __future__ import annotations

import sys
from .config import TomlConfigLoader
from .exceptions import SvgFileNotFound
from .templating import EnvironmentFactory
from .templating import SvgFileLoader
from .types import PGFGenOptions
from argparse import ArgumentParser
from jinja2.exceptions import TemplateNotFound
from jinja2.loaders import FileSystemLoader
from typing import Optional


class App:
    def __init__(self, config_loader: Optional[TomlConfigLoader] = None):
        self.argument_parser = self.get_argument_parser()
        if config_loader is None:
            config_loader = TomlConfigLoader()
        self.config_loader = config_loader

    def configure_argument_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "template", metavar="FILE", type=str, help="main template file"
        )
        parser.add_argument(
            "--svg-path",
            "-S",
            metavar="DIR",
            type=str,
            action="append",
            help="search path for svg files",
        )
        parser.add_argument(
            "--template-path",
            "-T",
            metavar="DIR",
            type=str,
            action="append",
            help="template search path",
        )
        parser.add_argument(
            "--output", "-o", metavar="FILE", type=str, help="output file"
        )

    def get_argument_parser(self) -> ArgumentParser:
        parser = ArgumentParser(description="Generate LaTeX/PGF code from template.")
        self.configure_argument_parser(parser)
        return parser

    def try_load_config_files(self) -> Optional[PGFGenOptions]:
        lookup = [
            ("pgfgen.toml", ""),
            (".ptfgen.toml", ""),
            ("pyproject.toml", "tool.pgfgen"),
        ]

        for file, context in lookup:
            self.config_loader.context = context
            options = self.config_loader.try_load_file(file)
            if options is not None:
                return options
            if self.config_loader.has_errors:
                return None
        return None

    def run(self) -> int:
        arguments = self.argument_parser.parse_args()
        config = self.try_load_config_files()

        status = 0

        if len(self.config_loader.log) > 0:
            sys.stderr.write("\n".join(self.config_loader.log))
            sys.stderr.write("\n")
            status = 2

        if self.config_loader.has_errors:
            return 1

        env = EnvironmentFactory.create(arguments, config).get_environment()
        try:
            pgf = env.get_template(arguments.template).render()
        except TemplateNotFound as e:
            sys.stderr.write(f"error: {str(e)}: template not found")
            if isinstance(env.loader, FileSystemLoader):
                sys.stderr.write(f" in {repr(env.loader.searchpath)}")
            sys.stderr.write("\n")
            return 1
        except SvgFileNotFound as e:
            sys.stderr.write(f"error: {str(e)}: file not found")
            loader = env.globals.get("loadsvg")
            if isinstance(loader, SvgFileLoader):
                sys.stderr.write(f" in {loader.searchpath}")
            sys.stderr.write("\n")
            return 1

        if arguments.output is None:
            sys.stdout.write(f"{pgf}\n")
        else:
            with open(arguments.output, "w") as output:
                output.write(f"{pgf}\n")

        return status


def main() -> int:
    return App().run()


if __name__ == "__main__":
    main()
