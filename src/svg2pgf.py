#!/usr/bin/env python3
from __future__ import annotations

import sys
from typing import Iterable, Union, final
from svgelements import *
from abc import ABC, abstractmethod

class Generator(ABC):
    @abstractmethod
    def generate(self, indent: str = '  ') -> list[str]:
        pass

    @classmethod
    def indent(cls, lines: Iterable[str], indent: str = '  ') -> list[str]:
        return list([(indent + s) for s in lines])

    @classmethod
    def transform_bbox(cls, matrix: Matrix, bbox: tuple[float,float,float,float]) -> tuple[float,float,float,float]:
        bb = (Point(bbox[0], bbox[1]), Point(bbox[2], bbox[3]))
        bb = (matrix.transform_point(bb[0]), matrix.transform_point(bb[1]))
        xmin = min(bb[0].x, bb[1].x)
        ymin = min(bb[0].y, bb[1].y)
        xmax = max(bb[0].x, bb[1].x)
        ymax = max(bb[0].y, bb[1].y)
        return (xmin, ymin, xmax, ymax)

class Hierarchical(ABC):
    @property
    @abstractmethod
    def parent(self) -> Union[Hierarchical, NoneType]:
        pass

    @property
    def root(self) -> Hierarchical:
        if self.parent is None:
            return self
        elif not isinstance(self.parent, Hierarchical):
            return self.parent
        else:
            return self.parent.root

class SVGElementHandler(Generator, Hierarchical):
    @property
    @abstractmethod
    def element(self) -> SVGElement:
        pass

    @property
    def values(self) -> dict:
        return self.element.values

    @property
    def tag(self) -> str:
        return self.element.values['tag']

    @property
    def attributes_to_generate(self) -> list[tuple[str,str]]:
        return [
            ('id', 'id'),
            ('transform', 'transform'),
            ('fill', 'fill'),
            ('stroke', 'stroke'),
            ('href', '{http://www.w3.org/1999/xlink}href')
        ]

    def generate_attribute_list(self, element_handler: SVGElementHandler) -> list[str]:
        generated = []
        attributes = element_handler.element.values.get('attributes', [])
        for key, attr  in self.attributes_to_generate:
            val = attributes.get(attr)
            if val is not None:
                generated.append(f"{key}={repr(val)}")
        return generated

    def generate_begin_pgfscope(self, indent: str = '  ') -> list[str]:
        attributes = ' '.join(self.generate_attribute_list(self))
        if attributes:
            attributes = ' ' + attributes
        lines = [ r'\begin{pgfscope} %% <%s%s>' % (self.tag, attributes)]
        lines.extend(self.indent(SVGElementInfoGenerator(self).generate(), indent))
        lines.extend(self.indent(DrawingOptionsGenerator(self).generate(), indent))
        return lines

    def generate_end_pgfscope(self) -> list[str]:
        return [ r'\end{pgfscope} %% </%s>' % self.tag ]

class SVGElementHandlerWrapper(SVGElementHandler):
    @property
    @abstractmethod
    def wrapped(self) -> SVGElementHandler:
        pass

    @property
    def parent(self) -> Union[Hierarchical,NoneType]:
        return self.wrapped.parent

    @property
    def element(self) -> SVGElement:
        return self.wrapped.element

    @property
    def root(self) -> Hierarchical:
        return self.wrapped.root

    @property
    def values(self) -> dict:
        return self.wrapped.values

    @property
    def tag(self) -> str:
        return self.wrapped.tag

