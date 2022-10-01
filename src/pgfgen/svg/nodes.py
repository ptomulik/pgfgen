from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from math import sqrt

from typing import Dict
from typing import Literal
from typing import Optional
from typing import TextIO
from typing import TypedDict
from typing import final

from svgelements import Arc
from svgelements import Circle
from svgelements import Close
from svgelements import Color
from svgelements import CubicBezier
from svgelements import DEFAULT_PPI
from svgelements import Ellipse
from svgelements import GraphicObject
from svgelements import Group
from svgelements import Line
from svgelements import Matrix
from svgelements import Move
from svgelements import Path
from svgelements import PathSegment
from svgelements import Point
from svgelements import Polygon
from svgelements import Polyline
from svgelements import QuadraticBezier
from svgelements import Rect
from svgelements import SVG
from svgelements import SVGElement
from svgelements import Shape
from svgelements import SimpleLine
from svgelements import Use

from svgelements.svgelements import _Polyshape

from ..types import SupportsAppend
from ..types import BboxTuple

from .visitor import NodeVisitor
from .visitor import NodeVisitee

import re


# only for typing
SVGElementAttributes = Dict[str, str]

# only for typing
SVGSource = str | TextIO


NotRequiredSVGElementValues = TypedDict(
    "NotRequiredSVGElementValues",
    {
        "alignment-baseline": Optional[str],
        "attributes": Optional[SVGElementAttributes],
        "baseline-shift": Optional[str],
        "clip-path": Optional[str],
        "clip-rule": Optional[str],
        "color": Optional[str],
        "color-interpolation": Optional[str],
        "color-interpolation-filters": Optional[str],
        "color-rendering": Optional[str],
        "cursor": Optional[str],
        "direction": Optional[str],
        "display": Optional[str],
        "dominant-baseline": Optional[str],
        "fill": Optional[str],
        "fill-opacity": Optional[str],
        "fill-rule": Optional[str],
        "filter": Optional[str],
        "flood-color": Optional[str],
        "flood-opacity": Optional[str],
        "font-family": Optional[str],
        "font-size": Optional[str],
        "font-size-adjust": Optional[str],
        "font-stretch": Optional[str],
        "font-style": Optional[str],
        "font-variant": Optional[str],
        "font-weight": Optional[str],
        "glyph-orientation-horizontal": Optional[str],
        "glyph-orientation-vertical": Optional[str],
        "image-rendering": Optional[str],
        "letter-spacing": Optional[str],
        "lighting-color": Optional[str],
        "marker-end": Optional[str],
        "marker-mid": Optional[str],
        "marker-start": Optional[str],
        "mask": Optional[str],
        "opacity": Optional[str],
        "overflow": Optional[str],
        "paint-order": Optional[str],
        "pointer-events": Optional[str],
        "shape-rendering": Optional[str],
        "stop-color": Optional[str],
        "stop-opacity": Optional[str],
        "stroke": Optional[str],
        "stroke-dasharray": Optional[str],
        "stroke-dashoffset": Optional[str],
        "stroke-linecap": Optional[str],
        "stroke-linejoin": Optional[str],
        "stroke-miterlimit": Optional[str],
        "stroke-opacity": Optional[str],
        "stroke-width": Optional[str],
        "text-anchor": Optional[str],
        "text-decoration": Optional[str],
        "text-overflow": Optional[str],
        "text-rendering": Optional[str],
        "transform": Optional[str],
        "unicode-bidi": Optional[str],
        "vector-effect": Optional[str],
        "visibility": Optional[str],
        "white-space": Optional[str],
        "word-spacing": Optional[str],
        "writing-mode": Optional[str],
    },
    total=False,
)


class SVGElementValues(NotRequiredSVGElementValues):
    tag: str


class SVGElementChildNode(ABC):
    @property
    @abstractmethod
    def parent(self) -> Optional[SVGElementNode]:
        pass  # pragma: no cover

    @property
    def root(self) -> SVGElementChildNode:
        if self.parent is None:
            return self
        return self.parent.root


class SVGElementContainerNode(ABC):
    @property
    @abstractmethod
    def children(self) -> list[SVGElementNode]:
        pass  # pragma: no cover


