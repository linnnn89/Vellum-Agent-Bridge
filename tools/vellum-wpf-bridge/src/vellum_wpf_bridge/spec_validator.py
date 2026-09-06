"""Dependency-free validation at the JSON and generator trust boundaries."""

from dataclasses import fields, is_dataclass
import math
import re
from .utils import is_binding_identifier, is_ir_color
from .assets import export_assets


class UiSpecValidationError(ValueError):
    pass


def _require(ok, path, expected):
    if not ok:
        raise UiSpecValidationError(f"{path}: expected {expected}")


def _number(value, path, minimum=None, maximum=None, integer=False):
    _require(type(value) in (int, float), path, "number (not bool or string)")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    _require(finite, path, "finite number")
    if integer:
        _require(type(value) is int, path, "integer")
    if minimum is not None:
        _require(value >= minimum, path, f"number >= {minimum}")
    if maximum is not None:
        _require(value <= maximum, path, f"number <= {maximum}")


def _string(value, path):
    _require(isinstance(value, str), path, "string")
    _require(all(c in '\t\n\r' or '\x20' <= c <= '\ud7ff' or
                 '\ue000' <= c <= '\ufffd' or '\U00010000' <= c <= '\U0010ffff'
                 for c in value), path, "XML 1.0 characters")


def _object(value, path):
    _require(isinstance(value, dict), path, "object")


def _enum_fields(data, path, rules):
    for key, choices in rules.items():
        if key in data:
            _require(isinstance(data[key], str) and data[key] in choices,
                     f"{path}.{key}", repr(choices))


