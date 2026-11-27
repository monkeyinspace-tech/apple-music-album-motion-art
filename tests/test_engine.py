import json, os, subprocess, sys
import cv2, numpy as np
import pytest
from conftest import ROOT

from amstudio import curves, scene as S, ingest, outputs
from amstudio.engine import Renderer

STUDIO = os.path.join(ROOT, 'scripts', 'studio.py')
DEMO = os.path.join(ROOT, 'examples', 'demo')


def run(*args, check=True):
    p = subprocess.run([sys.executable, STUDIO, *map(str, args)], capture_output=True, text=True, encoding='utf-8')
    if check: assert p.returncode == 0, p.stdout + p.stderr
    return p


@pytest.fixture(scope='module')
def demo_project(tmp_path_factory):
    d = str(tmp_path_factory.mktemp('proj') / 'demo')
    run('init', os.path.join(DEMO, 'demo_cover.png'), d, '--template', os.path.join(DEMO, 'demo_config.json'))
    return d


# ---------------------------------------------------------------- curvas
def test_wave_env_and_keys_close_the_loop():
    for spec in ({'wave': 'sin', 'amp': 3}, {'env': True, 'amp': -10}, {'wiggle': {'amp': 4, 'freq': 2, 'seed': 3}},
                 {'wave': 'cos', 'amp': 2, 'from_zero': True}, [[0, 0], [0.5, 5], [1, 0]]):
        assert curves.loop_error(spec) is None, spec


def test_wiggle_and_from_zero_start_at_zero():
    assert abs(curves.evaluate({'wiggle': {'amp': 9, 'freq': 3, 'seed': 1}}, 0.0)) < 1e-9
    assert abs(curves.evaluate({'wave': 'sin', 'amp': 5, 'phase': 0.37, 'from_zero': True}, 0.0)) < 1e-9


def test_open_keyframes_are_rejected():
    assert curves.loop_error([[0, 0], [1, 5]]) is not None


def test_phase_wave_closes_loop_even_without_from_zero():
    assert curves.loop_error({'wave': 'sin', 'amp': 1, 'phase': 0.3}) is None


# ---------------------------------------------------------------- ingestão
def test_fit_square_modes():
    img = np.zeros((300, 500, 3), np.uint8)
    assert ingest.fit_square(img, 'crop').shape[:2] == (300, 300)
    assert ingest.fit_square(img, 'extend').shape[:2] == (500, 500)
    with pytest.raises(ValueError): ingest.fit_square(img, 'error')


def test_working_size_and_size_classes():
    assert ingest.working_size(3000) == 3000 and ingest.working_size(4096) == 3840 and ingest.working_size(1500) == 2048
    assert '3000' in ingest.describe_size(3000, 3000)['class'] and '4K' in ingest.describe_size(3840, 3840)['class']


# ---------------------------------------------------------------- projeto/edição
def test_init_creates_layers_and_assets(demo_project):
    sc = S.load(demo_project)
    ids = [l['id'] for l in sc['layers']]
    assert 'bg' in ids and 'title' in ids and 'embers' in ids
    assert os.path.exists(os.path.join(demo_project, 'assets', 'bg.png'))
    assert not S.validate(demo_project, sc)[0]


def test_check_ok_on_demo(demo_project):
    p = run('check', demo_project)
    assert 'OK' in p.stdout


def test_add_layer_set_and_rejects_invalid(demo_project, tmp_path):
    d = str(tmp_path / 'p'); run('init', os.path.join(DEMO, 'demo_cover.png'), d, '--template', os.path.join(DEMO, 'demo_config.json'))
    run('add-layer', d, '--id', 'vig', '--effect', 'vignette', '--param', 'strength=0.4')
    run('add-effect', d, 'title', 'glow', '--param', 'radius=40')
    assert any(l['id'] == 'vig' for l in S.load(d)['layers'])
    before = open(S.scene_path(d), encoding='utf-8').read()
    bad = run('set', d, 'title.effects.0.nao_existe', '1', check=False)
    assert bad.returncode != 0 and open(S.scene_path(d), encoding='utf-8').read() == before      # nada foi salvo
    bad2 = run('add-effect', d, 'title', 'efeito_que_nao_existe', check=False)
    assert bad2.returncode != 0
    run('set', d, 'bg.effects.0.amp', '20')
    assert S.load(d)['layers'][0]['effects'][0]['amp'] == 20


def test_unclosed_keyframes_rejected_by_validation(demo_project, tmp_path):
    sc = S.load(demo_project)
    S.add_layer(sc, {'id': 'x', 'type': 'image', 'asset': 'assets/bg.png', 'transform': {'x': [[0, 0], [1, 9]]}})
    errs, _ = S.validate(demo_project, sc)
    assert any('loop' in e for e in errs)