class SVGElementNode(NodeVisitee, SVGElementChildNode):
    @property
    @abstractmethod
    def element(self) -> SVGElement:
        pass  # pragma: no cover

    @property
    def values(self) -> SVGElementValues:
        values: SVGElementValues = self.element.values
        return values

    @property
    def attributes(self) -> SVGElementAttributes:
        attributes: Optional[SVGElementAttributes] = self.values.get("attributes")
        return attributes or dict()

    @property
    def id(self) -> Optional[str]:
        return self.attributes.get("id")

    @property
    def tag(self) -> str:
        return self.values["tag"]

    @property
    def element_attributes(self) -> list[str | tuple[str, str]]:
        structural_attributes: list[str | tuple[str, str]] = [
            "id",
            "xlink:href",
            ("xlink:href", "{http://www.w3.org/1999/xlink}href"),
        ]
        return structural_attributes + self.presentation_attributes

    @property
    def presentation_attributes(self) -> list[str | tuple[str, str]]:
        """Returns presentation attributes supported by the element"""
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


@final
class UnsupportedSVGElementNode(SVGElementNode):
    def __init__(
        self, element: SVGElement, parent_element_node: Optional[SVGElementNode] = None
    ) -> None:
        self._element = element
        self.parent_element_node = parent_element_node

    @property
    def element(self) -> SVGElement:
        return self._element

    @property
    def parent(self) -> Optional[SVGElementNode]:
        return self.parent_element_node

    def accept_visitor(self, visitor: NodeVisitor) -> None:
        visitor.visit_unsupported_svg_element(self)


class SVGElementNodeWrapper(SVGElementNode):
    @property
    @abstractmethod
    def wrapped(self) -> SVGElementNode:
        pass  # pragma: no cover

    @property
    def element(self) -> SVGElement:
        return self.wrapped.element

    @property
    def parent(self) -> Optional[SVGElementNode]:
        return self.wrapped.parent

    @property
    def root(self) -> SVGElementChildNode:
        return self.wrapped.root

    @property
    def values(self) -> SVGElementValues:
        return self.wrapped.values

    @property
    def tag(self) -> str:
        return self.wrapped.tag

    def accept_visitor(self, visitor: NodeVisitor) -> None:
        self.wrapped.accept_visitor(visitor)


@final
class SVGElementNodeFactory:
    def __init__(
        self,
        parent_element_node: Optional[SVGElementNode] = None,
        shape_node_factory: Optional[ShapeNodeFactory] = None,
    ):
        self.parent_element_node = parent_element_node
        if shape_node_factory is None:
            shape_node_factory = ShapeNodeFactory(parent_element_node)
        self.shape_node_factory = shape_node_factory

    def create_node(self, element: SVGElement) -> SVGElementNode:
        if isinstance(element, Shape):
            return self.shape_node_factory.create_node(element)
        elif isinstance(element, SVG):
            return SVGNode(element, self.parent_element_node)
        elif isinstance(element, Group):
            return GroupNode(element, self.parent_element_node)
        elif isinstance(element, Use):
            return UseNode(element, self.parent_element_node)
        elif isinstance(element, SVGElement) and element.values["tag"] == "symbol":
            return SymbolNode(element, self.parent_element_node)
        else:
            return UnsupportedSVGElementNode(element, self.parent_element_node)


@final
class ShapeNodeFactory:
    def __init__(self, parent_element_node: Optional[SVGElementNode] = None):
        self.parent_element_node = parent_element_node

    def create_node(self, shape: Shape) -> ShapeNode:
        if isinstance(shape, Circle):
            return CircleNode(shape, self.parent_element_node)
        elif isinstance(shape, Ellipse):
            return EllipseNode(shape, self.parent_element_node)
        elif isinstance(shape, Rect):
            return RectNode(shape, self.parent_element_node)
        elif isinstance(shape, Path):
            return PathNode(shape, self.parent_element_node)
        elif isinstance(shape, SimpleLine):
            return SimpleLineNode(shape, self.parent_element_node)
        elif isinstance(shape, Polyline):
            return PolylineNode(shape, self.parent_element_node)
        elif isinstance(shape, Polygon):
            return PolygonNode(shape, self.parent_element_node)
        else:
            return UnsupportedShapeNode(shape, self.parent_element_node)


class SVGBboxProvider:
    @abstractmethod
    def svg_bbox(self) -> BboxTuple:
        pass


