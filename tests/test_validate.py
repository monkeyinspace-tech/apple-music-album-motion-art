import json, os, shutil, subprocess, sys
import pytest
from conftest import ROOT

pytestmark = pytest.mark.skipif(shutil.which('ffmpeg') is None, reason='ffmpeg não instalado')
VALIDATE = os.path.join(ROOT, 'scripts', 'validate_motion.py')


def make_video(path, br, sar='1', dur=8.2):
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'testsrc2=s=2048x2732:r=30:d={dur}',
           '-vf', f'format=yuv420p,setsar={sar}', '-c:v', 'libx264', '-preset', 'ultrafast', '-b:v', br, '-minrate', br,
           '-maxrate', '95M', '-bufsize', '140M', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
           '-an', '-f', 'mov', path]
    subprocess.run(cmd, check=True)


def run(path):
    p = subprocess.run([sys.executable, VALIDATE, path, '--json'], capture_output=True, text=True, encoding='utf-8')
    return p.returncode, json.loads(p.stdout)[0]['results']


def status(results, rule_part):
    return next(r['status'] for r in results if rule_part in r['rule'])


def test_good_file_passes_core_rules(tmp_path):
    f = str(tmp_path / 'X_3x4.mov'); make_video(f, '60M')
    _, res = run(f)
    assert status(res, 'resolução') == 'PASS'
    assert status(res, 'pixel quadrado') == 'PASS'
    assert status(res, 'bitrate') == 'PASS'
    assert status(res, 'duração') == 'PASS'
    assert status(res, 'sem áudio') == 'PASS'


def test_low_bitrate_fails(tmp_path):
    f = str(tmp_path / 'X_3x4.mov'); make_video(f, '15M')
    code, res = run(f)
    assert status(res, 'bitrate') == 'FAIL'
    assert code == 1


def test_non_square_pixel_fails(tmp_path):
    f = str(tmp_path / 'X_3x4.mov'); make_video(f, '60M', sar='4/3')
    code, res = run(f)
    assert status(res, 'pixel quadrado') == 'FAIL'
    assert code == 1
