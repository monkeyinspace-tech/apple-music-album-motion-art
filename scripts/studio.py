#!/usr/bin/env python3
"""Apple Music Album Motion Art — editor de motion por linha de comando (camadas · keyframes · efeitos · plugins).

Fluxo típico
  studio.py init capa.png work/proj --template punk-impact --intensity bold     # ou capa.psd (camadas) / 3000x3000 / 4K
  studio.py info work/proj                                                      # lista camadas e efeitos
  studio.py preview work/proj --sheet                                           # folha de contato (6 instantes)
  studio.py add-layer work/proj --effect embers --param origin=[742,1325] --param count=80
  studio.py add-effect work/proj title glow --param radius=40
  studio.py set work/proj subject.transform.rotation '{"wave":"sin","amp":2}'
  studio.py check work/proj                                                     # frame0, loop, flash, estouro
  studio.py render work/proj --upc 7891234567890 --formats 3x4
  studio.py render work/proj --upc 7891234567890 --formats 1x1
  studio.py effects                                                             # catálogo de efeitos
  studio.py new-effect meu_efeito --kind generator --project work/proj          # cria um plugin seu
  studio.py doctor --bench --selftest                                           # diagnóstico + estimativa de tempo
"""
import argparse, glob, json, os, shutil, sys, textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cv2
from amstudio.compat import imread, imwrite, fix_console
fix_console()
from amstudio import REF, fx, scene as S, ingest, outputs
from amstudio.curves import evaluate

INTENSITY = {'subtle': 0.6, 'standard': 1.0, 'bold': 1.5}


def _find_template(name):
    if os.path.exists(name): return name
    for base in (os.path.join(HERE, '..', 'configs', 'templates'), os.path.join(HERE, '..', 'configs')):
        p = os.path.join(base, name if name.endswith('.json') else name + '.json')
        if os.path.exists(p): return p
    sys.exit(f'template não encontrado: {name}. Disponíveis: {[os.path.basename(p)[:-5] for p in glob.glob(os.path.join(HERE, "..", "configs", "**", "*.json"), recursive=True)]}')


def _val(s):
    try: return json.loads(s)
    except Exception: return s


def _params(items):
    out = {}
    for it in items or []:
        k, _, v = it.partition('=')
        out[k.strip()] = _val(v)
    return out


def _load(a):
    d = a.project
    if not os.path.exists(S.scene_path(d)): sys.exit(f'projeto sem scene.json: {d} (rode "init" primeiro)')
    return d, S.load(d)