@final
class SVGElementHandlerFactory:
    def __init__(self, parent_element_handler: Union[SVGElementHandler,NoneType]=None,
                 shape_handler_factory: Union[ShapeHandlerFactory,NoneType]=None):
        self.parent_element_handler = parent_element_handler
        if shape_handler_factory is None:
            shape_handler_factory = ShapeHandlerFactory(parent_element_handler)
        self.shape_handler_factory = shape_handler_factory

    def handler(self, element: SVGElement) -> SVGElementHandler:
        if isinstance(element, Shape):
            return self.shape_handler_factory.handler(element)
        elif isinstance(element, SVG):
            return SVGHandler(element, self.parent_element_handler)
        elif isinstance(element, Group):
            return GroupHandler(element, self.parent_element_handler)
        elif isinstance(element, Use):
            return UseHandler(element, self.parent_element_handler)
        elif isinstance(element, SVGElement) and element.values['tag'] == 'symbol':
            return SymbolHandler(element, self.parent_element_handler)
        else:
            return UnsupportedSVGElementHandler(element, self.parent_element_handler)

@final
class ShapeHandlerFactory:
    def __init__(self, parent_element_handler: Union[SVGElementHandler,NoneType]=None):
        self.parent_element_handler = parent_element_handler

    def handler(self, shape: Shape) -> ShapeHandler:
        if isinstance(shape, Circle):
            return CircleHandler(shape, self.parent_element_handler)
        elif isinstance(shape, Ellipse):
            return EllipseHandler(shape, self.parent_element_handler)
        elif isinstance(shape, Rect):
            return RectHandler(shape, self.parent_element_handler)
        elif isinstance(shape, Path):
            return PathHandler(shape, self.parent_element_handler)
        elif isinstance(shape, SimpleLine):
            return SimpleLineHandler(shape, self.parent_element_handler)
        elif isinstance(shape, Polyline):
            return PolylineHandler(shape, self.parent_element_handler)
        elif isinstance(shape, Polygon):
            return PolygonHandler(shape, self.parent_element_handler)
        else:
            return UnsupportedShapeHandler(shape, self.parent_element_handler)


class SVGBBoxProvider:
    @abstractmethod
    def svg_bbox(self) -> tuple[float, float, float, float]:
        pass

class SVG2PGFTransform(SVGBBoxProvider):
    def _determine_pgf_bbox(self, bbox) -> tuple[float, float, float, float]:
        (xmin, ymin, xmax, ymax) = bbox
        w = xmax - xmin
        h = ymax - ymin
        if h < w:
            return (-1.0, -h/w, 1.0, h/w)
        elif w < h:
            return (-w/h, -1.0, w/h, 1.0)
        else:
            return (-1.0, -1.0, 1.0, 1.0)

    @staticmethod
    def _bbox_center(bbox) -> Point:
        (xmin, ymin, xmax, ymax) = bbox
        return Point((xmin + xmax)/2.0, (ymin + ymax)/2.0)

    @staticmethod
    def _bbox_size(bbox) -> Point:
        (xmin, ymin, xmax, ymax) = bbox
        return Point(abs(xmax - xmin), abs(ymax - ymin))

    def _determine_pgf_scale(self, bbox) -> Point:
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
        if not hasattr(self, '_svg2pgf_transform') or self._svg2pgf_transform is None:
            self._svg2pgf_transform = self._determine_svg2pgf_transform()
        return self._svg2pgf_transform

    def svg2pgf_point(self, point: Point) -> Point:
        if isinstance(self.root, SVG2PGFTransform):
            svg2pgf = self.root.svg2pgf_transform
            point = svg2pgf.point_in_matrix_space(point)
        return point

    def svg2pgf_vector(self, vector: Point) -> Point:
        if isinstance(self.root, SVG2PGFTransform):
            svg2pgf = self.root.svg2pgf_transform.vector()
            vector = svg2pgf.point_in_matrix_space(vector)
        return vector

    def svg2pgf_matrix(self, matrix: Matrix) -> Matrix:
        if isinstance(self.root, SVG2PGFTransform):
            svg2pgf = self.root.svg2pgf_transform
            matrix = ~svg2pgf * matrix * svg2pgf
        return matrix

