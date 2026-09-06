"""Data models for Vellum document representation and Semantic UI Spec.

Architecture Invariants:
1. Normalized Vellum Layer:
   - Vellum serializes a flat node list per page where hierarchy is defined solely by `parentId`.
   - VellumNode represents an individual node after reconstructing the child array while preserving
     the document's original painter (z-index) ordering.
   - Coordinates (x, y) are local to the node's parent container.

2. Semantic UI Spec Layer:
   - Framework-neutral declarative JSON representation.
   - Decouples graphical primitives from UI frameworks (WPF, Avalonia, React).
   - Preserves high-level layout intent (e.g. flex direction, star sizing, gap) instead of absolute coordinates.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


# ==========================================
# Normalized Vellum Models
# ==========================================

@dataclass
class VellumNode:
    """Normalized representation of a single node in a Vellum page.
    
    Invariant: `children` contains direct children ordered by painter order (z-index).
    """
    id: str
    type: str  # 'rect', 'ellipse', 'text', 'frame', 'group', 'path', 'line', 'image'
    name: str
    parent_id: Optional[str] = None
    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0
    rotation: float = 0.0
    opacity: float = 1.0
    visible: bool = True
    locked: bool = False
    clip: bool = False

    # Appearance
    fill: Optional[str] = None
    fill2: Optional[str] = None
    fill_type: str = "solid"
    stroke: Optional[str] = None
    stroke_width: float = 0.0
    radius: float = 0.0
    shadow: bool = False
    shadow_color: Optional[str] = None

    # Text properties
    text: Optional[str] = None
    font_family: Optional[str] = None
    font_size: Optional[float] = None
    font_weight: Optional[Union[int, str]] = None
    font_style: Optional[str] = None
    line_height: Optional[float] = None
    text_align: Optional[str] = None  # 'left', 'center', 'right'

    # Auto layout properties
    layout: Optional[str] = None  # 'none', 'horizontal', 'vertical'
    gap: Optional[float] = None
    padding: Optional[float] = None
    layout_align: Optional[str] = None  # 'start', 'center', 'end'

    # Constraints
    constraint_h: Optional[str] = None  # 'left', 'right', 'center', 'stretch', 'scale'
    constraint_v: Optional[str] = None

    # Component & instances
    component: bool = False
    is_instance: bool = False

    # Raw extra properties
    extra: Dict[str, Any] = field(default_factory=dict)
    children: List[VellumNode] = field(default_factory=list)


@dataclass
class VellumPage:
    id: str
    name: str
    nodes: List[VellumNode] = field(default_factory=list)
    root_nodes: List[VellumNode] = field(default_factory=list)


@dataclass
class VellumDocument:
    format: str
    version: int
    name: str
    pages: List[VellumPage] = field(default_factory=list)
    tokens: Dict[str, Any] = field(default_factory=dict)
    assets: Dict[str, Any] = field(default_factory=dict)


# ==========================================
# Semantic UI Spec Models
# ==========================================

@dataclass
class UiSource:
    format: str = "vellum"
    node_id: str = ""
    node_name: str = ""
    source_type: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "format": self.format,
            "nodeId": self.node_id,
            "nodeName": self.node_name,
            "sourceType": self.source_type,
        }


@dataclass
class UiLayout:
    type: Optional[str] = None  # 'stack', 'grid', 'dock', 'absolute', 'none'
    direction: Optional[str] = None  # 'horizontal', 'vertical'
    gap: Optional[float] = None
    padding: Optional[Union[float, List[float]]] = None
    align: Optional[str] = None  # 'start', 'center', 'end', 'stretch'
    cross_align: Optional[str] = None
    grow: Optional[float] = None
    # Sizing projection (LayoutContract). Never hug at this stage.
    width_mode: Optional[str] = None  # 'fixed' | 'fill'
    height_mode: Optional[str] = None  # 'fixed' | 'fill'
    # Source anchoring. Must not be collapsed into width_mode.
    constraint_h: Optional[str] = None  # left|right|center|stretch|scale
    constraint_v: Optional[str] = None  # top|bottom|center|stretch|scale
    design_width: Optional[float] = None
    design_height: Optional[float] = None
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[Union[float, str]] = None
    height: Optional[Union[float, str]] = None
    columns: Optional[List[Union[float, str]]] = None
    rows: Optional[List[Union[float, str]]] = None
    grid_column: Optional[int] = None
    grid_row: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        if self.type:
            d["type"] = self.type
        if self.direction:
            d["direction"] = self.direction
        if self.gap is not None:
            d["gap"] = self.gap
        if self.padding is not None:
            d["padding"] = self.padding
        if self.align:
            d["align"] = self.align
        if self.cross_align:
            d["crossAlign"] = self.cross_align
        if self.grow is not None:
            d["grow"] = self.grow
        if self.width_mode:
            d["widthMode"] = self.width_mode
        if self.height_mode:
            d["heightMode"] = self.height_mode
        if self.constraint_h:
            d["constraintH"] = self.constraint_h
        if self.constraint_v:
            d["constraintV"] = self.constraint_v
        if self.design_width is not None:
            d["designWidth"] = self.design_width
        if self.design_height is not None:
            d["designHeight"] = self.design_height
        if self.x is not None:
            d["x"] = self.x
        if self.y is not None:
            d["y"] = self.y
        if self.width is not None:
            d["width"] = self.width
        if self.height is not None:
            d["height"] = self.height
        if self.columns is not None:
            d["columns"] = self.columns
        if self.rows is not None:
            d["rows"] = self.rows
        if self.grid_column is not None:
            d["gridColumn"] = self.grid_column
        if self.grid_row is not None:
            d["gridRow"] = self.grid_row
        return d


@dataclass
class UiStyle:
    background: Optional[str] = None
    foreground: Optional[str] = None
    border_color: Optional[str] = None
    border_thickness: Optional[float] = None
    corner_radius: Optional[float] = None
    opacity: Optional[float] = None
    font_size: Optional[float] = None
    font_weight: Optional[Union[int, str]] = None
    font_family: Optional[str] = None
    font_style: Optional[str] = None
    text_align: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        if self.background is not None:
            d["background"] = self.background
        if self.foreground is not None:
            d["foreground"] = self.foreground
        if self.border_color is not None:
            d["borderColor"] = self.border_color
        if self.border_thickness is not None and self.border_thickness > 0:
            d["borderThickness"] = self.border_thickness
        if self.corner_radius is not None and self.corner_radius > 0:
            d["cornerRadius"] = self.corner_radius
        if self.opacity is not None and self.opacity < 1.0:
            d["opacity"] = self.opacity
        if self.font_size is not None:
            d["fontSize"] = self.font_size
        if self.font_weight is not None:
            d["fontWeight"] = self.font_weight
        if self.font_family is not None:
            d["fontFamily"] = self.font_family
        if self.font_style is not None and self.font_style != "normal":
            d["fontStyle"] = self.font_style
        if self.text_align is not None:
            d["textAlign"] = self.text_align
        return d


@dataclass
class UiNode:
    """A semantic UI node representing a window, panel, button, input, text, etc."""
    id: str
    type: str  # window, panel, frame, stack, grid, text, button, input, image, separator, card, badge, icon, unknown
    name: Optional[str] = None
    source: Optional[UiSource] = None
    layout: UiLayout = field(default_factory=UiLayout)
    style: UiStyle = field(default_factory=UiStyle)
    props: Dict[str, Any] = field(default_factory=dict)
    children: List[UiNode] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {
            "id": self.id,
            "type": self.type,
        }
        if self.name:
            res["name"] = self.name
        if self.source:
            res["source"] = self.source.to_dict()
        layout_dict = self.layout.to_dict()
        if layout_dict:
            res["layout"] = layout_dict
        style_dict = self.style.to_dict()
        if style_dict:
            res["style"] = style_dict
        if self.props:
            res["props"] = self.props
        if self.children:
            res["children"] = [c.to_dict() for c in self.children]
        if self.warnings:
            res["warnings"] = self.warnings
        return res


@dataclass
class UiSpec:
    """Root Semantic UI Spec document."""
    version: str = "0.1"
    name: str = "MainWindow"
    type: str = "window"
    width: float = 1200
    height: float = 800
    theme: str = "dark"
    resources: Dict[str, str] = field(default_factory=dict)
    root: Optional[UiNode] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "name": self.name,
            "type": self.type,
            "width": self.width,
            "height": self.height,
            "theme": self.theme,
            "resources": self.resources,
            "root": self.root.to_dict() if self.root else None,
        }


# ==========================================
# AI Refiner Interface (Placeholder for future Agent)
# ==========================================

class UiSpecRefiner:
    """Extension point for future AI agents to refine the UI Spec before code generation."""

    def refine(self, spec: UiSpec) -> UiSpec:
        """Refine the spec (e.g. reorganize layout, enrich semantic roles)."""
        return spec
