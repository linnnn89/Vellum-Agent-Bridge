"""Golden snapshot comparison test."""

from pathlib import Path
import unittest

from vellum_wpf_bridge.resources import ResourceManager
from vellum_wpf_bridge.semantic_mapper import SemanticMapper
from vellum_wpf_bridge.vellum_adapter import VellumDocumentAdapter
from vellum_wpf_bridge.wpf_generator import WpfGenerator


class TestGolden(unittest.TestCase):

    def setUp(self):
        self.sample_path = (
            Path(__file__).parent.parent / "samples" / "tabletop-chat.vellum"
        )
        self.expected_dir = Path(__file__).parent / "expected"
        self.expected_dir.mkdir(exist_ok=True)
        self.expected_file = self.expected_dir / "MainWindow.xaml"

    def test_golden_comparison(self):
        adapter = VellumDocumentAdapter()
        doc = adapter.load_from_file(self.sample_path)
        mapper = SemanticMapper()
        spec = mapper.map_document(doc)

        rm = ResourceManager()
        rm.extract_from_document_tokens(doc)
        generator = WpfGenerator(resource_manager=rm)
        outputs = generator.generate_all(spec, app_namespace="GeneratedWpfDemo")
        generated_xaml = outputs["MainWindow.xaml"]

        if not self.expected_file.exists():
            # Initial baseline creation
            with open(self.expected_file, "w", encoding="utf-8") as f:
                f.write(generated_xaml)

        with open(self.expected_file, "r", encoding="utf-8") as f:
            expected_xaml = f.read()

        # Normalize line endings
        gen_lines = [line.rstrip() for line in generated_xaml.splitlines()]
        exp_lines = [line.rstrip() for line in expected_xaml.splitlines()]

        self.assertEqual(
            gen_lines,
            exp_lines,
            "Generated MainWindow.xaml differs from golden snapshot.",
        )


if __name__ == "__main__":
    unittest.main()