class ShapeHandler(SVGElementHandler, SVG2PGFTransform):
    @property
    @abstractmethod
    def shape(self) -> Shape:
        pass

    @property
    def element(self) -> SVGElement:
        return self.shape

    def svg_bbox(self) -> tuple[float, float, float, float]:
        return self.shape.bbox()

    def generate_pgfusepath(self) -> list[str]:
        lines = []
        actions = []
        if isinstance(self.shape.fill, Color) and self.shape.fill.value:
            actions.append('fill')
        if isinstance(self.shape.stroke, Color) and self.shape.stroke.value:
            actions.append('stroke')
        if actions:
            mode = ', '.join(actions)
            lines.append(r'\pgfusepath{%s}' % mode)
        return lines

@final
class SVGElementInfoGenerator(SVGElementHandlerWrapper):
    def __init__(self, wrapped_element_handler: SVGElementHandler):
        self.wrapped_element_handler = wrapped_element_handler

    @property
    def wrapped(self) -> SVGElementHandler:
        return self.wrapped_element_handler

    def generate(self, indent: str = '  ') -> list[str]:
        lines = []
        if isinstance(self.wrapped, SVGBBoxProvider):
            svg_bb = self.wrapped.svg_bbox()
            if svg_bb is not None:
                lines.extend(self.generate_bbox(svg_bb))
        if isinstance(self.element, Transformable):
            svg_transform = self.element.transform
            if svg_transform is not None:
                lines.append(f'% SVG transform: {repr(svg_transform)}')
                if isinstance(self.root, SVG2PGFTransform):
                    pgf_transform = self.root.svg2pgf_matrix(svg_transform)
                    lines.append(f'% PGF transform: {repr(pgf_transform)}')
        return lines

    def generate_bbox(self, svg_bb: tuple[float,float,float,float]) -> list[str]:
        (xmin, ymin, xmax, ymax) = svg_bb
        (w, h) = (xmax - xmin, ymax - ymin)
        lines = [f'% SVG bounding box: [({xmin}, {ymin}), ({xmax}, {ymax})]: ({w} x {h})']
        if isinstance(self.root, SVG2PGFTransform):
            svg2pgf = self.root.svg2pgf_transform
            pgf_bb = self.transform_bbox(svg2pgf, svg_bb)
            (xmin, ymin, xmax, ymax) = pgf_bb
            (w, h) = (xmax - xmin, ymax - ymin)
            lines.append(f'% PGF bounding box: [({xmin}, {ymin}), ({xmax}, {ymax})]: ({w} x {h})')
        return lines

@final
class PGFTransformcmGenerator(Generator):
    def __init__(self, svg_transform: Matrix, svg2pgf_transform: Matrix):
        self.svg_transform = svg_transform
        self.svg2pgf_transform = svg2pgf_transform

    def generate(self, indent: str = '  ') -> list[str]:
        m = ~self.svg2pgf_transform * self.svg_transform * self.svg2pgf_transform
        t = r'\pgfpointxy{%r}{%r}' % (m.e, m.f) # translation
        return [r'\pgftransformcm{%r}{%r}{%r}{%r}{%s}' % (m.a, m.b, m.c, m.d, t)]

@final
class DrawingOptionsGenerator(SVGElementHandlerWrapper):
    def __init__(self, wrapped_element_handler: SVGElementHandler):
        self.wrapped_element_handler = wrapped_element_handler

    @property
    def wrapped(self) -> SVGElementHandler:
        return self.wrapped_element_handler

    def generate(self, indent: str = '  ') -> list[str]:
        lines = []
        if isinstance(self.element, GraphicObject):
            lines.extend(self.generate_color_options(self.element))
        return lines

    @classmethod
    def generate_color_options(cls, element: GraphicObject) -> list[str]:
        lines = []
        for option in ('fill', 'stroke'):
            lines.extend(cls.generate_color_option(element, option))
        return lines

    @classmethod
    def generate_color_option(cls, element: GraphicObject, option: str) -> list[str]:
        """The option is either 'fill' or 'stroke'"""
        lines = []
        if not hasattr(element, option):
            return []
        color = getattr(element, option)
        if isinstance(color, Color) and color.value != None:
            cvar = f'local{option}color'
            cval = color.hex[1:] # remove leading '#'
            lines.append(r'\definecolor{%s}{HTML}{%s}' % (cvar, cval))
            lines.append(r'\pgfset%scolor{%s}' % (option, cvar))
        return lines

