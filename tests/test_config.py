from __future__ import annotations

from unittest import main
from unittest import TestCase
from unittest.mock import Mock
from unittest.mock import patch

from typing import Any
from typing import Optional

from pgfgen.config import ConfigLoader
from pgfgen.config import OptionsValidator
from pgfgen.config import PGFGenOptionsValidator
from pgfgen.config import TomlConfigLoader

from pgfgen.types import PGFGenOptions


class TestOptionsValidator(TestCase):
    def test_constructor_with_one_arg(self):
        validator = OptionsValidator("options")
        self.assertIs("options", validator.context)
        self.assertEqual([], validator.log)

    def test_constructor_with_two_args(self):
        log = ["foo", "bar"]
        validator = OptionsValidator("options", log)
        self.assertIs("options", validator.context)
        self.assertIs(log, validator.log)

    def test_error(self):
        validator = OptionsValidator("options", ["error: previous error"])
        validator.error("is not a valid config")
        self.assertIsInstance(validator.log, list)
        self.assertEqual(2, len(validator.log), "the length of validator.log is wrong")
        self.assertEqual(
            ["error: previous error", "error: options is not a valid config"],
            validator.log,
        )

    def test_warning(self):
        validator = OptionsValidator("options", ["error: previous error"])
        validator.error("is not a valid config")
        self.assertIsInstance(validator.log, list)
        self.assertEqual(2, len(validator.log), "the length of validator.log is wrong")
        self.assertEqual(
            ["error: previous error", "error: options is not a valid config"],
            validator.log,
        )

    def test_nested_key(self):
        validator = OptionsValidator("options")
        with validator.nested_key("foo"):
            self.assertEqual("options.foo", validator.context)
        self.assertEqual("options", validator.context)

    def test_nested_offset(self):
        validator = OptionsValidator("options")
        with validator.nested_offset(1):
            self.assertEqual("options[1]", validator.context)
        self.assertEqual("options", validator.context)

    def test_nested_offset_of_nested_key(self):
        validator = OptionsValidator("options")
        with validator.nested_key("foo"):
            self.assertEqual("options.foo", validator.context)
            with validator.nested_offset(2):
                self.assertEqual("options.foo[2]", validator.context)
            self.assertEqual("options.foo", validator.context)
        self.assertEqual("options", validator.context)

    def test_validate_optional_key(self):
        def is_int(x: Any) -> bool:
            return isinstance(x, int)

        validator = OptionsValidator("options")
        options = {"number": 123, "string": "BAR"}
        args = (options, is_int, "is not an integer")

        self.assertTrue(validator.validate_optional_key("number", *args))
        self.assertFalse(validator.log)

        self.assertTrue(validator.validate_optional_key("foo", *args))
        self.assertFalse(validator.log)

        self.assertFalse(validator.validate_optional_key("string", *args))
        self.assertEqual(["error: options.string is not an integer"], validator.log)

    def test_validate_required_key(self):
        def is_int(x: Any) -> bool:
            return isinstance(x, int)

        validator = OptionsValidator("options")
        options = {"number": 123, "string": "BAR"}
        args = (options, is_int, "is not an integer")

        self.assertTrue(validator.validate_required_key("number", *args))
        self.assertFalse(validator.log)

        self.assertFalse(validator.validate_required_key("foo", *args))
        self.assertEqual(
            ["error: options.foo is required but it's missing"], validator.log
        )

        self.assertFalse(validator.validate_required_key("string", *args))
        self.assertEqual(
            [
                "error: options.foo is required but it's missing",
                "error: options.string is not an integer",
            ],
            validator.log,
        )

    def test_validate_list_item(self):
        def is_int(x: Any) -> bool:
            return isinstance(x, int)

        validator = OptionsValidator("options")
        args = (is_int, "is not an integer")

        self.assertTrue(validator.validate_list_item(2, 123, *args))
        self.assertFalse(validator.log)

        self.assertFalse(validator.validate_list_item(3, "A", *args))
        self.assertEqual(["error: options[3] is not an integer"], validator.log)

    def test_validate_list_items(self):
        def is_int(x: Any) -> bool:
            return isinstance(x, int)

        validator = OptionsValidator("options")
        args = (is_int, "is not an integer")

        self.assertTrue(validator.validate_list_items([0, 1, 2], *args))
        self.assertFalse(validator.log)

        self.assertFalse(validator.validate_list_items([0, "A", 1, None], *args))
        self.assertEqual(
            [
                "error: options[1] is not an integer",
                "error: options[3] is not an integer",
            ],
            validator.log,
        )

    def test_supported_keys(self):
        validator = OptionsValidator("options")
        self.assertEqual([], validator.supported_keys)

    def test_validate_no_unsupported_keys(self):
        validator = OptionsValidator("options")
        self.assertTrue(validator.validate_no_unsupported_keys({}))
        self.assertEqual([], validator.log)

        options = {"foo": "FOO", "bar": "BAR"}
        self.assertFalse(validator.validate_no_unsupported_keys(options))
        self.assertEqual(
            [
                "warning: options.foo is not supported",
                "warning: options.bar is not supported",
            ],
            validator.log,
        )


