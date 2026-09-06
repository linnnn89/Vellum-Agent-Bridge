"""TDD canary tests for the Layout Contract.

These tests encode the agreed invariants before (and independently of)
snapshot/golden output. If they fail, the compiler is not trustworthy.
"""

from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest
import sys
import xml.etree.ElementTree as ET

from vellum_wpf_bridge.layout_contract import (
    allocate_star_tracks,
    expand_tracks_with_spacers,
    physical_index,
)
from vellum_wpf_bridge.models import VellumDocument, VellumNode, VellumPage
from vellum_wpf_bridge.report import ConversionReport
from vellum_wpf_bridge.semantic_mapper import SemanticMapper
from vellum_wpf_bridge.vellum_adapter import VellumDocumentAdapter
from vellum_wpf_bridge.wpf_generator import WpfGenerator


SAMPLES = Path(__file__).parent.parent / "samples"
NS = {"w": "http://schemas.microsoft.com/winfx/2006/xaml/presentation"}


def convert_file(path: Path):
    doc = VellumDocumentAdapter().load_from_file(path)
    report = ConversionReport()
    spec = SemanticMapper(report).map_document(doc)
    xaml = WpfGenerator().generate_all(spec)["MainWindow.xaml"]
    return spec, xaml, report


def convert_tree(root: VellumNode):
    doc = VellumDocument(
        format="vellum",
        version=1,
        name="T",
        pages=[VellumPage(id="p", name="P", root_nodes=[root])],
    )
    report = ConversionReport()
    spec = SemanticMapper(report).map_document(doc)
    xaml = WpfGenerator().generate_all(spec)["MainWindow.xaml"]
    return spec, xaml, report


def as_child(node: VellumNode) -> VellumNode:
    """Host `node` under a dummy window frame so it is not projected as window-root fill."""
    return VellumNode(
        id="host",
        type="frame",
        name="Host",
        w=max(node.w, 1),
        h=max(node.h, 1),
        layout="vertical",
        children=[node],
    )


def first_grid(xaml: str):
    tree = ET.fromstring(xaml)
    for el in tree.iter():
        tag = el.tag.split("}", 1)[-1]
        if tag == "Grid":
            return el
    raise AssertionError("no Grid in XAML")


def column_widths(grid) -> list:
    defs = None
    for child in list(grid):
        if child.tag.split("}", 1)[-1] == "Grid.ColumnDefinitions":
            defs = child
            break
    if defs is None:
        raise AssertionError("no ColumnDefinitions")
    return [c.get("Width") for c in list(defs)]


def row_heights(grid) -> list:
    defs = None
    for child in list(grid):
        if child.tag.split("}", 1)[-1] == "Grid.RowDefinitions":
            defs = child
            break
    if defs is None:
        raise AssertionError("no RowDefinitions")
    return [c.get("Height") for c in list(defs)]


class TestStarAllocationCanary(unittest.TestCase):
    """Heartbeat: 260 | * | 260 grows only in the middle."""

    def test_allocate_1280_then_1600_delta_goes_to_star(self):
        tracks = [260, "*", 260]
        at_1280 = allocate_star_tracks(tracks, 1280)
        at_1600 = allocate_star_tracks(tracks, 1600)
        self.assertEqual(at_1280, [260.0, 760.0, 260.0])
        self.assertEqual(at_1600, [260.0, 1080.0, 260.0])
        delta = [b - a for a, b in zip(at_1280, at_1600)]
        self.assertEqual(delta, [0.0, 320.0, 0.0])

    def test_generated_canary_tracks_obey_the_same_allocation(self):
        spec, xaml, _ = convert_file(SAMPLES / "canary-three-column.vellum")
        self.assertEqual(spec.root.layout.columns, [260.0, "*", 260.0])
        widths = column_widths(first_grid(xaml))
        self.assertEqual(widths, ["260", "*", "260"])
        at_1280 = allocate_star_tracks(widths, 1280)
        at_1600 = allocate_star_tracks(widths, 1600)
        self.assertEqual(at_1280, [260.0, 760.0, 260.0])
        self.assertEqual(at_1600, [260.0, 1080.0, 260.0])
        self.assertEqual(
            [b - a for a, b in zip(at_1280, at_1600)],
            [0.0, 320.0, 0.0],
        )

    def test_gap_spacers_do_not_steal_from_fixed_content_tracks(self):
        logical = [260, "*", 260]
        physical, has_spacers = expand_tracks_with_spacers(logical, 12)
        self.assertTrue(has_spacers)
        self.assertEqual(physical, [260, 12, "*", 12, 260])
        self.assertEqual(physical_index(0, True), 0)
        self.assertEqual(physical_index(1, True), 2)
        self.assertEqual(physical_index(2, True), 4)

        # content width 804 = 260+12+260+12+260 with star=260
        allocated = allocate_star_tracks(physical, 804)
        self.assertEqual(allocated, [260.0, 12.0, 260.0, 12.0, 260.0])
        # stretching available space only grows the star, never the 260s or gaps
        stretched = allocate_star_tracks(physical, 804 + 320)
        self.assertEqual(stretched[0], 260.0)
        self.assertEqual(stretched[1], 12.0)
        self.assertEqual(stretched[2], 580.0)
        self.assertEqual(stretched[4], 260.0)

    def test_generated_gap_xaml_matches_spacer_tracks(self):
        spec, xaml, _ = convert_file(SAMPLES / "canary-gap.vellum")
        self.assertEqual(spec.root.layout.columns, [260.0, "*", 260.0])
        self.assertEqual(column_widths(first_grid(xaml)), ["260", "12", "*", "12", "260"])


