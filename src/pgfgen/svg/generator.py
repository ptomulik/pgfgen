from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from math import atan2
from math import sqrt

from typing import Iterable
from typing import Optional
from typing import final

from .visitor import NodeVisitor

from .nodes import ArcNode
from .nodes import CircleNode
from .nodes import CloseNode
from .nodes import CubicBezierNode
from .nodes import EllipseNode
from .nodes import GraphicObjectNode
from .nodes import GraphicObjectNodeWrapper
from .nodes import GroupNode
from .nodes import LineNode
from .nodes import MoveNode
from .nodes import PathNode
from .nodes import PathSegmentNode
from .nodes import PathSegmentNodeWrapper
from .nodes import PolygonNode
from .nodes import PolylineNode
from .nodes import QuadraticBezierNode
from .nodes import RectNode
from .nodes import SVGBboxProvider
from .nodes import SVGElementChildNode
from .nodes import SVGElementNode
from .nodes import SVGElementNodeWrapper
from .nodes import SVGNode
from .nodes import ShapeNode
from .nodes import SimpleLineNode
from .nodes import SymbolNode
from .nodes import UnsupportedPathSegmentNode
from .nodes import UnsupportedSVGElementNode
from .nodes import UnsupportedShapeNode
from .nodes import UseNode
from .nodes import _PolyshapeNode

# move there somewhere?
from .nodes import SVG2PGFTransform

from ..types import BboxTuple

from svgelements import Angle
from svgelements import Arc
from svgelements import Circle
from svgelements import Color
from svgelements import CubicBezier
from svgelements import Ellipse
from svgelements import Line
from svgelements import Matrix
from svgelements import Move
from svgelements import Path
from svgelements import Point
from svgelements import QuadraticBezier
from svgelements import Rect
from svgelements import Shape
from svgelements import SimpleLine
from svgelements import Transformable
from svgelements.svgelements import _Polyshape


class Generator(ABC):
    @abstractmethod
    def generate(self, indent: str = "  ") -> list[str]:
        pass

    @classmethod
    def indent(cls, lines: Iterable[str], indent: str = "  ") -> list[str]:
        return list([(indent + s) for s in lines])


class SVGElementGenerator(Generator, SVGElementNodeWrapper):
    """Base class for generators handling subclasses of SVGElementNode"""

    def generate_attribute_assignments(self) -> list[str]:
        assignments = []
        for item in self.wrapped.element_attributes:
            if isinstance(item, tuple):
                (key, attr) = item
            else:
                key = attr = item
            val = self.wrapped.attributes.get(attr)
            if val is not None:
                assignments.append(f"{key}={repr(val)}")
        return assignments

    def generate_begin_pgfscope(self, indent: str = "  ") -> list[str]:
        attributes = " ".join(self.generate_attribute_assignments())
        if attributes:
            attributes = " " + attributes
        lines = [r"\begin{pgfscope} %% <%s%s>" % (self.wrapped.tag, attributes)]
        lines.extend(self.indent(SVGElementInfoGenerator(self).generate(), indent))
        if isinstance(self.wrapped, GraphicObjectNode):
            lines.extend(
                self.indent(
                    GraphicObjectOptionsGenerator(self.wrapped).generate(indent), indent
                )
            )
        return lines

    def generate_end_pgfscope(self) -> list[str]:
        return [r"\end{pgfscope} %% </%s>" % self.tag]


# ----------------------------------------------------------------------------
# SVG generic elements (containers, etc.)
# ----------------------------------------------------------------------------
class GroupGenerator(SVGElementGenerator):
    def __init__(self, group_node: GroupNode):
        self.group_node = group_node

    @property
    def wrapped(self) -> SVGElementNode:
        return self.group_node

    def generate(self, indent: str = "  ") -> list[str]:
        lines = self.generate_begin_pgfscope(indent)
        generator = GeneratorNodeVisitor(indent)
        for child in self.group_node.children_element_nodes:
            child.accept_visitor(generator)
        lines.extend(self.indent(generator.lines, indent))
        lines.extend(self.generate_end_pgfscope())
        return lines