# ---------------------------------------------------------------------------------- comandos
def cmd_init(a):
    d = a.project
    os.makedirs(d, exist_ok=True)
    ext = os.path.splitext(a.source)[1].lower()
    K = INTENSITY.get(a.intensity, 1.0)
    impact = json.loads(a.impact) if a.impact else None
    if ext in ('.psd', '.psb'):
        from amstudio.psd_import import import_psd
        res = import_psd(a.source, d, mood=a.intensity, impact=impact)
        scene = {'version': 2, 'name': os.path.basename(d), 'source': {'flat': 'source_flat.png', 'psd': os.path.basename(a.source)},
                 'output': {'duration': a.duration, 'fps': a.fps, 'intensity': K, 'key_content_y': json.loads(a.key_content_y) if a.key_content_y else [75, 1320]},
                 'layers': res['layers']}
        if res['locks']:
            scene['layers'].append({'id': 'locks', 'type': 'lock', 'boxes': [[int(v) for v in next(l for l in res['layers'] if l['id'] == i)['bbox']] for i in res['locks']]})
        from amstudio import reconcile
        scene, e0, e1, applied = reconcile.reconcile(d, scene, res['adjust_index'])
        info = ingest.describe_size(*res['size'])
        notes = list(res['warnings'])
        rc = res['roles']
        notes.append('papéis detectados: ' + ', '.join(f'{n}×{r}' for r, n in sorted(rc.items(), key=lambda x: -x[1])))
        if applied:
            notes.append(f'camada "grade" criada: a composição divergia do Photoshop em {e0:.1f}/255 → {e1:.1f}/255 após a correção de cor')
        elif e0 > 1.5:
            notes.append(f'a composição diverge do Photoshop em {e0:.1f}/255')
        print(f'PSD: {info["w"]}x{info["h"]} ({info["class"]}) · {len([l for l in scene["layers"] if l["type"] == "image"])} camadas de imagem importadas')
    else:
        img, note = ingest.load_srgb(a.source)
        info = ingest.describe_size(img.shape[1], img.shape[0])
        img = ingest.fit_square(img, a.fit)
        notes = [f'cor: {note}']
        if a.remove_badge or a.badge_box:
            box = tuple(a.badge_box) if a.badge_box else ingest.detect_badge(img)
            if box is None: notes.append('selo NÃO detectado (use --badge-box x0 y0 x1 y1)')
            else:
                img = ingest.remove_region(img, box); notes.append(f'selo removido em {list(box)}')
        if not (a.remove_badge or a.badge_box) and ingest.detect_badge(img):
            notes.append('⚠ SELO Parental Advisory/Explicit detectado na capa: a Apple NÃO permite esse selo na arte de motion (a marcação explícita vai nos metadados). Rode de novo com --remove-badge')
        if min(img.shape[:2]) < 2048: notes.append(f'capa pequena ({img.shape[0]}px): o 1:1 (3840) será ampliado')
        imwrite(os.path.join(d, 'source_flat.png'), img)
        cfg = json.load(open(_find_template(a.template), encoding='utf-8')) if a.template else {'subject': {'enabled': False}, 'impact': None}
        if impact: cfg['impact'] = impact
        if a.key_content_y: cfg['key_content_y'] = json.loads(a.key_content_y)
        from amstudio import autolayer
        built = autolayer.build(img, cfg, d)
        scene = S.legacy_to_scene(cfg, built, name=os.path.basename(d), duration=a.duration, fps=a.fps, intensity=K)
        print(f'Imagem: {info["w"]}x{info["h"]} ({info["class"]}) · template: {a.template or "nenhum (só fundo + luz)"}')
    for n in notes: print('  •', n)
    errs, warns = S.validate(d, scene)
    S.save(d, scene)
    for w in warns: print('  AVISO:', w)
    for e in errs: print('  ERRO :', e)
    print(f'Projeto criado em {d}/  (scene.json + assets/). Próximo: studio.py info {d} · preview {d} --sheet')


def cmd_info(a):
    d, sc = _load(a)
    out = sc.get('output', {})
    print(f'Projeto: {sc.get("name")} · v{sc["version"]} · {out.get("duration")} s @ {out.get("fps")} fps · intensidade {out.get("intensity")}')
    print(f'Fonte: {sc.get("source")} · key_content_y {out.get("key_content_y")}')
    print(f'{"#":>2}  {"id":<14}{"tipo":<10}detalhes   (de baixo para cima)')
    for i, L in enumerate(sc['layers']):
        if L['type'] == 'generator': det = f'efeito={L["effect"]} {json.dumps(L.get("params", {}), ensure_ascii=False)[:90]}'
        elif L['type'] == 'lock': det = f'travar {len(L["boxes"])} região(ões)'
        else:
            fxs = ','.join(e['type'] for e in L.get('effects', []) or []) or '-'
            tr = ','.join(L.get('transform', {}) or {}) or '-'
            det = f'{L.get("asset", L.get("text", ""))!s:<24} efeitos[{fxs}] transform[{tr}] blend={L.get("blend", "normal")}'
        print(f'{i:>2}  {L["id"]:<14}{L["type"]:<10}{det}')


