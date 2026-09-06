"""Canonical .vellum validation via Vellum DocumentModel.parse() (Node, test-only)."""

from pathlib import Path
import shutil
import subprocess
import unittest


BRIDGE_ROOT = Path(__file__).parent.parent
SCRIPT = BRIDGE_ROOT / "scripts" / "validate-vellum.mjs"
SAMPLES = BRIDGE_ROOT / "samples"


class TestValidateVellum(unittest.TestCase):
    def test_sample_files_pass_document_model_parse(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not available for DocumentModel.parse() canonical validation")
        files = [
            SAMPLES / "tabletop-chat.vellum",
            SAMPLES / "canary-three-column.vellum",
            SAMPLES / "canary-gap.vellum",
            SAMPLES / "canary-freeform.vellum",
        ]
        result = subprocess.run(
            [node, str(SCRIPT), *[str(f) for f in files]],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            self.fail(result.stdout + "\n" + result.stderr)
        self.assertIn("PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
