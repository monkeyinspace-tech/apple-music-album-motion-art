"""Importa um PSD em camadas: cada camada de pixels vira um PNG em assets/ + uma camada na cena.

Papéis são adivinhados pelo TIPO da camada, pelo NOME (pt/en) e pelo NOME DO GRUPO (camadas herdam o papel do grupo pai).
Cada papel recebe um movimento inicial SEGURO — o que não é reconhecido fica PARADO (você ou o agente decidem depois):

  papel      palavras-chave (pt/en)                              movimento inicial
  bg         fundo, background, bg, smoke, cenario               fumaça viva (flow) + respiração de zoom
  subject    pessoa, artist, model, kid, menino, face…           balanço, flutuação (pivô na base)
  title      título, text, lettering, name… e camadas de texto    leve flutuação + brilho varrendo
  waves      onda(s), wave, mar, sea, água                        deslizamento horizontal suave
  floater    barco, boat, ship, balão, plane, fish                sobe/desce + leve rotação
  sun        sol, sun, lua, moon, estrela                         pulsa (zoom) + glow
  drift      nuvem, cloud, neblina, fog                           deriva horizontal lenta
  lock       logo, legal, créditos, parental, records…            PARADO
  overlay    camadas de tela cheia com mesclagem/opacidade/fill   PARADO (texturas, cores, brilhos)
  credit     texto pequeno nas margens                            PARADO
  other      qualquer outro                                       PARADO

Além disso entra um movimento de CÂMERA (push-in suave) sobre tudo, para garantir movimento visível mesmo com camadas paradas.
Camadas de AJUSTE (Curves, Hue/Saturation…) não são importadas como pixels: o `studio.py init` as aproxima com uma camada
`adjust` ajustada contra a prévia embutida do Photoshop (veja reconcile.py).
"""
import os, re, unicodedata, zlib
import cv2, numpy as np
from . import REF
from .compat import imwrite

ROLES = {
    'lock': ('logo', 'legal', 'credit', 'credito', 'creditos', 'parental', 'selo', 'copyright', 'gravadora', 'label', 'records'),
    'title': ('title', 'titulo', 'text', 'texto', 'lettering', 'letra', 'name', 'nome', 'typo', 'tipografia', 'headline'),
    'subject': ('person', 'pessoa', 'artist', 'artista', 'subject', 'sujeito', 'model', 'modelo', 'singer', 'cantor', 'cantora', 'girl',
                'boy', 'figura', 'personagem', 'character', 'kid', 'crianca', 'garoto', 'garota', 'man', 'woman', 'homem', 'mulher',
                'face', 'rosto', 'menino', 'meninos', 'menina'),
    'waves': ('onda', 'ondas', 'wave', 'waves', 'mar', 'sea', 'agua', 'water', 'ocean', 'oceano'),
    'floater': ('barco', 'boat', 'ship', 'navio', 'balao', 'balloon', 'nave', 'aviao', 'plane', 'bird', 'passaro', 'peixe', 'fish'),
    'sun': ('sol', 'sun', 'lua', 'moon', 'estrela', 'star', 'planeta', 'planet'),
    'drift': ('nuvem', 'nuvens', 'cloud', 'clouds', 'neblina', 'fog', 'mist'),
    'bg': ('background', 'fundo', 'bg', 'backdrop', 'sky', 'ceu', 'smoke', 'fumaca', 'cenario', 'base'),
}
ORDER = ('lock', 'title', 'subject', 'waves', 'floater', 'sun', 'drift', 'bg')
BLEND_MAP = {'NORMAL': 'normal', 'LINEAR_DODGE': 'add', 'SCREEN': 'screen', 'MULTIPLY': 'multiply', 'LIGHTEN': 'lighten', 'PASS_THROUGH': 'normal'}
RASTER_KINDS = ('pixel', 'type', 'shape', 'smartobject', 'solidcolorfill', 'gradientfill', 'patternfill')


def _slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '_', s).strip('_') or 'layer'


def guess_role(name):
    """Papel pelo nome (tokens exatos; palavras ≥5 letras também por substring). None se não reconhecido."""
    slug = _slug(name)
    toks = set(slug.split('_'))
    for role in ORDER:
        for k in ROLES[role]:
            if k in toks or (len(k) >= 5 and k in slug):
                return role
    return None


def _phase(key):
    return round((zlib.crc32(key.encode('utf-8')) % 1000) / 1000.0, 3)