class SVG2PGFTransform(SVGBboxProvider):
    def __init__(self) -> None:
        self._svg2pgf_transform: Optional[Matrix] = None

    def _determine_pgf_bbox(self, bbox: BboxTuple) -> BboxTuple:
        (xmin, ymin, xmax, ymax) = bbox
        w = xmax - xmin
        h = ymax - ymin
        if h < w:
            return (-1.0, -h / w, 1.0, h / w)
        elif w < h:
            return (-w / h, -1.0, w / h, 1.0)
        else:
            return (-1.0, -1.0, 1.0, 1.0)

    @staticmethod
    def _bbox_center(bbox: BboxTuple) -> Point:
        (xmin, ymin, xmax, ymax) = bbox
        return Point((xmin + xmax) / 2.0, (ymin + ymax) / 2.0)

    @staticmethod
    def _bbox_size(bbox: BboxTuple) -> Point:
        (xmin, ymin, xmax, ymax) = bbox
        return Point(abs(xmax - xmin), abs(ymax - ymin))

    def _determine_pgf_scale(self, bbox: BboxTuple) -> Point:
        svg = self._bbox_size(bbox)
        pgf = self._bbox_size(self._determine_pgf_bbox(bbox))
        if svg.x == 0.0 and svg.y == 0.0:
            s = 1.0
        elif svg.x > svg.y:
            s = pgf.x / svg.x
        else:
            s = pgf.y / svg.y
        return Point(s, -s)

    def _determine_svg2pgf_transform(self) -> Matrix:
        """A matrix that transforms from SVG to PGF coordinate system"""
        bbox = self.svg_bbox()
        svg_c = self._bbox_center(bbox)
        pgf_c = self._bbox_center(self._determine_pgf_bbox(bbox))
        s = self._determine_pgf_scale(bbox)
        matrix = Matrix.translate(-svg_c.x, -svg_c.y)
        matrix.post_scale(s.x, s.y)
        matrix.post_translate(pgf_c.x, pgf_c.y)
        return matrix

    @property
    def svg2pgf_transform(self) -> Matrix:
        if self._svg2pgf_transform is None:
            self._svg2pgf_transform = self._determine_svg2pgf_transform()
        return self._svg2pgf_transform

    def svg2pgf_point(self, point: Point) -> Point:
        svg2pgf = self.svg2pgf_transform
        point = svg2pgf.point_in_matrix_space(point)
        return point

    def svg2pgf_vector(self, vector: Point) -> Point:
        svg2pgf = self.svg2pgf_transform.vector()
        vector = svg2pgf.point_in_matrix_space(vector)
        return vector

    def svg2pgf_matrix(self, matrix: Matrix) -> Matrix:
        svg2pgf = self.svg2pgf_transform
        matrix = ~svg2pgf * matrix * svg2pgf
        return matrix

    def svg2pgf_bbox(self, bbox: BboxTuple) -> BboxTuple:
        svg2pgf = self.svg2pgf_transform
        bb = (Point(bbox[0], bbox[1]), Point(bbox[2], bbox[3]))
        bb = (svg2pgf.transform_point(bb[0]), svg2pgf.transform_point(bb[1]))
        xmin = min(bb[0].x, bb[1].x)
        ymin = min(bb[0].y, bb[1].y)
        xmax = max(bb[0].x, bb[1].x)
        ymax = max(bb[0].y, bb[1].y)
        return (xmin, ymin, xmax, ymax)