class TestFlowSelection(unittest.TestCase):
    def test_autolayout_without_fill_emits_stackpanel_not_grid(self):
        a = VellumNode(id="a", type="rect", name="A", w=40, h=20, fill="#111")
        b = VellumNode(id="b", type="rect", name="B", w=40, h=20, fill="#222")
        parent = VellumNode(
            id="row", type="frame", name="Row", w=100, h=20,
            layout="horizontal", gap=8, children=[a, b],
        )
        spec, xaml, _ = convert_tree(parent)
        self.assertEqual(spec.root.layout.type, "stack")
        self.assertIsNone(spec.root.layout.columns)
        self.assertIn('Orientation="Horizontal"', xaml)
        self.assertIn("<StackPanel", xaml)
        self.assertNotIn("ColumnDefinition", xaml)
        self.assertIn('Margin="0,0,8,0"', xaml)

    def test_vertical_stretch_emits_star_row_not_stackpanel(self):
        header = VellumNode(id="h", type="frame", name="Header", w=200, h=50, fill="#111")
        body = VellumNode(
            id="b", type="frame", name="Body", w=200, h=100, fill="#222", constraint_v="stretch",
        )
        footer = VellumNode(id="f", type="frame", name="Footer", w=200, h=40, fill="#111")
        parent = VellumNode(
            id="col", type="frame", name="Col", w=200, h=400,
            layout="vertical", gap=0, children=[header, body, footer],
        )
        spec, xaml, _ = convert_tree(parent)
        self.assertEqual(spec.root.layout.type, "grid")
        self.assertEqual(spec.root.layout.rows, [50.0, "*", 40.0])
        self.assertEqual(row_heights(first_grid(xaml)), ["50", "*", "40"])
        self.assertIn('Grid.Row="1"', xaml)
        self.assertNotIn('Height="100"', xaml)


class TestSizingAnchoringSplit(unittest.TestCase):
    def test_text_stays_fixed_not_hug(self):
        text = VellumNode(
            id="t", type="text", name="Paragraph", w=320, h=48,
            text="This is a long paragraph that must keep wrapping.",
            fill="#fff",
        )
        spec, _, _ = convert_tree(as_child(text))
        node = spec.root.children[0]
        self.assertEqual(node.type, "text")
        self.assertEqual(node.layout.width_mode, "fixed")
        self.assertEqual(node.layout.width, 320.0)
        self.assertEqual(node.layout.design_width, 320.0)
        self.assertNotEqual(node.layout.width_mode, "hug")

    def test_stretch_sets_fill_but_keeps_constraint_and_design_size(self):
        child = VellumNode(
            id="c", type="frame", name="Center", w=760, h=400,
            fill="#333", constraint_h="stretch",
        )
        parent = VellumNode(
            id="row", type="frame", name="Row", w=1280, h=400,
            layout="horizontal", children=[
                VellumNode(id="l", type="frame", name="L", w=260, h=400, fill="#222"),
                child,
                VellumNode(id="r", type="frame", name="R", w=260, h=400, fill="#222"),
            ],
        )
        spec, xaml, _ = convert_tree(parent)
        mid = spec.root.children[1]
        self.assertEqual(mid.layout.width_mode, "fill")
        self.assertEqual(mid.layout.constraint_h, "stretch")
        self.assertEqual(mid.layout.design_width, 760.0)
        self.assertIsNone(mid.layout.width)
        self.assertNotIn('Width="760"', xaml)

    def test_window_root_is_fill_without_inventing_hug_or_dropping_source_anchor(self):
        spec, xaml, _ = convert_file(SAMPLES / "canary-three-column.vellum")
        root = spec.root
        self.assertEqual(root.layout.width_mode, "fill")
        self.assertEqual(root.layout.height_mode, "fill")
        self.assertEqual(root.layout.constraint_h, "left")
        self.assertEqual(root.layout.constraint_v, "top")
        self.assertEqual(root.layout.design_width, 1280.0)
        grid = first_grid(xaml)
        self.assertIsNone(grid.get("Width"))
        self.assertIsNone(grid.get("Height"))

    def test_scale_constraint_is_kept_and_diagnosed(self):
        node = VellumNode(
            id="s", type="frame", name="Scaled", w=100, h=100, fill="#111",
            constraint_h="scale",
        )
        spec, _, report = convert_tree(as_child(node))
        child = spec.root.children[0]
        self.assertEqual(child.layout.constraint_h, "scale")
        self.assertEqual(child.layout.width_mode, "fixed")
        self.assertTrue(any(d.code == "CONSTRAINT_SCALE_NOT_RESPONSIVE" for d in report.diagnostics))

    def test_right_anchor_is_kept_and_diagnosed_not_turned_into_fill(self):
        node = VellumNode(
            id="s", type="frame", name="DockRight", w=100, h=40, fill="#111",
            constraint_h="right",
        )
        spec, _, report = convert_tree(as_child(node))
        child = spec.root.children[0]
        self.assertEqual(child.layout.constraint_h, "right")
        self.assertEqual(child.layout.width_mode, "fixed")
        self.assertTrue(any(d.code == "CONSTRAINT_PARTIAL" for d in report.diagnostics))


