"""Tests for strict .vellum source validation."""

import json
from pathlib import Path
import unittest

from vellum_wpf_bridge.validator import (
    VellumValidationError,
    validate_vellum_dict,
    validate_vellum_file,
)

BRIDGE_ROOT = Path(__file__).parent.parent
SAMPLES = BRIDGE_ROOT / "samples"


class TestSourceValidator(unittest.TestCase):
    def test_samples_pass_strict_validation(self):
        samples = [
            SAMPLES / "tabletop-chat.vellum",
            SAMPLES / "canary-three-column.vellum",
            SAMPLES / "canary-gap.vellum",
            SAMPLES / "canary-freeform.vellum",
        ]
        for s in samples:
            with self.subTest(sample=s.name):
                validate_vellum_file(s)

    def test_invalid_format_or_version_rejected(self):
        with self.assertRaises(VellumValidationError) as ctx:
            validate_vellum_dict({"format": "other", "version": 1, "pages": []})
        self.assertIn("Unsupported document format", str(ctx.exception))

        with self.assertRaises(VellumValidationError) as ctx:
            validate_vellum_dict({"format": "vellum", "version": 2, "pages": []})
        self.assertIn("Unsupported document format", str(ctx.exception))

    def test_empty_pages_rejected(self):
        with self.assertRaises(VellumValidationError):
            validate_vellum_dict({"format": "vellum", "version": 1, "pages": []})

    def test_duplicate_node_id_rejected(self):
        doc = {
            "format": "vellum",
            "version": 1,
            "pages": [
                {
                    "id": "p1",
                    "name": "Page 1",
                    "nodes": [
                        {"id": "dup-id", "type": "rect", "x": 0, "y": 0, "w": 100, "h": 100, "rotation": 0, "opacity": 1},
                        {"id": "dup-id", "type": "rect", "x": 10, "y": 10, "w": 50, "h": 50, "rotation": 0, "opacity": 1},
                    ],
                }
            ],
        }
        with self.assertRaises(VellumValidationError) as ctx:
            validate_vellum_dict(doc)
        self.assertIn("Duplicate node id", str(ctx.exception))

    def test_missing_or_non_numeric_fields_rejected(self):
        # Missing 'rotation'
        doc = {
            "format": "vellum",
            "version": 1,
            "pages": [
                {
                    "id": "p1",
                    "name": "Page 1",
                    "nodes": [
                        {"id": "n1", "type": "rect", "x": 0, "y": 0, "w": 100, "h": 100, "opacity": 1},
                    ],
                }
            ],
        }
        with self.assertRaises(VellumValidationError) as ctx:
            validate_vellum_dict(doc)
        self.assertIn("missing required numeric property", str(ctx.exception))

        # Non-numeric opacity (string)
        doc["pages"][0]["nodes"][0]["rotation"] = 0
        doc["pages"][0]["nodes"][0]["opacity"] = "1.0"
        with self.assertRaises(VellumValidationError) as ctx:
            validate_vellum_dict(doc)
        self.assertIn("must be a number", str(ctx.exception))

        # Negative width
        doc["pages"][0]["nodes"][0]["opacity"] = 1.0
        doc["pages"][0]["nodes"][0]["w"] = -10
        with self.assertRaises(VellumValidationError) as ctx:
            validate_vellum_dict(doc)
        self.assertIn("negative dimensions", str(ctx.exception))

    def test_nonexistent_parent_id_rejected(self):
        doc = {
            "format": "vellum",
            "version": 1,
            "pages": [
                {
                    "id": "p1",
                    "name": "Page 1",
                    "nodes": [
                        {"id": "n1", "type": "rect", "parentId": "ghost", "x": 0, "y": 0, "w": 10, "h": 10, "rotation": 0, "opacity": 1},
                    ],
                }
            ],
        }
        with self.assertRaises(VellumValidationError) as ctx:
            validate_vellum_dict(doc)
        self.assertIn("non-existent parentId", str(ctx.exception))

    def test_cyclic_hierarchy_rejected(self):
        doc = {
            "format": "vellum",
            "version": 1,
            "pages": [
                {
                    "id": "p1",
                    "name": "Page 1",
                    "nodes": [
                        {"id": "a", "type": "frame", "parentId": "b", "x": 0, "y": 0, "w": 10, "h": 10, "rotation": 0, "opacity": 1},
                        {"id": "b", "type": "frame", "parentId": "a", "x": 0, "y": 0, "w": 10, "h": 10, "rotation": 0, "opacity": 1},
                    ],
                }
            ],
        }
        with self.assertRaises(VellumValidationError) as ctx:
            validate_vellum_dict(doc)
        self.assertIn("Cyclic hierarchy detected", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
