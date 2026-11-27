#!/usr/bin/env python3
"""Compatibilidade (v1): capa + config.json → vídeos. Internamente usa o motor v2 (studio.py).

Para o fluxo completo (PSD, camadas, keyframes, efeitos, plugins) use `studio.py`.

Exemplos:
  render_motion.py --cover capa.png --config configs/templates/punk-impact.json --outdir out --preview
  render_motion.py --cover capa.png --config cfg.json --outdir out --upc 7891234567890 --formats 3x4
"""
import argparse, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cv2, numpy as np
from amstudio.compat import imread, imwrite, fix_console
fix_console()
import studio
from amstudio import scene as S, outputs
from amstudio.engine import Renderer

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--cover', required=True)
ap.add_argument('--config')
ap.add_argument('--outdir', default='out')
ap.add_argument('--upc', default='UPC')
ap.add_argument('--formats', default='3x4,1x1')
ap.add_argument('--duration', type=float, default=12)
ap.add_argument('--fps', type=int, default=30)
ap.add_argument('--intensity', choices=['subtle', 'standard', 'bold'], default='standard')
ap.add_argument('--codec', choices=['h264', 'prores'], default='h264')
ap.add_argument('--bitrate', default='80M')
ap.add_argument('--work-size', default='auto')
ap.add_argument('--preview', action='store_true')
ap.add_argument('--test-frames', type=int, default=0)
ap.add_argument('--gif')
a = ap.parse_args()

proj = os.path.join(a.outdir, '.project')
os.makedirs(a.outdir, exist_ok=True)
ns = argparse.Namespace(source=a.cover, project=proj, template=a.config, intensity=a.intensity, impact=None, fit='error',
                        remove_badge=False, badge_box=None, duration=a.duration, fps=a.fps, key_content_y=None)
import contextlib, io
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    studio.cmd_init(ns)
scene = S.load(proj)
errs, warns = S.validate(proj, scene)
if errs:
    sys.exit('Erro:\n  ' + '\n  '.join(errs))

K = studio.INTENSITY[a.intensity]
if a.preview:
    r = Renderer(proj, scene, 768, K)
    flat = cv2.resize(imread(S.flat_path(proj, scene)), (768, 768), interpolation=cv2.INTER_AREA)
    diff = float(np.abs(r.frame(0).astype(float) - flat.astype(float)).mean())
    print(f'frame0 vs capa (diferença média abs): {diff:.3f}')
    path = outputs.contact_sheet(proj, scene, os.path.join(a.outdir, 'preview_contact_sheet.png'), 768, intensity=K)
    print('preview:', path)
    sys.exit(0)
if a.gif:
    print('gif:', outputs.make_gif(proj, scene, a.gif, K)); sys.exit(0)
for fmt in [f.strip() for f in a.formats.split(',')]:
    outputs.render_format(proj, scene, fmt, a.upc, a.outdir, a.codec, a.bitrate, a.work_size, K, a.test_frames)
