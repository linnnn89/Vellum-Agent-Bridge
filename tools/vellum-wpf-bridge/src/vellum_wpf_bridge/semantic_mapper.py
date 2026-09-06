"""Semantic Mapper: Vellum nodes → Semantic UI Spec.

LayoutContract (sizing + anchoring + flow) is applied first and never uses
layer names. SemanticPromote (button/input/card) runs after and is reported.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from .layout_contract import apply_sizing_contract, autolayout_tracks, note_appearance
from .models import (
    UiLayout,
    UiNode,
    UiSource,
    UiSpec,
    UiStyle,
    VellumDocument,
    VellumNode,
)
from .report import ConversionReport
from .resources import ResourceManager
from .utils import normalize_hex_color, to_pascal_case, is_binding_identifier


_CONTAINER_NAME_MARKERS = (
    "panel", "sidebar", "header", "footer", "card", "inspector",
    "workspace", "window", "area", "bar",
)


class SemanticMapper:
    """Maps a normalized Vellum hierarchy to a high-level Semantic UI Spec."""

    def __init__(self, report: Optional[ConversionReport] = None):
        self.report = report or ConversionReport()

    def map_document(self, doc: VellumDocument, page_index: int = 0) -> UiSpec:
        """Map the primary page of a Vellum document to a UiSpec."""
        if not doc.pages:
            raise ValueError("Document has no pages to convert.")

        page = doc.pages[page_index] if page_index < len(doc.pages) else doc.pages[0]

        window_width = 1200.0
        window_height = 800.0
        theme = "dark"

        if page.root_nodes:
            frames = [n for n in page.root_nodes if n.type == "frame"]
            target_frame = frames[0] if frames else page.root_nodes[0]
            window_width = target_frame.w if target_frame.w > 0 else 1200.0
            window_height = target_frame.h if target_frame.h > 0 else 800.0
            if target_frame.fill:
                hex_val = target_frame.fill.lstrip("#")[-6:]
                if len(hex_val) >= 6:
                    r = int(hex_val[0:2], 16)
                    g = int(hex_val[2:4], 16)
                    b = int(hex_val[4:6], 16)
                    brightness = (r * 299 + g * 587 + b * 114) / 1000
                    theme = "dark" if brightness < 128 else "light"

        if len(page.root_nodes) == 1 and page.root_nodes[0].type == "frame":
            root_ui_node = self._map_node(page.root_nodes[0], is_window_root=True)
        else:
            children = [self._map_node(n) for n in page.root_nodes]
            root_ui_node = UiNode(
                id="window-root",
                type="window",
                name="MainWindow",
                layout=UiLayout(
                    type="absolute",
                    width_mode="fill",
                    height_mode="fill",
                ),
                children=children,
            )
            self.report.add_diagnostic(
                "warning",
                "ABSOLUTE_LAYOUT_NOT_RESPONSIVE",
                "Multiple page roots were wrapped in an absolute canvas.",
            )

        resources: Dict[str, str] = {}
        if doc.tokens:
            color_tokens = doc.tokens.get("colors", [])
            for item in color_tokens:
                name = item.get("name", "")
                val = normalize_hex_color(item.get("value"))
                if val and name:
                    key = ResourceManager.token_name_to_resource_key(name)
                    resources[key] = val

        spec = UiSpec(
            version="0.1",
            name=to_pascal_case(doc.name) or "MainWindow",
            type="window",
            width=window_width,
            height=window_height,
            theme=theme,
            resources=resources,
            root=root_ui_node,
            assets=dict(doc.assets),
        )
        return spec


    def _map_node(self, node: VellumNode, is_window_root: bool = False) -> UiNode:
        source = UiSource(
            format="vellum",
            node_id=node.id,
            node_name=node.name,
            source_type=node.type,
        )
        note_appearance(node, self.report)

        button_node = self._try_map_button(node, source)
        if button_node:
            return button_node

        input_node = self._try_map_input(node, source)
        if input_node:
            return input_node

        separator_node = self._try_map_separator(node, source)
        if separator_node:
            return separator_node

        if node.type == "text":
            self.report.record_node(converted=True)
            return self._map_text_node(node, source)

        if node.type == "image":
            self.report.record_node(converted=True)
            return self._map_image_node(node, source)

        if node.type in ("path", "ellipse"):
            return self._map_unknown_or_shape(node, source)

        return self._map_container_node(node, source, is_window_root=is_window_root)

    def _absorb_children(self, node: VellumNode, reason: str) -> None:
        for child in node.children:
            self.report.record_node(converted=False, absorbed=True)
            self.report.add_absorbed(child.id, node.id, reason)
            self._absorb_children(child, reason)

    def _try_map_button(self, node: VellumNode, source: UiSource) -> Optional[UiNode]:
        if node.type not in ("frame", "rect", "group"):
            return None
        if not (20 <= node.h <= 65 and node.w >= 30):
            return None

        name_lower = (node.name or "").lower()
        is_named_button = "button" in name_lower or "btn" in name_lower
        looks_like_container = any(marker in name_lower for marker in _CONTAINER_NAME_MARKERS)

        text_children = [c for c in node.children if c.type == "text"]
        button_text = None
        if len(text_children) == 1 and len(node.children) <= 2:
            button_text = (text_children[0].text or "").strip()
        elif is_named_button:
            button_text = node.name.replace("Button", "").replace("button", "").strip()

        common_labels = {
            "save", "send", "cancel", "submit", "search", "explore",
            "start", "login", "register", "apply", "ok", "yes", "no", "edit", "delete",
            "确定", "发送", "取消", "保存", "提交", "搜索",
        }
        is_action_label = button_text and (
            button_text.lower() in common_labels
            or any(k in button_text.lower() for k in ["save", "send", "cancel", "submit", "explore", "start", "view all", "→", "↗"])
        )

        if not is_named_button:
            if looks_like_container or not (is_action_label and node.radius > 0):
                return None

        command_name = None
        action_name = to_pascal_case(node.name) or (to_pascal_case(button_text) if button_text else None)
        if action_name:
            clean_action = re.sub(r"(Button|Btn)$", "", action_name)
            if clean_action:
                command_name = f"{clean_action}Command"

        style = UiStyle(
            background=node.fill if node.fill != "none" else None,
            foreground=text_children[0].fill if text_children and text_children[0].fill else "#FFFFFF",
            border_color=node.stroke if node.stroke_width > 0 else None,
            border_thickness=node.stroke_width if node.stroke_width > 0 else None,
            corner_radius=node.radius if node.radius > 0 else 4.0,
            font_size=text_children[0].font_size if text_children else 13.0,
            font_weight=text_children[0].font_weight if text_children else 500,
        )
        layout = apply_sizing_contract(UiLayout(), node, report=self.report)
        props: Dict[str, Any] = {"text": button_text or "Button"}
        if is_binding_identifier(command_name):
            props["command"] = command_name

        self.report.record_node(converted=True)
        self.report.add_promoted(
            node.id, node.type, "button",
            "named button" if is_named_button else f"action label '{button_text}'",
        )
        self._absorb_children(node, "absorbed into button content")
        return UiNode(
            id=node.id,
            type="button",
            name=to_pascal_case(node.name) or "ActionButton",
            source=source,
            layout=layout,
            style=style,
            props=props,
            children=[],
        )

    def _try_map_input(self, node: VellumNode, source: UiSource) -> Optional[UiNode]:
        if node.type not in ("frame", "rect", "group"):
            return None
        if not (24 <= node.h <= 60 and node.w >= 80):
            return None

        name_lower = (node.name or "").lower()
        is_named_input = any(k in name_lower for k in ("input", "search", "field", "textbox"))
        text_children = [c for c in node.children if c.type == "text"]
        placeholder = None
        if text_children:
            cand = (text_children[0].text or "").strip()
            if any(p in cand.lower() for p in ("...", "…", "search", "type", "message", "enter", "输入", "搜索")):
                placeholder = cand
            elif is_named_input:
                placeholder = cand
        if not (is_named_input or placeholder):
            return None

        style = UiStyle(
            background=node.fill if node.fill != "none" else None,
            foreground="#D0D0D0",
            border_color=node.stroke if node.stroke_width > 0 else "#444455",
            border_thickness=node.stroke_width if node.stroke_width > 0 else 1.0,
            corner_radius=node.radius if node.radius > 0 else 4.0,
            font_size=text_children[0].font_size if text_children else 13.0,
        )
        layout = apply_sizing_contract(UiLayout(), node, report=self.report)
        self.report.record_node(converted=True)
        self.report.add_promoted(node.id, node.type, "input", "named input or placeholder text")
        self._absorb_children(node, "absorbed into input placeholder")
        return UiNode(
            id=node.id,
            type="input",
            name=to_pascal_case(node.name) or "InputField",
            source=source,
            layout=layout,
            style=style,
            props={"placeholder": placeholder or "Enter text..."},
            children=[],
        )

    def _try_map_separator(self, node: VellumNode, source: UiSource) -> Optional[UiNode]:
        is_line = node.type == "line"
        is_thin_rect = node.type == "rect" and ((node.h <= 2 and node.w > 10) or (node.w <= 2 and node.h > 10))
        name_lower = (node.name or "").lower()
        is_named_divider = "divider" in name_lower or "separator" in name_lower
        if not (is_line or is_thin_rect or (is_named_divider and (node.h <= 4 or node.w <= 4))):
            return None
        direction = "horizontal" if node.w >= node.h else "vertical"
        layout = apply_sizing_contract(
            UiLayout(direction=direction),
            node,
            report=self.report,
        )
        self.report.record_node(converted=True)
        return UiNode(
            id=node.id,
            type="separator",
            name=to_pascal_case(node.name) or "Divider",
            source=source,
            layout=layout,
            style=UiStyle(background=node.stroke or node.fill or "#333344", opacity=node.opacity),
        )

    def _map_text_node(self, node: VellumNode, source: UiSource) -> UiNode:
        layout = apply_sizing_contract(UiLayout(), node, report=self.report)
        return UiNode(
            id=node.id,
            type="text",
            name=to_pascal_case(node.name),
            source=source,
            layout=layout,
            style=UiStyle(
                foreground=node.fill if node.fill != "none" else "#FFFFFF",
                font_size=node.font_size or 14.0,
                font_weight=node.font_weight or 400,
                font_family=node.font_family or "Segoe UI",
                font_style=node.font_style or "normal",
                text_align=node.text_align or "left",
                opacity=node.opacity,
            ),
            props={"text": node.text or ""},
        )

    def _map_image_node(self, node: VellumNode, source: UiSource) -> UiNode:
        layout = apply_sizing_contract(UiLayout(), node, report=self.report)
        return UiNode(
            id=node.id,
            type="image",
            name=to_pascal_case(node.name) or "Image",
            source=source,
            layout=layout,
            style=UiStyle(corner_radius=node.radius, opacity=node.opacity),
            props={"assetId": node.extra.get("assetId", "")},
        )

    def _map_unknown_or_shape(self, node: VellumNode, source: UiSource) -> UiNode:
        reason = f"Vector type '{node.type}' mapped with fallback representation."
        self.report.record_node(converted=False, fallback=True)
        self.report.add_unsupported(node.id, node.type, reason)
        layout = apply_sizing_contract(UiLayout(), node, report=self.report)
        return UiNode(
            id=node.id,
            type="unknown",
            name=to_pascal_case(node.name) or "VectorShape",
            source=source,
            layout=layout,
            style=UiStyle(
                background=node.fill if node.fill != "none" else None,
                border_color=node.stroke if node.stroke_width > 0 else None,
                border_thickness=node.stroke_width if node.stroke_width > 0 else None,
                corner_radius=node.w / 2 if node.type == "ellipse" else 0.0,
                opacity=node.opacity,
            ),
            warnings=[reason],
        )

    def _map_container_node(
        self, node: VellumNode, source: UiSource, is_window_root: bool = False
    ) -> UiNode:
        self.report.record_node(converted=True)
        style = UiStyle(
            background=node.fill if node.fill != "none" else None,
            border_color=node.stroke if node.stroke_width > 0 else None,
            border_thickness=node.stroke_width if node.stroke_width > 0 else None,
            corner_radius=node.radius if node.radius > 0 else None,
            opacity=node.opacity,
        )
        if is_window_root:
            node_type = "window"
        elif node.radius > 0 and node.fill and node.fill != "none" and len(node.children) > 0:
            node_type = "card"
        else:
            node_type = "panel"

        layout, child_ui_nodes = self._determine_container_layout(node, is_window_root=is_window_root)
        apply_sizing_contract(layout, node, is_window_root=is_window_root, report=self.report)
        name = to_pascal_case(node.name) or ("MainWindow" if is_window_root else "Panel")
        return UiNode(
            id=node.id,
            type=node_type,
            name=name,
            source=source,
            layout=layout,
            style=style,
            children=child_ui_nodes,
        )

    def _determine_container_layout(
        self, node: VellumNode, is_window_root: bool = False
    ) -> Tuple[UiLayout, List[UiNode]]:
        visible = [c for c in node.children if c.visible]
        for hidden in (c for c in node.children if not c.visible):
            self.report.record_node(converted=False, skipped=True)

        if node.layout in ("horizontal", "vertical"):
            mapped = [self._map_node(c) for c in visible]
            return autolayout_tracks(node, visible, mapped, self.report)

        mapped = [self._map_node(c) for c in visible]
        if not mapped:
            return UiLayout(), mapped

        self.report.add_diagnostic(
            "warning",
            "ABSOLUTE_LAYOUT_NOT_RESPONSIVE",
            "Container has no auto-layout; children keep local coordinates on a Canvas.",
            node.id,
        )
        for child_ui in mapped:
            if child_ui.layout.width_mode == "fill" or child_ui.layout.height_mode == "fill":
                warning_msg = "responsive constraint lost on Canvas"
                if warning_msg not in child_ui.warnings:
                    child_ui.warnings.append(warning_msg)
                self.report.add_diagnostic(
                    "warning",
                    "RESPONSIVE_CONSTRAINT_LOST_ON_CANVAS",
                    warning_msg,
                    child_ui.id,
                )
        return UiLayout(type="absolute"), mapped