class GraphicObjectNode:
    @property
    @abstractmethod
    def graphic_object(self) -> GraphicObject:
        pass

    @property
    def fill(self) -> Optional[Color]:
        return self.graphic_object.fill

    @property
    def stroke(self) -> Optional[Color]:
        return self.graphic_object.stroke

    @property
    def stroke_width(self) -> Optional[float]:
        width: Optional[float] = self.graphic_object.stroke_width
        return width

    @property
    def implicit_stroke_width(self) -> Optional[float]:
        width: Optional[float] = self.graphic_object.implicit_stroke_width
        return width

    @property
    def stroke_dasharray(self) -> Optional[list[float] | Literal["none"]]:
        # svgelements does not implement `stroke_dasharray' property
        if not isinstance(self.graphic_object, SVGElement):
            return None
        string: Optional[str] = self.graphic_object.values.get("stroke-dasharray")
        if string is None:
            return None
        if string.lower() == "none":
            return "none"
        dasharray = [float(x) for x in re.split("(?: *(?:,| ) *)", string)]
        return list(dasharray)

    @property
    def stroke_dashoffset(self) -> Optional[float]:
        # svgelements does not implement `stroke_dashoffset' property
        if not isinstance(self.graphic_object, SVGElement):
            return None
        string: str | None = self.graphic_object.values.get("stroke-dashoffset")
        if string is None:
            return None
        return float(string)

    @property
    def implicit_stroke_dasharray(self) -> Optional[list[float] | Literal["none"]]:
        # svgelements does not implement `implicit_stroke_dasharray' property
        dasharray = self.stroke_dasharray
        if dasharray is None or isinstance(dasharray, str):
            return dasharray
        if isinstance(self.graphic_object, SVGElement):
            # reified Paths have reset transform, so we obtain it from values
            # again
            transform: Optional[str] = self.graphic_object.values.get("transform")
            if transform is not None:
                matrix = Matrix(transform)
                scale = sqrt(abs(matrix.determinant))
                dasharray = list([scale * x for x in dasharray])
        return dasharray

    @property
    def implicit_stroke_dashoffset(self) -> Optional[float]:
        # svgelements does not implement `implicit_stroke_dashoffset' property
        dashoffset = self.stroke_dashoffset
        if dashoffset is None:
            return None
        if isinstance(self.graphic_object, SVGElement):
            # reified Paths have reset transform matrix, so we obtain it from
            # values again
            transform: Optional[str] = self.graphic_object.values.get("transform")
            if transform is not None:
                matrix = Matrix(transform)
                scale = sqrt(abs(matrix.determinant))
                dashoffset = scale * dashoffset
        return dashoffset


class GraphicObjectNodeWrapper(GraphicObjectNode):
    @property
    @abstractmethod
    def wrapped(self) -> GraphicObjectNode:
        pass

    @property
    def graphic_object(self) -> GraphicObject:
        return self.wrapped.graphic_object

    @property
    def fill(self) -> Optional[Color]:
        return self.wrapped.fill

    @property
    def stroke(self) -> Optional[Color]:
        return self.wrapped.stroke

    @property
    def stroke_width(self) -> Optional[float]:
        return self.wrapped.stroke_width

    @property
    def implicit_stroke_width(self) -> Optional[float]:
        return self.wrapped.implicit_stroke_width

    @property
    def stroke_dasharray(self) -> Optional[list[float] | Literal["none"]]:
        return self.wrapped.stroke_dasharray

    @property
    def stroke_dashoffset(self) -> Optional[float]:
        return self.wrapped.stroke_dashoffset

    @property
    def implicit_stroke_dasharray(self) -> Optional[list[float] | Literal["none"]]:
        return self.wrapped.implicit_stroke_dasharray

    @property
    def implicit_stroke_dashoffset(self) -> Optional[float]:
        return self.wrapped.implicit_stroke_dashoffset


class ShapeNode(SVGElementNode, GraphicObjectNode, SVG2PGFTransform):
    def __init__(self) -> None:
        SVG2PGFTransform.__init__(self)

    @property
    @abstractmethod
    def shape(self) -> Shape:
        pass

    @property
    def graphic_object(self) -> GraphicObject:
        return self.shape

    @property
    def element(self) -> SVGElement:
        return self.shape

    def svg_bbox(self) -> BboxTuple:
        bb: BboxTuple = self.shape.bbox()
        return bb


@final
class PathNode(ShapeNode):
    def __init__(
        self, path: Path, parent_element_node: Optional[SVGElementNode] = None
    ):
        ShapeNode.__init__(self)
        self.path = path
        self.parent_element_node = parent_element_node
        factory = PathSegmentNodeFactory(self)
        self.children_path_segment_nodes = list(
            [factory.create_node(e) for e in self.path]
        )

    @property
    def shape(self) -> Path:
        return self.path

    @property
    def parent(self) -> Optional[SVGElementNode]:
        return self.parent_element_node

    def accept_visitor(self, node: NodeVisitor) -> None:
        node.visit_path(self)