class UseGenerator(SVGElementGenerator):
    def __init__(self, use_node: UseNode):
        self.use_node = use_node

    @property
    def wrapped(self) -> SVGElementNode:
        return self.use_node

    def generate(self, indent: str = "  ") -> list[str]:
        lines = self.generate_begin_pgfscope(indent)
        generator = GeneratorNodeVisitor(indent)
        for child in self.use_node.children_element_nodes:
            child.accept_visitor(generator)
        lines.extend(self.indent(generator.lines, indent))
        lines.extend(self.generate_end_pgfscope())
        return lines


class SymbolGenerator(SVGElementGenerator):
    def __init__(self, symbol_node: SymbolNode):
        self.symbol_node = symbol_node

    @property
    def wrapped(self) -> SVGElementNode:
        return self.symbol_node

    def generate(self, indent: str = "  ") -> list[str]:
        lines = []
        if not isinstance(self.symbol_node.parent, UseNode):
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
class SVGGenerator(GroupGenerator):
    def __init__(self, svg_node: SVGNode):
        super().__init__(svg_node)


@final
class UnsupportedSVGElementGenerator(SVGElementGenerator):
    def __init__(self, unsupported_svg_element_node: UnsupportedSVGElementNode):
        self.unsupported_svg_element_node = unsupported_svg_element_node

    @property
    def wrapped(self) -> SVGElementNode:
        return self.unsupported_svg_element_node

    def generate(self, indent: str = "  ") -> list[str]:
        extra = ""
        if hasattr(self.element, "id"):
            extra = f" (id={self.element.id})"
        return [
            f"% warning: skipping unsupported SVGElement"
            f"({type(self.element)}) <{self.element.values['tag']}>{extra}"
        ]


# ----------------------------------------------------------------------------
# SVG Shape elements (<circle>, <rect>, ...)
# ----------------------------------------------------------------------------
class ShapeGenerator(SVGElementGenerator):
    """Base class for shape generators"""

    @property
    @abstractmethod
    def shape_node(self) -> ShapeNode:
        pass

    @property
    def shape(self) -> Shape:
        return self.shape_node.shape

    @property
    def wrapped(self) -> SVGElementNode:
        return self.shape_node

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
class CircleGenerator(ShapeGenerator):
    def __init__(self, circle_node: CircleNode):
        self.circle_node = circle_node

    @property
    def shape_node(self) -> ShapeNode:
        return self.circle_node

    @property
    def circle(self) -> Circle:
        return self.circle_node.circle

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
class EllipseGenerator(ShapeGenerator):
    def __init__(self, ellipse_node: EllipseNode):
        self.ellipse_node = ellipse_node

    @property
    def shape_node(self) -> ShapeNode:
        return self.ellipse_node

    @property
    def ellipse(self) -> Ellipse:
        return self.ellipse_node.ellipse

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
class PathGenerator(ShapeGenerator):
    def __init__(self, path_node: PathNode):
        self.path_node = path_node

    @property
    def shape_node(self) -> ShapeNode:
        return self.path_node

    @property
    def path(self) -> Path:
        return self.path_node.path

    def generate(self, indent: str = "  ") -> list[str]:
        lines = self.generate_begin_pgfscope(indent)
        generator = GeneratorNodeVisitor(indent)
        for child in self.path_node.children_path_segment_nodes:
            child.accept_visitor(generator)
        lines.extend(self.indent(generator.lines, indent))
        lines.extend(self.indent(self.generate_pgfusepath(), indent))
        lines.extend(self.generate_end_pgfscope())
        return lines


