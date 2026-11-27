#!/usr/bin/env python3
"""Prepara a capa para o pipeline.

- aceita PNG/JPG/TIFF/PSD em qualquer tamanho quadrado (2048, 3000, 3840, 4096…)
- converte para sRGB, avisa se for pequena, quadra imagens não-quadradas (--fit crop|extend)
- (opcional) detecta e remove o selo Parental Advisory / Explicit por inpainting
- salva PNG + relatório JSON no stdout

Uso:
  prepare_cover.py capa.jpg --out capa_limpa.png [--remove-badge] [--box x0 y0 x1 y1] [--size 2048] [--fit crop]
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cv2
from amstudio.compat import imread, imwrite, fix_console
from amstudio.ingest import load_srgb, detect_badge, remove_region, describe_size, fit_square  # noqa: F401  (reexport p/ testes)


def main():
    fix_console()
    ap = argparse.ArgumentParser()
    ap.add_argument('cover')
    ap.add_argument('--out', required=True)
    ap.add_argument('--remove-badge', action='store_true')
    ap.add_argument('--box', nargs=4, type=int, metavar=('X0', 'Y0', 'X1', 'Y1'))
    ap.add_argument('--size', type=int, default=0, help='reamostra a capa quadrada para este lado (ex.: 2048). Sem isso, mantém o tamanho nativo')
    ap.add_argument('--fit', choices=['error', 'crop', 'extend'], default='error', help='se a imagem não for quadrada')
    a = ap.parse_args()

    img, note = load_srgb(a.cover)
    h, w = img.shape[:2]
    info = describe_size(w, h)
    rep = {'entrada': a.cover, 'tamanho': [w, h], 'classe': info['class'], 'cor': note, 'avisos': []}
    if w != h:
        try:
            img = fit_square(img, a.fit)
            rep['avisos'].append(f'Imagem não quadrada ({w}x{h}) ajustada com --fit {a.fit}.')
        except ValueError as e:
            rep['avisos'].append(str(e)); print(json.dumps(rep, ensure_ascii=False, indent=2)); return 1
        h, w = img.shape[:2]
    if min(w, h) < 2048:
        rep['avisos'].append(f'Capa menor que 2048 px ({w}x{h}). O 1:1 (3840) será uma ampliação com perda de nitidez.')
    if a.size and w != a.size:
        img = cv2.resize(img, (a.size, a.size), interpolation=cv2.INTER_AREA if a.size < w else cv2.INTER_LANCZOS4)
        rep['reamostrada_para'] = a.size
    if a.remove_badge or a.box:
        box = tuple(a.box) if a.box else detect_badge(img)
        if box is None:
            rep['avisos'].append('Selo NÃO detectado automaticamente. Use --box x0 y0 x1 y1.')
        else:
            img = remove_region(img, box)
            rep['selo_removido_em'] = list(map(int, box))
    imwrite(a.out, img)
    rep['saida'] = a.out
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    sys.exit(main())
