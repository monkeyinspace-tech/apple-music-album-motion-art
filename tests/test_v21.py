"""Rodada 2.1: reconciliação com o Photoshop, camera, papéis de PSD, sujeito automático, extensão p/ capas claras, doctor, mp4/static."""
import json, os, subprocess, sys
import cv2, numpy as np
from conftest import ROOT
from amstudio import scene as S, reconcile, autolayer, outputs
from amstudio.engine import Renderer
from amstudio.compat import imread, imwrite

STUDIO = os.path.join(ROOT, 'scripts', 'studio.py')
DEMO = os.path.join(ROOT, 'examples', 'demo')


def run(*args, check=True):
    p = subprocess.run([sys.executable, STUDIO, *map(str, args)], capture_output=True, text=True, encoding='utf-8')
    if check: assert p.returncode == 0, p.stdout + p.stderr
    return p


def mkproj(tmp_path, name='p'):
    d = str(tmp_path / name)
    run('init', os.path.join(DEMO, 'demo_cover.png'), d, '--template', os.path.join(DEMO, 'demo_config.json'))
    return d


def test_fit_lut_recovers_a_tone_curve():
    ours = (np.random.default_rng(0).random((200, 200, 3)) * 255).astype(np.float32)
    flat = 255 * (ours / 255) ** 0.7
    luts = reconcile.fit_lut(ours, flat)
    graded = np.stack([np.interp(ours[..., i], np.arange(256), luts[i]) for i in range(3)], -1)
    assert np.abs(graded - flat).mean() < 2.0 < np.abs(ours - flat).mean()


def test_reconcile_adds_grade_layer_and_restores_frame0(tmp_path):
    d = mkproj(tmp_path)
    flat = imread(os.path.join(d, 'source_flat.png')).astype(np.float32)
    graded = np.clip(flat * 0.78 + 14, 0, 255).astype(np.uint8)
    imwrite(os.path.join(d, 'source_flat.png'), graded)
    sc = S.load(d)
    sc, e0, e1, applied = reconcile.reconcile(d, sc, len(sc['layers']))
    assert applied and e1 < 0.4 * e0 and e1 < 2.5
    assert sc['layers'][-1]['type'] == 'adjust' and not S.validate(d, sc)[0]


def test_reconcile_does_nothing_when_already_matching(tmp_path):
    d = mkproj(tmp_path); sc = S.load(d); n = len(sc['layers'])
    sc, e0, e1, applied = reconcile.reconcile(d, sc, n)
    assert not applied and len(sc['layers']) == n


