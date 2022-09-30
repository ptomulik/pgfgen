from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from math import atan2

from typing import Dict
from typing import TextIO
from typing import Iterable
from typing import Optional
from typing import TypedDict
from typing import final

from svgelements import Angle
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
from svgelements import Transformable
from svgelements import Use

from svgelements.svgelements import _Polyshape

from .types import SupportsAppend


# only for typing
Attributes = Dict[str, str]

# only for typing
Bbox = tuple[float, float, float, float]

# only for typing
SVGSource = str | TextIO


class NotRequiredValues(TypedDict, total=False):
    attributes: Optional[Attributes]


class Values(NotRequiredValues):
    tag: str


class Generator(ABC):
    @abstractmethod
    def generate(self, indent: str = "  ") -> list[str]:
        pass  # pragma: no cover

    @classmethod
    def indent(cls, lines: Iterable[str], indent: str = "  ") -> list[str]:
        return list([(indent + s) for s in lines])


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


class SVGElementNode(Generator, SVGElementChildNode):
    @property
    @abstractmethod
    def element(self) -> SVGElement:
        pass  # pragma: no cover

    @property
    def values(self) -> Values:
        values: Values = self.element.values
        return values

    @property
    def attributes(self) -> Attributes:
        attributes: Optional[Attributes] = self.values.get("attributes")
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

    def generate_attribute_list(self) -> list[str]:
        generated = []
        for item in self.element_attributes:
            if isinstance(item, tuple):
                (key, attr) = item
            else:
                key = attr = item
            val = self.attributes.get(attr)
            if val is not None:
                generated.append(f"{key}={repr(val)}")
        return generated

    def generate_begin_pgfscope(self, indent: str = "  ") -> list[str]:
        attributes = " ".join(self.generate_attribute_list())
        if attributes:
            attributes = " " + attributes
        lines = [r"\begin{pgfscope} %% <%s%s>" % (self.tag, attributes)]
        lines.extend(self.indent(SVGElementInfoGenerator(self).generate(), indent))
        lines.extend(self.indent(DrawingOptionsGenerator(self).generate(), indent))
        return lines

    def generate_end_pgfscope(self) -> list[str]:
        return [r"\end{pgfscope} %% </%s>" % self.tag]


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
    def values(self) -> Values:
        return self.wrapped.values

    @property
    def tag(self) -> str:
        return self.wrapped.tag


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
    def svg_bbox(self) -> Bbox:
        pass


class SVG2PGFTransform(SVGBboxProvider):
    def __init__(self):
        self._svg2pgf_transform: Optional[Matrix] = None

    def _determine_pgf_bbox(self, bbox: Bbox) -> Bbox:
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
    def _bbox_center(bbox: Bbox) -> Point:
        (xmin, ymin, xmax, ymax) = bbox
        return Point((xmin + xmax) / 2.0, (ymin + ymax) / 2.0)

    @staticmethod
    def _bbox_size(bbox: Bbox) -> Point:
        (xmin, ymin, xmax, ymax) = bbox
        return Point(abs(xmax - xmin), abs(ymax - ymin))

    def _determine_pgf_scale(self, bbox: Bbox) -> Point:
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

    def svg2pgf_bbox(self, bbox: Bbox) -> Bbox:
        svg2pgf = self.svg2pgf_transform
        bb = (Point(bbox[0], bbox[1]), Point(bbox[2], bbox[3]))
        bb = (svg2pgf.transform_point(bb[0]), svg2pgf.transform_point(bb[1]))
        xmin = min(bb[0].x, bb[1].x)
        ymin = min(bb[0].y, bb[1].y)
        xmax = max(bb[0].x, bb[1].x)
        ymax = max(bb[0].y, bb[1].y)
        return (xmin, ymin, xmax, ymax)