@final
class PathHandler(ShapeHandler):
    def __init__(self, path: Path, parent_element_handler: Union[SVGElementHandler,NoneType]=None):
        self.path = path
        self.parent_element_handler = parent_element_handler

    @property
    def shape(self) -> Path:
        return self.path

    @property
    def parent(self) -> Union[SVGElementHandler, NoneType]:
        return self.parent_element_handler

    def generate(self, indent: str = '  ') -> list[str]:
        lines = self.generate_begin_pgfscope(indent)

        factory = PathSegmentHandlerFactory(self)
        for segment in self.element:
            handler = factory.handler(segment)
            lines.extend(self.indent(handler.generate(), indent))

        lines.extend(self.indent(self.generate_pgfusepath(), indent))
        lines.extend(self.generate_end_pgfscope())
        return lines

@final
class PathSegmentHandlerFactory:
    def __init__(self, parent_path_handler: Union[PathHandler, NoneType]=None):
        self.parent_path_handler = parent_path_handler

    def handler(self, segment: PathSegment) -> PathSegmentHandler:
        if isinstance(segment, Close):
            return CloseHandler(segment, self.parent_path_handler)
        elif isinstance(segment, Move):
            return MoveHandler(segment, self.parent_path_handler)
        elif isinstance(segment, Line):
            return LineHandler(segment, self.parent_path_handler)
        elif isinstance(segment, CubicBezier):
            return CubicBezierHandler(segment, self.parent_path_handler)
        elif isinstance(segment, QuadraticBezier):
            return QuadraticBezierHandler(segment, self.parent_path_handler)
        elif isinstance(segment, Arc):
            return ArcHandler(segment, self.parent_path_handler)
        else:
            return UnsupportedPathSegmentHandler(segment)

class PathSegmentHandler(Generator, Hierarchical, SVG2PGFTransform):
    def __init__(self, parent_path_handler: PathHandler=None):
        self.parent_path_handler = parent_path_handler

    @property
    @abstractmethod
    def segment(self) -> PathSegment:
        pass

    @property
    def parent(self) -> Union[PathHandler, None]:
        return self.parent_path_handler

    def svg_bbox(self) -> tuple[float, float, float, float]:
        return self.segment.bbox()


@final
class UnsupportedSVGElementHandler(SVGElementHandler):
    def __init__(self, element: SVGElement, parent_element_handler: Union[SVGElementHandler,NoneType]=None):
        self._element = element
        self.parent_element_handler = parent_element_handler

    @property
    def element(self) -> SVGElement:
        return self._element

    @property
    def parent(self) -> Union[SVGElementHandler,NoneType]:
        return self.parent_element_handler

    def generate(self, indent: str = '  ') -> list[str]:
        extra = ''
        if hasattr(self.element, 'id'):
            extra = f' (id={self.element.id})'
        return [ f"% warning: skipping unsupported SVGElement ({type(self.element)}) <{self.element.values['tag']}>{extra}" ]

@final
class UnsupportedShapeHandler(ShapeHandler):
    def __init__(self, shape: Shape, parent_element_handler: Union[ShapeHandler,NoneType]=None):
        self._shape = shape
        self.parent_element_handler = parent_element_handler

    @property
    def shape(self) -> Shape:
        return self._shape

    @property
    def parent(self) -> Union[ShapeHandler,NoneType]:
        return self.parent_element_handler

    def generate(self, indent: str = '  ') -> list[str]:
        extra = ''
        if hasattr(self.element, 'id'):
            extra = f' (id={self.element.id})'
        return [ f"% warning: skipping unsupported Shape ({type(self.shape)}) <{self.element.values['tag']}>{extra}" ]

