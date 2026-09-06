"""WPF XAML Generator: Semantic UI Spec → XAML.

Hard constraints:
- Main-axis fill → Grid (never StackPanel).
- fill / star-track children never emit Width/Height on that axis.
- Root content never copies Window Width/Height.
- Grid gap → spacer tracks; StackPanel gap → trailing Margin.
- Freeform → Canvas + coordinates.
"""

from dataclasses import dataclass
import re
from typing import Dict, List, Optional, Set

from .layout_contract import expand_tracks_with_spacers, physical_index
from .models import UiNode, UiSpec
from .report import ConversionReport
from .resources import ResourceManager
from .utils import escape_xml, fmt_length, to_pascal_case


@dataclass
class EmitContext:
    is_root: bool = False
    parent_type: str = "grid"
    in_star_column: bool = False
    in_star_row: bool = False
    grid_column: Optional[int] = None
    grid_row: Optional[int] = None
    item_margin: Optional[str] = None


class WpfGenerator:
    """Generates clean, readable, valid WPF XAML files from a UiSpec."""

    def __init__(
        self,
        resource_manager: Optional[ResourceManager] = None,
        report: Optional[ConversionReport] = None,
    ):
        self.rm = resource_manager or ResourceManager()
        self.report = report
        self._used_names: Set[str] = set()

    def _sanitize_xaml_name(self, name: str) -> str:
        pascal = to_pascal_case(name)
        if not pascal:
            return "Element"
        cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", pascal)
        if cleaned and cleaned[0].isdigit():
            cleaned = "_" + cleaned
        return cleaned or "Element"

    def _resolve_x_name(
        self, node: UiNode, default_prefix: str = "Element", force: bool = True
    ) -> Optional[str]:
        if not force:
            if not (
                node.props.get("binding")
                or node.props.get("bind")
                or node.props.get("xName")
            ):
                return None
        raw_name = node.props.get("xName") or node.name or default_prefix
        base_name = self._sanitize_xaml_name(raw_name)
        candidate = base_name
        counter = 2
        while candidate in self._used_names:
            candidate = f"{base_name}_{counter}"
            counter += 1
        self._used_names.add(candidate)
        return candidate

    def generate_all(self, spec: UiSpec, app_namespace: str = "GeneratedWpfDemo") -> Dict[str, str]:
        self._used_names = set()
        self.rm.load_from_spec(spec)
        if spec.root:
            self.rm.collect_colors_from_tree(spec.root)
        self.rm.finalize_resources(min_occurrences=2)
        return {
            "Resources.xaml": self.generate_resources_xaml(),
            "MainWindow.xaml": self.generate_main_window_xaml(spec, app_namespace),
            "App.xaml": self.generate_app_xaml(app_namespace),
        }


    def generate_resources_xaml(self) -> str:
        lines = [
            '<ResourceDictionary xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"',
            '                    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">',
        ]
        entries = self.rm.get_xaml_resource_entries(indent="    ")
        if entries:
            lines.extend(entries)
        else:
            lines.append("    <!-- No shared brush resources detected -->")
        lines.append("</ResourceDictionary>")
        return "\n".join(lines)

    def generate_app_xaml(self, app_namespace: str = "GeneratedWpfDemo") -> str:
        return f"""<Application x:Class="{app_namespace}.App"
             xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
             StartupUri="MainWindow.xaml">
    <Application.Resources>
        <ResourceDictionary Source="Resources.xaml"/>
    </Application.Resources>
</Application>"""

    def generate_main_window_xaml(
        self, spec: UiSpec, app_namespace: str = "GeneratedWpfDemo", class_name: str = "MainWindow"
    ) -> str:
        self._used_names = set()
        bg_brush = self.rm.get_color_reference(spec.root.style.background if spec.root else None)
        if not bg_brush:
            bg_brush = "#1E1E24" if spec.theme == "dark" else "#FAFAFC"

        lines = [
            f'<Window x:Class="{app_namespace}.{class_name}"',
            '        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"',
            '        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"',
            '        xmlns:d="http://schemas.microsoft.com/expression/blend/2008"',
            '        xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"',
            '        mc:Ignorable="d"',
            f'        Title="{escape_xml(spec.name)}"',
            f'        Width="{fmt_length(spec.width)}"',
            f'        Height="{fmt_length(spec.height)}"',
            '        WindowStartupLocation="CenterScreen"',
            f'        Background="{bg_brush}">',
        ]
        if spec.root:
            lines.extend(self._generate_node(spec.root, 1, EmitContext(is_root=True, parent_type="window")))
        else:
            lines.append("    <Grid/>")
        lines.append("</Window>")
        return "\n".join(lines)

    def _generate_node(self, node: UiNode, indent_level: int, ctx: EmitContext) -> List[str]:
        indent = "    " * indent_level
        lines: List[str] = []
        if node.source and node.source.node_id:
            src_name = node.source.node_name or node.type
            lines.append(f"{indent}<!-- Vellum: {node.source.node_id} / {escape_xml(src_name)} -->")

        if node.type == "button":
            lines.extend(self._generate_button(node, indent_level, ctx))
        elif node.type == "input":
            lines.extend(self._generate_input(node, indent_level, ctx))
        elif node.type == "text":
            lines.extend(self._generate_text(node, indent_level, ctx))
        elif node.type == "separator":
            lines.extend(self._generate_separator(node, indent_level, ctx))
        elif node.type == "image":
            lines.extend(self._generate_image(node, indent_level, ctx))
        elif node.type == "unknown":
            lines.extend(self._generate_unknown(node, indent_level, ctx))
        else:
            lines.extend(self._generate_container(node, indent_level, ctx))
        return lines

    def _slot_attrs(self, node: UiNode, ctx: EmitContext) -> List[str]:
        attrs: List[str] = []
        col = ctx.grid_column if ctx.grid_column is not None else node.layout.grid_column
        row = ctx.grid_row if ctx.grid_row is not None else node.layout.grid_row
        if ctx.parent_type == "grid":
            if col is not None:
                attrs.append(f'Grid.Column="{col}"')
            if row is not None:
                attrs.append(f'Grid.Row="{row}"')
        elif ctx.parent_type == "canvas":
            if node.layout.x is not None:
                attrs.append(f'Canvas.Left="{fmt_length(node.layout.x)}"')
            if node.layout.y is not None:
                attrs.append(f'Canvas.Top="{fmt_length(node.layout.y)}"')
        if ctx.item_margin and ctx.item_margin != "0":
            attrs.append(f'Margin="{ctx.item_margin}"')
        return attrs

    def _size_attrs(self, node: UiNode, ctx: EmitContext) -> List[str]:
        attrs: List[str] = []
        emit_w = self._should_emit_width(node, ctx)
        emit_h = self._should_emit_height(node, ctx)
        if emit_w:
            width = node.layout.width if node.layout.width is not None else node.layout.design_width
            if width is not None:
                attrs.append(f'Width="{fmt_length(width)}"')
        elif node.layout.width_mode == "fill" and not ctx.is_root and ctx.parent_type != "canvas":
            attrs.append('HorizontalAlignment="Stretch"')
        if emit_h:
            height = node.layout.height if node.layout.height is not None else node.layout.design_height
            if height is not None:
                attrs.append(f'Height="{fmt_length(height)}"')
        elif node.layout.height_mode == "fill" and not ctx.is_root and ctx.parent_type != "canvas":
            attrs.append('VerticalAlignment="Stretch"')

        if ctx.parent_type == "canvas" and (node.layout.width_mode == "fill" or node.layout.height_mode == "fill"):
            warning_msg = "responsive constraint lost on Canvas"
            if warning_msg not in node.warnings:
                node.warnings.append(warning_msg)
            if self.report is not None:
                self.report.add_diagnostic(
                    "warning",
                    "RESPONSIVE_CONSTRAINT_LOST_ON_CANVAS",
                    warning_msg,
                    node.id,
                )
        return attrs

    def _should_emit_width(self, node: UiNode, ctx: EmitContext) -> bool:
        if ctx.is_root:
            return False
        if ctx.parent_type == "canvas":
            return True
        if ctx.in_star_column or node.layout.width_mode == "fill":
            return False
        return node.layout.width is not None or node.layout.design_width is not None

    def _should_emit_height(self, node: UiNode, ctx: EmitContext) -> bool:
        if ctx.is_root:
            return False
        if ctx.parent_type == "canvas":
            return True
        if ctx.in_star_row or node.layout.height_mode == "fill":
            return False
        return node.layout.height is not None or node.layout.design_height is not None

    def _generate_button(self, node: UiNode, indent_level: int, ctx: EmitContext) -> List[str]:
        indent = "    " * indent_level
        attrs = []
        pascal_name = self._resolve_x_name(node, default_prefix="Button", force=True)
        if pascal_name:
            attrs.append(f'x:Name="{pascal_name}"')
        attrs.append(f'Content="{escape_xml(node.props.get("text", "Button"))}"')
        cmd = node.props.get("command")
        if cmd:
            attrs.append(f'Command="{{Binding {cmd}}}"')
        attrs.extend(self._slot_attrs(node, ctx))
        attrs.extend(self._size_attrs(node, ctx))
        bg = self.rm.get_color_reference(node.style.background)
        if bg:
            attrs.append(f'Background="{bg}"')
        fg = self.rm.get_color_reference(node.style.foreground)
        if fg:
            attrs.append(f'Foreground="{fg}"')
        if node.style.font_size:
            attrs.append(f'FontSize="{fmt_length(node.style.font_size)}"')
        return [f"{indent}<Button {' '.join(attrs)}/>"]

    def _generate_input(self, node: UiNode, indent_level: int, ctx: EmitContext) -> List[str]:
        indent = "    " * indent_level
        attrs = []
        pascal_name = self._resolve_x_name(node, default_prefix="Input", force=True)
        if pascal_name:
            attrs.append(f'x:Name="{pascal_name}"')
        
        # TextBox.Text must remain empty unless explicitly set in props["text"]
        if node.props.get("text"):
            attrs.append(f'Text="{escape_xml(str(node.props["text"]))}"')
        
        placeholder = node.props.get("placeholder")
        if placeholder:
            attrs.append(f'ToolTip="{escape_xml(str(placeholder))}"')
            attrs.append(f'Tag="{escape_xml(str(placeholder))}"')

        attrs.extend(self._slot_attrs(node, ctx))
        attrs.extend(self._size_attrs(node, ctx))
        bg = self.rm.get_color_reference(node.style.background)
        if bg:
            attrs.append(f'Background="{bg}"')
        fg = self.rm.get_color_reference(node.style.foreground)
        if fg:
            attrs.append(f'Foreground="{fg}"')
        border = self.rm.get_color_reference(node.style.border_color)
        if border:
            attrs.append(f'BorderBrush="{border}"')
        if node.style.border_thickness:
            attrs.append(f'BorderThickness="{fmt_length(node.style.border_thickness)}"')
        if node.style.font_size:
            attrs.append(f'FontSize="{fmt_length(node.style.font_size)}"')
        attrs.append('VerticalContentAlignment="Center"')
        attrs.append('Padding="8,4"')
        return [f"{indent}<TextBox {' '.join(attrs)}/>"]

    def _generate_text(self, node: UiNode, indent_level: int, ctx: EmitContext) -> List[str]:
        indent = "    " * indent_level
        attrs = []
        pascal_name = self._resolve_x_name(node, default_prefix="Text", force=False)
        if pascal_name:
            attrs.append(f'x:Name="{pascal_name}"')
        attrs.append(f'Text="{escape_xml(node.props.get("text", ""))}"')
        attrs.extend(self._slot_attrs(node, ctx))
        attrs.extend(self._size_attrs(node, ctx))
        fg = self.rm.get_color_reference(node.style.foreground)
        if fg:
            attrs.append(f'Foreground="{fg}"')
        if node.style.font_size:
            attrs.append(f'FontSize="{fmt_length(node.style.font_size)}"')
        if node.style.font_weight:
            w = str(node.style.font_weight)
            weight_val = (
                "Bold" if w in ("700", "800", "bold")
                else "SemiBold" if w in ("500", "600")
                else "Normal"
            )
            attrs.append(f'FontWeight="{weight_val}"')
        if node.style.font_family:
            attrs.append(f'FontFamily="{node.style.font_family}"')
        if node.style.opacity is not None and node.style.opacity < 1.0:
            attrs.append(f'Opacity="{node.style.opacity:.2f}"')
        attrs.append('TextWrapping="Wrap"')
        return [f"{indent}<TextBlock {' '.join(attrs)}/>"]

    def _generate_separator(self, node: UiNode, indent_level: int, ctx: EmitContext) -> List[str]:
        indent = "    " * indent_level
        attrs = self._slot_attrs(node, ctx)
        if node.layout.direction == "vertical":
            attrs.append('Width="1"')
            attrs.append('HorizontalAlignment="Center"')
        else:
            attrs.append('Height="1"')
            attrs.append('HorizontalAlignment="Stretch"')
        bg = self.rm.get_color_reference(node.style.background)
        if bg:
            attrs.append(f'Background="{bg}"')
        return [f"{indent}<Separator {' '.join(attrs)}/>"]

    def _generate_image(self, node: UiNode, indent_level: int, ctx: EmitContext) -> List[str]:
        indent = "    " * indent_level
        attrs = self._slot_attrs(node, ctx) + self._size_attrs(node, ctx)
        return [f'{indent}<Image Stretch="Uniform" {" ".join(attrs)}/>']

    def _generate_unknown(self, node: UiNode, indent_level: int, ctx: EmitContext) -> List[str]:
        indent = "    " * indent_level
        attrs = self._slot_attrs(node, ctx) + self._size_attrs(node, ctx)
        bg = self.rm.get_color_reference(node.style.background)
        if bg:
            attrs.append(f'Fill="{bg}"')
        return [f"{indent}<Rectangle {' '.join(attrs)}/>"]

    def _generate_container(self, node: UiNode, indent_level: int, ctx: EmitContext) -> List[str]:
        indent = "    " * indent_level
        lines: List[str] = []
        has_border_props = bool(
            node.style.corner_radius
            or node.style.border_color
            or (node.style.background and not ctx.is_root)
            or node.layout.padding
        )
        inner_indent = indent_level
        border_opened = False

        if ctx.is_root:
            if node.layout.padding:
                pad = node.layout.padding
                pad_str = fmt_length(pad) if isinstance(pad, (int, float)) else ",".join(str(p) for p in pad)
                lines.append(f'{indent}<Border Padding="{pad_str}">')
                inner_indent += 1
                border_opened = True
                child_lines = self._generate_inner_layout(node, inner_indent, ctx, has_border_parent=True)
            else:
                child_lines = self._generate_inner_layout(node, inner_indent, ctx, has_border_parent=False)
        elif has_border_props:
            border_attrs = self._slot_attrs(node, ctx) + self._size_attrs(node, ctx)
            bg = self.rm.get_color_reference(node.style.background)
            if bg:
                border_attrs.append(f'Background="{bg}"')
            border_c = self.rm.get_color_reference(node.style.border_color)
            if border_c:
                border_attrs.append(f'BorderBrush="{border_c}"')
            if node.style.border_thickness:
                border_attrs.append(f'BorderThickness="{fmt_length(node.style.border_thickness)}"')
            if node.style.corner_radius:
                border_attrs.append(f'CornerRadius="{fmt_length(node.style.corner_radius)}"')
            if node.layout.padding:
                pad = node.layout.padding
                pad_str = fmt_length(pad) if isinstance(pad, (int, float)) else ",".join(str(p) for p in pad)
                border_attrs.append(f'Padding="{pad_str}"')
            lines.append(f"{indent}<Border {' '.join(border_attrs)}>")
            inner_indent += 1
            border_opened = True
            inner_ctx = EmitContext(is_root=False, parent_type=ctx.parent_type)
            child_lines = self._generate_inner_layout(node, inner_indent, inner_ctx, has_border_parent=True)
        else:
            child_lines = self._generate_inner_layout(node, inner_indent, ctx, has_border_parent=False)

        lines.extend(child_lines)
        if border_opened:
            lines.append(f"{indent}</Border>")
        return lines

    def _generate_inner_layout(
        self, node: UiNode, indent_level: int, ctx: EmitContext, has_border_parent: bool
    ) -> List[str]:
        indent = "    " * indent_level
        layout_type = node.layout.type or "stack"
        if layout_type == "absolute":
            container_tag = "Canvas"
        elif layout_type == "grid" or node.layout.columns or node.layout.rows:
            container_tag = "Grid"
        else:
            container_tag = "StackPanel"

        attrs: List[str] = []
        pascal_name = self._resolve_x_name(node, default_prefix="Panel", force=False)
        if pascal_name and not has_border_parent and not ctx.is_root:
            attrs.append(f'x:Name="{pascal_name}"')
        if not has_border_parent:
            attrs.extend(self._slot_attrs(node, ctx))
            attrs.extend(self._size_attrs(node, ctx))
        if container_tag == "StackPanel":
            direction = "Horizontal" if node.layout.direction == "horizontal" else "Vertical"
            attrs.append(f'Orientation="{direction}"')


        attr_str = (" " + " ".join(attrs)) if attrs else ""
        if not node.children and not node.layout.columns and not node.layout.rows:
            return [f"{indent}<{container_tag}{attr_str}/>"]

        lines = [f"{indent}<{container_tag}{attr_str}>"]
        col_spacers = False
        row_spacers = False
        logical_cols = node.layout.columns
        logical_rows = node.layout.rows
        if container_tag == "Grid":
            if logical_cols:
                physical_cols, col_spacers = expand_tracks_with_spacers(logical_cols, node.layout.gap)
                lines.append(f"{indent}    <Grid.ColumnDefinitions>")
                for col in physical_cols:
                    lines.append(f'{indent}        <ColumnDefinition Width="{fmt_length(col)}"/>')
                lines.append(f"{indent}    </Grid.ColumnDefinitions>")
            if logical_rows:
                physical_rows, row_spacers = expand_tracks_with_spacers(logical_rows, node.layout.gap)
                lines.append(f"{indent}    <Grid.RowDefinitions>")
                for row in physical_rows:
                    lines.append(f'{indent}        <RowDefinition Height="{fmt_length(row)}"/>')
                lines.append(f"{indent}    </Grid.RowDefinitions>")

        gap = node.layout.gap or 0.0
        is_horiz_stack = container_tag == "StackPanel" and node.layout.direction == "horizontal"
        is_vert_stack = container_tag == "StackPanel" and node.layout.direction != "horizontal"
        parent_kind = "canvas" if container_tag == "Canvas" else ("grid" if container_tag == "Grid" else "stack")

        total = len(node.children)
        for i, child in enumerate(node.children):
            child_margin = None
            if gap > 0 and i < total - 1:
                if is_horiz_stack:
                    child_margin = f"0,0,{fmt_length(gap)},0"
                elif is_vert_stack:
                    child_margin = f"0,0,0,{fmt_length(gap)}"
            logical_col = child.layout.grid_column
            logical_row = child.layout.grid_row
            in_star_col = bool(
                logical_cols is not None
                and logical_col is not None
                and 0 <= logical_col < len(logical_cols)
                and logical_cols[logical_col] == "*"
            )
            in_star_row = bool(
                logical_rows is not None
                and logical_row is not None
                and 0 <= logical_row < len(logical_rows)
                and logical_rows[logical_row] == "*"
            )
            child_ctx = EmitContext(
                parent_type=parent_kind,
                in_star_column=in_star_col,
                in_star_row=in_star_row,
                grid_column=physical_index(logical_col, col_spacers),
                grid_row=physical_index(logical_row, row_spacers),
                item_margin=child_margin,
            )
            lines.extend(self._generate_node(child, indent_level + 1, child_ctx))
        lines.append(f"{indent}</{container_tag}>")
        return lines
