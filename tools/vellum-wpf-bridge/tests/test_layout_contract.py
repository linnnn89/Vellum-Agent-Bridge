"""LayoutContract tests: sizing/anchoring split, Grid vs StackPanel, gap, Canvas."""

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from vellum_wpf_bridge.models import VellumDocument, VellumNode, VellumPage
from vellum_wpf_bridge.report import ConversionReport
from vellum_wpf_bridge.semantic_mapper import SemanticMapper
from vellum_wpf_bridge.vellum_adapter import VellumDocumentAdapter
from vellum_wpf_bridge.wpf_generator import WpfGenerator


SAMPLES = Path(__file__).parent.parent / "samples"
NS = {"w": "http://schemas.microsoft.com/winfx/2006/xaml/presentation"}


def convert(path: Path):
    adapter = VellumDocumentAdapter()
    doc = adapter.load_from_file(path)
    report = ConversionReport()
    spec = SemanticMapper(report).map_document(doc)
    xaml = WpfGenerator().generate_all(spec)["MainWindow.xaml"]
    return spec, xaml, report


def local(tag: str) -> str:
    return tag.split("}", 1)[-1]


class TestLayoutContract(unittest.TestCase):
    def test_three_column_canary_uses_star_without_child_width(self):
        spec, xaml, _ = convert(SAMPLES / "canary-three-column.vellum")
        root = spec.root
        self.assertEqual(root.layout.type, "grid")
        self.assertEqual(root.layout.columns, [260.0, "*", 260.0])
        self.assertEqual(root.layout.width_mode, "fill")
        self.assertEqual(root.layout.height_mode, "fill")
        self.assertIsNone(root.layout.width)
        self.assertIsNone(root.layout.height)

        mid = root.children[1]
        self.assertEqual(mid.layout.width_mode, "fill")
        self.assertEqual(mid.layout.constraint_h, "stretch")
        self.assertEqual(mid.layout.design_width, 760.0)
        self.assertIsNone(mid.layout.width)

        self.assertIn('<ColumnDefinition Width="260"/>', xaml)
        self.assertIn('<ColumnDefinition Width="*"/>', xaml)
        self.assertNotIn('Width="1280"', xaml.split(">", 1)[1])  # content, not Window
        # fill child in star column must not freeze pixel width
        self.assertNotIn('Width="760"', xaml)
        center_block = xaml
        self.assertNotRegex(center_block, r'Grid\.Column="1"[^>]*Width="')

    def test_grid_gap_uses_spacer_tracks_not_inner_margin(self):
        spec, xaml, _ = convert(SAMPLES / "canary-gap.vellum")
        self.assertEqual(spec.root.layout.columns, [260.0, "*", 260.0])
        self.assertEqual(spec.root.layout.gap, 12.0)
        self.assertIn('<ColumnDefinition Width="260"/>', xaml)
        self.assertIn('<ColumnDefinition Width="12"/>', xaml)
        self.assertIn('<ColumnDefinition Width="*"/>', xaml)
        self.assertIn('Grid.Column="2"', xaml)
        self.assertIn('Grid.Column="4"', xaml)
        self.assertNotIn('Margin="0,0,12,0"', xaml)

    def test_freeform_preserves_canvas_coordinates(self):
        spec, xaml, report = convert(SAMPLES / "canary-freeform.vellum")
        self.assertEqual(spec.root.layout.type, "absolute")
        codes = [d.code for d in report.diagnostics]
        self.assertIn("ABSOLUTE_LAYOUT_NOT_RESPONSIVE", codes)
        self.assertIn("<Canvas", xaml)
        self.assertIn('Canvas.Left="10"', xaml)
        self.assertIn('Canvas.Top="10"', xaml)
        self.assertIn('Canvas.Left="40"', xaml)
        self.assertIn('Canvas.Top="40"', xaml)
        self.assertIn('Width="80"', xaml)

    def test_name_does_not_steal_star_row(self):
        heading = VellumNode(id="h", type="text", name="ChatHeading", w=100, h=24, text="Title", fill="#fff")
        card = VellumNode(id="c1", type="frame", name="Msg1", w=100, h=80, fill="#333", radius=8)
        area = VellumNode(
            id="chat", type="frame", name="ChatArea", w=700, h=660,
            layout="vertical", gap=12, fill="#111", radius=10,
            children=[heading, card],
        )
        doc = VellumDocument(
            format="vellum", version=1, name="t",
            pages=[VellumPage(id="p", name="P", root_nodes=[area])],
        )
        spec = SemanticMapper(ConversionReport()).map_document(doc)
        self.assertEqual(spec.root.layout.type, "stack")
        self.assertIsNone(spec.root.layout.rows)
        self.assertEqual(spec.root.children[0].type, "text")
        self.assertNotEqual(spec.root.children[0].layout.height_mode, "fill")

    def test_settings_panel_is_not_a_button(self):
        child = VellumNode(id="tx", type="text", name="Label", w=80, h=20, text="Settings", fill="#fff")
        panel = VellumNode(
            id="s", type="frame", name="SettingsPanel", w=120, h=40, fill="#333", radius=8, children=[child],
        )
        doc = VellumDocument(
            format="vellum", version=1, name="b",
            pages=[VellumPage(id="p", name="P", root_nodes=[panel])],
        )
        spec = SemanticMapper(ConversionReport()).map_document(doc)
        self.assertNotEqual(spec.root.type, "button")

    def test_multi_stretch_is_normalized_with_diagnostic(self):
        a = VellumNode(id="a", type="frame", name="A", w=300, h=40, fill="#111", constraint_h="stretch")
        b = VellumNode(id="b", type="frame", name="B", w=300, h=40, fill="#222", constraint_h="stretch")
        parent = VellumNode(
            id="row", type="frame", name="Row", w=600, h=40, layout="horizontal", children=[a, b],
        )
        doc = VellumDocument(
            format="vellum", version=1, name="m",
            pages=[VellumPage(id="p", name="P", root_nodes=[parent])],
        )
        report = ConversionReport()
        spec = SemanticMapper(report).map_document(doc)
        self.assertEqual(spec.root.layout.columns, ["*", "*"])
        self.assertTrue(any(d.code == "LAYOUT_MULTI_STRETCH_NORMALIZED" for d in report.diagnostics))

    def test_gradient_and_shadow_are_warned(self):
        n = VellumNode(
            id="g", type="frame", name="Hero", w=400, h=200,
            fill="#8462e8", fill2="#e1d8ff", fill_type="linear", shadow=True, radius=12,
        )
        doc = VellumDocument(
            format="vellum", version=1, name="g",
            pages=[VellumPage(id="p", name="P", root_nodes=[n])],
        )
        report = ConversionReport()
        SemanticMapper(report).map_document(doc)
        codes = [d.code for d in report.diagnostics]
        self.assertIn("GRADIENT_FALLBACK", codes)
        self.assertIn("SHADOW_IGNORED", codes)

    def test_tabletop_workspace_is_logical_three_column_grid(self):
        spec, xaml, report = convert(SAMPLES / "tabletop-chat.vellum")
        workspace = spec.root.children[1]
        self.assertEqual(workspace.name, "MainWorkspace")
        self.assertEqual(workspace.layout.type, "grid")
        self.assertEqual(workspace.layout.columns, [260.0, "*", 260.0])
        chat = workspace.children[1]
        self.assertEqual(chat.layout.width_mode, "fill")
        self.assertEqual(chat.layout.type, "stack")
        self.assertNotIn("<Canvas", xaml)
        self.assertGreater(report.nodes_total, report.nodes_converted)
        self.assertGreater(report.nodes_absorbed, 0)

    def test_fill_child_in_generated_tabletop_has_no_frozen_workspace_height(self):
        _, xaml, _ = convert(SAMPLES / "tabletop-chat.vellum")
        self.assertNotIn('Height="660"', xaml)
        self.assertNotIn('Width="704"', xaml)
        self.assertNotIn('Width="1248"', xaml)
        tree = ET.fromstring(xaml)
        # Root content element (skip comments) should be Grid without Width/Height.
        content = None
        for child in list(tree):
            if local(child.tag) in ("Grid", "Border", "StackPanel", "Canvas"):
                content = child
                break
        self.assertIsNotNone(content)
        self.assertIsNone(content.get("Width"))
        self.assertIsNone(content.get("Height"))


if __name__ == "__main__":
    unittest.main()