@final
class PathSegmentNodeFactory:
    def __init__(self, parent_path_node: Optional[PathNode] = None) -> None:
        self.parent_path_node = parent_path_node

    def create_node(self, segment: PathSegment) -> PathSegmentNode:
        if isinstance(segment, Close):
            return CloseNode(segment, self.parent_path_node)
        elif isinstance(segment, Move):
            return MoveNode(segment, self.parent_path_node)
        elif isinstance(segment, Line):
            return LineNode(segment, self.parent_path_node)
        elif isinstance(segment, CubicBezier):
            return CubicBezierNode(segment, self.parent_path_node)
        elif isinstance(segment, QuadraticBezier):
            return QuadraticBezierNode(segment, self.parent_path_node)
        elif isinstance(segment, Arc):
            return ArcNode(segment, self.parent_path_node)
        else:
            return UnsupportedPathSegmentNode(segment)


class PathSegmentNode(NodeVisitee, SVGElementChildNode, SVG2PGFTransform):
    def __init__(self, parent_path_node: Optional[PathNode] = None) -> None:
        SVG2PGFTransform.__init__(self)
        self.parent_path_node = parent_path_node

    @property
    @abstractmethod
    def segment(self) -> PathSegment:
        pass

    @property
    def parent(self) -> Optional[PathNode]:
        return self.parent_path_node

    def svg_bbox(self) -> BboxTuple:
        bb: BboxTuple = self.segment.bbox()
        return bb


class PathSegmentNodeWrapper(PathSegmentNode):
    @property
    @abstractmethod
    def wrapped(self) -> PathSegmentNode:
        pass

    @property
    def parent(self) -> Optional[PathNode]:
        return self.wrapped.parent

    @property
    def segment(self) -> PathSegment:
        return self.wrapped.segment

    @property
    def svg_bbox(self) -> BboxTuple:
        return self.wrapped.svg_bbox()

    def accept_visitor(self, visitor: NodeVisitor) -> None:
        self.wrapped.accept_visitor(visitor)


@final
class UnsupportedShapeNode(ShapeNode):
    def __init__(
        self, shape: Shape, parent_element_node: Optional[SVGElementNode] = None
    ) -> None:
        ShapeNode.__init__(self)
        self._shape = shape
        self.parent_element_node = parent_element_node

    @property
    def shape(self) -> Shape:
        return self._shape

    @property
    def parent(self) -> Optional[SVGElementNode]:
        return self.parent_element_node

    def accept_visitor(self, visitor: NodeVisitor) -> None:
        visitor.visit_unsupported_shape(self)


@final
class UnsupportedPathSegmentNode(PathSegmentNode):
    def __init__(
        self, path_segment: PathSegment, parent_path_node: Optional[PathNode] = None
    ) -> None:
        super().__init__(parent_path_node)
        self.path_segment = path_segment

    @property
    def segment(self) -> PathSegment:
        return self.path_segment

    def accept_visitor(self, visitor: NodeVisitor) -> None:
        visitor.visit_unsupported_path_semgment(self)


@final
class CloseNode(PathSegmentNode):
    def __init__(
        self, close: Close, parent_path_node: Optional[PathNode] = None
    ) -> None:
        super().__init__(parent_path_node)
        self.close = close

    @property
    def segment(self) -> Close:
        return self.close

    def accept_visitor(self, visitor: NodeVisitor) -> None:
        visitor.visit_close(self)


@final
class MoveNode(PathSegmentNode):
    def __init__(self, move: Move, parent_path_node: Optional[PathNode] = None) -> None:
        super().__init__(parent_path_node)
        self.move = move

    @property
    def segment(self) -> Move:
        return self.move

    def accept_visitor(self, visitor: NodeVisitor) -> None:
        visitor.visit_move(self)


@final
class LineNode(PathSegmentNode):
    def __init__(self, line: Line, parent_path_node: Optional[PathNode] = None) -> None:
        super().__init__(parent_path_node)
        self.line = line

    @property
    def segment(self) -> Line:
        return self.line

    def accept_visitor(self, visitor: NodeVisitor) -> None:
        visitor.visit_line(self)


@final
class CubicBezierNode(PathSegmentNode):
    def __init__(
        self, cubic_bezier: CubicBezier, parent_path_node: Optional[PathNode] = None
    ) -> None:
        super().__init__(parent_path_node)
        self.cubic_bezier = cubic_bezier

    @property
    def segment(self) -> CubicBezier:
        return self.cubic_bezier

    def accept_visitor(self, visitor: NodeVisitor) -> None:
        visitor.visit_cubic_bezier(self)