@final
class RectGenerator(ShapeGenerator):
    def __init__(self, rect_node: RectNode):
        self.rect_node = rect_node

    @property
    def shape_node(self) -> ShapeNode:
        return self.rect_node

    @property
    def rect(self) -> Rect:
        return self.rect_node.rect

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
class SimpleLineGenerator(ShapeGenerator):
    def __init__(self, simple_line_node: SimpleLineNode):
        self.simple_line_node = simple_line_node

    @property
    def shape_node(self) -> ShapeNode:
        return self.simple_line_node

    @property
    def simple_line(self) -> SimpleLine:
        return self.simple_line_node.simple_line

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


class _PolyshapeGenerator(ShapeGenerator):
    def __init__(self, polyshape_node: _PolyshapeNode):
        self.polyshape_node = polyshape_node

    @property
    def shape_node(self) -> ShapeNode:
        return self.polyshape_node

    @property
    def shape(self) -> _Polyshape:
        return self.polyshape_node.shape

    def generate(self, indent: str = "  ") -> list[str]:
        first = True
        lines = self.generate_begin_pgfscope(indent)
        for point in self.shape:
            if isinstance(self.root, SVG2PGFTransform):
                point = self.root.svg2pgf_point(point)
            point_str = r"\pgfpointxy{%r}{%r}" % (point.x, point.y)
            if first:
                cmd = r"\pgfpathmoveto{%s}" % point_str
                first = False
            else:
                cmd = r"\pgfpathlineto{%s}" % point_str
            lines.extend(self.indent([cmd], indent))
        if self.polyshape_node.is_closed:
            lines.extend(self.indent([r"\pgfpathclose"], indent))
        lines.extend(self.indent(self.generate_pgfusepath(), indent))
        lines.extend(self.generate_end_pgfscope())
        return lines


@final
class PolylineGenerator(_PolyshapeGenerator):
    def __init__(self, polyline_node: PolylineNode):
        super().__init__(polyline_node)


@final
class PolygonGenerator(_PolyshapeGenerator):
    def __init__(self, polygon_node: PolygonNode):
        super().__init__(polygon_node)


@final
class UnsupportedShapeGenerator(ShapeGenerator):
    def __init__(self, unsupported_shape_node: UnsupportedShapeNode):
        self.unsupported_shape_node = unsupported_shape_node

    @property
    def shape_node(self) -> ShapeNode:
        return self.unsupported_shape_node

    def generate(self, indent: str = "  ") -> list[str]:
        extra = ""
        if hasattr(self.element, "id"):
            extra = f" (id={self.element.id})"
        return [
            f"% warning: skipping unsupported Shape ({type(self.shape)})"
            f" <{self.element.values['tag']}>{extra}"
        ]


# ----------------------------------------------------------------------------
# Path segments
# ----------------------------------------------------------------------------
class PathSegmentGenerator(PathSegmentNodeWrapper):
    pass


class ArcGenerator(PathSegmentGenerator):
    def __init__(self, arc_node: ArcNode):
        self.arc_node = arc_node

    @property
    def wrapped(self) -> PathSegmentNode:
        return self.arc_node

    @property
    def arc(self) -> Arc:
        return self.arc_node.arc

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

        return float(Angle(sweep).as_degrees)

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


class CloseGenerator(PathSegmentGenerator):
    def __init__(self, close_node: CloseNode):
        self.close_node = close_node

    @property
    def wrapped(self) -> PathSegmentNode:
        return self.close_node

    def generate(self, indent: str = "  ") -> list[str]:
        return [r"\pgfpathclose"]


class CubicBezierGenerator(PathSegmentGenerator):
    def __init__(self, cubic_bezier_node: CubicBezierNode):
        self.cubic_bezier_node = cubic_bezier_node

    @property
    def wrapped(self) -> PathSegmentNode:
        return self.cubic_bezier_node

    @property
    def cubic_bezier(self) -> CubicBezier:
        return self.cubic_bezier_node.cubic_bezier

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


