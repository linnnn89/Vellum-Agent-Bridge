"""Regression coverage for follow-up audit findings."""
from copy import deepcopy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import sys
import shutil
import subprocess
import xml.etree.ElementTree as ET

from vellum_wpf_bridge.cli import convert, generate, refine_apply
from vellum_wpf_bridge.models import UiSpec, UiNode, UiStyle, VellumDocument, VellumNode, VellumPage
from vellum_wpf_bridge.refiner import SafeAgentRefiner, compute_spec_canonical_sha256
from vellum_wpf_bridge.semantic_mapper import SemanticMapper
from vellum_wpf_bridge.wpf_generator import WpfGenerator
from test_review_findings import SAMPLE_SPEC, _patch

PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aV1cAAAAASUVORK5CYII='


class TestFollowupFindings(unittest.TestCase):
    def test_persisted_audit_redacts_old_new_and_reason_but_spec_retains_ui_text(self):
        spec = deepcopy(SAMPLE_SPEC)
        spec['root']['props']['text'] = 'old-private-text'
        patch = _patch(spec, 'props.text', 'new-private-text')
        patch['operations'][0]['reason'] = 'private-reason'
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'spec.json').write_text(json.dumps(spec), encoding='utf-8')
            (root / 'patch.json').write_text(json.dumps(patch), encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(refine_apply(str(root / 'spec.json'), str(root / 'patch.json'), temp), 0)
            report = (root / 'refinement-report.json').read_text(encoding='utf-8')
            for secret in ('old-private-text', 'new-private-text', 'private-reason'):
                self.assertNotIn(secret, report)
            self.assertEqual(json.loads(report)['version'], 2)
            self.assertIn('new-private-text', (root / 'refined-ui-spec.json').read_text())

    def test_accessibility_patch_reaches_every_rendered_node_type(self):
        for kind in ('button', 'input', 'text', 'panel', 'separator', 'unknown', 'image'):
            spec = deepcopy(SAMPLE_SPEC)
            spec['root']['type'] = kind
            spec['root']['style'] = {'background': '#123456'}
            spec['root']['props']['placeholder'] = 'fallback'
            if kind == 'image':
                spec['assets'] = {'pic1': PNG}
                spec['root']['props']['assetId'] = 'pic1'
            for prop in ('tooltip', 'accessibleName', 'helpText'):
                spec, _ = SafeAgentRefiner().apply_patch(spec, _patch(spec, 'props.' + prop, '{Binding Literal}'))
            tree = ET.fromstring(WpfGenerator().generate_all(UiSpec.from_dict(spec))['MainWindow.xaml'])
            rendered = list(tree)[0]
            for attr in ('ToolTip', 'AutomationProperties.Name', 'AutomationProperties.HelpText'):
                self.assertEqual(rendered.get(attr), '{}{Binding Literal}', (kind, attr))

    def test_ir_rejects_invalid_command_and_colors(self):
        for props, style, resources in (({'command': '{Binding Steal}'}, {}, {}),
                 ({}, {'background': '{x:Null}'}, {}), ({}, {}, {'Brush.Bad': 'red'})):
            spec = deepcopy(SAMPLE_SPEC)
            spec['root']['props'] = props
            spec['root']['style'] = style
            spec['resources'] = resources
            with self.assertRaises(ValueError):
                UiSpec.from_dict(spec)
            with self.assertRaises(ValueError):
                SafeAgentRefiner().apply_patch(spec, _patch(spec, 'props.text', 'ok'))

    def test_argb_theme_uses_rgb_not_alpha(self):
        for fill, theme in (('#00FFFF00', 'light'), ('#FF0000FF', 'dark')):
            frame = VellumNode(id='f', type='frame', name='Frame', fill=fill, w=100, h=100)
            doc = VellumDocument(format='vellum', version=1, name='T',
                                pages=[VellumPage(id='p', name='P', root_nodes=[frame])])
            self.assertEqual(SemanticMapper().map_document(doc).theme, theme)

    def test_image_generate_writes_local_bytes_and_source(self):
        spec = UiSpec(root=UiNode(id='img', type='image', props={'assetId': 'pic1'}), assets={'pic1': PNG})
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'spec.json'
            source.write_text(json.dumps(spec.to_dict()), encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(generate(str(source), str(root / 'out')), 0)
            tree = ET.parse(root / 'out/MainWindow.xaml')
            asset = list(tree.getroot())[0].get('Source')
            self.assertTrue(asset.startswith('Assets/'))
            self.assertTrue((root / 'out' / asset).read_bytes().startswith(b'\x89PNG'))

    def test_missing_or_external_image_is_rejected(self):
        for assets in ({}, {'pic1': 'https://example.com/image.png'}, {'pic1': '../../secret.png'},
                       {'pic1': 'data:image/png;base64,aGVsbG8='}):
            with self.assertRaises(ValueError):
                UiSpec.from_dict(UiSpec(root=UiNode(id='i', type='image', props={'assetId': 'pic1'}), assets=assets).to_dict())

    def test_convert_carries_embedded_assets_into_standalone_ir(self):
        sample = Path(__file__).parent.parent / 'samples/tabletop-chat.vellum'
        data = json.loads(sample.read_text(encoding='utf-8'))
        picture = deepcopy(data['pages'][0]['nodes'][0])
        picture.update(id='audit-image', type='image', name='Picture',
                       parentId=picture['id'], assetId='pic1')
        data['pages'][0]['nodes'].append(picture)
        data['assets'] = {'pic1': PNG}
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(temp)
            source = root / 'image.vellum'
            source.write_text(json.dumps(data), encoding='utf-8')
            self.assertEqual(convert(str(source), str(root / 'conv')), 0)
            self.assertEqual(generate(str(root / 'conv/ui-spec.json'), str(root / 'gen')), 0)
            self.assertEqual((root / 'conv/MainWindow.xaml').read_bytes(), (root / 'gen/MainWindow.xaml').read_bytes())
            self.assertEqual(len(list((root / 'gen/Assets').iterdir())), 1)

    @unittest.skipUnless(sys.platform == 'win32' and shutil.which('dotnet'), 'Windows WPF unavailable')
    def test_wpf_decodes_generated_image_source(self):
        spec = UiSpec(root=UiNode(id='i', type='image', props={'assetId': 'pic1'}), assets={'pic1': PNG})
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for filename, content in WpfGenerator().generate_all(spec).items():
                path = root / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content if isinstance(content, bytes) else content.encode('utf-8'))
            result = subprocess.run(['dotnet', 'run', '--project', str(Path(__file__).parent / 'wpf-canary'),
                                     '--', '--image', str(root / 'MainWindow.xaml')],
                                    capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('IMAGE_OK', result.stdout)

    def test_convert_applies_verified_patch_and_rejects_stale_patch(self):
        sample = Path(__file__).parent.parent / 'samples/tabletop-chat.vellum'
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            root = Path(temp)
            self.assertEqual(convert(str(sample), str(root / 'base'), spec_only=True), 0)
            spec = json.loads((root / 'base/ui-spec.json').read_text(encoding='utf-8'))
            patch = {'version': 1, 'baseSpecSha256': compute_spec_canonical_sha256(spec), 'operations': [
                {'op': 'set', 'nodeId': spec['root']['id'], 'path': 'props.tooltip', 'value': 'converted-tip', 'reason': 'private'}]}
            source = root / 'patch.json'
            source.write_text(json.dumps(patch), encoding='utf-8')
            self.assertEqual(convert(str(sample), str(root / 'ok'), patch_file=str(source)), 0)
            self.assertIn('converted-tip', (root / 'ok/MainWindow.xaml').read_text(encoding='utf-8'))
            self.assertNotIn('private', (root / 'ok/refinement-report.json').read_text(encoding='utf-8'))
            patch['baseSpecSha256'] = '0' * 64
            source.write_text(json.dumps(patch), encoding='utf-8')
            self.assertEqual(convert(str(sample), str(root / 'bad'), patch_file=str(source)), 1)
            self.assertFalse((root / 'bad').exists())