@final
class QuadraticBezierNode(PathSegmentNode):
    def __init__(
        self,
        quadratic_bezier: QuadraticBezier,
        parent_path_node: Optional[PathNode] = None,
    ) -> None:
        super().__init__(parent_path_node)
        self.quadratic_bezier = quadratic_bezier

    @property
    def segment(self) -> QuadraticBezier:
        return self.quadratic_bezier

    def accept_visitor(self, visitor: NodeVisitor) -> None:
        visitor.visit_quadratic_bezier(self)


@final
class ArcNode(PathSegmentNode):
    def __init__(self, arc: Arc, parent_path_node: Optional[PathNode] = None) -> None:
        super().__init__(parent_path_node)
        self.arc = arc

    @property
    def segment(self) -> Arc:
        return self.arc

    def accept_visitor(self, visitor: NodeVisitor) -> None:
        visitor.visit_arc(self)


@final
class CircleNode(ShapeNode):
    def __init__(
        self, circle: Circle, parent_element_node: Optional[SVGElementNode] = None
    ) -> None:
        ShapeNode.__init__(self)
        self.circle = circle
        self.parent_element_node = parent_element_node

    @property
    def shape(self) -> Circle:
        return self.circle

    @property
    def parent(self) -> Optional[SVGElementNode]:
        return self.parent_element_node

    @property
    def presentation_attributes(self) -> list[str | tuple[str, str]]:
        return super().presentation_attributes + ["cx", "cy" "r"]

    def accept_visitor(self, visitor: NodeVisitor) -> None:
        visitor.visit_circle(self)


@final
class EllipseNode(ShapeNode):
    def __init__(
        self, ellipse: Ellipse, parent_element_node: Optional[SVGElementNode] = None
    ) -> None:
        ShapeNode.__init__(self)
        self.ellipse = ellipse
        self.parent_element_node = parent_element_node

    @property
    def shape(self) -> Ellipse:
        return self.ellipse

    @property
    def parent(self) -> Optional[SVGElementNode]:
        return self.parent_element_node

    @property
    def presentation_attributes(self) -> list[str | tuple[str, str]]:
        return super().presentation_attributes + ["cx", "cy", "rx", "ry"]

    def accept_visitor(self, visitor: NodeVisitor) -> None:
        visitor.visit_ellipse(self)


@final
class RectNode(ShapeNode):
    def __init__(
        self, rect: Rect, parent_element_node: Optional[SVGElementNode] = None
    ) -> None:
        ShapeNode.__init__(self)
        self.rect = rect
        self.parent_element_node = parent_element_node

    @property
    def shape(self) -> Rect:
        return self.rect

    @property
    def parent(self) -> Optional[SVGElementNode]:
        return self.parent_element_node

    @property
    def presentation_attributes(self) -> list[str | tuple[str, str]]:
        return super().presentation_attributes + [
            "height",
            "width",
            "x",
            "y",
            "rx",
            "ry",
        ]

    def accept_visitor(self, visitor: NodeVisitor) -> None:
        visitor.visit_rect(self)


@final
class SimpleLineNode(ShapeNode):
    def __init__(
        self,
        simple_line: SimpleLine,
        parent_element_node: Optional[SVGElementNode] = None,
    ) -> None:
        ShapeNode.__init__(self)
        self.simple_line = simple_line
        self.parent_element_node = parent_element_node

    @property
    def shape(self) -> SimpleLine:
        return self.simple_line

    @property
    def parent(self) -> Optional[SVGElementNode]:
        return self.parent_element_node

    def accept_visitor(self, visitor: NodeVisitor) -> None:
        visitor.visit_simpleline(self)


class _PolyshapeNode(ShapeNode):
    def __init__(
        self,
        polyshape: _Polyshape,
        parent_element_node: Optional[SVGElementNode] = None,
    ) -> None:
        ShapeNode.__init__(self)
        self.polyshape = polyshape
        self.parent_element_node = parent_element_node

    @property
    def parent(self) -> Optional[SVGElementNode]:
        return self.parent_element_node

    @property
    def shape(self) -> _Polyshape:
        return self.polyshape

    @property
    @abstractmethod
    def is_closed(self) -> bool:
        pass


