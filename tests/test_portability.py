"""Portabilidade (Windows/macOS/Linux): caminhos com acentos, console legado e E/S Unicode."""
import json, os, subprocess, sys
import numpy as np
from conftest import ROOT
from amstudio import compat

STUDIO = os.path.join(ROOT, 'scripts', 'studio.py')
DEMO = os.path.join(ROOT, 'examples', 'demo')


def run(*args, env=None):
    e = dict(os.environ, **(env or {}))
    return subprocess.run([sys.executable, STUDIO, *map(str, args)], capture_output=True, text=True, encoding='utf-8', env=e)


def test_imread_imwrite_roundtrip_with_accented_path(tmp_path):
    d = tmp_path / 'Área de Trabalho' / 'João — capas'
    d.mkdir(parents=True)
    img = (np.random.default_rng(1).random((40, 60, 3)) * 255).astype(np.uint8)
    p = str(d / 'capa ção.png')
    assert compat.imwrite(p, img) and os.path.exists(p)
    out = compat.imread(p)
    assert out is not None and np.array_equal(out, img)
    assert compat.imread(str(d / 'nao_existe.png')) is None


def test_full_flow_inside_accented_folder(tmp_path):
    base = tmp_path / 'Área de Trabalho' / 'Lançamento ação'
    base.mkdir(parents=True)
    proj = str(base / 'projeto único')
    p = run('init', os.path.join(DEMO, 'demo_cover.png'), proj, '--template', os.path.join(DEMO, 'demo_config.json'))
    assert p.returncode == 0, p.stdout + p.stderr
    assert run('preview', proj, '--sheet', '--width', '384').returncode == 0
    p = run('check', proj)
    assert p.returncode == 0 and 'OK' in p.stdout, p.stdout + p.stderr


def test_legacy_console_encoding_does_not_crash():
    for enc in ('cp1252', 'ascii'):
        env = {'PYTHONIOENCODING': enc, 'PYTHONUTF8': '0'}
        assert run('effects', env=env).returncode == 0
        q = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'check_config.py'), os.path.join(ROOT, 'configs', 'templates', 'minimal.json')],
                           capture_output=True, text=True, encoding='utf-8', env=dict(os.environ, **env))
        assert q.returncode == 0, (enc, q.stderr[-300:])


def test_scene_json_uses_forward_slashes_for_assets(tmp_path):
    proj = str(tmp_path / 'p')
    assert run('init', os.path.join(DEMO, 'demo_cover.png'), proj, '--template', os.path.join(DEMO, 'demo_config.json')).returncode == 0
    sc = json.load(open(os.path.join(proj, 'scene.json'), encoding='utf-8'))
    assert all('\\' not in l.get('asset', '') for l in sc['layers'])