def cmd_effects(a):
    fx.load_plugins(os.path.join(a.project, 'plugins') if a.project else None)
    cat = fx.catalog()
    if a.md:
        for kind, title in (('layer', 'Efeitos de camada'), ('generator', 'Geradores')):
            print(f'\n## {title}\n')
            for e in [c for c in cat if c['kind'] == kind]:
                print(f'### `{e["name"]}`\n{e["doc"]}\n')
                print('| parâmetro | tipo | padrão | descrição |\n|---|---|---|---|')
                for k, v in e['params'].items():
                    print(f'| `{k}` | {v["type"]} | `{json.dumps(v["default"])}` | {v["doc"]} |')
                print()
        return
    for kind in ('layer', 'generator'):
        print(f'\n== {"EFEITOS DE CAMADA" if kind == "layer" else "GERADORES"} ==')
        for e in [c for c in cat if c['kind'] == kind]:
            print(f'  {e["name"]:<13} {e["doc"]}')
            print(f'  {"":<13} params: {", ".join(e["params"]) or "-"}')


def cmd_add_layer(a):
    d, sc = _load(a)
    if a.json: spec = json.loads(a.json)
    else:
        if not (a.effect and a.id): sys.exit('use --json ou (--id e --effect)')
        spec = {'id': a.id, 'type': 'generator', 'effect': a.effect, 'params': _params(a.param)}
    S.add_layer(sc, spec, a.index)
    errs, _ = S.validate(d, sc)
    if errs: sys.exit('inválido:\n  ' + '\n  '.join(errs))
    S.save(d, sc); print('ok: camada', spec['id'], 'adicionada')


def cmd_add_effect(a):
    d, sc = _load(a)
    S.add_effect(sc, a.layer, a.effect, _params(a.param))
    errs, _ = S.validate(d, sc)
    if errs: sys.exit('inválido:\n  ' + '\n  '.join(errs))
    S.save(d, sc); print(f'ok: {a.effect} adicionado a {a.layer}')


def cmd_set(a):
    d, sc = _load(a)
    S.set_path(sc, a.path, _val(a.value))
    errs, _ = S.validate(d, sc)
    if errs: sys.exit('inválido (nada foi salvo):\n  ' + '\n  '.join(errs))
    S.save(d, sc); print('ok:', a.path, '=', a.value)


def cmd_remove(a):
    d, sc = _load(a); S.remove_layer(sc, a.layer); S.save(d, sc); print('ok: removida', a.layer)


def cmd_move(a):
    d, sc = _load(a); S.move_layer(sc, a.layer, a.index); S.save(d, sc); print('ok: movida', a.layer, '→', a.index)


def cmd_preview(a):
    d, sc = _load(a)
    K = INTENSITY[a.intensity] if a.intensity else None
    pv = os.path.join(d, 'preview'); os.makedirs(pv, exist_ok=True)
    if a.gif:
        print('gif:', outputs.make_gif(d, sc, a.gif, K)); return
    if a.t:
        for p in outputs.stills(d, sc, pv, [float(t) for t in a.t], a.width, K, a.format): print('frame:', p)
        return
    p = outputs.contact_sheet(d, sc, os.path.join(pv, 'contact_sheet.png'), a.width, intensity=K, fmt=a.format)
    print('folha de contato:', p)


def cmd_check(a):
    d, sc = _load(a)
    rep = outputs.check(d, sc, intensity=INTENSITY[a.intensity] if a.intensity else None)
    for k, v in rep['metrics'].items(): print(f'  {k:<26} {v}')
    for w in rep['warnings']: print('  ⚠️ ', w)
    for e in rep['errors']: print('  ❌', e)
    print('RESULTADO:', 'REPROVADO' if rep['errors'] else 'OK (veja os avisos)')
    sys.exit(1 if rep['errors'] else 0)


def cmd_render(a):
    d, sc = _load(a)
    errs, _ = S.validate(d, sc)
    if errs: sys.exit('cena inválida:\n  ' + '\n  '.join(errs))
    if a.duration: sc['output']['duration'] = a.duration
    for fmt in [f.strip() for f in a.formats.split(',')]:
        outputs.render_format(d, sc, fmt, a.upc, a.outdir, a.codec, a.bitrate, a.work_size,
                              INTENSITY[a.intensity] if a.intensity else None, a.test_frames, container=a.container, static=a.static)


