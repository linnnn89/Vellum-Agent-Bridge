"""Vellum-Agent-Bridge 0.3 workflow tests."""

from copy import deepcopy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from vellum_wpf_bridge.cli import spec_hash
from vellum_wpf_bridge.models import UiNode, UiSpec, UiStyle
from vellum_wpf_bridge.refiner import (
    PatchValidationError,
    SafeAgentRefiner,
    compute_spec_canonical_sha256,
)
from vellum_wpf_bridge.semantic_mapper import SemanticMapper
from vellum_wpf_bridge.vellum_adapter import VellumDocumentAdapter
from vellum_wpf_bridge.wpf_generator import WpfGenerator
from test_review_findings import SAMPLE_SPEC, _patch


SAMPLES = Path(__file__).parent.parent / "samples"


class TestGeneratedNameStable(unittest.TestCase):
    def test_agent_rename_does_not_change_x_name(self):
        spec = deepcopy(SAMPLE_SPEC)
        spec["root"]["generatedName"] = "SendBtn"
        spec["root"]["name"] = "SendButton"
        xaml_before = WpfGenerator().generate_main_window_xaml(UiSpec.from_dict(spec))
        self.assertIn('x:Name="SendBtn"', xaml_before)

        patched, _ = SafeAgentRefiner().apply_patch(
            spec, _patch(spec, "name", "Primary Send Control")
        )
        self.assertEqual(patched["root"]["name"], "Primary Send Control")
        self.assertEqual(patched["root"]["generatedName"], "SendBtn")
        xaml_after = WpfGenerator().generate_main_window_xaml(UiSpec.from_dict(patched))
        self.assertIn('x:Name="SendBtn"', xaml_after)
        self.assertNotIn('x:Name="PrimarySendControl"', xaml_after)

    def test_agent_cannot_patch_generated_name(self):
        spec = deepcopy(SAMPLE_SPEC)
        spec["root"]["generatedName"] = "SendBtn"
        with self.assertRaises(PatchValidationError):
            SafeAgentRefiner().validate_patch(spec, _patch(spec, "generatedName", "Hacked"))


class TestNoInferredCommand(unittest.TestCase):
    def test_sample_mapper_does_not_emit_command(self):
        doc = VellumDocumentAdapter().load_from_file(SAMPLES / "tabletop-chat.vellum")
        spec = SemanticMapper().map_document(doc)
        xaml = WpfGenerator().generate_all(spec)["MainWindow.xaml"]
        self.assertNotIn("Command=", xaml)
        send = next(n for n in spec.root.children[2].children if n.type == "button")
        self.assertNotIn("command", send.props)
        self.assertEqual(send.props.get("commandCandidate"), "SendCommand")

    def test_explicit_command_still_binds(self):
        spec = UiSpec(
            root=UiNode(
                id="btn-send",
                type="button",
                generated_name="BtnSend",
                props={"text": "Send", "command": "SendCommand"},
            )
        )
        xaml = WpfGenerator().generate_main_window_xaml(spec)
        self.assertIn('Command="{Binding SendCommand}"', xaml)


