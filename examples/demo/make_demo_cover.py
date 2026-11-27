#!/usr/bin/env python3
"""Gera a capa de demonstração 'ORBIT / DEMO COVER' (2048x2048) 100% por código.

Livre de direitos autorais (CC0): serve para testar o pipeline, os templates e o CI sem expor arte de ninguém.
Uso: python make_demo_cover.py [saida.png]
"""
import sys
import numpy as np, cv2

S = 2048
rng = np.random.default_rng(42)


def smooth(h, w, cell, seed):
    r = np.random.default_rng(seed)
    f = r.normal(0, 1, (h // cell + 2, w // cell + 2)).astype(np.float32)
    f = cv2.resize(f, (w, h), interpolation=cv2.INTER_CUBIC)
    return cv2.GaussianBlur(f, (0, 0), cell / 3)


# --- fundo: fumaça roxa/magenta sobre preto -------------------------------------------------
yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
n = smooth(S, S, 300, 1) * 0.6 + smooth(S, S, 120, 2) * 0.4
n = (n - n.min()) / (n.max() - n.min())
base = np.zeros((S, S, 3), np.float32)                      # BGR
vign = np.clip(1.15 - np.hypot(xx - S * 0.55, yy - S * 0.6) / (S * 0.75), 0, 1)
base[..., 2] = 30 + 190 * n * vign                           # R
base[..., 1] = 8 + 40 * n * vign                             # G
base[..., 0] = 40 + 150 * n * vign                           # B
base *= np.clip(0.35 + 0.65 * (yy / S) ** 0.7, 0, 1)[..., None]   # topo mais escuro

# --- planeta rachado no canto inferior esquerdo ---------------------------------------------
cx, cy, R = 560, 1380, 470
d = np.hypot(xx - cx, yy - cy)
inside = d < R
shade = np.clip(1 - ((xx - cx + 140) ** 2 + (yy - cy + 160) ** 2) ** 0.5 / (R * 1.5), 0, 1)
tex = smooth(S, S, 40, 7) * 0.5 + smooth(S, S, 12, 8) * 0.5
planet = np.stack([60 + 90 * shade + 25 * tex, 40 + 70 * shade + 18 * tex, 25 + 55 * shade + 12 * tex], -1)
a = cv2.GaussianBlur(inside.astype(np.float32), (0, 0), 2)[..., None]
img = base * (1 - a) + planet * a

# rachaduras brilhantes (laranja) saindo do ponto de impacto
IMPACT = (900, 1300)
crack = np.zeros((S, S), np.uint8)
for ang in np.linspace(0, 2 * np.pi, 13)[:-1] + rng.uniform(-0.2, 0.2, 12):
    x, y = IMPACT
    for _ in range(14):
        ang += rng.uniform(-0.45, 0.45)
        L = rng.uniform(35, 75)
        nx, ny = int(x + np.cos(ang) * L), int(y + np.sin(ang) * L)
        if np.hypot(nx - cx, ny - cy) > R * 0.98:
            break
        cv2.line(crack, (x, y), (nx, ny), 255, rng.integers(2, 6), cv2.LINE_AA)
        x, y = nx, ny
crack = crack.astype(np.float32) / 255 * (d < R)
glow = cv2.GaussianBlur(crack, (0, 0), 10)
img[..., 2] += crack * 255 + glow * 160
img[..., 1] += crack * 105 + glow * 40
img[..., 0] += crack * 15

# fragmentos escuros voando
for _ in range(90):
    ang = rng.uniform(-np.pi, -0.05)
    dist = rng.uniform(80, 700)
    px, py = IMPACT[0] + np.cos(ang) * dist, IMPACT[1] + np.sin(ang) * dist * 0.9
    r = rng.uniform(5, 26)
    pts = np.array([[px + np.cos(t) * r * rng.uniform(0.5, 1), py + np.sin(t) * r * rng.uniform(0.5, 1)]
                    for t in np.linspace(0, 2 * np.pi, rng.integers(5, 8), endpoint=False)], np.int32)
    cv2.fillConvexPoly(img, pts, (36, 28, 40), cv2.LINE_AA)
    cv2.polylines(img, [pts], True, (110, 90, 240), 1, cv2.LINE_AA)

# --- título em peças de papel (estilo bilhete de resgate) -----------------------------------
PAPER = [(190, 90, 255), (60, 140, 255), (230, 225, 245), (170, 60, 240), (90, 170, 255)]   # BGR
def piece(img, text, x, y, w, h, color, ang, scale):
    layer = np.zeros((h + 40, w + 40, 3), np.uint8)
    alpha = np.zeros((h + 40, w + 40), np.uint8)
    cv2.rectangle(layer, (20, 20), (w + 20, h + 20), color, -1)
    cv2.rectangle(alpha, (20, 20), (w + 20, h + 20), 255, -1)
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, scale, 14)
    cv2.putText(layer, text, (20 + (w - tw) // 2, 20 + (h + th) // 2), cv2.FONT_HERSHEY_DUPLEX, scale, (15, 10, 20), 14, cv2.LINE_AA)
    M = cv2.getRotationMatrix2D(((w + 40) / 2, (h + 40) / 2), ang, 1)
    layer = cv2.warpAffine(layer, M, (w + 40, h + 40), flags=cv2.INTER_LINEAR)
    alpha = cv2.warpAffine(alpha, M, (w + 40, h + 40), flags=cv2.INTER_LINEAR)
    x0, y0 = int(x - (w + 40) / 2), int(y - (h + 40) / 2)
    sa = (alpha.astype(np.float32) / 255)[..., None]
    roi = img[y0:y0 + h + 40, x0:x0 + w + 40]
    roi[:] = roi * (1 - sa) + layer.astype(np.float32) * sa


for i, ch in enumerate('ORBIT'):
    piece(img, ch, 260 + i * 290, 300, 250, 330, PAPER[i % 5], float(rng.uniform(-6, 6)), 6.0)
for i, ch in enumerate('DEMO'):
    piece(img, ch, 520 + i * 270, 720, 230, 300, PAPER[(i + 2) % 5], float(rng.uniform(-6, 6)), 5.4)

# --- ruído de filme leve --------------------------------------------------------------------
img += rng.normal(0, 0.9, (S, S, 1)).astype(np.float32)
out = np.clip(img, 0, 255).astype(np.uint8)
cv2.imwrite(sys.argv[1] if len(sys.argv) > 1 else 'demo_cover.png', out)
print('ok')
