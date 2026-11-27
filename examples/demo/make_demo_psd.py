#!/usr/bin/env python3
"""Gera um PSD EM CAMADAS de demonstração (Fundo · Planeta · Titulo · Logo) — livre de direitos (CC0).

Uso: python make_demo_psd.py [saida.psd] [lado_em_px=3000]
Serve para testar a importação de PSD (nomes de camada → papéis → movimento automático).
"""
import sys
import numpy as np, cv2
from PIL import Image
from psd_tools import PSDImage
from psd_tools.api.layers import PixelLayer

out = sys.argv[1] if len(sys.argv) > 1 else 'demo_layers.psd'
S = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
k = S / 2048
rng = np.random.default_rng(7)


def smooth(h, w, cell, seed):
    r = np.random.default_rng(seed)
    f = r.normal(0, 1, (h // cell + 2, w // cell + 2)).astype(np.float32)
    return cv2.GaussianBlur(cv2.resize(f, (w, h), interpolation=cv2.INTER_CUBIC), (0, 0), cell / 3)


# --- Fundo (opaco, completo) ------------------------------------------------------------
yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
n = smooth(S, S, int(400 * k), 1) * 0.6 + smooth(S, S, int(150 * k), 2) * 0.4
n = (n - n.min()) / (n.max() - n.min())
vig = np.clip(1.15 - np.hypot(xx - S * 0.55, yy - S * 0.6) / (S * 0.75), 0, 1)
bg = np.stack([40 + 150 * n * vig, 8 + 40 * n * vig, 30 + 190 * n * vig], -1) * np.clip(0.35 + 0.65 * (yy / S) ** 0.7, 0, 1)[..., None]
bg_rgba = np.dstack([np.clip(bg, 0, 255)[..., ::-1], np.full((S, S), 255)]).astype(np.uint8)   # RGB

# --- Planeta (RGBA, recorte) ------------------------------------------------------------
R = int(470 * k); pw = 2 * R + 20; c = pw // 2
d = np.hypot(*(np.mgrid[0:pw, 0:pw].astype(np.float32) - c))
shade = np.clip(1 - np.hypot(*(np.mgrid[0:pw, 0:pw].astype(np.float32) - c + 140 * k)) / (R * 1.5), 0, 1)
tex = smooth(pw, pw, int(40 * k), 5)
pl = np.stack([25 + 55 * shade + 12 * tex, 40 + 70 * shade + 18 * tex, 60 + 90 * shade + 25 * tex], -1)
pl_rgba = np.dstack([np.clip(pl, 0, 255), np.clip((R - d) * 2, 0, 1) * 255]).astype(np.uint8)
crack = np.zeros((pw, pw), np.uint8)
for ang in np.linspace(0, 2 * np.pi, 11)[:-1]:
    x, y = int(c + R * 0.55), c
    for _ in range(12):
        ang += rng.uniform(-0.4, 0.4); L = rng.uniform(30, 70) * k
        nx, ny = int(x + np.cos(ang) * L), int(y + np.sin(ang) * L)
        if np.hypot(nx - c, ny - c) > R * 0.97: break
        cv2.line(crack, (x, y), (nx, ny), 255, max(1, int(rng.integers(2, 4) * k * 0.6)), cv2.LINE_AA); x, y = nx, ny
g = cv2.GaussianBlur(crack.astype(np.float32), (0, 0), 8 * k)
pl_rgba[..., 0] = np.clip(pl_rgba[..., 0] + crack + g * 150, 0, 255); pl_rgba[..., 1] = np.clip(pl_rgba[..., 1] + crack * 0.45 + g * 60, 0, 255)

# --- Título (RGBA com papéis) -----------------------------------------------------------
tw, th = int(1500 * k), int(900 * k)
tl = np.zeros((th, tw, 4), np.uint8)
PAPER = [(255, 90, 190), (255, 140, 60), (245, 225, 230), (240, 60, 170), (255, 170, 90)]   # RGB
def piece(txt, cx, cy, w, h, col, ang, sc):
    pd = max(6, int(20 * k))
    lay = np.zeros((h + 2 * pd, w + 2 * pd, 4), np.uint8); lay[pd:h + pd, pd:w + pd] = (*col, 255)
    (a, b), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_DUPLEX, sc, max(1, int(14 * k)))
    cv2.putText(lay, txt, (pd + (w - a) // 2, pd + (h + b) // 2), cv2.FONT_HERSHEY_DUPLEX, sc, (15, 10, 20, 255), max(1, int(14 * k)), cv2.LINE_AA)
    M = cv2.getRotationMatrix2D(((w + 2 * pd) / 2, (h + 2 * pd) / 2), ang, 1)
    lay = cv2.warpAffine(lay, M, (w + 2 * pd, h + 2 * pd))
    x0, y0 = int(cx - (w + 2 * pd) / 2), int(cy - (h + 2 * pd) / 2)
    reg = tl[y0:y0 + h + 2 * pd, x0:x0 + w + 2 * pd]; a_ = lay[..., 3:] / 255.0
    reg[:] = (reg * (1 - a_) + lay * a_).astype(np.uint8)
    reg[..., 3] = np.maximum(reg[..., 3], lay[..., 3])
for i, ch in enumerate('ORBIT'):
    piece(ch, int((175 + i * 290) * k), int(220 * k), int(250 * k), int(330 * k), PAPER[i % 5], float(rng.uniform(-6, 6)), 6.0 * k)
for i, ch in enumerate('DEMO'):
    piece(ch, int((430 + i * 270) * k), int(640 * k), int(230 * k), int(300 * k), PAPER[(i + 2) % 5], float(rng.uniform(-6, 6)), 5.4 * k)

# --- Logo (RGBA, deve ficar parado) -----------------------------------------------------
lw, lh = int(420 * k), int(110 * k)
lg = np.zeros((lh, lw, 4), np.uint8); lg[:] = (255, 255, 255, 235)
(a, b), _ = cv2.getTextSize('LABEL', cv2.FONT_HERSHEY_DUPLEX, 2.2 * k, int(6 * k))
cv2.putText(lg, 'LABEL', ((lw - a) // 2, (lh + b) // 2), cv2.FONT_HERSHEY_DUPLEX, 2.2 * k, (10, 10, 10, 255), int(6 * k), cv2.LINE_AA)

psd = PSDImage.new('RGB', (S, S), color=(0, 0, 0))
for name, arr, left, top in (('Fundo', bg_rgba, 0, 0), ('Planeta', pl_rgba, int(120 * k), int(930 * k)),
                              ('Titulo', tl, int(100 * k), int(90 * k)), ('Logo', lg, int(70 * k), S - lh - int(70 * k))):
    psd.append(PixelLayer.frompil(Image.fromarray(arr, 'RGBA'), psd, name, top=top, left=left))
psd.save(out)
print('ok', out, f'{S}x{S}', [l.name for l in psd])
