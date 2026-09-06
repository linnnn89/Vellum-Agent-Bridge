"""Tests for self-contained UI Spec and WPF Generator fixes."""

import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from vellum_wpf_bridge.cli import convert, generate
from vellum_wpf_bridge.models import UiLayout, UiNode, UiSpec, UiStyle
from vellum_wpf_bridge.report import ConversionReport
from vellum_wpf_bridge.resources import ResourceManager
from vellum_wpf_bridge.wpf_generator import WpfGenerator

BRIDGE_ROOT = Path(__file__).parent.parent
SAMPLES = BRIDGE_ROOT / "samples"


class TestSelfContainedGenerate(unittest.TestCase):
    def test_generate_from_ui_spec_standalone(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            out_conv = tmp_path / "conv"
            out_gen = tmp_path / "gen"

            # Step 1: convert .vellum to ui-spec.json
            code = convert(
                str(SAMPLES / "tabletop-chat.vellum"),
                output_dir=str(out_conv),
                spec_only=False,
            )
            self.assertEqual(code, 0)
            spec_path = out_conv / "ui-spec.json"
            self.assertTrue(spec_path.exists())

            # Step 2: generate from ui-spec.json without .vellum
            code_gen = generate(
                str(spec_path),
                output_dir=str(out_gen),
            )
            self.assertEqual(code_gen, 0)

            self.assertTrue((out_gen / "MainWindow.xaml").exists())
            self.assertTrue((out_gen / "Resources.xaml").exists())
            self.assertTrue((out_gen / "App.xaml").exists())

            # Verify equivalence of generated XAML
            conv_main = (out_conv / "MainWindow.xaml").read_text(encoding="utf-8")
            gen_main = (out_gen / "MainWindow.xaml").read_text(encoding="utf-8")
            self.assertEqual(conv_main, gen_main)

    def test_canvas_child_preserves_design_size_and_warns(self):
        report = ConversionReport()
        gen = WpfGenerator(report=report)

        spec = UiSpec(
            name="CanvasTest",
            width=800,
            height=600,
            root=UiNode(
                id="root",
                type="panel",
                name="CanvasRoot",
                layout=UiLayout(type="absolute"),
                children=[
                    UiNode(
                        id="child-fill",
                        type="panel",
                        name="FillCard",
                        layout=UiLayout(
                            x=50,
                            y=100,
                            width_mode="fill",
                            height_mode="fill",
                            design_width=200,
                            design_height=150,
                        ),
                    )
                ],
            ),
        )

        xaml = gen.generate_main_window_xaml(spec)
        self.assertIn('Canvas.Left="50"', xaml)
        self.assertIn('Canvas.Top="100"', xaml)
        self.assertIn('Width="200"', xaml)
        self.assertIn('Height="150"', xaml)

        # Verify diagnostic was reported
        diag_codes = [d.code for d in report.diagnostics]
        self.assertIn("RESPONSIVE_CONSTRAINT_LOST_ON_CANVAS", diag_codes)

    def test_input_placeholder_does_not_become_text(self):
        gen = WpfGenerator()
        spec = UiSpec(
            name="InputTest",
            root=UiNode(
                id="input-1",
                type="input",
                name="SearchBox",
                props={
                    "placeholder": "Type search keywords...",
                },
            ),
        )
        xaml = gen.generate_main_window_xaml(spec)
        self.assertNotIn('Text="Type search keywords..."', xaml)
        self.assertIn('Tag="Type search keywords..."', xaml)
        self.assertIn('ToolTip="Type search keywords..."', xaml)

    def test_padding_uses_border_wrapper(self):
        gen = WpfGenerator()
        spec = UiSpec(
            name="PaddingTest",
            root=UiNode(
                id="card",
                type="panel",
                name="Card",
                layout=UiLayout(
                    type="stack",
                    direction="vertical",
                    padding=[16, 12, 16, 12],
                ),
                children=[
                    UiNode(id="txt", type="text", name="Label", props={"text": "Hello"})
                ],
            ),
        )
        xaml = gen.generate_main_window_xaml(spec)
        self.assertIn('<Border Padding="16,12,16,12">', xaml)

    def test_selective_x_name_generation(self):
        gen = WpfGenerator()
        spec = UiSpec(
            name="NameTest",
            root=UiNode(
                id="root",
                type="panel",
                name="Container",
                layout=UiLayout(type="stack"),
                children=[
                    UiNode(id="btn", type="button", name="SubmitButton", props={"text": "Submit"}),
                    UiNode(id="inp", type="input", name="UserNameInput"),
                    UiNode(id="txt", type="text", name="StaticDescription", props={"text": "Plain text"}),
                ],
            ),
        )
        xaml = gen.generate_main_window_xaml(spec)
        self.assertIn('x:Name="Btn"', xaml)
        self.assertIn('x:Name="Inp"', xaml)
        self.assertNotIn('x:Name="SubmitButton"', xaml)
        self.assertNotIn('x:Name="UserNameInput"', xaml)
        # Plain text should NOT receive x:Name
        self.assertNotIn('x:Name="StaticDescription"', xaml)


if __name__ == "__main__":
    unittest.main()