@final
class PolylineNode(_PolyshapeNode):
    @property
    def is_closed(self) -> bool:
        return False

    def accept_visitor(self, visitor: NodeVisitor) -> None:
        visitor.visit_polyline(self)


@final
class PolygonNode(_PolyshapeNode):
    @property
    def is_closed(self) -> bool:
        return True

    def accept_visitor(self, visitor: NodeVisitor) -> None:
        visitor.visit_polygon(self)


class GroupNode(SVGElementNode, SVGElementContainerNode, SVG2PGFTransform):
    def __init__(
        self, group: Group, parent_element_node: Optional[SVGElementNode] = None
    ) -> None:
        SVG2PGFTransform.__init__(self)
        self.group = group
        self.parent_element_node = parent_element_node
        factory = SVGElementNodeFactory(self)
        self.children_element_nodes = list(
            [factory.create_node(e) for e in self.element]
        )

    @property
    def element(self) -> Group:
        return self.group

    @property
    def parent(self) -> Optional[SVGElementNode]:
        return self.parent_element_node

    @property
    def children(self) -> list[SVGElementNode]:
        return self.children_element_nodes

    def svg_bbox(self) -> BboxTuple:
        bb: BboxTuple = self.group.bbox()
        return bb

    def accept_visitor(self, visitor: NodeVisitor) -> None:
        visitor.visit_group(self)


class UseNode(SVGElementNode, SVGElementContainerNode, SVG2PGFTransform):
    def __init__(
        self, use: Use, parent_element_node: Optional[SVGElementNode] = None
    ) -> None:
        SVG2PGFTransform.__init__(self)
        self.use = use
        self.parent_element_node = parent_element_node
        factory = SVGElementNodeFactory(self)
        self.children_element_nodes = list(
            [factory.create_node(e) for e in self.element]
        )

    @property
    def element(self) -> Use:
        return self.use

    @property
    def parent(self) -> Optional[SVGElementNode]:
        return self.parent_element_node

    @property
    def children(self) -> list[SVGElementNode]:
        return self.children_element_nodes

    @property
    def presentation_attributes(self) -> list[str | tuple[str, str]]:
        return super().presentation_attributes + [
            "height",
            "width",
            "x",
            "y",
        ]

    def svg_bbox(self) -> BboxTuple:
        bb: BboxTuple = self.use.bbox()
        return bb

    def accept_visitor(self, visitor: NodeVisitor) -> None:
        visitor.visit_use(self)


class SymbolNode(SVGElementNode):
    def __init__(
        self, symbol: SVGElement, parent_element_node: Optional[SVGElementNode] = None
    ) -> None:
        self.symbol = symbol
        self.parent_element_node = parent_element_node

    @property
    def element(self) -> SVGElement:
        return self.symbol

    @property
    def parent(self) -> Optional[SVGElementNode]:
        return self.parent_element_node

    def accept_visitor(self, visitor: NodeVisitor) -> None:
        visitor.visit_symbol(self)


@final
class SVGNode(GroupNode):
    def __init__(
        self, svg: SVG, parent_element_node: Optional[SVGElementNode] = None
    ) -> None:
        super().__init__(svg, parent_element_node)

    @classmethod
    def parse(
        cls,
        source: SVGSource,
        reify: bool = True,
        ppi: Optional[int] = DEFAULT_PPI,
        width: Optional[int] = None,
        height: Optional[int] = None,
        color: str | Color = "black",
        transform: Optional[str | Matrix] = None,
        context: Optional[SupportsAppend] = None,
        parse_display_none: bool = False,
    ) -> SVGNode:
        svg = SVG.parse(
            source=source,
            reify=reify,
            ppi=ppi,
            width=width,
            height=height,
            color=color,
            transform=transform,
            context=context,
            parse_display_none=parse_display_none,
        )
        return cls(svg)

    @property
    def presentation_attributes(self) -> list[str | tuple[str, str]]:
        return super().presentation_attributes + [
            "height",
            "width",
            "x",
            "y",
        ]

    @property
    def root(self) -> SVGNode:
        return self

    def accept_visitor(self, visitor: NodeVisitor) -> None:
        visitor.visit_svg(self)
