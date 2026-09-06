"""Untrusted IR and literal payload regression tests."""
from copy import deepcopy
import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import sys
import xml.etree.ElementTree as ET

from vellum_wpf_bridge.cli import generate
from vellum_wpf_bridge.models import UiSpec, UiNode, UiLayout, UiStyle
from vellum_wpf_bridge.refiner import SafeAgentRefiner
from vellum_wpf_bridge.resources import ResourceManager
from vellum_wpf_bridge.semantic_mapper import SemanticMapper
from vellum_wpf_bridge.spec_validator import UiSpecValidationError
from vellum_wpf_bridge.utils import fmt_length, normalize_ir_color
from vellum_wpf_bridge.vellum_adapter import VellumDocumentAdapter
from vellum_wpf_bridge.wpf_generator import WpfGenerator
from test_review_findings import SAMPLE_SPEC, _patch


class TestGenerationSecurity(unittest.TestCase):
    def test_agent_text_patch_is_a_literal(self):
        for payload in ('{Binding Steal}', '{StaticResource Missing}', '{}already escaped',
                        ' {Binding Steal}', '{x:Null}', '{"<&'):
            with self.subTest(payload=payload):
                patched, _ = SafeAgentRefiner().apply_patch(
                    SAMPLE_SPEC, _patch(SAMPLE_SPEC, 'props.text', payload))
                tree = ET.fromstring(WpfGenerator().generate_all(UiSpec.from_dict(patched))['MainWindow.xaml'])
                button = next(e for e in tree.iter() if e.tag.endswith('}Button'))
                self.assertEqual(button.get('Content'), '{}' + payload)

    def test_all_literal_slots_and_intentional_binding(self):
        payload = '{Binding Steal}'
        spec = UiSpec(name=payload, root=UiNode(id='root', type='panel', children=[
            UiNode(id='b', type='button', props={'text': payload, 'command': 'Send'}),
            UiNode(id='i', type='input', props={'text': payload, 'placeholder': payload}),
            UiNode(id='t', type='text', props={'text': payload}, style=UiStyle(font_family=payload))]))
        tree = ET.fromstring(WpfGenerator().generate_all(spec)['MainWindow.xaml'])
        count = 0
        for e in tree.iter():
            for key, val in e.attrib.items():
                if key in ('Title', 'Content', 'Text', 'ToolTip', 'Tag', 'FontFamily'):
                    self.assertEqual(val, '{}' + payload)
                    count += 1
        self.assertEqual(count, 7)
        self.assertIn('Command="{Binding Send}"', ET.tostring(tree, encoding='unicode'))

    def test_comment_cannot_inject_an_element(self):
        data = deepcopy(SAMPLE_SPEC)
        data['root']['source'] = {'nodeId': '---><Button Content="pwned"/><!--',
                                  'nodeName': '-----'}
        xaml = WpfGenerator().generate_all(UiSpec.from_dict(data))['MainWindow.xaml']
        tree = ET.fromstring(xaml)
        self.assertEqual(sum(e.tag.endswith('}Button') for e in tree.iter()), 1)
        self.assertNotIn('<!-- Vellum: --', xaml)

    def test_bad_layout_inputs_fail_before_output(self):
        bad = [('width', '100"/><Button'), ('height', '*'), ('padding', [0, 0, '"/>', 0]),
               ('padding', [1, 2]), ('gridColumn', '0"/>'), ('gridRow', True),
               ('gridRow', -1), ('gridColumn', 2**31), ('gap', float('nan')),
               ('x', float('inf')), ('width', True), ('rows', ['{Binding Evil}']),
               ('columns', ['2*']), ('width', [10]), ('padding', -1)]
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'spec.json'
            output = Path(temp) / 'out'
            for key, val in bad:
                with self.subTest(key=key, value=val):
                    data = deepcopy(SAMPLE_SPEC)
                    data['root']['layout'][key] = val
                    source.write_text(json.dumps(data), encoding='utf-8')
                    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(generate(str(source), str(output)), 1)
                    self.assertFalse(output.exists())

    def test_shape_types_and_required_fields(self):
        cases = [{}, [], dict(SAMPLE_SPEC, width='100'), dict(SAMPLE_SPEC, width=float('nan')),
                 dict(SAMPLE_SPEC, root=None), dict(SAMPLE_SPEC, name='\x00')]
        for section in ('layout', 'style', 'props', 'source', 'children'):
            data = deepcopy(SAMPLE_SPEC)
            data['root'][section] = 1
            cases.append(data)
        data = deepcopy(SAMPLE_SPEC)
        data['root']['children'] = [deepcopy(data['root'])]
        cases.append(data)
        for data in cases:
            with self.subTest(data=data), self.assertRaises(UiSpecValidationError):
                UiSpec.from_dict(data)

    def test_invalid_spec_does_not_overwrite_existing_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            source = directory / 'bad.json'
            source.write_text('{}', encoding='utf-8')
            target = directory / 'MainWindow.xaml'
            target.write_text('keep existing output', encoding='utf-8')
            with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(generate(str(source), str(directory)), 1)
            self.assertEqual(target.read_text(encoding='utf-8'), 'keep existing output')

    def test_direct_model_entry_points_are_validated_without_lossy_serialization(self):
        for generator_method in ('generate_all', 'generate_main_window_xaml'):
            for layout, style in ((UiLayout(width='"/>'), UiStyle()),
                                   (UiLayout(), UiStyle(border_thickness=-1)),
                                   (UiLayout(grid_row=True), UiStyle())):
                with self.subTest(method=generator_method), self.assertRaises(UiSpecValidationError):
                    getattr(WpfGenerator(), generator_method)(UiSpec(root=UiNode(
                        id='root', type='panel', layout=layout, style=style)))

    def test_length_formatter_rejects_untyped_tokens(self):
        for val in ('100', '"/>', '{Binding Evil}', True, float('nan'), float('inf')):
            with self.subTest(value=val), self.assertRaises(ValueError):
                fmt_length(val)
        self.assertEqual([fmt_length(v) for v in (10, 1.5, '*', 'Auto')], ['10', '1.5', '*', 'Auto'])

    def test_ir_argb_is_idempotent_in_inline_and_shared_colors(self):
        color = '#80123456'
        self.assertEqual(normalize_ir_color(normalize_ir_color(color)), color)
        self.assertEqual(normalize_ir_color('80123456'), color)
        for shared in (False, True):
            spec = UiSpec(resources={'Brush.Alpha': color} if shared else {},
                          root=UiNode(id='root', type='panel', style=UiStyle(background=color)))
            files = WpfGenerator().generate_all(UiSpec.from_dict(spec.to_dict()))
            self.assertIn(color, files['Resources.xaml'] if shared else files['MainWindow.xaml'])
            self.assertNotIn('#56801234', ''.join(files.values()))
        spec = UiSpec(root=UiNode(id='root', type='panel', children=[
            UiNode(id='a', type='text', style=UiStyle(foreground=color)),
            UiNode(id='b', type='text', style=UiStyle(foreground=color))]))
        files = WpfGenerator().generate_all(spec)
        self.assertIn('Color="#80123456"', files['Resources.xaml'])
        self.assertEqual(files['MainWindow.xaml'].count('{StaticResource Brush.Color_80123456}'), 2)

    def test_source_rgba_becomes_argb_once_through_adapter_mapper_and_roundtrip(self):
        sample = Path(__file__).parent.parent / 'samples' / 'tabletop-chat.vellum'
        data = json.loads(sample.read_text(encoding='utf-8'))
        data['pages'][0]['nodes'][0]['fill'] = '#12345680'
        data['tokens'] = {'colors': [{'name': 'Alpha', 'value': '#12345680'}]}
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'alpha.vellum'
            source.write_text(json.dumps(data), encoding='utf-8')
            doc = VellumDocumentAdapter().load_from_file(source)
            spec = SemanticMapper().map_document(doc)
        self.assertEqual(spec.root.style.background, '#80123456')
        self.assertEqual(spec.resources['Brush.Alpha'], '#80123456')
        files = WpfGenerator().generate_all(spec)
        self.assertEqual(files, WpfGenerator().generate_all(UiSpec.from_dict(spec.to_dict())))
        self.assertIn('Color="#80123456"', files['Resources.xaml'])

    @unittest.skipUnless(sys.platform == 'win32' and shutil.which('dotnet'), 'Windows WPF runtime is unavailable')
    def test_wpf_runtime_preserves_literals_and_argb(self):
        payload = '{Binding Steal}'
        spec = UiSpec(name=payload, root=UiNode(id='root', type='panel', children=[
            UiNode(id='b', type='button', props={'text': payload, 'tooltip': payload, 'accessibleName': payload, 'helpText': payload}),
            UiNode(id='i', type='input', props={'text': payload, 'placeholder': payload}),
            UiNode(id='t', type='text', props={'text': payload},
                   style=UiStyle(font_family=payload, foreground='#80123456'))]))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'MainWindow.xaml'
            path.write_text(WpfGenerator().generate_all(spec)['MainWindow.xaml'], encoding='utf-8')
            result = subprocess.run(['dotnet', 'run', '--project',
                str(Path(__file__).parent / 'wpf-canary'), '--', '--security', str(path)],
                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('SECURITY_OK', result.stdout)