class ShapeNode(SVGElementNode, SVG2PGFTransform):
    def __init__(self):
        SVG2PGFTransform.__init__(self)

    @property
    @abstractmethod
    def shape(self) -> Shape:
        pass

    @property
    def element(self) -> SVGElement:
        return self.shape

    def svg_bbox(self) -> Bbox:
        bb: Bbox = self.shape.bbox()
        return bb

    def generate_pgfusepath(self) -> list[str]:
        lines = []
        actions = []
        if isinstance(self.shape.fill, Color) and self.shape.fill.value:
            actions.append("fill")
        if isinstance(self.shape.stroke, Color) and self.shape.stroke.value:
            actions.append("stroke")
        if actions:
            mode = ", ".join(actions)
            lines.append(r"\pgfusepath{%s}" % mode)
        return lines


@final
class SVGElementInfoGenerator(SVGElementNodeWrapper):
    def __init__(self, wrapped_element_node: SVGElementNode):
        self.wrapped_element_node = wrapped_element_node

    @property
    def wrapped(self) -> SVGElementNode:
        return self.wrapped_element_node

    def generate(self, indent: str = "  ") -> list[str]:
        lines = []
        if isinstance(self.wrapped, SVGBboxProvider):
            svg_bb = self.wrapped.svg_bbox()
            lines.extend(self.generate_svg_bbox(svg_bb))
            if isinstance(self.root, SVG2PGFTransform):
                pgf_bb = self.root.svg2pgf_bbox(svg_bb)
                lines.extend(self.generate_pgf_bbox(pgf_bb))
        if self.wrapped is self.root and isinstance(self.wrapped, SVG2PGFTransform):
            svg2pgf = self.wrapped.svg2pgf_transform
            lines.append(f"% SVG2PGF transform: {repr(svg2pgf)}")
        if isinstance(self.element, Transformable):
            svg_transform = self.element.transform
            if svg_transform is not None:
                lines.append(f"% SVG transform: {repr(svg_transform)}")
                if isinstance(self.root, SVG2PGFTransform):
                    pgf_transform = self.root.svg2pgf_matrix(svg_transform)
                    lines.append(f"% PGF transform: {repr(pgf_transform)}")
        return lines

    def generate_svg_bbox(self, bb: Bbox) -> list[str]:
        return [f"% SVG bounding box: {self.bbox_to_str(bb)}"]

    def generate_pgf_bbox(self, bb: Bbox) -> list[str]:
        return [f"% PGF bounding box: {self.bbox_to_str(bb)}"]

    def bbox_to_str(self, bb: Bbox) -> str:
        (xmin, ymin, xmax, ymax) = bb
        (w, h) = (xmax - xmin, ymax - ymin)
        return f"{{{xmin}}}{{{ymin}}}{{{xmax}}}{{{ymax}}} % {w} x {h}"


@final
class PGFTransformcmGenerator(Generator):
    def __init__(self, svg_transform: Matrix, svg2pgf_transform: Matrix):
        self.svg_transform = svg_transform
        self.svg2pgf_transform = svg2pgf_transform

    def generate(self, indent: str = "  ") -> list[str]:
        m = ~self.svg2pgf_transform * self.svg_transform * self.svg2pgf_transform
        t = r"\pgfpointxy{%r}{%r}" % (m.e, m.f)  # translation
        return [r"\pgftransformcm{%r}{%r}{%r}{%r}{%s}" % (m.a, m.b, m.c, m.d, t)]


