"""scene.json (v2): leitura, validação, edição e compilação de configs antigas (v1)."""
import copy, json, os
from . import REF, fx
from .curves import is_spec, loop_error
from .engine import BLEND_MODES

TRANSFORM_KEYS = {'x', 'y', 'rotation', 'scale', 'opacity'}
LAYER_TYPES = ('image', 'text', 'generator', 'lock', 'adjust')


def scene_path(d): return os.path.join(d, 'scene.json')
def flat_path(d, scene): return os.path.join(d, (scene.get('source') or {}).get('flat', 'source_flat.png'))


def load(d):
    with open(scene_path(d), encoding='utf-8') as f:
        return json.load(f)


def save(d, scene):
    with open(scene_path(d), 'w', encoding='utf-8') as f:
        json.dump(scene, f, ensure_ascii=False, indent=2)


def find(scene, lid):
    for L in scene['layers']:
        if L['id'] == lid: return L
    raise KeyError(f'camada "{lid}" não existe (ids: {[l["id"] for l in scene["layers"]]})')


# ------------------------------------------------------------------ validação
def _check_params(kind, name, params, table, errs, where):
    cls = table.get(name)
    if cls is None:
        errs.append(f'{where}: efeito "{name}" desconhecido. Disponíveis: {sorted(table)}'); return
    for k, v in (params or {}).items():
        if k not in cls.fx_params:
            errs.append(f'{where}: parâmetro "{k}" não existe em "{name}" (válidos: {sorted(cls.fx_params)})')
        elif cls.fx_params[k][0] == 'spec' and not is_spec(v):
            errs.append(f'{where}.{k}: valor animável inválido')
        elif cls.fx_params[k][0] == 'spec':
            le = loop_error(v)
            if le: errs.append(f'{where}.{k}: {le}')
    for k, (typ, default, _) in cls.fx_params.items():
        if default is None and typ in ('point', 'box') and k not in (params or {}):
            errs.append(f'{where}: parâmetro obrigatório "{k}" ausente em "{name}"')
        if name == 'sparkles' and k == 'zones' and k not in (params or {}):
            errs.append(f'{where}: parâmetro obrigatório "zones" ausente em "sparkles"')


def validate(d, scene):
    errs, warns = [], []
    fx.load_plugins(os.path.join(d, 'plugins'))
    if scene.get('version') != 2: errs.append('version deve ser 2')
    out = scene.get('output', {})
    if not 8 <= out.get('duration', 12) <= 35: errs.append('output.duration deve estar entre 8 e 35 s (regra da Apple)')
    if out.get('intensity', 1.0) > 2: warns.append('output.intensity > 2 é muito alto')
    ids = set()
    for i, L in enumerate(scene.get('layers', [])):
        lid, ty = L.get('id'), L.get('type')
        where = f'camada[{lid}]'
        if not lid: errs.append(f'camada #{i} sem "id"'); continue
        if lid in ids: errs.append(f'id duplicado: {lid}')
        ids.add(lid)
        if ty not in LAYER_TYPES: errs.append(f'{where}: type inválido "{ty}" (use {LAYER_TYPES})'); continue
        if ty in ('image', 'text'):
            if ty == 'image' and not os.path.exists(os.path.join(d, L.get('asset', ''))): errs.append(f'{where}: asset não encontrado: {L.get("asset")}')
            if L.get('blend', 'normal') not in BLEND_MODES: errs.append(f'{where}: blend inválido (use {BLEND_MODES})')
            bb = L.get('bbox')
            if bb and not (len(bb) == 4 and bb[0] < bb[2] and bb[1] < bb[3]): errs.append(f'{where}: bbox inválida {bb}')
            for k, v in (L.get('transform') or {}).items():
                if k not in TRANSFORM_KEYS: errs.append(f'{where}.transform: chave "{k}" inválida (use {sorted(TRANSFORM_KEYS)})')
                elif not is_spec(v): errs.append(f'{where}.transform.{k}: valor animável inválido')
                else:
                    le = loop_error(v)
                    if le: errs.append(f'{where}.transform.{k}: {le}')
            for j, e in enumerate(L.get('effects') or []):
                _check_params('layer', e.get('type'), {k: v for k, v in e.items() if k not in ('type', 'enabled')}, fx.LAYER, errs, f'{where}.effects[{j}]')
        elif ty == 'generator':
            _check_params('generator', L.get('effect'), L.get('params'), fx.GEN, errs, where)
        elif ty == 'lock':
            if not L.get('boxes'): errs.append(f'{where}: "boxes" vazio')
        elif ty == 'adjust':
            for k in ('lut', 'residual'):
                if L.get(k) and not os.path.exists(os.path.join(d, L[k])): errs.append(f'{where}: arquivo não encontrado: {L[k]}')
            if not (L.get('lut') or L.get('residual')): errs.append(f'{where}: informe "lut" e/ou "residual"')
    return errs, warns