class TestDiagnosticsAndCounts(unittest.TestCase):
    def test_clip_is_warned(self):
        node = VellumNode(id="c", type="frame", name="Clip", w=80, h=80, fill="#111", clip=True)
        _, _, report = convert_tree(node)
        self.assertTrue(any(d.code == "CLIP_IGNORED" for d in report.diagnostics))

    def test_absorbed_children_count_toward_total(self):
        label = VellumNode(id="txt", type="text", name="SendBtnText", w=80, h=20, text="Send", fill="#fff")
        btn = VellumNode(
            id="btn", type="frame", name="SendButton", w=100, h=38, fill="#8462e8",
            radius=6, children=[label],
        )
        _, _, report = convert_tree(btn)
        self.assertEqual(report.nodes_total, 2)
        self.assertEqual(report.nodes_absorbed, 1)
        self.assertEqual(report.nodes_converted, 1)
        self.assertEqual(report.absorbed[0]["id"], "txt")

    def test_hidden_children_are_skipped_not_emitted(self):
        shown = VellumNode(id="a", type="rect", name="Shown", w=40, h=20, fill="#111")
        hidden = VellumNode(
            id="b", type="rect", name="Hidden", w=40, h=20, fill="#222", visible=False,
        )
        parent = VellumNode(
            id="row", type="frame", name="Row", w=80, h=20,
            layout="horizontal", children=[shown, hidden],
        )
        spec, xaml, report = convert_tree(parent)
        self.assertEqual(len(spec.root.children), 1)
        self.assertEqual(spec.root.children[0].id, "a")
        self.assertEqual(report.nodes_skipped, 1)
        self.assertNotIn("Hidden", xaml)


class TestWpfRuntimeStarMeasure(unittest.TestCase):
    """Runtime canary: WPF Grid.ActualWidth at content 1280 then 1600."""

    def test_wpf_grid_actual_width_delta(self):
        dotnet = shutil.which("dotnet")
        if sys.platform != "win32" or not dotnet:
            self.skipTest("dotnet SDK not available")
        project = Path(__file__).parent / "wpf-canary" / "WpfCanary.csproj"
        if not project.exists():
            self.skipTest("WPF canary project missing")

        spec, xaml, _ = convert_file(SAMPLES / "canary-three-column.vellum")
        self.assertEqual(spec.root.layout.columns, [260.0, "*", 260.0])
        with tempfile.TemporaryDirectory() as tmp:
            xaml_path = Path(tmp) / "canary.xaml"
            xaml_path.write_text(xaml, encoding="utf-8")
            result = subprocess.run(
                [dotnet, "run", "--project", str(project), "--", str(xaml_path), "1280", "1600"],
                capture_output=True,
                text=True,
                timeout=120,
            )
        if result.returncode != 0:
            self.fail(result.stdout + "\n" + result.stderr)
        # Expected line: 1280=260,760,260;1600=260,1080,260;delta=0,320,0
        self.assertIn("1280=260,760,260", result.stdout.replace(".0", ""))
        self.assertIn("1600=260,1080,260", result.stdout.replace(".0", ""))
        self.assertIn("delta=0,320,0", result.stdout.replace(".0", ""))


if __name__ == "__main__":
    unittest.main()