class TestSpecHashAndPatchUsability(unittest.TestCase):
    def test_spec_hash_matches_canonical_sha(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "ui-spec.json"
            path.write_text(json.dumps(SAMPLE_SPEC, indent=4), encoding="utf-8")
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                self.assertEqual(spec_hash(str(path)), 0)
            self.assertEqual(
                captured.getvalue().strip(),
                compute_spec_canonical_sha256(SAMPLE_SPEC),
            )

    def test_placeholder_allowed_on_input_rejected_on_button(self):
        spec = deepcopy(SAMPLE_SPEC)
        spec["root"]["children"] = [
            {"id": "chat-input", "type": "input", "name": "ChatInput", "props": {}},
        ]
        sha = compute_spec_canonical_sha256(spec)
        ok = {
            "version": 1,
            "baseSpecSha256": sha,
            "operations": [
                {
                    "op": "set",
                    "nodeId": "chat-input",
                    "path": "props.placeholder",
                    "value": "Type here",
                    "reason": "placeholder copy",
                }
            ],
        }
        refined, _ = SafeAgentRefiner().apply_patch(spec, ok)
        self.assertEqual(refined["root"]["children"][0]["props"]["placeholder"], "Type here")

        bad = _patch(SAMPLE_SPEC, "props.placeholder", "nope")
        with self.assertRaises(PatchValidationError) as ctx:
            SafeAgentRefiner().validate_patch(SAMPLE_SPEC, bad)
        self.assertIn("not valid for node type", str(ctx.exception))

    def test_command_rejected_on_text_node(self):
        spec = deepcopy(SAMPLE_SPEC)
        spec["root"]["type"] = "text"
        spec["root"]["props"] = {"text": "Hello"}
        with self.assertRaises(PatchValidationError) as ctx:
            SafeAgentRefiner().validate_patch(spec, _patch(spec, "props.command", "DoIt"))
        self.assertIn("not valid for node type", str(ctx.exception))

    def test_duplicate_operations_rejected(self):
        spec = deepcopy(SAMPLE_SPEC)
        patch = {
            "version": 1,
            "baseSpecSha256": compute_spec_canonical_sha256(spec),
            "operations": [
                {
                    "op": "set",
                    "nodeId": "send-btn",
                    "path": "props.text",
                    "value": "One",
                    "reason": "first",
                },
                {
                    "op": "set",
                    "nodeId": "send-btn",
                    "path": "props.text",
                    "value": "Two",
                    "reason": "second",
                },
            ],
        }
        with self.assertRaises(PatchValidationError) as ctx:
            SafeAgentRefiner().validate_patch(spec, patch)
        self.assertIn("Duplicate operation", str(ctx.exception))


class TestVisualFidelityAndNeutralResources(unittest.TestCase):
    def test_textblock_font_style_and_alignment(self):
        spec = UiSpec(
            root=UiNode(
                id="t",
                type="text",
                props={"text": "Hello"},
                style=UiStyle(font_style="italic", text_align="center"),
            )
        )
        xaml = WpfGenerator().generate_main_window_xaml(spec)
        self.assertIn('FontStyle="Italic"', xaml)
        self.assertIn('TextAlignment="Center"', xaml)

    def test_button_emits_corner_radius_and_border(self):
        spec = UiSpec(
            root=UiNode(
                id="b",
                type="button",
                props={"text": "Go"},
                style=UiStyle(
                    background="#8462E8",
                    border_color="#FFFFFF",
                    border_thickness=1,
                    corner_radius=6,
                ),
            )
        )
        xaml = WpfGenerator().generate_main_window_xaml(spec)
        self.assertIn('CornerRadius="6"', xaml)
        self.assertIn("BorderBrush=", xaml)
        self.assertIn("BorderThickness=", xaml)
        self.assertIn("ControlTemplate", xaml)

    def test_input_keeps_placeholder_metadata_and_radius(self):
        spec = UiSpec(
            root=UiNode(
                id="i",
                type="input",
                props={"placeholder": "Search..."},
                style=UiStyle(corner_radius=6, border_color="#444455", border_thickness=1),
            )
        )
        xaml = WpfGenerator().generate_main_window_xaml(spec)
        self.assertIn('Tag="Search..."', xaml)
        self.assertNotIn('Text="Search..."', xaml)
        self.assertIn('CornerRadius="6"', xaml)

    def test_ir_keeps_semantic_resource_names(self):
        doc = VellumDocumentAdapter().load_from_file(SAMPLES / "tabletop-chat.vellum")
        spec = SemanticMapper().map_document(doc)
        self.assertIn("Brand / Purple", spec.resources)
        self.assertNotIn("Brush.Brand.Purple", spec.resources)
        xaml = WpfGenerator().generate_all(spec)
        self.assertIn('x:Key="Brush.Brand.Purple"', xaml["Resources.xaml"])
        self.assertIn("{StaticResource Brush.Brand.Purple}", xaml["MainWindow.xaml"])
