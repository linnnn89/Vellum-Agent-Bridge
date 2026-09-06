"""LayoutContract: project Vellum geometry/constraints into sizing + anchoring.

Sizing (widthMode/heightMode) and anchoring (constraintH/constraintV) are
independent. This stage never infers hug from node type or layer names.
"""

from typing import List, Optional, Tuple, Union

from .models import UiLayout, UiNode, VellumNode
from .report import ConversionReport


def apply_sizing_contract(
    layout: UiLayout,
    node: VellumNode,
    *,
    is_window_root: bool = False,
    report: Optional[ConversionReport] = None,
) -> UiLayout:
    """Fill sizing/anchoring fields from a Vellum node. Does not change flow type."""
    layout.constraint_h = node.constraint_h or "left"
    layout.constraint_v = node.constraint_v or "top"
    layout.design_width = node.w if node.w > 0 else None
    layout.design_height = node.h if node.h > 0 else None
    layout.x = node.x
    layout.y = node.y

    if is_window_root:
        layout.width_mode = "fill"
        layout.height_mode = "fill"
        layout.width = None
        layout.height = None
    else:
        layout.width_mode = "fill" if layout.constraint_h == "stretch" else "fixed"
        layout.height_mode = "fill" if layout.constraint_v == "stretch" else "fixed"
        layout.width = layout.design_width if layout.width_mode == "fixed" else None
        layout.height = layout.design_height if layout.height_mode == "fixed" else None

    if report is not None:
        if layout.constraint_h == "scale" or layout.constraint_v == "scale":
            report.add_diagnostic(
                "warning",
                "CONSTRAINT_SCALE_NOT_RESPONSIVE",
                "constraint scale is preserved in the spec but not mapped to a responsive WPF size.",
                node.id,
            )
        if layout.constraint_h in ("right", "center") or layout.constraint_v in ("bottom", "center"):
            report.add_diagnostic(
                "warning",
                "CONSTRAINT_PARTIAL",
                f"anchoring constraintH={layout.constraint_h} constraintV={layout.constraint_v} is kept in IR; WPF v2 only honors stretch vs fixed.",
                node.id,
            )
    return layout


def note_appearance(node: VellumNode, report: ConversionReport) -> None:
    fill_type = (node.fill_type or "solid").lower()
    if fill_type not in ("solid", "none", ""):
        report.add_diagnostic(
            "warning",
            "GRADIENT_FALLBACK",
            f"fillType '{node.fill_type}' is not supported; first solid fill used.",
            node.id,
        )
    if node.shadow:
        report.add_diagnostic(
            "warning",
            "SHADOW_IGNORED",
            "shadow is parsed but not emitted in XAML.",
            node.id,
        )
    if node.clip:
        report.add_diagnostic(
            "warning",
            "CLIP_IGNORED",
            "clip is parsed but not emitted in XAML.",
            node.id,
        )


def main_axis_is_fill(child: UiNode, horizontal: bool) -> bool:
    if horizontal:
        return child.layout.width_mode == "fill"
    return child.layout.height_mode == "fill"


def autolayout_tracks(
    parent: VellumNode,
    children: List[VellumNode],
    mapped: List[UiNode],
    report: ConversionReport,
) -> Tuple[UiLayout, List[UiNode]]:
    """Build stack or grid tracks from auto-layout + child widthMode/heightMode.

    Main-axis fill requires Grid. Names are never consulted.
    """
    horizontal = parent.layout == "horizontal"
    direction = "horizontal" if horizontal else "vertical"
    fill_indexes = [i for i, child in enumerate(mapped) if main_axis_is_fill(child, horizontal)]

    if fill_indexes:
        if len(fill_indexes) > 1:
            report.add_normalized(
                "LAYOUT_MULTI_STRETCH_NORMALIZED",
                f"{len(fill_indexes)} stretch children on the {direction} axis were normalized to equal star sizing.",
                parent.id,
            )
        tracks: List[Union[float, str]] = []
        for i, child_ui in enumerate(mapped):
            if i in fill_indexes:
                tracks.append("*")
            else:
                size = child_ui.layout.design_width if horizontal else child_ui.layout.design_height
                tracks.append(size if size is not None else 0)
            if horizontal:
                mapped[i].layout.grid_column = i
            else:
                mapped[i].layout.grid_row = i
        layout = UiLayout(
            type="grid",
            direction=direction,
            gap=parent.gap,
            padding=parent.padding,
            align=parent.layout_align,
        )
        if horizontal:
            layout.columns = tracks
        else:
            layout.rows = tracks
        return layout, mapped

    layout = UiLayout(
        type="stack",
        direction=direction,
        gap=parent.gap if parent.gap is not None else 0.0,
        padding=parent.padding,
        align=parent.layout_align,
    )
    return layout, mapped


def expand_tracks_with_spacers(
    tracks: List[Union[float, str]], gap: Optional[float]
) -> Tuple[List[Union[float, str]], bool]:
    """Expand logical tracks with spacer tracks. Spec stays logical; XAML is physical."""
    if not tracks or not gap or gap <= 0:
        return list(tracks), False
    physical: List[Union[float, str]] = []
    for i, track in enumerate(tracks):
        if i:
            physical.append(gap)
        physical.append(track)
    return physical, True


def physical_index(logical: Optional[int], has_spacers: bool) -> Optional[int]:
    if logical is None:
        return None
    return logical * 2 if has_spacers else logical


def parse_track_size(value: Union[float, int, str]) -> Tuple[str, float]:
    """Parse a GridLength-like track into ('pixel'|'star'|'auto', weight)."""
    if value == "*" or value == "1*":
        return "star", 1.0
    if isinstance(value, str):
        raw = value.strip()
        if raw.lower() == "auto":
            return "auto", 0.0
        if raw.endswith("*"):
            weight = raw[:-1]
            return "star", float(weight) if weight else 1.0
        return "pixel", float(raw)
    return "pixel", float(value)


def allocate_star_tracks(
    tracks: List[Union[float, int, str]], available: float
) -> List[float]:
    """Reproduce WPF Grid star allocation: pixels first, remainder split by star weight.

    This is the canary: 260 | * | 260 at 1280 → 260 | 760 | 260,
    at 1600 → 260 | 1080 | 260 (delta 0 | +320 | 0).
    """
    parsed = [parse_track_size(t) for t in tracks]
    star_weight = sum(weight for kind, weight in parsed if kind == "star")
    fixed = sum(weight for kind, weight in parsed if kind == "pixel")
    remaining = max(0.0, float(available) - fixed)
    allocated: List[float] = []
    for kind, weight in parsed:
        if kind == "star":
            allocated.append(remaining * (weight / star_weight) if star_weight else 0.0)
        elif kind == "auto":
            allocated.append(0.0)
        else:
            allocated.append(weight)
    return allocated