def test_camera_moves_the_frame_but_starts_and_ends_at_zero(tmp_path):
    d = mkproj(tmp_path)
    run('add-layer', d, '--id', 'cam', '--effect', 'camera', '--param', 'zoom=0.04', '--param', 'drift=[12,8]', '--index', '99')
    sc = S.load(d); r = Renderer(d, sc, 384)
    fm = r.frame(r.N // 2).astype(float)
    sc2 = dict(sc); sc2['layers'] = [l for l in sc['layers'] if l['id'] != 'cam']
    assert np.abs(fm - Renderer(d, sc2, 384).frame(r.N // 2).astype(float)).mean() > 0.5
    assert 'OK' in run('check', d).stdout


def _psd(path, size, layers, hidden=()):
    from PIL import Image
    from psd_tools import PSDImage
    from psd_tools.api.layers import PixelLayer
    psd = PSDImage.new('RGB', (size, size))
    for name, rgba, left, top, blend in layers:
        l = PixelLayer.frompil(Image.new('RGBA', rgba[0], rgba[1]), psd, name, top=top, left=left)
        if blend: l.blend_mode = blend
        if name in hidden: l.visible = False
        psd.append(l)
    psd.save(path)


def test_psd_roles_motion_and_safe_defaults(tmp_path):
    from psd_tools.constants import BlendMode
    N = 600
    layers = [('Plano de Fundo', ((N, N), (30, 20, 60, 255)), 0, 0, None), ('Ondas', ((N, 120), (20, 120, 200, 255)), 0, 400, None),
              ('Barco', ((120, 80), (150, 90, 40, 255)), 200, 340, None), ('Sol', ((90, 90), (255, 220, 80, 255)), 420, 60, None),
              ('Nuvem', ((140, 50), (240, 240, 250, 255)), 40, 80, None), ('Pessoa', ((100, 200), (200, 120, 100, 255)), 380, 300, None),
              ('Logo', ((100, 40), (255, 255, 255, 255)), 20, 540, None), ('Textura grao', ((N, N), (255, 255, 255, 40)), 0, 0, BlendMode.SCREEN),
              ('Camada escondida', ((50, 50), (255, 0, 0, 255)), 0, 0, None), ('Coisa qualquer', ((60, 60), (10, 200, 10, 255)), 100, 100, None)]
    psd = str(tmp_path / 'r.psd'); _psd(psd, N, layers, hidden=('Camada escondida',))
    d = str(tmp_path / 'proj'); run('init', psd, d)
    sc = S.load(d); by = {l['id']: l for l in sc['layers']}
    roles = {i: l.get('role') for i, l in by.items() if l['type'] == 'image'}
    assert roles['plano_de_fundo'] == 'bg' and roles['ondas'] == 'waves' and roles['barco'] == 'floater'
    assert roles['sol'] == 'sun' and roles['nuvem'] == 'drift' and roles['pessoa'] == 'subject' and roles['logo'] == 'lock'
    assert roles['textura_grao'] == 'overlay' and roles['coisa_qualquer'] == 'other' and 'camada_escondida' not in by
    for stat in ('logo', 'textura_grao', 'coisa_qualquer'):
        assert not by[stat].get('transform') and not by[stat].get('effects')
    assert by['ondas']['transform']['x']['from_zero'] is True and 'pivot' in by['barco'] and 'camera' in by
    assert 'OK' in run('check', d).stdout


def test_derive_subject_box_from_mask():
    m = np.zeros((2048, 2048), np.float32); m[300:1700, 900:1500] = 1
    r = autolayer.derive_subject_box(m); x0, y0, x1, y1 = r['box']
    assert 700 < x0 < 900 and 150 < y0 < 300 and 1500 < x1 < 1700 and 1700 < y1 < 1900
    assert r['pivot'] == [int((x0 + x1) / 2), y1] and r['key_content_y'][1] - r['key_content_y'][0] <= 1251
    assert autolayer.derive_subject_box(np.zeros((2048, 2048), np.float32)) is None


def test_portrait_template_uses_auto_subject():
    cfg = json.load(open(os.path.join(ROOT, 'configs', 'templates', 'portrait-clean.json'), encoding='utf-8'))
    assert cfg['subject']['auto'] is True and 'pivot' not in cfg['subject'] and 'isnet_boxes' not in cfg['subject']


def test_ext3x4_does_not_over_darken_bright_covers():
    bright = np.full((512, 512, 3), 235, np.uint8); dark = np.full((512, 512, 3), 25, np.uint8)
    eb, ed = outputs.Ext3x4(bright, [75, 1320], 512), outputs.Ext3x4(dark, [75, 1320], 512)
    assert eb.top.mean() > 0.75 * 235 and eb.top.mean() > 4 * ed.top.mean()


def test_doctor_and_selftest_run_clean():
    p = run('doctor', '--selftest')
    assert 'AMBIENTE OK' in p.stdout and '❌' not in p.stdout


def test_render_mp4_and_static_png(tmp_path):
    d = mkproj(tmp_path); out = str(tmp_path / 'o')
    run('render', d, '--upc', 'T1', '--formats', '3x4', '--container', 'mp4', '--static', '--test-frames', '3', '--outdir', out)
    assert os.path.exists(os.path.join(out, 'T1_3x4.mp4')) and imread(os.path.join(out, 'T1_3x4_static.png')).shape[:2] == (2732, 2048)
    run('render', d, '--upc', 'T2', '--formats', '3x4', '--codec', 'prores', '--container', 'mp4', '--test-frames', '2', '--outdir', out)
    assert os.path.exists(os.path.join(out, 'T2_3x4.mov'))


def test_check_warns_on_short_duration(tmp_path):
    assert '15 s' in run('check', mkproj(tmp_path)).stdout