@final
class UnsupportedPathSegmentHandler(PathSegmentHandler):
    def __init__(self, path_segment: PathSegment, parent_path_handler: Union[PathHandler,NoneType]=None):
        super().__init__(parent_path_handler)
        self.path_segment = path_segment

    @property
    def segment(self) -> PathSegment:
        return self.path_segment

    def generate(self, indent: str = '  ') -> list[str]:
        extra = ''
        if hasattr(self.segment, 'id'):
            extra = f' (id={self.segment.id})'
        return [ f"% warning: skipping unsupported path segment {type(self.segment)}{extra}" ]

@final
class CloseHandler(PathSegmentHandler):
    def __init__(self, close: Close, parent_path_handler: Union[PathHandler,NoneType]=None):
        super().__init__(parent_path_handler)
        self.close = close

    @property
    def segment(self) -> Close:
        return self.close

    def generate(self, indent: str = '  ') -> list[str]:
        return [ r"\pgfpathclose"]

@final
class MoveHandler(PathSegmentHandler):
    def __init__(self, move: Move, parent_path_handler: Union[PathHandler,NoneType]=None):
        super().__init__(parent_path_handler)
        self.move = move

    @property
    def segment(self) -> Move:
        return self.move

    def generate(self, indent: str = '  ') -> list[str]:
        end = self.svg2pgf_point(self.move.end)
        return [r"\pgfpathmoveto{\pgfpointxy{%r}{%r}}" % (end.x, end.y)]

@final
class LineHandler(PathSegmentHandler):
    def __init__(self, line: Line, parent_path_handler: Union[PathHandler,NoneType]=None):
        super().__init__(parent_path_handler)
        self.line = line

    @property
    def segment(self) -> Line:
        return self.line

    def generate(self, indent: str = '  ') -> list[str]:
        end = self.svg2pgf_point(self.line.end)
        return [r"\pgfpathlineto{\pgfpointxy{%r}{%r}}" % (end.x, end.y)]

@final
class CubicBezierHandler(PathSegmentHandler):
    def __init__(self, cubic_bezier: CubicBezier, parent_path_handler: Union[PathHandler,NoneType]=None):
        super().__init__(parent_path_handler)
        self.cubic_bezier = cubic_bezier

    @property
    def segment(self) -> Union[CubicBezier,NoneType]:
        return self.cubic_bezier

    def generate(self, indent: str = '  ') -> list[str]:
        c1 = self.svg2pgf_point(self.cubic_bezier.control1)
        c2 = self.svg2pgf_point(self.cubic_bezier.control2)
        end = self.svg2pgf_point(self.segment.end)
        c1_str = r'\pgfpointxy{%r}{%r}' % (c1.x, c1.y)
        c2_str = r'\pgfpointxy{%r}{%r}' % (c2.x, c2.y)
        end_str = r'\pgfpointxy{%r}{%r}' % (end.x, end.y)
        return [r'\pgfpathcurveto{%s}{%s}{%s}' % (c1_str, c2_str, end_str)]

@final
class QuadraticBezierHandler(PathSegmentHandler):
    def __init__(self, quadratic_bezier: QuadraticBezier, parent_path_handler: Union[PathHandler,NoneType]=None):
        super().__init__(parent_path_handler)
        self.quadratic_bezier = quadratic_bezier

    @property
    def segment(self) -> QuadraticBezier:
        return self.quadratic_bezier

    def generate(self, indent: str = '  ') -> list[str]:
        c = self.svg2pgf_point(self.quadratic_bezier.control)
        end = self.svg2pgf_point(self.segment.end)
        c_str = r'\pgfpointxy{%r}{%r}' % (c.x, c.y)
        end_str = r'\pgfpointxy{%r}{%r}' % (end.x, end.y)
        return [r'\pgfpathquadraticcurveto{%s}{%s}' % (c_str, end_str)]

