from __future__ import annotations

from abc import ABC
from abc import abstractmethod

import pgfgen.svg.nodes as nodes


class NodeVisitor(ABC):
    @abstractmethod
    def visit_arc(self, node: nodes.ArcNode) -> None:
        pass

    @abstractmethod
    def visit_circle(self, node: nodes.CircleNode) -> None:
        pass

    @abstractmethod
    def visit_close(self, node: nodes.CloseNode) -> None:
        pass

    @abstractmethod
    def visit_cubic_bezier(self, node: nodes.CubicBezierNode) -> None:
        pass

    @abstractmethod
    def visit_ellipse(self, node: nodes.EllipseNode) -> None:
        pass

    @abstractmethod
    def visit_group(self, node: nodes.GroupNode) -> None:
        pass

    @abstractmethod
    def visit_line(self, node: nodes.LineNode) -> None:
        pass

    @abstractmethod
    def visit_move(self, node: nodes.MoveNode) -> None:
        pass

    @abstractmethod
    def visit_path(self, node: nodes.PathNode) -> None:
        pass

    @abstractmethod
    def visit_polygon(self, node: nodes.PolygonNode) -> None:
        pass

    @abstractmethod
    def visit_polyline(self, node: nodes.PolylineNode) -> None:
        pass

    @abstractmethod
    def visit_quadratic_bezier(self, node: nodes.QuadraticBezierNode) -> None:
        pass

    @abstractmethod
    def visit_rect(self, node: nodes.RectNode) -> None:
        pass

    @abstractmethod
    def visit_simpleline(self, node: nodes.SimpleLineNode) -> None:
        pass

    @abstractmethod
    def visit_svg(self, node: nodes.SVGNode) -> None:
        pass

    @abstractmethod
    def visit_symbol(self, node: nodes.SymbolNode) -> None:
        pass

    @abstractmethod
    def visit_unsupported_path_semgment(
        self, node: nodes.UnsupportedPathSegmentNode
    ) -> None:
        pass

    @abstractmethod
    def visit_unsupported_svg_element(
        self, node: nodes.UnsupportedSVGElementNode
    ) -> None:
        pass

    @abstractmethod
    def visit_unsupported_shape(self, node: nodes.UnsupportedShapeNode) -> None:
        pass

    @abstractmethod
    def visit_use(self, node: nodes.UseNode) -> None:
        pass


class NodeVisitee(ABC):
    @abstractmethod
    def accept_visitor(self, visitor: NodeVisitor) -> None:
        pass
