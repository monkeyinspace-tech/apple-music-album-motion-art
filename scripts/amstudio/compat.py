"""Portabilidade (Windows/macOS/Linux): E/S de imagens com caminhos Unicode e console UTF-8.

- cv2.imread/imwrite NÃO funcionam com caminhos não-ASCII no Windows (ex.: C:\\Users\\João\\Área de Trabalho) e falham em silêncio.
  `imread`/`imwrite` aqui usam numpy + imdecode/imencode, que funcionam em qualquer SO.
- O console legado do Windows (cp1252) quebra com emojis (✅ ❌ ⚠️): `fix_console()` força UTF-8 com substituição segura.
"""
import os, sys
import cv2, numpy as np


def imread(path, flags=cv2.IMREAD_COLOR):
    try:
        data = np.fromfile(path, dtype=np.uint8)
    except (FileNotFoundError, OSError):
        return None
    if data.size == 0:
        return None
    return cv2.imdecode(data, flags)


def imwrite(path, img, params=None):
    ext = os.path.splitext(path)[1] or '.png'
    ok, buf = cv2.imencode(ext, img, params or [])
    if not ok:
        return False
    buf.tofile(path)
    return True


def fix_console():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