@final
class ArcHandler(PathSegmentHandler):
    def __init__(self, arc: Arc, parent_path_handler: Union[PathHandler,NoneType]=None):
        super().__init__(parent_path_handler)
        self.arc = arc

    @property
    def segment(self) -> Arc:
        return self.arc

    def generate(self, indent: str = '  ') -> list[str]:
        if self.arc.start == self.arc.end:
            # this is equivalent to omitting the segment, so do nothing
            return []
        if self.arc.radius.x == 0 or self.arc.radius.y == 0:
            end = self.svg2pgf_point(self.arc.end)
            return [r"\pgfpathlineto{\pgfpointxy{%r}{%r}}" % (end.x, end.y)]

        vrx = self.arc.prx - self.arc.center
        vry = self.arc.pry - self.arc.center
        vrx = self.svg2pgf_vector(vrx)
        vry = self.svg2pgf_vector(vry)

        start_angle = Angle(self.arc.get_start_angle()).as_positive_degrees
        end_angle = Angle(self.arc.get_end_angle()).as_positive_degrees
        sweep = Angle(self.arc.sweep).as_degrees

        if end_angle < start_angle and sweep > 0:
            end_angle += 360
        elif end_angle > start_angle and sweep < 0:
            start_angle += 360

        vrx_str = r'\pgfpointxy{%r}{%r}' % (vrx.x, vrx.y)
        vry_str = r'\pgfpointxy{%r}{%r}' % (vry.x, vry.y)
        return [r'\pgfpatharcaxes{%r}{%r}{%s}{%s}' % (start_angle, end_angle, vrx_str, vry_str)]

@final
class CircleHandler(ShapeHandler):
    def __init__(self, circle: Circle, parent_element_handler: Union[SVGElementHandler,NoneType]=None):
        self.circle = circle
        self.parent_element_handler = parent_element_handler

    @property
    def shape(self) -> Circle:
        return self.circle

    @property
    def parent(self) -> Union[SVGElementHandler,NoneType]:
        return self.parent_element_handler

    def generate(self, indent: str = '  ') -> list[str]:
        c = self.circle.implicit_center
        vrx = Point(self.circle.implicit_rx, 0)
        vry = Point(0, self.circle.implicit_ry)

        m = self.element.transform

        vrx = m.transform_vector(vrx)
        vry = m.transform_vector(vry)

        c = self.svg2pgf_point(c)
        vrx = self.svg2pgf_vector(vrx)
        vry = self.svg2pgf_vector(vry)

        c_str = r'\pgfpointxy{%r}{%r}' % (c.x, c.y)
        vrx_str = r'\pgfpointxy{%r}{%r}' % (vrx.x, vrx.y)
        vry_str = r'\pgfpointxy{%r}{%r}' % (vry.x, vry.y)

        lines = self.generate_begin_pgfscope(indent)
        lines.extend(self.indent([r'\pgfpathellipse{%s}{%s}{%s}' % (c_str, vrx_str, vry_str)], indent))
        lines.extend(self.indent(self.generate_pgfusepath(), indent))
        lines.extend(self.generate_end_pgfscope())

        return lines

@final
class EllipseHandler(ShapeHandler):
    def __init__(self, ellipse: Ellipse, parent_element_handler: Union[SVGElementHandler,NoneType]=None):
        self.ellipse = ellipse
        self.parent_element_handler = parent_element_handler

    @property
    def shape(self) -> Ellipse:
        return self.ellipse

    @property
    def parent(self) -> Union[SVGElementHandler,NoneType]:
        return self.parent_element_handler

    def generate(self, indent: str = '  ') -> list[str]:
        c = self.ellipse.implicit_center
        vrx = Point(self.ellipse.implicit_rx, 0)
        vry = Point(0, self.ellipse.implicit_ry)

        m = self.element.transform

        vrx = m.transform_vector(vrx)
        vry = m.transform_vector(vry)

        c = self.svg2pgf_point(c)
        vrx = self.svg2pgf_vector(vrx)
        vry = self.svg2pgf_vector(vry)

        lines = self.generate_begin_pgfscope(indent)
        c_str = r'\pgfpointxy{%r}{%r}' % (c.x, c.y)
        vrx_str = r'\pgfpointxy{%r}{%r}' % (vrx.x, vrx.y)
        vry_str = r'\pgfpointxy{%r}{%r}' % (vry.x, vry.y)
        lines.extend(self.indent([r'\pgfpathellipse{%s}{%s}{%s}' % (c_str, vrx_str, vry_str)], indent))
        lines.extend(self.indent(self.generate_pgfusepath(), indent))
        lines.extend(self.generate_end_pgfscope())
        return lines;

