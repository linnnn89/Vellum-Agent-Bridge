"""Export embedded raster assets without fetching URLs or reading source paths."""
import base64
import binascii
import hashlib
import re


def export_assets(assets):
    if not isinstance(assets, dict):
        raise ValueError('assets must be an object')
    files, references = {}, {}
    total = 0
    for key, value in assets.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError('Asset IDs and data URIs must be strings')
        if len(value) > 28_000_000:
            raise ValueError('Embedded image exceeds 20 MiB limit')
        match = re.fullmatch(r'data:image/(png|jpeg|gif|bmp|x-icon|tiff);base64,([A-Za-z0-9+/=\s]+)', value)
        if not match:
            raise ValueError('Expected embedded PNG/JPEG/GIF/BMP/ICO/TIFF data URI; external sources are unsupported')
        try:
            data = base64.b64decode(re.sub(r'\s', '', match[2]), validate=True)
        except binascii.Error as e:
            raise ValueError('Invalid embedded image base64') from e
        signatures = {'png': (b'\x89PNG\r\n\x1a\n',), 'jpeg': (b'\xff\xd8\xff',),
                      'gif': (b'GIF87a', b'GIF89a'), 'bmp': (b'BM',),
                      'x-icon': (b'\x00\x00\x01\x00',), 'tiff': (b'II*\x00', b'MM\x00*')}
        if not data.startswith(signatures[match[1]]):
            raise ValueError('Embedded image signature does not match its MIME type')
        total += len(data)
        if len(data) > 20 * 1024**2 or total > 100 * 1024**2:
            raise ValueError('Embedded image size limit exceeded')
        extension = {'jpeg': 'jpg', 'x-icon': 'ico'}.get(match[1], match[1])
        path = f'Assets/{hashlib.sha256(data).hexdigest()}.{extension}'
        references[key] = path
        files[path] = data
    return files, references