@final
class DrawingOptionsGenerator(SVGElementNodeWrapper):
    def __init__(self, wrapped_element_node: SVGElementNode):
        self.wrapped_element_node = wrapped_element_node

    @property
    def wrapped(self) -> SVGElementNode:
        return self.wrapped_element_node

    def generate(self, indent: str = "  ") -> list[str]:
        lines = []
        if isinstance(self.element, GraphicObject):
            lines.extend(self.generate_color_options(self.element))
        return lines

    @classmethod
    def generate_color_options(cls, element: GraphicObject) -> list[str]:
        lines = []
        for option in ("fill", "stroke"):
            lines.extend(cls.generate_color_option(element, option))
        return lines

    @classmethod
    def generate_color_option(cls, element: GraphicObject, option: str) -> list[str]:
        """The option is either 'fill' or 'stroke'"""
        lines = []
        if not hasattr(element, option):
            return []
        color = getattr(element, option)
        if isinstance(color, Color) and color.value is not None:
            cvar = f"local{option}color"
            cval = color.hex[1:]  # remove leading '#'
            lines.append(r"\definecolor{%s}{HTML}{%s}" % (cvar, cval))
            lines.append(r"\pgfset%scolor{%s}" % (option, cvar))
        return lines


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

    def generate(self, indent: str = "  ") -> list[str]:
        lines = self.generate_begin_pgfscope(indent)

        factory = PathSegmentNodeFactory(self)
        for segment in self.element:
            node = factory.create_node(segment)
            lines.extend(self.indent(node.generate(), indent))

        lines.extend(self.indent(self.generate_pgfusepath(), indent))
        lines.extend(self.generate_end_pgfscope())
        return lines


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


class PathSegmentNode(Generator, SVGElementChildNode, SVG2PGFTransform):
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

    def svg_bbox(self) -> Bbox:
        bb: Bbox = self.segment.bbox()
        return bb


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

    def generate(self, indent: str = "  ") -> list[str]:
        extra = ""
        if hasattr(self.element, "id"):
            extra = f" (id={self.element.id})"
        return [
            f"% warning: skipping unsupported SVGElement"
            f"({type(self.element)}) <{self.element.values['tag']}>{extra}"
        ]


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

    def generate(self, indent: str = "  ") -> list[str]:
        extra = ""
        if hasattr(self.element, "id"):
            extra = f" (id={self.element.id})"
        return [
            f"% warning: skipping unsupported Shape ({type(self.shape)})"
            f" <{self.element.values['tag']}>{extra}"
        ]


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

    def generate(self, indent: str = "  ") -> list[str]:
        extra = ""
        if hasattr(self.segment, "id"):
            extra = f" (id={self.segment.id})"
        return [
            f"% warning: skipping unsupported path segment {type(self.segment)}{extra}"
        ]


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

    def generate(self, indent: str = "  ") -> list[str]:
        return [r"\pgfpathclose"]


@final
class MoveNode(PathSegmentNode):
    def __init__(self, move: Move, parent_path_node: Optional[PathNode] = None) -> None:
        super().__init__(parent_path_node)
        self.move = move

    @property
    def segment(self) -> Move:
        return self.move

    def generate(self, indent: str = "  ") -> list[str]:
        end = self.move.end
        if isinstance(self.root, SVG2PGFTransform):
            end = self.root.svg2pgf_point(end)
        return [r"\pgfpathmoveto{\pgfpointxy{%r}{%r}}" % (end.x, end.y)]


@final
class LineNode(PathSegmentNode):
    def __init__(self, line: Line, parent_path_node: Optional[PathNode] = None) -> None:
        super().__init__(parent_path_node)
        self.line = line

    @property
    def segment(self) -> Line:
        return self.line

    def generate(self, indent: str = "  ") -> list[str]:
        end = self.line.end
        if isinstance(self.root, SVG2PGFTransform):
            end = self.root.svg2pgf_point(end)
        return [r"\pgfpathlineto{\pgfpointxy{%r}{%r}}" % (end.x, end.y)]


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

    def generate(self, indent: str = "  ") -> list[str]:
        c1 = self.cubic_bezier.control1
        c2 = self.cubic_bezier.control2
        end = self.segment.end
        if isinstance(self.root, SVG2PGFTransform):
            c1 = self.root.svg2pgf_point(c1)
            c2 = self.root.svg2pgf_point(c2)
            end = self.root.svg2pgf_point(end)
        c1_str = r"\pgfpointxy{%r}{%r}" % (c1.x, c1.y)
        c2_str = r"\pgfpointxy{%r}{%r}" % (c2.x, c2.y)
        end_str = r"\pgfpointxy{%r}{%r}" % (end.x, end.y)
        return [r"\pgfpathcurveto{%s}{%s}{%s}" % (c1_str, c2_str, end_str)]


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

    def generate(self, indent: str = "  ") -> list[str]:
        c = self.quadratic_bezier.control
        end = self.segment.end
        if isinstance(self.root, SVG2PGFTransform):
            c = self.root.svg2pgf_point(c)
            end = self.root.svg2pgf_point(end)
        c_str = r"\pgfpointxy{%r}{%r}" % (c.x, c.y)
        end_str = r"\pgfpointxy{%r}{%r}" % (end.x, end.y)
        return [r"\pgfpathquadraticcurveto{%s}{%s}" % (c_str, end_str)]


