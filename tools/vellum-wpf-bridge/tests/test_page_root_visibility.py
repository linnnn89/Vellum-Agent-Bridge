"""Regressions for page-root visibility during WPF export."""

from copy import deepcopy
import json
import unittest
import xml.etree.ElementTree as ET

from vellum_wpf_bridge.models import UiSpec, VellumDocument, VellumNode, VellumPage
from vellum_wpf_bridge.report import ConversionReport
from vellum_wpf_bridge.semantic_mapper import SemanticMapper
from vellum_wpf_bridge.wpf_generator import WpfGenerator


class TestPageRootVisibility(unittest.TestCase):
    def setUp(self):
        self.hidden = VellumNode(
            id="hidden-frame",
            type="frame",
            name="Hidden",
            w=1800,
            h=1200,
            fill="#101010",
            visible=False,
            children=[
                VellumNode(
                    id="hidden-child", type="text", name="Old", text="Retired title"
                )
            ],
        )
        self.frame = VellumNode(
            id="artboard",
            type="frame",
            name="Artboard",
            w=640,
            h=480,
            fill="#ffffff",
            layout="vertical",
            children=[
                VellumNode(id="title", type="text", name="Title", text="Active title")
            ],
        )
        self.label = VellumNode(
            id="caption",
            type="text",
            name="Caption",
            text="Page caption",
            w=160,
            h=28,
        )

    def convert(self, *roots):
        doc = VellumDocument(
            "vellum", 1, "Example", [VellumPage("p", "P", root_nodes=list(roots))]
        )
        original = deepcopy(doc)
        report = ConversionReport()
        spec = SemanticMapper(report).map_document(doc)
        self.assertEqual(doc, original)
        payload = spec.to_dict()
        serialized = json.dumps(payload)
        restored = UiSpec.from_dict(json.loads(serialized))
        self.assertEqual(restored.to_dict(), payload)
        xaml = WpfGenerator().generate_all(restored)["MainWindow.xaml"]
        for omitted in ("hidden-frame", "hidden-child", "Retired title"):
            self.assertNotIn(omitted, serialized)
            self.assertNotIn(omitted, xaml)
        window = ET.fromstring(xaml)
        self.assertEqual(float(window.attrib["Width"]), spec.width)
        self.assertEqual(float(window.attrib["Height"]), spec.height)
        return spec, xaml, report

    def test_hidden_frame_before_single_visible_frame(self):
        spec, xaml, report = self.convert(self.hidden, self.frame)
        self.assertEqual((spec.width, spec.height, spec.theme), (640, 480, "light"))
        self.assertEqual((spec.root.id, spec.root.type), ("artboard", "window"))
        self.assertIn("Active title", xaml)
        visible_spec, visible_xaml, _ = self.convert(self.frame)
        self.assertEqual(spec.to_dict(), visible_spec.to_dict())
        self.assertEqual(xaml, visible_xaml)
        self.assertEqual((report.nodes_skipped, report.nodes_total), (1, 3))
        self.assertNotIn(
            "ABSOLUTE_LAYOUT_NOT_RESPONSIVE", [d.code for d in report.diagnostics]
        )

    def test_multiple_visible_roots_keep_painter_order(self):
        spec, xaml, report = self.convert(self.label, self.hidden, self.frame)
        self.assertEqual((spec.width, spec.height, spec.theme), (640, 480, "light"))
        self.assertEqual(
            [child.id for child in spec.root.children], ["caption", "artboard"]
        )
        self.assertLess(xaml.index("Page caption"), xaml.index("Active title"))
        self.assertIn("<Canvas", xaml)
        self.assertEqual(report.nodes_skipped, 1)
        self.assertIn(
            "ABSOLUTE_LAYOUT_NOT_RESPONSIVE", [d.code for d in report.diagnostics]
        )

    def test_single_non_frame_uses_canvas(self):
        spec, xaml, report = self.convert(self.hidden, self.label)
        self.assertEqual((spec.width, spec.height), (160, 28))
        self.assertEqual([child.id for child in spec.root.children], ["caption"])
        self.assertIn("<Canvas", xaml)
        self.assertIn("Page caption", xaml)
        self.assertEqual(report.nodes_skipped, 1)
        self.assertEqual(
            [d.code for d in report.diagnostics], ["ABSOLUTE_LAYOUT_NOT_RESPONSIVE"]
        )
        self.assertNotIn("multiple", report.diagnostics[0].message.lower())

    def test_all_hidden_matches_empty_page(self):
        empty, empty_xaml, empty_report = self.convert()
        another = VellumNode(id="unused", type="text", name="Unused", visible=False)
        spec, xaml, report = self.convert(self.hidden, another)
        self.assertEqual((spec.width, spec.height, spec.theme), (1200, 800, "dark"))
        self.assertEqual(
            (spec.root.id, spec.root.type, spec.root.children),
            ("window-root", "window", []),
        )
        self.assertEqual((spec, xaml), (empty, empty_xaml))
        self.assertEqual((report.nodes_skipped, report.nodes_total), (2, 2))
        self.assertEqual(empty_report.nodes_skipped, 0)
        self.assertFalse(
            any("multiple" in d.message.lower() for d in report.diagnostics)
        )


if __name__ == "__main__":
    unittest.main()