class LineGenerator(PathSegmentGenerator):
    def __init__(self, line_node: LineNode):
        self.line_node = line_node

    @property
    def wrapped(self) -> PathSegmentNode:
        return self.line_node

    @property
    def line(self) -> Line:
        return self.line_node.line

    def generate(self, indent: str = "  ") -> list[str]:
        end = self.line.end
        if isinstance(self.root, SVG2PGFTransform):
            end = self.root.svg2pgf_point(end)
        return [r"\pgfpathlineto{\pgfpointxy{%r}{%r}}" % (end.x, end.y)]


class MoveGenerator(PathSegmentGenerator):
    def __init__(self, move_node: MoveNode):
        self.move_node = move_node

    @property
    def wrapped(self) -> PathSegmentNode:
        return self.move_node

    @property
    def move(self) -> Move:
        return self.move_node.move

    def generate(self, indent: str = "  ") -> list[str]:
        end = self.move.end
        if isinstance(self.root, SVG2PGFTransform):
            end = self.root.svg2pgf_point(end)
        return [r"\pgfpathmoveto{\pgfpointxy{%r}{%r}}" % (end.x, end.y)]


class QuadraticBezierGenerator(PathSegmentGenerator):
    def __init__(self, quadratic_bezier_node: QuadraticBezierNode):
        self.quadratic_bezier_node = quadratic_bezier_node

    @property
    def wrapped(self) -> PathSegmentNode:
        return self.quadratic_bezier_node

    @property
    def quadratic_bezier(self) -> QuadraticBezier:
        return self.quadratic_bezier_node.quadratic_bezier

    def generate(self, indent: str = "  ") -> list[str]:
        c = self.quadratic_bezier.control
        end = self.segment.end
        if isinstance(self.root, SVG2PGFTransform):
            c = self.root.svg2pgf_point(c)
            end = self.root.svg2pgf_point(end)
        c_str = r"\pgfpointxy{%r}{%r}" % (c.x, c.y)
        end_str = r"\pgfpointxy{%r}{%r}" % (end.x, end.y)
        return [r"\pgfpathquadraticcurveto{%s}{%s}" % (c_str, end_str)]


class UnsupportedPathSegmentGenerator(PathSegmentGenerator):
    def __init__(self, unsupported_path_segment_node: UnsupportedPathSegmentNode):
        self.unsupported_path_segment_node = unsupported_path_segment_node

    @property
    def wrapped(self) -> PathSegmentNode:
        return self.unsupported_path_segment_node

    def generate(self, indent: str = "  ") -> list[str]:
        extra = ""
        if hasattr(self.segment, "id"):
            extra = f" (id={self.segment.id})"
        return [
            f"% warning: skipping unsupported path segment {type(self.segment)}{extra}"
        ]