@final
class RectHandler(ShapeHandler):
    def __init__(self, rect: Rect, parent_element_handler: Union[SVGElementHandler,NoneType]=None):
        self.rect = rect
        self.parent_element_handler = parent_element_handler

    @property
    def shape(self) -> Rect:
        return self.rect

    @property
    def parent(self) -> Union[SVGElementHandler,NoneType]:
        return self.parent_element_handler

    def generate(self, indent: str = '  ') -> list[str]:
        position = Point(self.rect.x, self.rect.y)
        diagonal = Point(self.rect.width, self.rect.height)

        svg2pgf = self.root.svg2pgf_transform
        position = self.root.svg2pgf_point(position)
        diagonal = self.root.svg2pgf_vector(diagonal)

        lines = self.generate_begin_pgfscope(indent)
        lines.extend(self.indent(PGFTransformcmGenerator(self.element.transform, svg2pgf).generate(), indent))
        position_str = r'\pgfpointxy{%r}{%r}' % (position.x, position.y)
        diagonal_str = r'\pgfpointxy{%r}{%r}' % (diagonal.x, diagonal.y)
        lines.extend(self.indent([r'\pgfpathrectangle{%s}{%s}' % (position_str, diagonal_str)], indent))
        lines.extend(self.indent(self.generate_pgfusepath(), indent))
        lines.extend(self.generate_end_pgfscope())
        return lines;

@final
class SimpleLineHandler(ShapeHandler):
    def __init__(self, simple_line: SimpleLine, parent_element_handler: Union[SVGElementHandler,NoneType]=None):
        self.simple_line = simple_line
        self.parent_element_handler = parent_element_handler

    @property
    def shape(self) -> SimpleLine:
        return self.simple_line

    @property
    def parent(self) -> Union[SVGElementHandler,NoneType]:
        return self.parent_element_handler

    def generate(self, indent: str = '  ') -> list[str]:
        p1 = Point(self.simple_line.implicit_x1, self.simple_line.implicit_y1)
        p2 = Point(self.simple_line.implicit_x2, self.simple_line.implicit_y2)

        p1 = self.root.svg2pgf_point(p1)
        p2 = self.root.svg2pgf_point(p2)

        lines = self.generate_begin_pgfscope(indent)
        p1_str = r'\pgfpointxy{%r}{%r}' % (p1.x, p1.y)
        p2_str = r'\pgfpointxy{%r}{%r}' % (p2.x, p2.y)
        lines.extend(self.indent([
            r'\pgfpathmoveto{%s}' % p1_str,
            r'\pgfpathlineto{%s}' % p2_str,
        ], indent))
        lines.extend(self.indent(self.generate_pgfusepath(), indent))
        lines.extend(self.generate_end_pgfscope())
        return lines

class _PolyshapeHandler(ShapeHandler):
    def __init__(self, polyshape: _Polyshape, parent_element_handler: Union[SVGElementHandler,NoneType]=None):
        self.polyshape = polyshape
        self.parent_element_handler = parent_element_handler

    @property
    def parent(self) -> Union[SVGElementHandler,NoneType]:
        return self.parent_element_handler

    @property
    def shape(self) -> _Polyshape:
        return self.polyshape

    @property
    @abstractmethod
    def is_closed(self) -> bool:
        pass

    def generate(self, indent: str = '  ') -> list[str]:
        first = True
        lines = self.generate_begin_pgfscope(indent)
        for point in self.polyshape:
            point = self.root.svg2pgf_point(point)
            point_str = r'\pgfpointxy{%r}{%r}' % (point.x, point.y)
            if first:
                cmd = r'\pgfpathmoveto{%s}' % point_str
                first = False
            else:
                cmd = r'\pgfpathlineto{%s}' % point_str
            lines.extend(self.indent([cmd], indent))
        if self.is_closed:
            lines.extend(self.indent([r'\pgfpathclose'], indent))
        lines.extend(self.indent(self.generate_pgfusepath(), indent))
        lines.extend(self.generate_end_pgfscope())
        return lines


