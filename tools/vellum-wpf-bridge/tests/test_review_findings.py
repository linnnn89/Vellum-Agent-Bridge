"""Repro tests for review findings on Gemini's Phase 1-4 updates.

These encode the *required* security/contract behavior, not the current
happy-path suite. Failures here are bugs, not flaky tests.
"""

from copy import deepcopy
from pathlib import Path
import re
import unittest

from vellum_wpf_bridge.models import UiLayout, UiNode, UiSpec, UiStyle
from vellum_wpf_bridge.refiner import (
    PatchValidationError,
    SafeAgentRefiner,
    compute_spec_canonical_sha256,
)
from vellum_wpf_bridge.wpf_generator import WpfGenerator


REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_SPEC = {
    "version": "0.1",
    "name": "MainWindow",
    "type": "window",
    "width": 800,
    "height": 400,
    "theme": "dark",
    "resources": {},
    "root": {
        "id": "send-btn",
        "type": "button",
        "name": "SendButton",
        "props": {"text": "Send"},
        "layout": {"widthMode": "fixed", "width": 100, "height": 32},
        "children": [],
    },
}


def _patch(spec, path, value):
    return {
        "version": 1,
        "baseSpecSha256": compute_spec_canonical_sha256(spec),
        "operations": [
            {
                "op": "set",
                "nodeId": "send-btn",
                "path": path,
                "value": value,
                "reason": "review repro",
            }
        ],
    }


class TestCommandBindingMustBeIdentifier(unittest.TestCase):
    """Safe refiner + generator must not emit markup-extension injection."""

    def setUp(self):
        self.refiner = SafeAgentRefiner()
        self.spec = deepcopy(SAMPLE_SPEC)

    def test_refiner_rejects_command_that_breaks_out_of_binding(self):
        payload = 'Foo} Background="{x:Null'
        with self.assertRaises(PatchValidationError):
            self.refiner.apply_patch(self.spec, _patch(self.spec, "props.command", payload))

    def test_refiner_rejects_non_string_command(self):
        with self.assertRaises(PatchValidationError):
            self.refiner.apply_patch(self.spec, _patch(self.spec, "props.command", {"nested": True}))

    def test_generator_does_not_emit_injected_binding_if_spec_already_poisoned(self):
        spec = UiSpec(
            name="MainWindow",
            width=400,
            height=200,
            root=UiNode(
                id="send-btn",
                type="button",
                name="SendButton",
                props={"text": "Send", "command": 'Foo} Background="{x:Null'},
                layout=UiLayout(width=100, height=32, width_mode="fixed", height_mode="fixed"),
            ),
        )
        with self.assertRaisesRegex(ValueError, "props.command"):
            WpfGenerator().generate_main_window_xaml(spec)


class TestSha256MustBeCanonicalOnly(unittest.TestCase):
    def test_raw_file_hash_of_unrelated_bytes_must_not_validate(self):
        spec = deepcopy(SAMPLE_SPEC)
        canonical = compute_spec_canonical_sha256(spec)
        unrelated_file_hash = "a" * 64
        patch = _patch(spec, "props.text", "Hi")
        patch["baseSpecSha256"] = unrelated_file_hash
        with self.assertRaises(PatchValidationError):
            SafeAgentRefiner().validate_patch(
                spec, patch, raw_file_sha256=unrelated_file_hash
            )
        self.assertNotEqual(canonical, unrelated_file_hash)


class TestGenerateSanitizesUntrustedSpec(unittest.TestCase):
    def test_background_color_cannot_break_out_of_attribute(self):
        spec = UiSpec(
            name="MainWindow",
            width=400,
            height=200,
            root=UiNode(
                id="p",
                type="panel",
                name="Panel",
                layout=UiLayout(type="stack"),
                style=UiStyle(background='#112233" /><Button Content="pwned'),
            ),
        )
        with self.assertRaisesRegex(ValueError, "style.background"):
            WpfGenerator().generate_main_window_xaml(spec)


class TestCiWorkflowMatchesThisFork(unittest.TestCase):
    def test_pages_workflow_includes_default_branch(self):
        yaml = (REPO_ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
        self.assertIn("Vellum-Agent-Bridge", yaml)
        self.assertRegex(
            yaml,
            r"branches:\s*\[[^\]]*(Vellum-Agent-Bridge|main)[^\]]*\]",
        )

    def test_windows_job_uses_net10_for_wpf_demo(self):
        yaml = (REPO_ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
        csproj = (
            REPO_ROOT
            / "tools"
            / "vellum-wpf-bridge"
            / "samples"
            / "generated-wpf-demo"
            / "GeneratedWpfDemo.csproj"
        ).read_text(encoding="utf-8")
        tfm = re.search(r"<TargetFramework>([^<]+)</TargetFramework>", csproj).group(1)
        self.assertEqual(tfm, "net10.0-windows")
        self.assertIn("10.0.x", yaml)
        self.assertNotIn("dotnet-version: '8.0.x'", yaml)


if __name__ == "__main__":
    unittest.main()