# ---------------------------------------------------------------------------
# Helper generators
# ---------------------------------------------------------------------------
@final
class GraphicObjectOptionsGenerator(GraphicObjectNodeWrapper):
    def __init__(self, graphic_object_node: GraphicObjectNode):
        self.graphic_object_node = graphic_object_node

    @property
    def wrapped(self) -> GraphicObjectNode:
        return self.graphic_object_node

    def generate(self, indent: str = "  ") -> list[str]:
        lines = []
        lines.extend(self.generate_color_options())
        lines.extend(self.generate_stroke_width())
        lines.extend(self.generate_stroke_dash())
        lines.extend(self.generate_stroke_linejoin())
        lines.extend(self.generate_stroke_miterlimit())
        lines.extend(self.generate_stroke_linecap())
        return lines

    def generate_color_options(self) -> list[str]:
        lines = []
        for option in ("fill", "stroke"):
            lines.extend(self.generate_color_option(option))
        return lines

    def generate_color_option(self, option: str) -> list[str]:
        """The option is either 'fill' or 'stroke'"""
        lines = []
        color = getattr(self, option)
        if isinstance(color, Color):
            if color.value is not None:
                cvar = f"{option}color"
                chex = color.hexrgb[1:]  # remove leading '#'
                lines.append(r"\definecolor{%s}{HTML}{%s}" % (cvar, chex))
                lines.append(r"\pgfset%scolor{%s}" % (option, cvar))
            if color.opacity is not None:
                lines.append(r"\pgfset%sopacity{%s}" % (option, color.opacity))
        return lines

    def generate_stroke_width(self) -> list[str]:
        if not isinstance(self.implicit_stroke_width, float):
            return []

        e = 1.0 / sqrt(2.0)
        w = self.implicit_stroke_width * self._svg2pgf_scale()
        return [
            r"\pgf@process{\pgfpointxy{%r}{%r}}" % (e, e),
            r"\pgfmathparse{veclen(scalar(\the\pgf@x), scalar(\the\pgf@y))}",
            r"\pgfmathsetlength\pgf@xa{\pgfmathresult} % scale factor",
            r"\pgfsetlinewidth{%r\pgf@xa}" % w,
        ]

    def generate_stroke_dash(self) -> list[str]:
        if not isinstance(self.wrapped, SVGElementNode):
            return []
        dasharray = self.implicit_stroke_dasharray
        dashoffset: float = self.implicit_stroke_dashoffset or 0.0
        if dasharray is None:
            return [r"% dasharray is None!"]
        if dasharray == "none":
            return [r"\pgfsetdash{}{0pt}"]

        scale = self._svg2pgf_scale()
        dashoffset = scale * dashoffset
        dasharray = [scale * x for x in dasharray]
        dasharray_str = "".join([(r"{%r\pgf@xa}" % x) for x in dasharray])

        e = 1.0 / sqrt(2.0)

        return [
            r"\pgf@process{\pgfpointxy{%r}{%r}}" % (e, e),
            r"\pgfmathparse{veclen(scalar(\the\pgf@x), scalar(\the\pgf@y))}",
            r"\pgfmathsetlength\pgf@xa{\pgfmathresult} % scale factor",
            r"\pgfsetdash{%s}{%r\pgf@xa}" % (dasharray_str, dashoffset),
        ]

    def generate_stroke_linejoin(self) -> list[str]:
        if not isinstance(self.wrapped, SVGElementNode):
            return []
        linejoin: Optional[str] = self.wrapped.values.get("stroke-linejoin")
        if linejoin is None:
            return []
        if linejoin == "miter" or linejoin == "miter-clip":
            return [r"\pgfsys@miterjoin"]
        if linejoin == "round":
            return [r"\pgfsys@roundjoin"]
        if linejoin == "bevel":
            return [r"\pgfsys@beveljoin"]
        if linejoin == "arcs":
            # no 'arcjoin' in PGF/TiKZ, mitter seems to be similar
            return [r"\pgfsys@miterjoin"]
        return []

    def generate_stroke_miterlimit(self) -> list[str]:
        if not isinstance(self.wrapped, SVGElementNode):
            return []
        miterlimit: Optional[str] = self.wrapped.values.get("stroke-miterlimit")
        if miterlimit is None:
            return []
        return [r"\pgfsys@setmiterlimit{%r}" % float(miterlimit)]

    def generate_stroke_linecap(self) -> list[str]:
        if not isinstance(self.wrapped, SVGElementNode):
            return []
        linecap: Optional[str] = self.wrapped.values.get("stroke-linecap")
        if linecap is None:
            return []
        if linecap == "butt":
            return [r"\pgfsys@buttcap"]
        if linecap == "round":
            return [r"\pgfsys@roundcap"]
        if linecap == "square":
            return [r"\pgfsys@rectcap"]
        return []

    def _svg2pgf_scale(self) -> float:
        if not isinstance(self.wrapped, SVGElementChildNode) or not isinstance(
            self.wrapped.root, SVG2PGFTransform
        ):
            return 1.0
        return self._scale(self.wrapped.root.svg2pgf_transform)

    def _scale(self, transform: Matrix) -> float:
        return sqrt(abs(transform.determinant))


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

    def generate_svg_bbox(self, bb: BboxTuple) -> list[str]:
        return [f"% SVG bounding box: {self.bbox_to_str(bb)}"]

    def generate_pgf_bbox(self, bb: BboxTuple) -> list[str]:
        return [f"% PGF bounding box: {self.bbox_to_str(bb)}"]

    def bbox_to_str(self, bb: BboxTuple) -> str:
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