def _motion(role, bb, phase, group_bb):
    """(transform, effects, pivot) iniciais por papel. Tudo fecha o loop e vale 0 em t=0 (frame 0 == capa)."""
    gb = group_bb or bb
    pv = [round((gb[0] + gb[2]) / 2), round(gb[3])]
    if role == 'bg':
        return {'scale': {'env': True, 'base': 1.0, 'amp': 0.012}}, [{'type': 'flow', 'amp': 10}], None
    if role == 'subject':
        return ({'rotation': {'wave': 'sin', 'amp': 1.3}, 'x': {'wave': 'sin', 'amp': 8}, 'y': {'env': True, 'amp': -10},
                 'scale': {'env': True, 'base': 1.0, 'amp': 0.010}}, [], pv)
    if role == 'title':
        return {'y': {'env': True, 'amp': -8}}, [{'type': 'shine'}], None
    if role == 'waves':
        return ({'x': {'wave': 'sin', 'amp': 22, 'phase': phase, 'from_zero': True},
                 'y': {'wave': 'sin', 'amp': 5, 'phase': phase + 0.25, 'from_zero': True}}, [], None)
    if role == 'floater':
        return ({'y': {'wave': 'sin', 'amp': 10, 'phase': phase, 'from_zero': True},
                 'rotation': {'wave': 'sin', 'amp': 1.4, 'phase': phase + 0.1, 'from_zero': True}}, [], pv)
    if role == 'sun':
        c = [round((bb[0] + bb[2]) / 2), round((bb[1] + bb[3]) / 2)]
        return {'scale': {'env': True, 'base': 1.0, 'amp': 0.04}}, [{'type': 'glow', 'radius': 40, 'strength': {'env': True, 'amp': 0.5}}], c
    if role == 'drift':
        return {'x': {'wave': 'sin', 'amp': 30, 'phase': phase, 'from_zero': True}}, [], None
    return {}, [], None            # lock / overlay / credit / other: PARADO