# ------------------------------------------------------------------ edição
def _coerce(tok):
    return int(tok) if tok.lstrip('-').isdigit() else tok


def set_path(scene, path, value):
    """path: '<id-da-camada>.transform.rotation' | 'output.duration' | '<id>.effects.0.amp'."""
    toks = path.split('.')
    head = toks[0]
    node = scene.setdefault(head, {}) if head in ('output', 'source') else find(scene, head)
    for tk in toks[1:-1]:
        k = _coerce(tk)
        if isinstance(node, list): node = node[k]
        else: node = node.setdefault(k, {})
    last = _coerce(toks[-1])
    if isinstance(node, list): node[last] = value
    else: node[last] = value


def add_layer(scene, spec, index=None):
    if any(l['id'] == spec['id'] for l in scene['layers']): raise ValueError(f'id já existe: {spec["id"]}')
    scene['layers'].insert(len(scene['layers']) if index is None else index, spec)


def remove_layer(scene, lid):
    scene['layers'].remove(find(scene, lid))


def move_layer(scene, lid, index):
    L = find(scene, lid); scene['layers'].remove(L); scene['layers'].insert(index, L)


def add_effect(scene, lid, etype, params):
    L = find(scene, lid)
    if L['type'] != 'image' and L['type'] != 'text': raise ValueError('efeitos de camada só em camadas image/text')
    L.setdefault('effects', []).append({'type': etype, **params})


# ------------------------------------------------------------------ compilação de config v1 -> cena v2
def legacy_to_scene(cfg, built, name='projeto', duration=12, fps=30, intensity=1.0):
    """built = {'bg':{'asset','bbox'}, 'title':{...}|None, 'subject':{...}|None} (saída do autolayer)."""
    L = []
    sub = cfg.get('subject') or {}
    has_sub, has_title, imp = built.get('subject') is not None, built.get('title') is not None, cfg.get('impact')
    flow = {'type': 'flow', 'amp': 13, 'seed': 1}
    if cfg.get('flow_protect'): flow['protect'] = cfg['flow_protect']
    if has_sub: flow['protect_layers'] = ['subject']
    L.append({'id': 'bg', 'type': 'image', 'asset': built['bg']['asset'], 'effects': [flow]})
    if cfg.get('light_leaks', True):
        p = {}
        if cfg.get('leak_colors'): p['colors'] = cfg['leak_colors']
        L.append({'id': 'leaks', 'type': 'generator', 'effect': 'light_leaks', 'params': p})
    if imp and cfg.get('hot_cracks'):
        L.append({'id': 'cracks', 'type': 'generator', 'effect': 'hot_pulse',
                  'params': {'roi': cfg['hot_cracks']['roi'], **({'exclude_layers': ['subject']} if has_sub else {})}})
    if imp and cfg.get('rings', True):
        L.append({'id': 'shockwaves', 'type': 'generator', 'effect': 'rings', 'params': {'center': imp}})
    if has_title:
        L.append({'id': 'title', 'type': 'image', 'asset': built['title']['asset'], 'bbox': built['title']['bbox'],
                  'effects': [{'type': 'boil', 'amp': 1.6, 'cell': 70, 'rate': 6, 'seed': 100}, {'type': 'shine'}]})
    if imp and cfg.get('shards', 26) > 0:
        L.append({'id': 'shards', 'type': 'generator', 'effect': 'shards', 'params': {'origin': imp, 'count': cfg.get('shards', 26)}})
    if has_sub:
        L.append({'id': 'subject', 'type': 'image', 'asset': built['subject']['asset'], 'bbox': built['subject']['bbox'],
                  'pivot': built['subject'].get('pivot') or sub.get('pivot', [1500, 1500]),
                  'transform': {'rotation': {'wave': 'sin', 'amp': sub.get('sway_deg', 1.3)},
                                'x': {'wave': 'sin', 'amp': sub.get('shift_px', 8)},
                                'y': {'env': True, 'amp': -sub.get('float_px', 10)},
                                'scale': {'env': True, 'base': 1.0, 'amp': 0.010}}})
    if imp and cfg.get('embers', 130) > 0:
        L.append({'id': 'embers', 'type': 'generator', 'effect': 'embers', 'params': {'origin': imp, 'count': cfg.get('embers', 130)}})
    if cfg.get('sparkles'):
        L.append({'id': 'sparkles', 'type': 'generator', 'effect': 'sparkles', 'params': {'zones': cfg['sparkles'], 'seed': cfg.get('seed', 5)}})
    if cfg.get('lock_boxes'):
        L.append({'id': 'locks', 'type': 'lock', 'boxes': cfg['lock_boxes']})
    return {'version': 2, 'name': name, 'source': {'flat': 'source_flat.png', 'psd': None},
            'output': {'duration': duration, 'fps': fps, 'intensity': intensity, 'key_content_y': cfg.get('key_content_y') or built.get('key_content_y') or [75, 1320]},
            'layers': L}
