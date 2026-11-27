#!/usr/bin/env python3
"""Mede o tempo REAL de render de projetos (segundos por quadro) e extrapola para a duração completa.

Uso:  python tools/benchmark.py rotulo=pasta_do_projeto:formato[:work_size] ...  [--frames 24] [--json saida.json]
Ex.:  python tools/benchmark.py demo=work/demo:3x4 psd3000=work/psd:1x1:auto
Nenhum conteúdo dos projetos é gravado nos resultados — só números.
"""
import argparse, json, os, sys, tempfile, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
import cv2
from amstudio import scene as S, outputs
from amstudio.engine import Renderer
from amstudio.ingest import working_size
from amstudio.compat import imread


def bench(project, fmt, work='auto', frames=24):
    sc = S.load(project)
    flat = imread(S.flat_path(project, sc))
    W = 2048 if fmt == '3x4' else working_size(flat.shape[0], work)
    t0 = time.time(); r = Renderer(project, sc, W); init = time.time() - t0
    fps = sc['output'].get('fps', 30); N = r.N
    out = os.path.join(tempfile.gettempdir(), 'amstudio_bench_out.mov')
    if fmt == '3x4':
        ext = outputs.Ext3x4(r.ctx.cover, sc['output'].get('key_content_y', [75, 1320]), W)
        pp = outputs.encoder(out, W, ext.H, fps); conv = ext.make
    else:
        pp = outputs.encoder(out, 3840, 3840, fps)
        conv = (lambda f: f) if W == 3840 else (lambda f: cv2.resize(f, (3840, 3840), interpolation=cv2.INTER_CUBIC))
    r.frame(0); t_render = 0.0; t_all = time.time()
    for f in range(1, frames + 1):
        t = time.time(); fr = r.frame(f); t_render += time.time() - t
        pp.stdin.write(conv(fr).tobytes())
    pp.stdin.close(); pp.wait()
    wall = (time.time() - t_all) / frames
    try: os.remove(out)
    except OSError: pass
    return {'formato': fmt, 'motor_px': W, 'camadas': len(sc['layers']), 'init_s': round(init, 1), 'render_s_por_quadro': round(t_render / frames, 2),
            'parede_s_por_quadro': round(wall, 2), 'estimativa_360_quadros_min': round(wall * N / 60 + init / 60, 1)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cases', nargs='+'); ap.add_argument('--frames', type=int, default=24); ap.add_argument('--json')
    a = ap.parse_args(); res = {}
    for c in a.cases:
        label, _, rest = c.partition('='); parts = rest.split(':')
        res[label] = bench(parts[0], parts[1], parts[2] if len(parts) > 2 else 'auto', a.frames)
        print(label, json.dumps(res[label], ensure_ascii=False), flush=True)
    if a.json: json.dump(res, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