# ---------------------------------------------------------------- PSD
def test_psd_import_roles_and_check(tmp_path):
    psd = str(tmp_path / 'l.psd')
    subprocess.run([sys.executable, os.path.join(DEMO, 'make_demo_psd.py'), psd, '600'], check=True, capture_output=True)
    d = str(tmp_path / 'ppsd')
    run('init', psd, d, '--impact', '[900,1300]')
    sc = S.load(d)
    by = {l['id']: l for l in sc['layers']}
    assert {'fundo', 'planeta', 'titulo', 'logo'} <= set(by)
    assert by['fundo']['effects'][0]['type'] == 'flow'
    assert [e['type'] for e in by['titulo']['effects']] == ['shine']
    assert 'transform' not in by['logo'] or not by['logo']['transform']          # logo parado
    assert 'effects' in by['fundo'] and by['fundo']['effects'][0].get('protect_layers') is None   # sem sujeito nomeado
    assert 'OK' in run('check', d).stdout


def test_psd_not_square_is_rejected(tmp_path):
    from PIL import Image
    from psd_tools import PSDImage
    from psd_tools.api.layers import PixelLayer
    psd = PSDImage.new('RGB', (400, 300)); psd.append(PixelLayer.frompil(Image.new('RGBA', (400, 300), (9, 9, 9, 255)), psd, 'Fundo'))
    path = str(tmp_path / 'x.psd'); psd.save(path)
    p = run('init', path, str(tmp_path / 'q'), check=False)
    assert p.returncode != 0


# ---------------------------------------------------------------- 3000 / 4K
def test_3000px_cover_runs_native_pipeline(tmp_path):
    big = cv2.resize(cv2.imread(os.path.join(DEMO, 'demo_cover.png')), (3000, 3000), interpolation=cv2.INTER_CUBIC)
    src = str(tmp_path / 'c3000.png'); cv2.imwrite(src, big)
    d = str(tmp_path / 'p3000'); run('init', src, d, '--template', os.path.join(DEMO, 'demo_config.json'))
    sc = S.load(d)
    assert cv2.imread(os.path.join(d, 'assets', 'bg.png')).shape[:2] == (3000, 3000)       # assets em resolução NATIVA
    r = Renderer(d, sc, 1500)                                                                # motor em outro tamanho: mesma cena
    f0 = r.frame(0)
    flat = cv2.resize(cv2.imread(S.flat_path(d, sc)), (1500, 1500), interpolation=cv2.INTER_AREA)
    assert np.abs(cv2.GaussianBlur(f0.astype(np.float32), (0, 0), 1.5) - cv2.GaussianBlur(flat.astype(np.float32), (0, 0), 1.5)).mean() < 1.5


def test_same_scene_renders_at_any_working_size(demo_project):
    sc = S.load(demo_project)
    for W in (384, 640):
        fr = Renderer(demo_project, sc, W).frame(100)
        assert fr.shape == (W, W, 3)


# ---------------------------------------------------------------- 3:4
def test_ext3x4_geometry():
    cov = np.full((512, 512, 3), 40, np.uint8)
    e = outputs.Ext3x4(cov, [75, 1320], 512)
    assert e.H == 683 and e.pt + 512 + e.pb == 683
    out = e.make(cov)
    assert out.shape == (683, 512, 3)


# ---------------------------------------------------------------- plugins personalizados
def test_custom_generator_plugin_passes_check(demo_project, tmp_path):
    d = str(tmp_path / 'pp'); run('init', os.path.join(DEMO, 'demo_cover.png'), d)
    run('new-effect', 'respira', '--kind', 'generator', '--project', d)
    run('add-layer', d, '--id', 'r1', '--effect', 'respira')
    assert 'OK' in run('check', d).stdout


def test_bad_plugin_is_caught_by_check(tmp_path):
    d = str(tmp_path / 'bad'); run('init', os.path.join(DEMO, 'demo_cover.png'), d)
    os.makedirs(os.path.join(d, 'plugins'), exist_ok=True)
    open(os.path.join(d, 'plugins', 'ruim.py'), 'w', encoding='utf-8').write(
        "from amstudio.fx import generator\n@generator('ruim', {}, 'não começa em zero')\nclass Ruim:\n"
        "    def __init__(self, ctx): pass\n    def render(self, fr, t, e): fr += 80.0\n")
    run('add-layer', d, '--id', 'r', '--effect', 'ruim')
    p = run('check', d, check=False)
    assert p.returncode != 0 and 'frame 0' in p.stdout


# ---------------------------------------------------------------- texto e elementos novos
def test_text_layer_must_fade_in_to_keep_frame0(tmp_path):
    d = str(tmp_path / 'ptxt'); run('init', os.path.join(DEMO, 'demo_cover.png'), d)
    spec = {'id': 'nome', 'type': 'text', 'text': 'ARTISTA', 'size': 170, 'position': [1024, 1700], 'effects': [{'type': 'glow', 'radius': 20}]}
    run('add-layer', d, '--json', json.dumps(spec))
    bad = run('check', d, check=False)
    assert bad.returncode != 0 and 'frame 0' in bad.stdout                                 # aparece já no frame 0 → reprovado
    run('set', d, 'nome.transform.opacity', '{"env":true,"amp":1}')
    assert 'OK' in run('check', d).stdout                                                  # surge com fade → aprovado