@final
class PolylineHandler(_PolyshapeHandler):
    @property
    def is_closed(self) -> bool:
        return False

@final
class PolygonHandler(_PolyshapeHandler):
    @property
    def is_closed(self) -> bool:
        return True

class GroupHandler(SVGElementHandler, SVG2PGFTransform):
    def __init__(self, group: Group, parent_element_handler: Union[SVGElementHandler,NoneType]=None):
        self.group = group
        self.parent_element_handler = parent_element_handler

    @property
    def element(self) -> Group:
        return self.group

    @property
    def parent(self) -> Union[SVGElementHandler,NoneType]:
        return self.parent_element_handler

    def svg_bbox(self) -> tuple[float, float, float, float]:
        return self.group.bbox()

    def generate(self, indent: str = '  ') -> list[str]:
        lines = self.generate_begin_pgfscope(indent)
        factory = SVGElementHandlerFactory(self)
        for element in self.element:
            if element.values.get('visibility') == 'hidden':
                continue
            handler = factory.handler(element)
            lines.extend(self.indent(handler.generate(), indent))
        lines.extend(self.generate_end_pgfscope())
        return lines

class UseHandler(SVGElementHandler, SVG2PGFTransform):
    def __init__(self, use: Use, parent_element_handler: Union[SVGElementHandler,NoneType]=None):
        self.use = use
        self.parent_element_handler = parent_element_handler

    @property
    def element(self) -> Use:
        return self.use

    @property
    def parent(self) -> Union[SVGElementHandler,NoneType]:
        return self.parent_element_handler

    def svg_bbox(self) -> tuple[float, float, float, float]:
        # For an unknown reason the Use class does not implement bbox() method.
        return Group.union_bbox(self.use.select())

    def generate(self, indent: str = '  ') -> list[str]:
        lines = self.generate_begin_pgfscope(indent)
        factory = SVGElementHandlerFactory(self)
        for element in self.element:
            if element.values.get('visibility') == 'hidden':
                continue
            handler = factory.handler(element)
            lines.extend(self.indent(handler.generate(), indent))
        lines.extend(self.generate_end_pgfscope())
        return lines

class SymbolHandler(SVGElementHandler):
    def __init__(self, symbol: SVGElement, parent_element_handler: Union[SVGElementHandler,NoneType]=None):
        self.symbol = symbol
        self.parent_element_handler = parent_element_handler

    @property
    def element(self) -> SVGElement:
        return self.symbol

    @property
    def parent(self) -> Union[SVGElementHandler,NoneType]:
        return self.parent_element_handler

    def generate(self, indent: str = '  ') -> list[str]:
        lines = []
        if not isinstance(self.parent, UseHandler):
            lines.append('% warning: The following code may be a result of rendering <symbol> declaration.')
            lines.append('% warning: This is a bug, <symbol>s should only be rendered when <use>d.')
            lines.append('% warning: This is a missing feature or existing bug in the svgelements library we use.')
            lines.append('% warning: It results with generating duplicated code or rendering <symbol>s that are not <use>d.')
            lines.append('% warning: Try to identify what part of the following code should be deleted and do it manually.')
        return lines

@final
class SVGHandler(GroupHandler):
    def __init__(self, svg: SVG, parent_element_handler: Union[SVGElementHandler,NoneType]=None):
        super().__init__(svg, parent_element_handler)

    @property
    def root(self) -> SVGHandler:
        return self

svg = SVG.parse(sys.stdin)
lines = SVGHandler(svg).generate()
print("\n".join(lines))
