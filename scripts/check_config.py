#!/usr/bin/env python3
"""Valida um config.json do Album Motion Studio (chaves, tipos e coordenadas no espaço 2048x2048).

Uso: check_config.py configs/templates/punk-impact.json [outro.json ...]
Código de saída 1 se houver ERRO. AVISOS não reprovam.
"""
import json, sys
for _s in (sys.stdout, sys.stderr):   # console legado do Windows (cp1252) quebra com emojis
    try: _s.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

S = 2048
KNOWN = {'key_content_y', 'impact', 'subject', 'title', 'hot_cracks', 'flow_protect', 'light_leaks', 'rings', 'shards',
         'embers', 'sparkles', 'lock_boxes', 'seed', 'leak_colors'}
SUB_KEYS = {'enabled', 'auto', 'pivot', 'bbox_origin', 'isnet_boxes', 'sway_deg', 'float_px', 'shift_px'}


def pt(v, name, errs):
    if not (isinstance(v, list) and len(v) == 2 and all(isinstance(i, (int, float)) for i in v)):
        errs.append(f'{name}: esperado [x, y]'); return
    if not (0 <= v[0] <= S and 0 <= v[1] <= S):
        errs.append(f'{name}: ponto {v} fora de 0..{S}')


def box(v, name, errs):
    if not (isinstance(v, list) and len(v) == 4 and all(isinstance(i, (int, float)) for i in v)):
        errs.append(f'{name}: esperado [x0, y0, x1, y1]'); return
    x0, y0, x1, y1 = v
    if not (0 <= x0 < x1 <= S and 0 <= y0 < y1 <= S):
        errs.append(f'{name}: caixa {v} inválida (precisa x0<x1, y0<y1, dentro de 0..{S})')


def check(cfg):
    errs, warns = [], []
    for k in cfg:
        if k not in KNOWN and not k.startswith('_'):
            warns.append(f'chave desconhecida "{k}" (será ignorada)')
    kc = cfg.get('key_content_y')
    if kc is not None:
        if not (isinstance(kc, list) and len(kc) == 2 and 0 <= kc[0] < kc[1] <= S):
            errs.append('key_content_y: esperado [y_topo, y_base] dentro de 0..2048')
        elif kc[1] - kc[0] > 1251:
            warns.append(f'key_content_y cobre {kc[1] - kc[0]} px; a Art Safe Area do 3:4 tem ~1251 px. '
                         'Itens-chave podem ficar sob a UI. Reduza a faixa ou aceite o corte.')
    if cfg.get('impact') is not None:
        pt(cfg['impact'], 'impact', errs)
    sub = cfg.get('subject') or {}
    for k in sub:
        if k not in SUB_KEYS:
            warns.append(f'subject.{k} desconhecido')
    if sub.get('enabled', True):
        if 'pivot' in sub: pt(sub['pivot'], 'subject.pivot', errs)
        if 'bbox_origin' in sub: pt(sub['bbox_origin'], 'subject.bbox_origin', errs)
        for i, b in enumerate(sub.get('isnet_boxes', [])):
            box(b, f'subject.isnet_boxes[{i}]', errs)
        if not sub.get('isnet_boxes') and not sub.get('auto'):
            warns.append('subject.isnet_boxes vazio: só o modelo u2net será usado (pode perder objetos finos como tacos/instrumentos).')
        for k, lim in (('sway_deg', 4), ('float_px', 40), ('shift_px', 40)):
            if sub.get(k, 0) > lim:
                warns.append(f'subject.{k}={sub[k]} é alto; movimentos grandes expõem o fundo reconstruído.')
    if cfg.get('title'):
        box(cfg['title'].get('box'), 'title.box', errs)
        if not 10 <= cfg['title'].get('texture_thr', 55) <= 200:
            warns.append('title.texture_thr fora de 10..200')
    if cfg.get('hot_cracks'):
        box(cfg['hot_cracks'].get('roi'), 'hot_cracks.roi', errs)
        if not cfg.get('impact'):
            warns.append('hot_cracks sem "impact": será ignorado.')
    for i, pr in enumerate(cfg.get('flow_protect', [])):
        pt(pr.get('center'), f'flow_protect[{i}].center', errs)
        if not (isinstance(pr.get('axes'), list) and len(pr['axes']) == 2):
            errs.append(f'flow_protect[{i}].axes: esperado [a, b]')
    for i, z in enumerate(cfg.get('sparkles', [])):
        box(z.get('box'), f'sparkles[{i}].box', errs)
        if not isinstance(z.get('count'), int) or z['count'] < 0:
            errs.append(f'sparkles[{i}].count: inteiro >= 0')
    for i, b in enumerate(cfg.get('lock_boxes', [])):
        box(b, f'lock_boxes[{i}]', errs)
    if cfg.get('leak_colors') is not None:
        lc = cfg['leak_colors']
        if not (len(lc) == 2 and all(len(c) == 3 and all(0 <= v <= 255 for v in c) for c in lc)):
            errs.append('leak_colors: esperado [[B,G,R],[B,G,R]] com 0..255 (ordem BGR do OpenCV)')
    for k in ('shards', 'embers'):
        if not isinstance(cfg.get(k, 0), int) or cfg.get(k, 0) < 0:
            errs.append(f'{k}: inteiro >= 0')
        elif cfg.get(k, 0) > 300:
            warns.append(f'{k}={cfg[k]} é muito alto; o render ficará lento.')
    if (cfg.get('shards') or cfg.get('embers') or cfg.get('rings')) and not cfg.get('impact'):
        warns.append('shards/embers/rings sem "impact": nada será desenhado. Defina "impact" ou ponha 0/false.')
    return errs, warns


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    bad = False
    for path in sys.argv[1:]:
        try:
            cfg = json.load(open(path, encoding='utf-8'))
        except Exception as e:
            print(f'❌ {path}: JSON inválido ({e})'); bad = True; continue
        errs, warns = check(cfg)
        print(('❌' if errs else '✅') + f' {path}')
        for e in errs: print('   ERRO  :', e)
        for w in warns: print('   AVISO :', w)
        bad |= bool(errs)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
