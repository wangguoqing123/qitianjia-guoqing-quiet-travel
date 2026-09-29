"""Read explicitly listed local raster assets; never fetch images at render time."""
from __future__ import annotations
import base64
import hashlib
import os
from pathlib import Path
from trip_support import inside

MAX_IMAGE_BYTES = 3 * 1024 * 1024
MAX_MEDIA_BYTES = 8 * 1024 * 1024

def media_assets(trip, base_dir):
    records = trip.get('media', [])
    if not records:
        return {}
    if not base_dir:
        raise ValueError('含图片的行程需要实际行程目录以读取本地图片')
    result, total = {}, 0
    for record in records:
        rel = record['path']
        if os.path.isabs(rel) or not rel.replace('\\', '/').startswith('media/'):
            raise ValueError('图片必须保存为行程目录内 media/ 下的相对路径')
        path = Path(inside(base_dir, os.path.join(base_dir, rel)))
        size = path.stat().st_size
        if size > MAX_IMAGE_BYTES:
            raise ValueError('单张图片超过 3 MB，请先选取合适分辨率的版本')
        total += size
        if total > MAX_MEDIA_BYTES:
            raise ValueError('行程图片合计超过 8 MB，请减少或优化素材')
        data = path.read_bytes()
        if data.startswith(b'\xff\xd8\xff'):
            mime = 'image/jpeg'
        elif data.startswith(b'\x89PNG\r\n\x1a\n'):
            mime = 'image/png'
        elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            mime = 'image/webp'
        else:
            raise ValueError('图片内容不是支持的 JPEG、PNG 或 WebP')
        result[record['media_id']] = dict(record, full_path=str(path), mime=mime,
            bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
            data_uri='data:' + mime + ';base64,' + base64.b64encode(data).decode('ascii'))
    return result