@final
class ArcNode(PathSegmentNode):
    def __init__(self, arc: Arc, parent_path_node: Optional[PathNode] = None) -> None:
        super().__init__(parent_path_node)
        self.arc = arc

    @property
    def segment(self) -> Arc:
        return self.arc

    def generate(self, indent: str = "  ") -> list[str]:
        if self.arc.start == self.arc.end:
            # this is equivalent to omitting the segment, so do nothing
            return []
        if self.arc.radius.x == 0 or self.arc.radius.y == 0:
            end = self.arc.end
            if isinstance(self.root, SVG2PGFTransform):
                end = self.root.svg2pgf_point(end)
            return [r"\pgfpathlineto{\pgfpointxy{%r}{%r}}" % (end.x, end.y)]

        if isinstance(self.root, SVG2PGFTransform):
            arc = self.arc * self.root.svg2pgf_transform
        else:
            arc = self.arc

        vrx = arc.prx - arc.center
        vry = arc.pry - arc.center

        sweep = self._determine_sweep(vrx, vry)
        (start_angle, end_angle) = self._determine_angles(vrx, vry, arc, sweep)

        vrx_str = r"\pgfpointxy{%r}{%r}" % (vrx.x, vrx.y)
        vry_str = r"\pgfpointxy{%r}{%r}" % (vry.x, vry.y)
        return [
            r"\pgfpatharcaxes{%r}{%r}{%s}{%s}"
            % (start_angle, end_angle, vrx_str, vry_str)
        ]

    def _determine_sweep(self, vrx: Point, vry: Point) -> float:
        # Test whether our SVG axes transformed to PGF space comprise right- or
        # left-handed pair of vectors. If left-handed,then we have to change
        # sweep sign.
        ex = Point(1, 0)
        ey = Point(0, 1)
        if isinstance(self.root, SVG2PGFTransform):
            ex = self.root.svg2pgf_vector(ex)
            ey = self.root.svg2pgf_vector(ey)
        ez = ex.x * ey.y - ex.y * ey.x
        if ez > 0:  # right-handed
            sweep = self.arc.sweep
        else:  # left-handed
            sweep = -self.arc.sweep

        # Check whether the pair (vrx, vry) is right- or left-handed
        # If left-handed, we have to change sweep again.
        vrz = vrx.x * vry.y - vrx.y * vry.x
        if vrz < 0:
            sweep = -sweep

        return Angle(sweep).as_degrees

    def _determine_angles(
        self, vrx: Point, vry: Point, arc: Arc, sweep: float
    ) -> tuple[float, float]:
        # arc is self.arc in pgf space
        vs = arc.start - arc.center
        ve = arc.end - arc.center

        vrx2 = vrx.x * vrx.x + vrx.y * vrx.y
        vry2 = vry.x * vry.x + vry.y * vry.y

        # projection of vs on vrx and vry (dot products used)
        vsp = Point(
            (vs.x * vrx.x + vs.y * vrx.y) / vrx2, (vs.x * vry.x + vs.y * vry.y) / vry2
        )
        # projection of ve on vrx and vry (dot products used)
        vep = Point(
            (ve.x * vrx.x + ve.y * vrx.y) / vrx2, (ve.x * vry.x + ve.y * vry.y) / vry2
        )

        # PGF uses different definition of start_angle and end_angle
        # While svgelements measures angles w.r.t global x-axis,
        # PGF uses angles measured w.r.t vrx.
        start_angle = Angle(atan2(vsp.y, vsp.x)).as_positive_degrees
        end_angle = Angle(atan2(vep.y, vep.x)).as_positive_degrees

        # Sweep is determined by PGF from start and end angle, so we must
        # set up these two appropriatelly to preserve information about
        # sweep's sign.
        if sweep > 0:
            while end_angle <= start_angle:
                end_angle += 360
        elif sweep < 0:
            while start_angle <= end_angle:
                start_angle += 360

        return (start_angle, end_angle)


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

    def generate(self, indent: str = "  ") -> list[str]:
        c = self.circle.implicit_center
        vrx = Point(self.circle.implicit_rx, 0)
        vry = Point(0, self.circle.implicit_ry)

        m = self.element.transform

        vrx = m.transform_vector(vrx)
        vry = m.transform_vector(vry)

        if isinstance(self.root, SVG2PGFTransform):
            c = self.root.svg2pgf_point(c)
            vrx = self.root.svg2pgf_vector(vrx)
            vry = self.root.svg2pgf_vector(vry)

        c_str = r"\pgfpointxy{%r}{%r}" % (c.x, c.y)
        vrx_str = r"\pgfpointxy{%r}{%r}" % (vrx.x, vrx.y)
        vry_str = r"\pgfpointxy{%r}{%r}" % (vry.x, vry.y)

        lines = self.generate_begin_pgfscope(indent)
        lines.extend(
            self.indent(
                [r"\pgfpathellipse{%s}{%s}{%s}" % (c_str, vrx_str, vry_str)], indent
            )
        )
        lines.extend(self.indent(self.generate_pgfusepath(), indent))
        lines.extend(self.generate_end_pgfscope())

        return lines


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

    def generate(self, indent: str = "  ") -> list[str]:
        c = self.ellipse.implicit_center
        vrx = Point(self.ellipse.implicit_rx, 0)
        vry = Point(0, self.ellipse.implicit_ry)

        m = self.element.transform

        vrx = m.transform_vector(vrx)
        vry = m.transform_vector(vry)

        if isinstance(self.root, SVG2PGFTransform):
            c = self.root.svg2pgf_point(c)
            vrx = self.root.svg2pgf_vector(vrx)
            vry = self.root.svg2pgf_vector(vry)

        lines = self.generate_begin_pgfscope(indent)
        c_str = r"\pgfpointxy{%r}{%r}" % (c.x, c.y)
        vrx_str = r"\pgfpointxy{%r}{%r}" % (vrx.x, vrx.y)
        vry_str = r"\pgfpointxy{%r}{%r}" % (vry.x, vry.y)
        lines.extend(
            self.indent(
                [r"\pgfpathellipse{%s}{%s}{%s}" % (c_str, vrx_str, vry_str)], indent
            )
        )
        lines.extend(self.indent(self.generate_pgfusepath(), indent))
        lines.extend(self.generate_end_pgfscope())
        return lines


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

    def generate(self, indent: str = "  ") -> list[str]:
        position = Point(self.rect.x, self.rect.y)
        diagonal = Point(self.rect.width, self.rect.height)

        if isinstance(self.root, SVG2PGFTransform):
            svg2pgf = self.root.svg2pgf_transform
            position = self.root.svg2pgf_point(position)
            diagonal = self.root.svg2pgf_vector(diagonal)
        else:
            svg2pgf = Matrix.identity()

        lines = self.generate_begin_pgfscope(indent)
        lines.extend(
            self.indent(
                PGFTransformcmGenerator(self.element.transform, svg2pgf).generate(),
                indent,
            )
        )
        position_str = r"\pgfpointxy{%r}{%r}" % (position.x, position.y)
        diagonal_str = r"\pgfpointxy{%r}{%r}" % (diagonal.x, diagonal.y)
        lines.extend(
            self.indent(
                [r"\pgfpathrectangle{%s}{%s}" % (position_str, diagonal_str)], indent
            )
        )
        lines.extend(self.indent(self.generate_pgfusepath(), indent))
        lines.extend(self.generate_end_pgfscope())
        return lines


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

    def generate(self, indent: str = "  ") -> list[str]:
        p1 = Point(self.simple_line.implicit_x1, self.simple_line.implicit_y1)
        p2 = Point(self.simple_line.implicit_x2, self.simple_line.implicit_y2)

        if isinstance(self.root, SVG2PGFTransform):
            p1 = self.root.svg2pgf_point(p1)
            p2 = self.root.svg2pgf_point(p2)

        lines = self.generate_begin_pgfscope(indent)
        p1_str = r"\pgfpointxy{%r}{%r}" % (p1.x, p1.y)
        p2_str = r"\pgfpointxy{%r}{%r}" % (p2.x, p2.y)
        lines.extend(
            self.indent(
                [
                    r"\pgfpathmoveto{%s}" % p1_str,
                    r"\pgfpathlineto{%s}" % p2_str,
                ],
                indent,
            )
        )
        lines.extend(self.indent(self.generate_pgfusepath(), indent))
        lines.extend(self.generate_end_pgfscope())
        return lines


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

    def generate(self, indent: str = "  ") -> list[str]:
        first = True
        lines = self.generate_begin_pgfscope(indent)
        for point in self.polyshape:
            if isinstance(self.root, SVG2PGFTransform):
                point = self.root.svg2pgf_point(point)
            point_str = r"\pgfpointxy{%r}{%r}" % (point.x, point.y)
            if first:
                cmd = r"\pgfpathmoveto{%s}" % point_str
                first = False
            else:
                cmd = r"\pgfpathlineto{%s}" % point_str
            lines.extend(self.indent([cmd], indent))
        if self.is_closed:
            lines.extend(self.indent([r"\pgfpathclose"], indent))
        lines.extend(self.indent(self.generate_pgfusepath(), indent))
        lines.extend(self.generate_end_pgfscope())
        return lines


