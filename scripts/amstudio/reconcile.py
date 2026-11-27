"""Reconciliação com o achatado do Photoshop.

PSDs reais usam camadas de ajuste (Curves, Brightness/Contrast, Hue/Saturation), máscaras, efeitos de camada e smart objects que
o motor não replica pixel a pixel. Para que o FRAME 0 continue == capa (exigência da Apple), comparamos a composição das
camadas com a PRÉVIA EMBUTIDA do Photoshop e ajustamos:
  1) uma curva de cor por canal (LUT monótona) — aproxima Curves/BC/Levels/Hue-Sat globais;
  2) uma correção suave de baixa frequência (resíduo borrado) — aproxima vinhetas, texturas translúcidas e desvios de cor locais.
Ambas entram como uma camada `adjust` (estática) acima das camadas do PSD. Não mexe em detalhes finos (nada de "fantasmas").
"""
import json, os
import cv2, numpy as np
from .compat import imread, imwrite
from . import scene as S


def _blur(x, s): return cv2.GaussianBlur(x.astype(np.float32), (0, 0), s)


def fit_lut(ours, flat, bins=256, min_count=40):
    """LUT monótona por canal (BGR) que leva `ours` → `flat` (medianas por faixa de intensidade). ours/flat: float32 HxWx3."""
    luts = []
    for c in range(3):
        x = np.clip(ours[..., c].ravel(), 0, 255).astype(np.int32)
        y = flat[..., c].ravel()
        lut = np.full(bins, np.nan, np.float32)
        order = np.argsort(x, kind='stable'); xs, ys = x[order], y[order]
        edges = np.searchsorted(xs, np.arange(bins + 1))
        for v in range(bins):
            a, b = edges[v], edges[v + 1]
            if b - a >= min_count:
                lut[v] = np.median(ys[a:b])
        ok = ~np.isnan(lut)
        if ok.sum() < 8:
            lut = np.arange(bins, dtype=np.float32)
        else:
            lut = np.interp(np.arange(bins), np.arange(bins)[ok], lut[ok]).astype(np.float32)
            lut = np.maximum.accumulate(lut)                 # monótona não decrescente
            k = 9; lut = np.convolve(np.pad(lut, (k // 2, k // 2), mode='edge'), np.ones(k) / k, mode='valid')
        luts.append(np.clip(lut, 0, 255))
    return luts


def reconcile(project_dir, scene, insert_at, W=1024, residual_sigma=24.0, log=print):
    """Insere uma camada `adjust` em `insert_at` se a composição divergir do achatado. Retorna (scene, erro_antes, erro_depois, aplicou)."""
    from .engine import Renderer
    flat = imread(S.flat_path(project_dir, scene))
    flat = cv2.resize(flat, (W, W), interpolation=cv2.INTER_AREA).astype(np.float32)
    ours = Renderer(project_dir, scene, W).frame(0).astype(np.float32)
    err0 = float(np.abs(_blur(ours, 1.5) - _blur(flat, 1.5)).mean())
    if err0 <= 1.5:
        return scene, err0, err0, False
    luts = fit_lut(ours, flat)
    lut_d = {c: [round(float(v), 2) for v in luts[i]] for i, c in enumerate(('b', 'g', 'r'))}
    graded = np.stack([np.interp(np.clip(ours[..., i], 0, 255), np.arange(256), luts[i]) for i in range(3)], -1)
    # resíduo suave (σ proporcional ao W de análise)
    res = np.clip(_blur(flat - graded, residual_sigma * W / 1024.0), -120, 120)
    after = float(np.abs(_blur(graded + res, 1.5) - _blur(flat, 1.5)).mean())
    assets = os.path.join(project_dir, 'assets'); os.makedirs(assets, exist_ok=True)
    with open(os.path.join(assets, 'grade_lut.json'), 'w', encoding='utf-8') as f:
        json.dump(lut_d, f)
    imwrite(os.path.join(assets, 'grade_residual.png'), np.clip(res + 128, 0, 255).astype(np.uint8))
    layer = {'id': 'grade', 'type': 'adjust', 'lut': 'assets/grade_lut.json', 'residual': 'assets/grade_residual.png',
             'note': f'aproxima camadas de ajuste/efeitos do PSD (erro vs. Photoshop: {err0:.1f} → {after:.1f}/255)'}
    scene['layers'].insert(insert_at, layer)
    return scene, err0, after, True