PLUGIN_GEN = '''"""Efeito personalizado: {name} (gerador).  Edite, salve e rode:  studio.py check <projeto>

REGRAS DE OURO (o `check` confere):
  1. Multiplique tudo por `e` (0 nas pontas do loop) -> frame 0 == capa e o loop fecha.
  2. Nada de flashes: mudanças suaves.
  3. Dimensione por `ctx.sc` (W/2048): o mesmo efeito funciona em 2048, 3000 e 4K.
"""
import math
import numpy as np
from amstudio.fx import generator


@generator('{name}', {{
    'strength': ('float', 0.2, 'intensidade do efeito'),
}}, 'Descreva aqui o que o efeito faz.')
class {cls}:
    def __init__(self, ctx, strength=0.2):
        self.W, self.K, self.s = ctx.W, ctx.K, strength

    def render(self, fr, t, e):
        # fr: float32 BGR 0..255 (W x W x 3). t: 0..1 do loop. e: (1-cos 2πt)/2  (0 → 1 → 0)
        # Exemplo: pulsar levemente o brilho do quadro todo
        fr *= 1.0 + self.s * self.K * e * 0.2
'''
PLUGIN_LAYER = '''"""Efeito personalizado: {name} (de camada).  Edite, salve e rode:  studio.py check <projeto>

`img` é float32 H x W x 4 (BGR pré-multiplicado + alfa). Retorne o array (novo ou modificado).
Mesmas regras de ouro: comece/termine em zero (use `e` ou sin(2πt)), sem flashes, escale por ctx.sc.
"""
import math
import numpy as np
from amstudio.fx import layer_fx


@layer_fx('{name}', {{
    'amp': ('float', 6.0, 'amplitude em px (espaço 2048)'),
}}, 'Descreva aqui o que o efeito faz.')
class {cls}:
    def __init__(self, ctx, layer, amp=6.0):
        self.a, self.ctx = amp * ctx.sc * ctx.K, ctx

    def apply(self, img, t, e):
        # Exemplo: desloca a camada na horizontal com onda que começa em zero
        import cv2
        dx = self.a * math.sin(2 * math.pi * t)
        M = np.float32([[1, 0, dx], [0, 1, 0]])
        return cv2.warpAffine(img, M, (img.shape[1], img.shape[0]), borderMode=cv2.BORDER_REPLICATE)
'''


def cmd_new_effect(a):
    pd = os.path.join(a.project, 'plugins') if a.project else os.path.join(os.path.expanduser('~'), '.apple_music_album_motion_art', 'plugins')
    os.makedirs(pd, exist_ok=True)
    path = os.path.join(pd, f'{a.name}.py')
    if os.path.exists(path) and not a.force: sys.exit(f'já existe: {path} (use --force)')
    cls = ''.join(p.capitalize() for p in a.name.split('_'))
    open(path, 'w', encoding='utf-8').write((PLUGIN_GEN if a.kind == 'generator' else PLUGIN_LAYER).format(name=a.name, cls=cls))
    print('plugin criado:', path)
    print('Use na cena:', '{"id":"x","type":"generator","effect":"%s","params":{}}' % a.name if a.kind == 'generator'
          else 'effects: [{"type":"%s"}] em uma camada de imagem' % a.name)


