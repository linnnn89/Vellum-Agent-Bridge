"""Adapter for loading and normalizing raw .vellum JSON documents."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .models import VellumDocument, VellumNode, VellumPage
from .utils import normalize_hex_color
from .validator import validate_vellum_dict


class VellumDocumentAdapter:
    """Reads raw .vellum JSON and produces a normalized hierarchy of VellumNode objects."""

    def load_from_file(self, file_path: Union[str, Path]) -> VellumDocument:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self.load_from_dict(data)

    def load_from_json(self, json_str: str) -> VellumDocument:
        data = json.loads(json_str)
        return self.load_from_dict(data)

    def load_from_dict(self, data: Dict[str, Any]) -> VellumDocument:
        validate_vellum_dict(data)

        fmt = data["format"]
        version = data["version"]
        name = data.get("name", "Untitled")

        tokens = data.get("tokens", {})
        assets = data.get("assets", {})
        pages_data = data.get("pages", [])

        if not pages_data or not isinstance(pages_data, list):
            raise ValueError("Invalid Vellum document: pages array is empty or missing.")

        pages: List[VellumPage] = []
        for p_data in pages_data:
            pages.append(self._parse_page(p_data))

        return VellumDocument(
            format=fmt,
            version=version,
            name=name,
            pages=pages,
            tokens=tokens,
            assets=assets,
        )

    def _parse_page(self, p_data: Dict[str, Any]) -> VellumPage:
        page_id = str(p_data.get("id", "page-1"))
        page_name = str(p_data.get("name", "Page"))
        raw_nodes = p_data.get("nodes", [])

        # Pass 1: Parse all nodes into VellumNode objects
        nodes_map: Dict[str, VellumNode] = {}
        all_nodes: List[VellumNode] = []

        for n_data in raw_nodes:
            node = self._parse_node(n_data)
            nodes_map[node.id] = node
            all_nodes.append(node)

        # Pass 2: Reconstruct parent-child hierarchy
        root_nodes: List[VellumNode] = []
        for node in all_nodes:
            parent_id = node.parent_id
            if parent_id and parent_id in nodes_map and parent_id != node.id:
                nodes_map[parent_id].children.append(node)
            else:
                root_nodes.append(node)

        return VellumPage(
            id=page_id,
            name=page_name,
            nodes=all_nodes,
            root_nodes=root_nodes,
        )

    def _parse_node(self, d: Dict[str, Any]) -> VellumNode:
        node_id = str(d.get("id", ""))
        node_type = str(d.get("type", "rect")).lower()
        name = str(d.get("name", node_type))
        parent_id = d.get("parentId")
        if parent_id is not None:
            parent_id = str(parent_id)

        # Geometry - strictly required, not silently defaulted
        x = float(d["x"])
        y = float(d["y"])
        w = float(d["w"])
        h = float(d["h"])
        rotation = float(d["rotation"])
        opacity = float(d["opacity"])

        visible = bool(d.get("visible", True))
        locked = bool(d.get("locked", False))
        clip = bool(d.get("clip", False))

        # Appearance
        fill = normalize_hex_color(d.get("fill"))
        fill2 = normalize_hex_color(d.get("fill2"))
        fill_type = str(d.get("fillType", "solid"))
        stroke = normalize_hex_color(d.get("stroke"))
        stroke_width = float(d.get("strokeWidth", 0.0))
        radius = float(d.get("radius", 0.0))
        shadow = bool(d.get("shadow", False))
        shadow_color = normalize_hex_color(d.get("shadowColor"))

        # Text
        text = d.get("text")
        font_family = d.get("fontFamily")
        font_size = float(d.get("fontSize")) if d.get("fontSize") is not None else None
        font_weight = d.get("fontWeight")
        font_style = d.get("fontStyle")
        line_height = float(d.get("lineHeight")) if d.get("lineHeight") is not None else None
        text_align = d.get("textAlign")

        # Auto Layout
        layout = d.get("layout")
        if layout == "none":
            layout = None
        gap = float(d.get("gap")) if d.get("gap") is not None else None
        padding = float(d.get("padding")) if d.get("padding") is not None else None
        layout_align = d.get("layoutAlign")

        # Constraints
        constraint_h = d.get("constraintH")
        constraint_v = d.get("constraintV")

        # Component
        component = bool(d.get("component", False))
        is_instance = bool(d.get("isInstance", False))

        known_keys = {
            "id", "type", "name", "parentId", "x", "y", "w", "h", "rotation", "opacity",
            "visible", "locked", "clip", "fill", "fill2", "fillType", "stroke", "strokeWidth",
            "radius", "shadow", "shadowColor", "text", "fontFamily", "fontSize", "fontWeight",
            "fontStyle", "lineHeight", "textAlign", "layout", "gap", "padding", "layoutAlign",
            "constraintH", "constraintV", "component", "isInstance"
        }
        extra = {k: v for k, v in d.items() if k not in known_keys}

        return VellumNode(
            id=node_id,
            type=node_type,
            name=name,
            parent_id=parent_id,
            x=x,
            y=y,
            w=w,
            h=h,
            rotation=rotation,
            opacity=opacity,
            visible=visible,
            locked=locked,
            clip=clip,
            fill=fill,
            fill2=fill2,
            fill_type=fill_type,
            stroke=stroke,
            stroke_width=stroke_width,
            radius=radius,
            shadow=shadow,
            shadow_color=shadow_color,
            text=text,
            font_family=font_family,
            font_size=font_size,
            font_weight=font_weight,
            font_style=font_style,
            line_height=line_height,
            text_align=text_align,
            layout=layout,
            gap=gap,
            padding=padding,
            layout_align=layout_align,
            constraint_h=constraint_h,
            constraint_v=constraint_v,
            component=component,
            is_instance=is_instance,
            extra=extra,
            children=[],
        )
