from __future__ import annotations

from unittest import TestCase, main
from pgfgen.exceptions import InvalidPath
from pgfgen.util import split_sanitize_path
from pgfgen.util import find_in_search_path


class TestUtilFunctions(TestCase):
    def test_split_sanitize_path(self):
        self.assertEqual([], split_sanitize_path(""))
        self.assertEqual([], split_sanitize_path("/"))
        self.assertEqual(["foo"], split_sanitize_path("foo"))
        self.assertEqual(["foo"], split_sanitize_path("/foo"))
        self.assertEqual(["foo", "bar"], split_sanitize_path("/foo/bar"))
        self.assertEqual(["foo", "bar"], split_sanitize_path("//foo//bar"))
        self.assertEqual(["foo", "bar"], split_sanitize_path("//foo/././bar"))

        with self.assertRaisesRegex(InvalidPath, "/foo/../bar"):
            split_sanitize_path("/foo/../bar")

    def test_find_in_search_path(self):
        filesystem = {
            "/usr/bin/cat",
            "/usr/bin/firefox",
            "/home/user/.local/bin/firefox",
            "/usr/share/konsole/default.keytab",
        }
        search_path = ["/home/user/.local/bin", "/usr/bin", "/usr/share"]

        def exists(f: str) -> bool:
            return f in filesystem

        result = find_in_search_path(search_path, "firefox", exists)
        self.assertEqual("/home/user/.local/bin/firefox", result)

        result = find_in_search_path(search_path, "cat", exists)
        self.assertEqual("/usr/bin/cat", result)

        result = find_in_search_path(search_path, "konsole/default.keytab", exists)
        self.assertEqual("/usr/share/konsole/default.keytab", result)

        result = find_in_search_path(search_path, "/konsole/default.keytab", exists)
        self.assertEqual("/usr/share/konsole/default.keytab", result)

        result = find_in_search_path(search_path, "inexistent", exists)
        self.assertIsNone(result)


if __name__ == "__main__":
    main()  # pragma: no cover