def import_psd(psd_path, project_dir, mood='standard', impact=None):
    from psd_tools import PSDImage
    psd = PSDImage.open(psd_path)
    W0, H0 = psd.size
    if W0 != H0:
        raise ValueError(f'O PSD não é quadrado ({W0}x{H0}). No Photoshop: Imagem → Tamanho da Tela → quadrado (ex.: 3000×3000) e reexporte.')
    k = REF / W0
    assets = os.path.join(project_dir, 'assets'); os.makedirs(assets, exist_ok=True)
    flat = psd.composite().convert('RGB')          # usa a PRÉVIA do Photoshop quando o PSD a contém ("Maximizar compatibilidade")
    flat_bgr = cv2.cvtColor(np.array(flat), cv2.COLOR_RGB2BGR)
    imwrite(os.path.join(project_dir, 'source_flat.png'), flat_bgr)

    entries, used, warns, adjust_kinds = [], set(), [], []
    if not psd.has_preview():
        warns.append('O PSD não tem a prévia embutida do Photoshop ("Maximizar compatibilidade" desligado): o achatado é recalculado pelo leitor e pode divergir.')
    for layer in psd.descendants():
        if layer.is_group():
            continue
        if layer.kind not in RASTER_KINDS:                       # curves, huesaturation, brightnesscontrast, levels…
            adjust_kinds.append(layer.kind); continue
        if not layer.is_visible():
            continue
        l, t, r, b = layer.bbox
        if r <= l or b <= t:
            continue
        pil = layer.composite()
        if pil is None:
            warns.append(f'camada "{layer.name}" ({layer.kind}) não pôde ser rasterizada (ignorada)'); continue
        pil = pil.convert('RGBA')
        slug, i = _slug(layer.name), 2
        while slug in used: slug, i = f'{_slug(layer.name)}_{i}', i + 1
        used.add(slug)
        bgra = np.array(pil)[..., [2, 1, 0, 3]]
        imwrite(os.path.join(assets, f'{slug}.png'), bgra)
        bm = BLEND_MAP.get(str(layer.blend_mode).split('.')[-1])
        if bm is None: warns.append(f'camada "{layer.name}": modo de mesclagem {layer.blend_mode} não suportado → normal')
        anc = []
        p = layer.parent
        while p is not None and p is not psd:
            anc.append(p.name); p = p.parent
        bb = [l * k, t * k, r * k, b * k]
        cover = ((min(r, W0) - max(l, 0)) * (min(b, H0) - max(t, 0))) / float(W0 * H0)
        entries.append({'id': slug, 'name': layer.name, 'kind': layer.kind, 'anc': anc, 'bbox': bb, 'opacity': round(layer.opacity / 255, 3),
                        'blend': bm or 'normal', 'asset': f'assets/{slug}.png', 'cover': cover,
                        'fill': layer.kind in ('solidcolorfill', 'gradientfill', 'patternfill')})
    if not entries:
        raise ValueError('Nenhuma camada de pixels visível encontrada no PSD.')

    # ---- papéis -------------------------------------------------------------------------------
    for e in entries:
        role = guess_role(e['name'])
        if role is None:
            for a in e['anc']:                                   # herda do grupo mais próximo que tenha papel
                role = guess_role(a)
                if role: break
        cy = (e['bbox'][1] + e['bbox'][3]) / 2
        small = ((e['bbox'][2] - e['bbox'][0]) * (e['bbox'][3] - e['bbox'][1])) / float(REF * REF) < 0.04
        if role is None and e['kind'] == 'type':
            role = 'credit' if small and (cy < 0.10 * REF or cy > 0.85 * REF) else 'title'
        if role == 'title' and e['kind'] != 'type' and small and (cy < 0.10 * REF or cy > 0.85 * REF):
            role = 'credit'
        if role is None and (e['fill'] or (e['cover'] > 0.85 and (e['blend'] != 'normal' or e['opacity'] < 0.99))):
            role = 'overlay'
        e['role'] = role or 'other'
    if not any(e['role'] == 'bg' for e in entries):
        e0 = entries[0]
        if e0['cover'] > 0.9 and e0['role'] in ('other', 'overlay'):
            e0['role'] = 'bg'

    groups = {}
    for e in entries:
        if e['anc']:
            g = groups.setdefault(e['anc'][0], [1e9, 1e9, -1e9, -1e9])
            g[0], g[1], g[2], g[3] = min(g[0], e['bbox'][0]), min(g[1], e['bbox'][1]), max(g[2], e['bbox'][2]), max(g[3], e['bbox'][3])
    subjects = [e['id'] for e in entries if e['role'] == 'subject']
    layers, role_count = [], {}
    for e in entries:
        key = e['anc'][0] if e['anc'] else e['id']
        gbb = groups.get(e['anc'][0]) if e['anc'] else None
        gbb = [max(gbb[0], 0), max(gbb[1], 0), min(gbb[2], REF), min(gbb[3], REF)] if gbb else None
        tr, fxs, pivot = _motion(e['role'], e['bbox'], _phase(key), gbb)
        spec = {'id': e['id'], 'type': 'image', 'asset': e['asset'], 'bbox': [round(v, 1) for v in e['bbox']],
                'opacity': e['opacity'], 'blend': e['blend'], 'name': e['name'], 'role': e['role']}
        if e['role'] == 'bg' and subjects:
            fxs = [dict(f, protect_layers=subjects) if f['type'] == 'flow' else f for f in fxs]
        if e['role'] == 'bg' and e['cover'] < 0.98:
            warns.append(f'fundo "{e["name"]}" tem áreas transparentes (buracos): preencha o que fica atrás dos elementos no PSD, '
                         'ou o movimento revelará transparência.')
        if pivot: spec['pivot'] = pivot
        if tr: spec['transform'] = tr
        if fxs: spec['effects'] = fxs
        layers.append(spec)
        role_count[e['role']] = role_count.get(e['role'], 0) + 1

    warns[:] = list(dict.fromkeys(warns))                         # sem avisos repetidos
    if adjust_kinds:
        from collections import Counter
        c = Counter(adjust_kinds)
        warns.append('camadas de ajuste detectadas (' + ', '.join(f'{n}×{kd}' for kd, n in c.items()) +
                     '): não são animáveis; o importador as aproxima por uma curva de cor + correção suave (camada "grade").')

    # ---- geradores (clima) --------------------------------------------------------------------
    gens = [{'id': 'leaks', 'type': 'generator', 'effect': 'light_leaks', 'params': {}}]
    focus = next((e for e in entries if e['role'] == 'subject'), None) or next((e for e in entries if e['role'] in ('title', 'sun')), None)
    zone = [int(max(v, 0)) for v in focus['bbox']] if focus else [200, 200, 1850, 1500]
    zone = [min(zone[0], REF - 10), min(zone[1], REF - 10), min(max(zone[2], zone[0] + 10), REF), min(max(zone[3], zone[1] + 10), REF)]
    gens.append({'id': 'sparkles', 'type': 'generator', 'effect': 'sparkles', 'params': {'zones': [{'box': zone, 'count': 6 if mood != 'subtle' else 4}]}})
    if mood == 'bold':
        gens.append({'id': 'sweep', 'type': 'generator', 'effect': 'light_sweep', 'params': {}})
    if impact:
        gens += [{'id': 'shockwaves', 'type': 'generator', 'effect': 'rings', 'params': {'center': impact}},
                 {'id': 'embers', 'type': 'generator', 'effect': 'embers', 'params': {'origin': impact}},
                 {'id': 'shards', 'type': 'generator', 'effect': 'shards', 'params': {'origin': impact}}]
    base = [L for L in layers if L['role'] == 'bg']
    mid = [L for L in layers if L['role'] != 'bg']
    back_gens = [g for g in gens if g['id'] in ('leaks', 'shockwaves')]
    top_gens = [g for g in gens if g['id'] not in ('leaks', 'shockwaves')]
    cam_zoom = {'subtle': 0.012, 'standard': 0.02, 'bold': 0.03}.get(mood, 0.02)
    camera = [{'id': 'camera', 'type': 'generator', 'effect': 'camera', 'params': {'zoom': cam_zoom, 'drift': [10, 6]}}]   # garante movimento visível mesmo com camadas paradas
    scene_layers = base + back_gens + mid + camera + top_gens
    # a camada de ajuste entra logo ACIMA de todo o conteúdo do PSD e ABAIXO da câmera/geradores do topo
    adjust_index = len(base) + len(back_gens) + len(mid)
    locks = [L['id'] for L in layers if L['role'] == 'lock']
    return {'layers': scene_layers, 'warnings': warns, 'locks': locks, 'size': (W0, H0), 'adjust_index': adjust_index,
            'roles': role_count, 'has_adjustments': bool(adjust_kinds)}
