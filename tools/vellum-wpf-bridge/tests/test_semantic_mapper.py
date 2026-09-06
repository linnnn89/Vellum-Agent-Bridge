"""Unit tests for SemanticMapper."""

from pathlib import Path
import unittest

from vellum_wpf_bridge.models import VellumDocument, VellumNode, VellumPage
from vellum_wpf_bridge.report import ConversionReport
from vellum_wpf_bridge.semantic_mapper import SemanticMapper
from vellum_wpf_bridge.vellum_adapter import VellumDocumentAdapter


class TestSemanticMapper(unittest.TestCase):

    def setUp(self):
        self.report = ConversionReport()
        self.mapper = SemanticMapper(report=self.report)
        self.sample_path = (
            Path(__file__).parent.parent / "samples" / "tabletop-chat.vellum"
        )
        self.adapter = VellumDocumentAdapter()

    def test_map_sample_document(self):
        doc = self.adapter.load_from_file(self.sample_path)
        spec = self.mapper.map_document(doc)

        self.assertEqual(spec.version, "0.1")
        self.assertEqual(spec.theme, "dark")
        self.assertEqual(spec.type, "window")
        self.assertIsNotNone(spec.root)

        root = spec.root
        # Window root contains: AppHeader, MainWorkspace, ActionBar
        self.assertEqual(len(root.children), 3)

        header = root.children[0]
        workspace = root.children[1]
        action_bar = root.children[2]

        self.assertEqual(header.name, "AppHeader")
        self.assertEqual(workspace.name, "MainWorkspace")
        self.assertEqual(action_bar.name, "ActionBar")

        # Workspace has 3 columns: CharacterSidebar, ChatArea, InspectorSidebar
        self.assertEqual(len(workspace.children), 3)
        char_sidebar = workspace.children[0]
        chat_area = workspace.children[1]
        inspector = workspace.children[2]

        self.assertEqual(char_sidebar.name, "CharacterSidebar")
        self.assertEqual(chat_area.name, "ChatArea")
        self.assertEqual(inspector.name, "InspectorSidebar")

        # Check column definitions: Left fixed, middle *, right fixed
        self.assertEqual(workspace.layout.columns, [260.0, "*", 260.0])
        self.assertEqual(workspace.layout.type, "grid")
        self.assertEqual(chat_area.layout.width_mode, "fill")
        self.assertEqual(chat_area.layout.constraint_h, "stretch")
        self.assertEqual(header.layout.constraint_h, "stretch")

        # Check Button heuristic in ActionBar: Send button is mapped to button
        send_btn = next((c for c in action_bar.children if c.type == "button"), None)
        self.assertIsNotNone(send_btn)
        self.assertEqual(send_btn.props.get("text"), "Send")
        self.assertEqual(send_btn.props.get("command"), "SendCommand")

        # Check Input heuristic in ActionBar: Message input is mapped to input
        msg_input = next((c for c in action_bar.children if c.type == "input"), None)
        self.assertIsNotNone(msg_input)
        self.assertIn("Describe your action", msg_input.props.get("placeholder", ""))

    def test_fallback_unsupported_node(self):
        # Create a document with a complex path
        doc = VellumDocument(
            format="vellum",
            version=1,
            name="VectorDoc",
            pages=[
                VellumPage(
                    id="p1",
                    name="P1",
                    root_nodes=[
                        VellumNode(
                            id="path-1",
                            type="path",
                            name="SplineCurve",
                            w=100,
                            h=100,
                        )
                    ],
                )
            ],
        )
        report = ConversionReport()
        mapper = SemanticMapper(report=report)
        spec = mapper.map_document(doc)

        self.assertEqual(report.nodes_fallback, 1)
        self.assertEqual(len(report.unsupported), 1)
        self.assertEqual(report.unsupported[0].type, "path")
        self.assertIn("Vector type 'path'", report.unsupported[0].reason)


if __name__ == "__main__":
    unittest.main()