@final
class PolylineNode(_PolyshapeNode):
    @property
    def is_closed(self) -> bool:
        return False


@final
class PolygonNode(_PolyshapeNode):
    @property
    def is_closed(self) -> bool:
        return True


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

    def svg_bbox(self) -> Bbox:
        bb: Bbox = self.group.bbox()
        return bb

    def generate(self, indent: str = "  ") -> list[str]:
        lines = self.generate_begin_pgfscope(indent)
        for child in self.children_element_nodes:
            lines.extend(self.indent(child.generate(), indent))
        lines.extend(self.generate_end_pgfscope())
        return lines


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

    def svg_bbox(self) -> Bbox:
        bb: Bbox = self.use.bbox()
        return bb

    def generate(self, indent: str = "  ") -> list[str]:
        lines = self.generate_begin_pgfscope(indent)
        for child in self.children_element_nodes:
            lines.extend(self.indent(child.generate(), indent))
        lines.extend(self.generate_end_pgfscope())
        return lines


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

    def generate(self, indent: str = "  ") -> list[str]:
        lines = []
        if not isinstance(self.parent, UseNode):
            lines.extend(
                [
                    "% warning: The following code may be a result of rendering"
                    " <symbol> declaration.",
                    "% warning: This is a bug, <symbol>s should only be rendered"
                    " when <use>d.",
                    "% warning: This is a missing feature or existing bug in the"
                    "svgelements library we use.",
                    "% warning: It results with generating duplicated code or"
                    "rendering <symbol>s that are not <use>d.",
                    "% warning: Try to identify what part of the following code"
                    "should be deleted and do it manually.",
                ]
            )
        return lines


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
