from __future__ import annotations

from typing import Any
from typing import Optional
from typing import Iterable
from typing import Iterator
from typing import TypeGuard

import abc
import contextlib
import tomli

from .types import ValueGuard
from .types import PGFGenOptions


class Guards:
    """Common type-guard functions."""

    @staticmethod
    def is_str_list(value: Any) -> TypeGuard[list[str]]:
        if not isinstance(value, list):
            return False
        return all([isinstance(v, str) for v in value])


class OptionsValidator:
    """A base class for concrete validators."""

    def __init__(self, context: str, log: Optional[list[str]] = None):
        self.context = context
        if log is None:
            log = []
        self.log = log

    def error(self, message: str) -> None:
        full_message = f"error: {self.context} {message}"
        self.log.append(full_message)

    def warning(self, message: str) -> None:
        full_message = f"warning: {self.context} {message}"
        self.log.append(full_message)

    @contextlib.contextmanager
    def nested_key(self, key: str) -> Iterator[OptionsValidator]:
        previous = self.context
        try:
            self.context = f"{self.context}.{key}"
            yield self
        finally:
            self.context = previous

    @contextlib.contextmanager
    def nested_offset(self, offset: int) -> Iterator[OptionsValidator]:
        previous = self.context
        try:
            self.context = f"{self.context}[{offset}]"
            yield self
        finally:
            self.context = previous

    def validate_optional_key(
        self,
        key: str,
        container: dict[Any, Any],
        guard: ValueGuard,
        message: str,
    ) -> bool:
        try:
            value = container[key]
        except KeyError:
            return True
        with self.nested_key(key):
            if not guard(value):
                self.error(message)
                return False
        return True

    def validate_required_key(
        self, key: str, container: dict[Any, Any], guard: ValueGuard, message: str
    ) -> bool:
        with self.nested_key(key):
            try:
                value = container[key]
            except KeyError:
                self.error("is required but it's missing")
                return False
            if not guard(value):
                self.error(message)
                return False
        return True

    def validate_list_item(
        self, offset: int, value: Any, guard: ValueGuard, message: str
    ) -> bool:
        with self.nested_offset(offset):
            if not guard(value):
                self.error(message)
                return False
        return True

    def validate_list_items(
        self, items: Iterable[Any], guard: ValueGuard, message: str
    ) -> bool:
        result = True
        i = 0
        for item in items:
            if not self.validate_list_item(i, item, guard, message):
                result = False
            i += 1
        return result

    @property
    def supported_keys(self) -> list[str]:
        return []

    def validate_no_unsupported_keys(self, options: dict[Any, Any]) -> bool:
        result = True
        for key in options.keys():
            if key not in self.supported_keys:
                with self.nested_key(key):
                    self.warning("is not supported")
                result = False
        return result


class PGFGenOptionsValidator(OptionsValidator):
    """Validator for predefined pgfgen options."""

    def validate_options(self, options: Any) -> TypeGuard[PGFGenOptions]:
        if not isinstance(options, dict):
            self.error("is not a dictionary")
            return False

        result = True
        if not self.validate_search_path(options, "svg_path"):
            result = False
        if not self.validate_search_path(options, "template_path"):
            result = False

        # only for warnings, result is unaltered
        self.validate_no_unsupported_keys(options)

        return result

    def validate_search_path(self, options: dict[Any, Any], key: str) -> bool:
        return self.validate_optional_key(
            key,
            options,
            Guards.is_str_list,
            "is not a valid list of strings",
        )

    @property
    def supported_keys(self) -> list[str]:
        return ["svg_path", "template_path"]


class ConfigLoader(abc.ABC):
    def __init__(self, log: Optional[list[str]] = None):
        if log is None:
            log = []
        self.log = log
        self.has_errors = False

    def try_load_file(self, file: str) -> Optional[PGFGenOptions]:
        try:
            return self.load_file(file)
        except FileNotFoundError:
            return None

    def load_file(self, file: str) -> Optional[PGFGenOptions]:
        with open(file, "rt", encoding="utf-8") as fp:
            return self.load_string(fp.read(), file)

    @abc.abstractmethod
    def load_string(
        self, string: str, file: Optional[str] = None
    ) -> Optional[PGFGenOptions]:
        pass  # pragma: no cover


class TomlConfigLoader(ConfigLoader):
    def __init__(self, context: str = "", log: Optional[list[str]] = None):
        self.context = context
        super().__init__(log)

    def load_string(
        self, string: str, file: Optional[str] = None
    ) -> Optional[PGFGenOptions]:
        self.has_errors = False
        try:
            data = tomli.loads(string)
        except tomli.TOMLDecodeError as e:
            self.has_errors = True
            if file is None:
                self.log.append(f"error: {str(e)}")
            else:
                self.log.append(f"error: {file}: {str(e)}")
            self.has_errors = True
            return None

        conf = data
        if self.context:
            for key in self.context.split(r"."):
                if not isinstance(conf, dict) or key not in conf:
                    return None
                conf = conf[key]

        if file is None:
            context = self.context
        else:
            context = f"{file}: {self.context}"

        validator = PGFGenOptionsValidator(context, self.log)
        if not validator.validate_options(conf):
            self.has_errors = True
            return None
        return conf
