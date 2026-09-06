"""Unit tests for VellumDocumentAdapter."""

import json
from pathlib import Path
import unittest

from vellum_wpf_bridge.vellum_adapter import VellumDocumentAdapter


class TestVellumAdapter(unittest.TestCase):

    def setUp(self):
        self.adapter = VellumDocumentAdapter()
        self.sample_path = (
            Path(__file__).parent.parent / "samples" / "tabletop-chat.vellum"
        )

    def test_load_sample_file(self):
        doc = self.adapter.load_from_file(self.sample_path)
        self.assertEqual(doc.format, "vellum")
        self.assertEqual(doc.version, 1)
        self.assertEqual(len(doc.pages), 1)

        page = doc.pages[0]
        self.assertEqual(page.id, "page-tabletop-1")
        self.assertGreater(len(page.nodes), 10)

        # Hierarchy checks
        root_nodes = page.root_nodes
        self.assertEqual(len(root_nodes), 1)
        root = root_nodes[0]
        self.assertEqual(root.id, "win-root")
        self.assertGreater(len(root.children), 0)

        # Check AppHeader child of win-root
        header = next((c for c in root.children if c.id == "app-header"), None)
        self.assertIsNotNone(header)
        self.assertEqual(header.parent_id, "win-root")

        # Check title text child of header
        title = next((c for c in header.children if c.id == "app-title"), None)
        self.assertIsNotNone(title)
        self.assertEqual(title.text, "⚔ Tabletop Campaign Workspace")

    def test_invalid_format_raises(self):
        bad_json = json.dumps({"format": "figma", "version": 1, "pages": []})
        with self.assertRaises(ValueError):
            self.adapter.load_from_json(bad_json)


if __name__ == "__main__":
    unittest.main()
