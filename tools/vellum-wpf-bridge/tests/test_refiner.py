"""Tests for SafeAgentRefiner and patch application."""

import copy
import json
from pathlib import Path
import tempfile
import unittest

from vellum_wpf_bridge.refiner import (
    PatchValidationError,
    SafeAgentRefiner,
    compute_spec_canonical_sha256,
)

SAMPLE_SPEC = {
    "version": "0.1",
    "name": "MainWindow",
    "type": "window",
    "width": 1200,
    "height": 800,
    "theme": "dark",
    "resources": {
        "Brush.Brand": "#8B6CFF",
    },
    "root": {
        "id": "root-1",
        "type": "panel",
        "name": "RootPanel",
        "layout": {
            "type": "grid",
            "columns": [260, "*", 260],
            "direction": "horizontal",
        },
        "style": {
            "background": "#1E1E24",
        },
        "children": [
            {
                "id": "send-btn",
                "type": "button",
                "name": "SendButton",
                "props": {
                    "text": "Send",
                },
            },
            {
                "id": "chat-input",
                "type": "input",
                "name": "ChatInput",
                "props": {
                    "placeholder": "Type here...",
                },
            },
        ],
    },
}


class TestSafeAgentRefiner(unittest.TestCase):
    def setUp(self):
        self.refiner = SafeAgentRefiner()
        self.spec = copy.deepcopy(SAMPLE_SPEC)
        self.base_sha = compute_spec_canonical_sha256(self.spec)

    def test_valid_semantic_patch_applied_successfully(self):
        patch = {
            "version": 1,
            "baseSpecSha256": self.base_sha,
            "operations": [
                {
                    "op": "set",
                    "nodeId": "send-btn",
                    "path": "props.command",
                    "value": "SendCommand",
                    "reason": "Wire up submit command",
                },
                {
                    "op": "set",
                    "nodeId": "send-btn",
                    "path": "props.tooltip",
                    "value": "Send active chat message",
                    "reason": "Add accessibility tooltip",
                },
                {
                    "op": "set",
                    "nodeId": "chat-input",
                    "path": "props.accessibleName",
                    "value": "MessageComposerInput",
                    "reason": "Screen reader label",
                },
            ],
        }
        refined_spec, report = self.refiner.apply_patch(self.spec, patch)
        self.assertEqual(len(report.changes), 3)

        # Verify modifications in refined spec
        btn_node = refined_spec["root"]["children"][0]
        self.assertEqual(btn_node["props"]["command"], "SendCommand")
        self.assertEqual(btn_node["props"]["tooltip"], "Send active chat message")

        input_node = refined_spec["root"]["children"][1]
        self.assertEqual(input_node["props"]["accessibleName"], "MessageComposerInput")

        # Verify layout and styles are completely untouched
        self.assertEqual(refined_spec["root"]["layout"], SAMPLE_SPEC["root"]["layout"])
        self.assertEqual(refined_spec["root"]["style"], SAMPLE_SPEC["root"]["style"])

    def test_sha256_mismatch_rejected(self):
        patch = {
            "version": 1,
            "baseSpecSha256": "0000000000000000000000000000000000000000000000000000000000000000",
            "operations": [
                {
                    "op": "set",
                    "nodeId": "send-btn",
                    "path": "props.command",
                    "value": "Cmd",
                    "reason": "test",
                }
            ],
        }
        with self.assertRaises(PatchValidationError) as ctx:
            self.refiner.validate_patch(self.spec, patch)
        self.assertIn("baseSpecSha256 mismatch", str(ctx.exception))

    def test_forbidden_layout_and_style_modifications_rejected(self):
        forbidden_paths = [
            "id",
            "type",
            "source",
            "layout",
            "layout.columns",
            "layout.gap",
            "layout.width",
            "style",
            "style.background",
            "children",
            "resources",
            "generatedName",
        ]
        for path in forbidden_paths:
            with self.subTest(path=path):
                patch = {
                    "version": 1,
                    "baseSpecSha256": self.base_sha,
                    "operations": [
                        {
                            "op": "set",
                            "nodeId": "send-btn",
                            "path": path,
                            "value": "hacked",
                            "reason": "forbidden attempt",
                        }
                    ],
                }
                with self.assertRaises(PatchValidationError) as ctx:
                    self.refiner.validate_patch(self.spec, patch)
                self.assertIn("Disallowed patch path", str(ctx.exception))

    def test_nonexistent_node_id_rejected_atomically(self):
        patch = {
            "version": 1,
            "baseSpecSha256": self.base_sha,
            "operations": [
                {
                    "op": "set",
                    "nodeId": "send-btn",
                    "path": "props.command",
                    "value": "SendCommand",
                    "reason": "valid",
                },
                {
                    "op": "set",
                    "nodeId": "ghost-node-404",
                    "path": "props.command",
                    "value": "GhostCmd",
                    "reason": "invalid target",
                },
            ],
        }
        with self.assertRaises(PatchValidationError) as ctx:
            self.refiner.apply_patch(self.spec, patch)
        self.assertIn("targets non-existent nodeId", str(ctx.exception))

        # Atomic guarantee: send-btn was NOT modified
        self.assertNotIn("command", self.spec["root"]["children"][0]["props"])


if __name__ == "__main__":
    unittest.main()
