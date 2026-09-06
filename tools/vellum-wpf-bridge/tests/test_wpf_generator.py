"""Unit tests for WpfGenerator and XAML validity."""

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from vellum_wpf_bridge.resources import ResourceManager
from vellum_wpf_bridge.semantic_mapper import SemanticMapper
from vellum_wpf_bridge.vellum_adapter import VellumDocumentAdapter
from vellum_wpf_bridge.wpf_generator import WpfGenerator


class TestWpfGenerator(unittest.TestCase):

    def setUp(self):
        self.sample_path = (
            Path(__file__).parent.parent / "samples" / "tabletop-chat.vellum"
        )
        self.adapter = VellumDocumentAdapter()
        self.doc = self.adapter.load_from_file(self.sample_path)
        self.mapper = SemanticMapper()
        self.spec = self.mapper.map_document(self.doc)
        self.rm = ResourceManager()
        self.rm.extract_from_document_tokens(self.doc)
        self.generator = WpfGenerator(resource_manager=self.rm)

    def test_generate_and_parse_valid_xml(self):
        outputs = self.generator.generate_all(self.spec, app_namespace="GeneratedWpfDemo")

        self.assertIn("MainWindow.xaml", outputs)
        self.assertIn("Resources.xaml", outputs)
        self.assertIn("App.xaml", outputs)

        # 1. Parse Resources.xaml
        res_xml = outputs["Resources.xaml"]
        root_res = ET.fromstring(res_xml)
        self.assertIn("ResourceDictionary", root_res.tag)
        # Should have brushes
        self.assertGreater(len(root_res), 0)

        # 2. Parse App.xaml
        app_xml = outputs["App.xaml"]
        root_app = ET.fromstring(app_xml)
        self.assertIn("Application", root_app.tag)

        # 3. Parse MainWindow.xaml
        win_xml = outputs["MainWindow.xaml"]
        root_win = ET.fromstring(win_xml)
        self.assertIn("Window", root_win.tag)

        # Tabletop sample is auto-layout; the window content must not be a Canvas.
        self.assertNotIn("<Canvas", win_xml)

        # Multi-column layout uses Grid star sizing (integer track sizes).
        self.assertIn('<ColumnDefinition Width="260"/>', win_xml)
        self.assertIn('<ColumnDefinition Width="*"/>', win_xml)

        # Compiler must not infer Command bindings from button labels.
        self.assertNotIn("Command=", win_xml)
        self.assertIn('x:Name="BtnSend"', win_xml)
        self.assertIn('x:Name="InputMessage"', win_xml)

        # Assert Source metadata comments are included
        self.assertIn("<!-- Vellum:", win_xml)


if __name__ == "__main__":
    unittest.main()
