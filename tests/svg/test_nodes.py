from __future__ import annotations

from unittest import TestCase
from unittest import main
from unittest.mock import Mock

from typing import Optional

from svgelements import SVGElement

from pgfgen.svg.nodes import Generator
from pgfgen.svg.nodes import SVGElementChildNode
from pgfgen.svg.nodes import SVGElementContainerNode
from pgfgen.svg.nodes import SVGElementNode


class TestGenerator(TestCase):
    def test_class_is_abstract(self):
        with self.assertRaisesRegex(TypeError, r"abstract method generate"):
            Generator()

    def test_subclassing(self):
        class Subclass(Generator):
            def generate(self, indent: str = "  ") -> list[str]:
                return []

        self.assertEqual([], Subclass().generate())

    def test_indent_without_arg(self):
        self.assertEqual(["  first", "  second"], Generator.indent(["first", "second"]))

    def test_indent_with_arg(self):
        self.assertEqual(
            [">>first", ">>second"], Generator.indent(["first", "second"], ">>")
        )


class TestSVGElementChildNode(TestCase):
    class Node(SVGElementChildNode):
        def __init__(self, parent: Optional[SVGElementChildNode] = None):
            self._parent = parent

        @property
        def parent(self) -> Optional[SVGElementChildNode]:
            return self._parent

    def test_class_is_abstract(self):
        with self.assertRaisesRegex(TypeError, r"abstract method parent"):
            SVGElementChildNode()

    def test_root_without_parent(self):
        element = self.Node()
        self.assertIs(element.root, element)

    def test_root_with_parent(self):
        parent = self.Node()
        element = self.Node(parent)
        self.assertIs(element.root, parent)

    def test_root_with_two_parents(self):
        root = self.Node()
        parent = self.Node(root)
        element = self.Node(parent)
        self.assertIs(element.root, root)


class TestSVGElementContainerNode(TestCase):
    def test_class_is_abstract(self):
        with self.assertRaisesRegex(TypeError, r"abstract method children"):
            SVGElementContainerNode()

    def test_subclassing(self):
        class Node(SVGElementContainerNode):
            @property
            def children(self) -> list[SVGElementNode]:
                return []

        self.assertEqual([], Node().children)


class TestSVGElementNode(TestCase):
    class Node(SVGElementNode):
        def __init__(self, element: SVGElement, parent: Optional[SVGElement] = None):
            self._element = element
            self._parent = parent

        @property
        def element(self) -> SVGElement:
            return self._element

        @property
        def parent(self) -> Optional[SVGElement]:
            return self._parent

        def generate(self, indent: str = " ") -> list[str]:
            return []  # pragma: no cover

    @property
    def element_attributes(self) -> list[tuple[str, str] | str]:
        return [
            "id",
            "xlink:href",
            ("xlink:href", "{http://www.w3.org/1999/xlink}href"),
        ] + self.presentation_attributes

    @property
    def presentation_attributes(self) -> list[tuple[str, str]]:
        return [
            "alignment-baseline",
            "baseline-shift",
            "clip-path",
            "clip-rule",
            "color",
            "color-interpolation",
            "color-interpolation-filters",
            "color-rendering",
            "cursor",
            "direction",
            "display",
            "dominant-baseline",
            "fill",
            "fill-opacity",
            "fill-rule",
            "filter",
            "flood-color",
            "flood-opacity",
            "font-family",
            "font-size",
            "font-size-adjust",
            "font-stretch",
            "font-style",
            "font-variant",
            "font-weight",
            "glyph-orientation-horizontal",
            "glyph-orientation-vertical",
            "image-rendering",
            "letter-spacing",
            "lighting-color",
            "marker-end",
            "marker-mid",
            "marker-start",
            "mask",
            "opacity",
            "overflow",
            "paint-order",
            "pointer-events",
            "shape-rendering",
            "stop-color",
            "stop-opacity",
            "stroke",
            "stroke-dasharray",
            "stroke-dashoffset",
            "stroke-linecap",
            "stroke-linejoin",
            "stroke-miterlimit",
            "stroke-opacity",
            "stroke-width",
            "text-anchor",
            "text-decoration",
            "text-overflow",
            "text-rendering",
            "transform",
            "unicode-bidi",
            "vector-effect",
            "visibility",
            "white-space",
            "word-spacing",
            "writing-mode",
        ]

    def test_class_is_abstract(self):
        with self.assertRaisesRegex(
            TypeError, "abstract methods element, generate, parent"
        ):
            SVGElementNode()

    def test_values(self):
        element = Mock(SVGElement)
        element.values = {"foo": "bar"}
        node = self.Node(element)
        self.assertIs(element.values, node.values)

    def test_attributes(self):
        element = Mock(SVGElement)
        element.values = {"attributes": {"id": "A"}}
        node = self.Node(element)
        self.assertIs(element.values["attributes"], node.attributes)

    def test_default_attributes(self):
        element = Mock(SVGElement)
        element.values = {"x": "X"}
        node = self.Node(element)
        self.assertEqual(dict(), node.attributes)

    def test_id(self):
        element = Mock(SVGElement)
        element.values = {"attributes": {"id": "A"}}
        node = self.Node(element)
        self.assertIs("A", node.id)

    def test_default_id(self):
        element = Mock(SVGElement)
        element.values = {"attributes": {"x": "X"}}
        node = self.Node(element)
        self.assertIsNone(node.id)

    def test_default_id_2(self):
        element = Mock(SVGElement)
        element.values = dict()
        node = self.Node(element)
        self.assertIsNone(node.id)

    def test_tag(self):
        element = Mock(SVGElement)
        element.values = {"tag": "svg"}
        node = self.Node(element)
        self.assertIs("svg", node.tag)

    def test_element_attributes(self):
        element = Mock(SVGElement)
        node = self.Node(element)
        self.assertIsInstance(node.element_attributes, list)
        self.assertTrue(node.element_attributes)  # not empty
        self.assertEqual(self.element_attributes, node.element_attributes)

    def test_generate_attribute_list(self):
        element = Mock(SVGElement)
        element.values = {
            "attributes": {
                "color": "black",
                "fill": "gray",
                "foo": "FOO",
                "{http://www.w3.org/1999/xlink}href": "#A",
            }
        }
        node = self.Node(element)
        self.assertListEqual(
            sorted(["color='black'", "fill='gray'", "xlink:href='#A'"]),
            sorted(node.generate_attribute_list()),
        )

    def test_generate_begin_pgfscope(self):
        element = Mock(SVGElement)
        element.values = {"tag": "svg"}
        node = self.Node(element)
        self.assertEqual(
            [
                r"\begin{pgfscope} % <svg>",
            ],
            node.generate_begin_pgfscope(),
        )

    def test_generate_begin_pgfscope_with_attributes(self):
        element = Mock(SVGElement)
        element.values = {"tag": "svg", "attributes": {"id": "A", "color": "black"}}
        node = self.Node(element)
        self.assertEqual(
            [
                r"\begin{pgfscope} % <svg id='A' color='black'>",
            ],
            node.generate_begin_pgfscope(),
        )


if __name__ == "__main__":
    main()  # pragma: no cover