def validate_ui_spec_dict(data, *, allow_empty_root=False):
    _object(data, '$')
    for key in ('version', 'name', 'type', 'root'):
        _require(key in data, '$', f"required field {key}")
    _string(data['name'], '$.name')
    _enum_fields(data, '$', {'version': ('0.1',), 'type': ('window', 'page', 'component'),
                            'theme': ('dark', 'light', 'auto')})
    for key in ('width', 'height'):
        if key in data:
            _number(data[key], f'$.{key}', 0)
    resources = data.get('resources', {})
    _object(resources, '$.resources')
    for key, value in resources.items():
        _string(key, '$.resources.key')
        _string(value, '$.resources.value')
        _require(is_ir_color(value), '$.resources', 'hex color (#RGB, #RRGGBB, #AARRGGBB)')

    seen = set()
    _, asset_refs = export_assets(data.get('assets', {}))

    def node(value, path, depth):
        _require(depth <= 128 and len(seen) < 10000, path, 'at most 128 levels and 10000 nodes')
        _object(value, path)
        for key in ('id', 'type'):
            _require(key in value, path, f'required field {key}')
            _string(value[key], f'{path}.{key}')
        _require(value['id'] not in seen, path + '.id', 'unique node id')
        seen.add(value['id'])
        _enum_fields(value, path, {'type': ('window', 'panel', 'frame', 'stack', 'grid',
                     'text', 'button', 'input', 'image', 'separator', 'card', 'badge', 'icon', 'unknown')})
        if 'name' in value:
            _string(value['name'], path + '.name')
        source = value.get('source', {})
        _object(source, path + '.source')
        for key in ('format', 'nodeId', 'nodeName', 'sourceType'):
            if key in source:
                _string(source[key], f'{path}.source.{key}')
        layout = value.get('layout', {})
        _object(layout, path + '.layout')
        _enum_fields(layout, path + '.layout', {
            'type': ('stack', 'grid', 'dock', 'absolute', 'none'),
            'direction': ('horizontal', 'vertical'),
            'align': ('start', 'center', 'end', 'stretch'),
            'crossAlign': ('start', 'center', 'end', 'stretch'),
            'widthMode': ('fixed', 'fill'), 'heightMode': ('fixed', 'fill'),
            'constraintH': ('left', 'right', 'center', 'stretch', 'scale'),
            'constraintV': ('top', 'bottom', 'center', 'stretch', 'scale')})
        for key in ('gap', 'grow', 'designWidth', 'designHeight', 'x', 'y', 'gridColumn', 'gridRow'):
            if key in layout:
                _number(layout[key], f'{path}.layout.{key}',
                        None if key in ('x', 'y') else 0,
                        2147483647 if key in ('gridColumn', 'gridRow') else None,
                        integer=key in ('gridColumn', 'gridRow'))
        for key in ('width', 'height', 'columns', 'rows', 'padding'):
            if key not in layout:
                continue
            val = layout[key]
            if key in ('columns', 'rows'):
                _require(isinstance(val, list), f'{path}.layout.{key}', 'array')
            if key == 'padding' and isinstance(val, list):
                _require(len(val) == 4, f'{path}.layout.{key}', 'four numbers')
            for item in val if isinstance(val, list) and key in ('columns', 'rows', 'padding') else [val]:
                allowed = ('*', 'Auto') if key in ('columns', 'rows') else ('Auto',) if key in ('width', 'height') else ()
                if isinstance(item, str) and item in allowed:
                    continue
                _number(item, f'{path}.layout.{key}', 0)
        style = value.get('style', {})
        _object(style, path + '.style')
        for key in ('background', 'foreground', 'borderColor', 'fontFamily', 'fontStyle', 'textAlign'):
            if key in style:
                _string(style[key], f'{path}.style.{key}')
        for key in ('background', 'foreground', 'borderColor'):
            if key in style:
                _require(is_ir_color(style[key]), f'{path}.style.{key}', 'hex color (#RGB, #RRGGBB, #AARRGGBB)')
        for key in ('borderThickness', 'cornerRadius', 'opacity', 'fontSize'):
            if key in style:
                _number(style[key], f'{path}.style.{key}', 0, 1 if key == 'opacity' else None)
                if key == 'fontSize':
                    _require(style[key] > 0, f'{path}.style.{key}', 'positive number')
        if 'fontWeight' in style:
            if isinstance(style['fontWeight'], str):
                _string(style['fontWeight'], path + '.style.fontWeight')
            else:
                _number(style['fontWeight'], path + '.style.fontWeight', 0)
        props = value.get('props', {})
        _object(props, path + '.props')
        for key in ('text', 'placeholder', 'command', 'icon', 'assetId', 'xName', 'tooltip', 'accessibleName', 'helpText', 'semanticRole'):
            if key in props:
                _string(props[key], f'{path}.props.{key}')
        if 'command' in props:
            _require(is_binding_identifier(props['command']), path + '.props.command', 'ASCII identifier')
        if value['type'] == 'image':
            _require(props.get('assetId') in asset_refs, path + '.props.assetId', 'existing embedded image asset')
        warnings = value.get('warnings', [])
        _require(isinstance(warnings, list), path + '.warnings', 'array')
        for warning in warnings:
            _string(warning, path + '.warnings')
        children = value.get('children', [])
        _require(isinstance(children, list), path + '.children', 'array')
        for i, child in enumerate(children):
            node(child, f'{path}.children[{i}]', depth + 1)

    if data['root'] is None and allow_empty_root:
        return
    node(data['root'], '$.root', 1)


def validate_ui_spec_model(spec):
    # Unlike to_dict(), do not drop invalid negative style values before validation.
    def raw(value, depth=0):
        _require(depth <= 260, '$', 'bounded, acyclic model')
        if is_dataclass(value):
            return {re.sub(r'_([a-z])', lambda m: m[1].upper(), f.name): raw(getattr(value, f.name), depth + 1)
                    for f in fields(value) if getattr(value, f.name) is not None or f.name == 'root'}
        if isinstance(value, list):
            return [raw(v, depth + 1) for v in value]
        return value
    validate_ui_spec_dict(raw(spec), allow_empty_root=True)