class TestPGFGenOptionsValidator(TestCase):
    def test_validate_search_path(self):
        validator = PGFGenOptionsValidator("options")

        self.assertTrue(validator.validate_search_path({}, "foo_path"))
        self.assertEqual([], validator.log)

        options = {"foo_path": []}
        self.assertTrue(validator.validate_search_path(options, "foo_path"))
        self.assertEqual([], validator.log)

        options = {"foo_path": ["foo", "bar"]}
        self.assertTrue(validator.validate_search_path(options, "foo_path"))
        self.assertEqual([], validator.log)

        options = {"foo_path": "X"}
        self.assertFalse(validator.validate_search_path(options, "foo_path"))
        self.assertEqual(
            ["error: options.foo_path is not a valid list of strings"], validator.log
        )
        validator.log = []

        options = {"foo_path": ["A", 123, None]}
        self.assertFalse(validator.validate_search_path(options, "foo_path"))
        self.assertEqual(
            ["error: options.foo_path is not a valid list of strings"], validator.log
        )

    def test_supported_keys(self):
        validator = PGFGenOptionsValidator("options")
        self.assertEqual(["svg_path", "template_path"], validator.supported_keys)

    def test_validate_no_unsupported_keys(self):
        validator = PGFGenOptionsValidator("options")

        self.assertTrue(validator.validate_no_unsupported_keys({}))
        self.assertEqual([], validator.log)

        options = {"template_path": []}
        self.assertTrue(validator.validate_no_unsupported_keys(options))
        self.assertEqual([], validator.log)

        options = {"svg_path": []}
        self.assertTrue(validator.validate_no_unsupported_keys(options))
        self.assertEqual([], validator.log)

        options = {
            "template_path": [],
            "svg_path": [],
            "foo": "FOO",
            "bar": "BAR",
        }
        validator.log = []
        self.assertFalse(validator.validate_no_unsupported_keys(options))
        self.assertEqual(
            [
                "warning: options.foo is not supported",
                "warning: options.bar is not supported",
            ],
            validator.log,
        )

    def test_validate_options(self):
        validator = PGFGenOptionsValidator("options")

        self.assertTrue(validator.validate_options({}))
        self.assertEqual([], validator.log)

        options = {"template_path": []}
        self.assertTrue(validator.validate_options(options))
        self.assertEqual([], validator.log)

        options = {"svg_path": []}
        self.assertTrue(validator.validate_options(options))
        self.assertEqual([], validator.log)

        options = {"template_path": ["foo", "bar"]}
        self.assertTrue(validator.validate_options(options))
        self.assertEqual([], validator.log)

        options = {"svg_path": ["foo", "bar"]}
        self.assertTrue(validator.validate_options(options))
        self.assertEqual([], validator.log)

        options = {"template_path": [], "svg_path": [], "foo": "FOO"}
        self.assertTrue(validator.validate_options(options))
        self.assertEqual(["warning: options.foo is not supported"], validator.log)
        validator.log = []

        options = {"svg_path": None, "template_path": None}
        self.assertFalse(validator.validate_options(options))
        self.assertEqual(
            [
                "error: options.svg_path is not a valid list of strings",
                "error: options.template_path is not a valid list of strings",
            ],
            validator.log,
        )
        validator.log = []

        self.assertFalse(validator.validate_options("X"))
        self.assertEqual(["error: options is not a dictionary"], validator.log)


class TestConfigLoader(TestCase):
    def test_class_is_abstract(self):
        with self.assertRaisesRegex(TypeError, r"abstract method load_string"):
            ConfigLoader()

    def test_load_file(self):
        class Loader(ConfigLoader):
            def __init__(self):
                self.string = None
                self.file = None

            def load_string(
                self, string: str, file: Optional[str] = None
            ) -> Optional[PGFGenOptions]:
                self.string = string
                self.file = file
                return {"template_path": ["tp"]}

        loader = Loader()

        fp = Mock()
        fp.read = Mock(return_value='template_path = "tp"')
        with patch("pgfgen.config.open") as open_mock:
            open_mock.return_value.__enter__.return_value = fp
            self.assertEqual({"template_path": ["tp"]}, loader.load_file("foo.toml"))
            open_mock.assert_called_once_with("foo.toml", "rt", encoding="utf-8")
        fp.read.assert_called_once()
        self.assertEqual('template_path = "tp"', loader.string)
        self.assertEqual("foo.toml", loader.file)

    def test_load_file_inexistent(self):
        class Loader(ConfigLoader):
            def load_string(
                self, string: str, file: Optional[str] = None
            ) -> Optional[PGFGenOptions]:
                return None  # pragma: no cover

        loader = Loader()
        with self.assertRaises(FileNotFoundError):
            loader.load_file("inexistent-12387f40-41f1-422e-a50f-5061c87d5fb3.missing")

    def test_try_load_file(self):
        class Loader(ConfigLoader):
            def __init__(self):
                self.file = None
                super().__init__()

            def load_file(self, file: str) -> Optional[PGFGenOptions]:
                self.file = file
                return {}

            def load_string(
                self, string: str, file: Optional[str] = None
            ) -> Optional[PGFGenOptions]:
                return None  # pragma: no cover

        loader = Loader()
        self.assertEqual({}, loader.try_load_file("foo.toml"))
        self.assertEqual([], loader.log)
        self.assertFalse(loader.has_errors)
        self.assertEqual("foo.toml", loader.file)

    def test_try_load_file_with_file_not_found_error(self):
        class Loader(ConfigLoader):
            def __init__(self):
                super().__init__()
                self.file = None

            def load_file(self, file: str) -> Optional[PGFGenOptions]:
                self.file = file
                raise FileNotFoundError

            def load_string(
                self, string: str, file: Optional[str] = None
            ) -> Optional[PGFGenOptions]:
                return None  # pragma: no cover

        loader = Loader()
        self.assertEqual(None, loader.try_load_file("foo.toml"))
        self.assertEqual([], loader.log)
        self.assertFalse(loader.has_errors)
        self.assertEqual("foo.toml", loader.file)