def cmd_doctor(a):
    from amstudio import doctor
    sys.exit(doctor.run(a))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)

    p = sp.add_parser('init', help='cria um projeto a partir de capa (PNG/JPG/TIFF 2048/3000/4K) ou PSD em camadas')
    p.add_argument('source'); p.add_argument('project')
    p.add_argument('--template', help='nome (punk-impact…) ou caminho de um config v1 .json')
    p.add_argument('--intensity', choices=list(INTENSITY), default='standard')
    p.add_argument('--impact', help='JSON [x,y] do ponto de energia (espaço 2048); habilita ondas/estilhaços/brasas')
    p.add_argument('--fit', choices=['error', 'crop', 'extend'], default='error', help='se a imagem não for quadrada')
    p.add_argument('--remove-badge', action='store_true'); p.add_argument('--badge-box', nargs=4, type=int)
    p.add_argument('--duration', type=float, default=12); p.add_argument('--fps', type=int, default=30)
    p.add_argument('--key-content-y', default=None, help='faixa vertical que deve caber na Safe Area do 3:4 (padrão: do template, ou automática com sujeito auto)')
    p.set_defaults(fn=cmd_init)

    p = sp.add_parser('info'); p.add_argument('project'); p.set_defaults(fn=cmd_info)
    p = sp.add_parser('effects', help='catálogo de efeitos'); p.add_argument('--md', action='store_true'); p.add_argument('--project'); p.set_defaults(fn=cmd_effects)

    p = sp.add_parser('add-layer'); p.add_argument('project'); p.add_argument('--json'); p.add_argument('--id'); p.add_argument('--effect')
    p.add_argument('--param', action='append'); p.add_argument('--index', type=int); p.set_defaults(fn=cmd_add_layer)
    p = sp.add_parser('add-effect'); p.add_argument('project'); p.add_argument('layer'); p.add_argument('effect'); p.add_argument('--param', action='append'); p.set_defaults(fn=cmd_add_effect)
    p = sp.add_parser('set'); p.add_argument('project'); p.add_argument('path'); p.add_argument('value'); p.set_defaults(fn=cmd_set)
    p = sp.add_parser('remove'); p.add_argument('project'); p.add_argument('layer'); p.set_defaults(fn=cmd_remove)
    p = sp.add_parser('move'); p.add_argument('project'); p.add_argument('layer'); p.add_argument('index', type=int); p.set_defaults(fn=cmd_move)

    p = sp.add_parser('preview'); p.add_argument('project'); p.add_argument('--sheet', action='store_true')
    p.add_argument('--t', nargs='*', help='instantes 0..1 (ex.: --t 0 0.5)'); p.add_argument('--gif'); p.add_argument('--width', type=int, default=768)
    p.add_argument('--format', choices=['3x4', '1x1'], default='3x4'); p.add_argument('--intensity', choices=list(INTENSITY)); p.set_defaults(fn=cmd_preview)

    p = sp.add_parser('check'); p.add_argument('project'); p.add_argument('--intensity', choices=list(INTENSITY)); p.set_defaults(fn=cmd_check)

    p = sp.add_parser('render'); p.add_argument('project'); p.add_argument('--upc', default='UPC'); p.add_argument('--formats', default='3x4')
    p.add_argument('--outdir', default='out'); p.add_argument('--codec', choices=['h264', 'prores'], default='h264'); p.add_argument('--bitrate', default='80M')
    p.add_argument('--container', choices=['mov', 'mp4'], default='mov', help='H.264: mov ou mp4 (algumas distribuidoras esperam .mp4 para H.264). ProRes é sempre mov')
    p.add_argument('--static', action='store_true', help='também salva o PNG estático (frame 0 == capa) de cada formato')
    p.add_argument('--work-size', default='auto', help='motor do 1:1: auto (nativo até 3840) | 2048 | 3000 | 3840')
    p.add_argument('--intensity', choices=list(INTENSITY)); p.add_argument('--duration', type=float); p.add_argument('--test-frames', type=int, default=0)
    p.set_defaults(fn=cmd_render)

    p = sp.add_parser('new-effect', help='cria o esqueleto de um efeito seu (plugin)'); p.add_argument('name')
    p.add_argument('--kind', choices=['generator', 'layer'], default='generator'); p.add_argument('--project'); p.add_argument('--force', action='store_true')
    p.set_defaults(fn=cmd_new_effect)

    p = sp.add_parser('doctor', help='autodiagnóstico: Python, FFmpeg, RAM, Unicode; --bench estima o tempo de render; --selftest roda um mini fluxo')
    p.add_argument('--bench', action='store_true'); p.add_argument('--selftest', action='store_true'); p.set_defaults(fn=cmd_doctor)

    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