# ----------------------------------------------------------------------------
# Node visitor which generates PGF code from SVG nodes.
# ----------------------------------------------------------------------------
class GeneratorNodeVisitor(NodeVisitor):
    def __init__(self, indent: str = "  "):
        self.lines: list[str] = []
        self.indent = indent

    def visit_arc(self, node: ArcNode) -> None:
        generator = ArcGenerator(node)
        self.lines.extend(generator.generate(self.indent))

    def visit_circle(self, node: CircleNode) -> None:
        generator = CircleGenerator(node)
        self.lines.extend(generator.generate(self.indent))

    def visit_close(self, node: CloseNode) -> None:
        generator = CloseGenerator(node)
        self.lines.extend(generator.generate(self.indent))

    def visit_cubic_bezier(self, node: CubicBezierNode) -> None:
        generator = CubicBezierGenerator(node)
        self.lines.extend(generator.generate(self.indent))

    def visit_ellipse(self, node: EllipseNode) -> None:
        generator = EllipseGenerator(node)
        self.lines.extend(generator.generate(self.indent))

    def visit_group(self, node: GroupNode) -> None:
        generator = GroupGenerator(node)
        self.lines.extend(generator.generate(self.indent))

    def visit_line(self, node: LineNode) -> None:
        generator = LineGenerator(node)
        self.lines.extend(generator.generate(self.indent))

    def visit_move(self, node: MoveNode) -> None:
        generator = MoveGenerator(node)
        self.lines.extend(generator.generate(self.indent))

    def visit_path(self, node: PathNode) -> None:
        generator = PathGenerator(node)
        self.lines.extend(generator.generate(self.indent))

    def visit_polygon(self, node: PolygonNode) -> None:
        generator = PolygonGenerator(node)
        self.lines.extend(generator.generate(self.indent))

    def visit_polyline(self, node: PolylineNode) -> None:
        generator = PolylineGenerator(node)
        self.lines.extend(generator.generate(self.indent))

    def visit_quadratic_bezier(self, node: QuadraticBezierNode) -> None:
        generator = QuadraticBezierGenerator(node)
        self.lines.extend(generator.generate(self.indent))

    def visit_rect(self, node: RectNode) -> None:
        generator = RectGenerator(node)
        self.lines.extend(generator.generate(self.indent))

    def visit_simpleline(self, node: SimpleLineNode) -> None:
        generator = SimpleLineGenerator(node)
        self.lines.extend(generator.generate(self.indent))

    def visit_svg(self, node: SVGNode) -> None:
        generator = SVGGenerator(node)
        self.lines.extend(generator.generate(self.indent))

    def visit_symbol(self, node: SymbolNode) -> None:
        generator = SymbolGenerator(node)
        self.lines.extend(generator.generate(self.indent))

    def visit_unsupported_path_semgment(self, node: UnsupportedPathSegmentNode) -> None:
        generator = UnsupportedPathSegmentGenerator(node)
        self.lines.extend(generator.generate(self.indent))

    def visit_unsupported_svg_element(self, node: UnsupportedSVGElementNode) -> None:
        generator = UnsupportedSVGElementGenerator(node)
        self.lines.extend(generator.generate(self.indent))

    def visit_unsupported_shape(self, node: UnsupportedShapeNode) -> None:
        generator = UnsupportedShapeGenerator(node)
        self.lines.extend(generator.generate(self.indent))

    def visit_use(self, node: UseNode) -> None:
        generator = UseGenerator(node)
        self.lines.extend(generator.generate(self.indent))