class TestTomlConfigLoader(TestCase):
    def test_constructor(self):
        loader = TomlConfigLoader()
        self.assertEqual("", loader.context)
        self.assertEqual([], loader.log)
        self.assertFalse(loader.has_errors)

        loader = TomlConfigLoader("foo.bar")
        self.assertEqual("foo.bar", loader.context)
        self.assertEqual([], loader.log)
        self.assertFalse(loader.has_errors)

        log = ["error: foo"]
        loader = TomlConfigLoader("foo.bar", log)
        self.assertEqual("foo.bar", loader.context)
        self.assertIs(log, loader.log)
        self.assertFalse(loader.has_errors)

    def test_load_string_with_syntax_error(self):
        loader = TomlConfigLoader()
        self.assertIsNone(loader.load_string("*^$*#"))
        self.assertTrue(loader.has_errors)
        self.assertEqual(["error: Invalid statement (at line 1, column 1)"], loader.log)

        loader = TomlConfigLoader()
        self.assertIsNone(loader.load_string("*^$*#", "foo.toml"))
        self.assertTrue(loader.has_errors)
        self.assertEqual(
            ["error: foo.toml: Invalid statement (at line 1, column 1)"], loader.log
        )

    def test_load_string_with_inexistent_context(self):
        loader = TomlConfigLoader("the.context")
        self.assertIsNone(loader.load_string('foo = "bar"'))
        self.assertFalse(loader.has_errors)
        self.assertEqual([], loader.log)

        loader = TomlConfigLoader("the.context")
        self.assertIsNone(
            loader.load_string(
                """
            [the]
            foo = "bar"
            """
            )
        )
        self.assertFalse(loader.has_errors)
        self.assertEqual([], loader.log)

    def test_load_string_with_invalid_value(self):
        loader = TomlConfigLoader("the.context")
        self.assertIsNone(
            loader.load_string(
                """
            [the.context]
            template_path = "should be a list"
            """
            )
        )
        self.assertTrue(loader.has_errors)
        self.assertEqual(
            ["error: the.context.template_path is not a valid list of strings"],
            loader.log,
        )

        loader = TomlConfigLoader("the.context")
        self.assertIsNone(
            loader.load_string(
                """
            [the.context]
            template_path = "should be a list"
            """,
                "foo.toml",
            )
        )
        self.assertTrue(loader.has_errors)
        self.assertEqual(
            [
                "error: foo.toml: the.context.template_path is not a valid"
                " list of strings"
            ],
            loader.log,
        )

    def test_load_string_with_valid_config(self):
        loader = TomlConfigLoader("the.context")

        self.assertEqual(
            {"template_path": ["a", "b"]},
            loader.load_string(
                """
            [the.context]
            template_path = ["a", "b"]
            """
            ),
        )
        self.assertFalse(loader.has_errors)
        self.assertEqual([], loader.log)

    def test_load_string_with_unsupported_option(self):
        loader = TomlConfigLoader("the.context")
        self.assertEqual(
            {
                "template_path": ["a", "b"],
                "foo": "FOO",
            },
            loader.load_string(
                """
            [the.context]
            template_path = ["a", "b"]
            foo = "FOO"
            """
            ),
        )
        self.assertFalse(loader.has_errors)
        self.assertEqual(["warning: the.context.foo is not supported"], loader.log)

        loader = TomlConfigLoader("the.context")
        self.assertEqual(
            {
                "template_path": ["a", "b"],
                "foo": "FOO",
            },
            loader.load_string(
                """
            [the.context]
            template_path = ["a", "b"]
            foo = "FOO"
            """,
                "foo.toml",
            ),
        )
        self.assertFalse(loader.has_errors)
        self.assertEqual(
            ["warning: foo.toml: the.context.foo is not supported"], loader.log
        )


if __name__ == "__main__":
    main()  # pragma: no cover
