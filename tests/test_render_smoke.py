import os, re, subprocess, sys
import pytest
from conftest import ROOT

RENDER = os.path.join(ROOT, 'scripts', 'render_motion.py')
DEMO = os.path.join(ROOT, 'examples', 'demo')


def test_preview_runs_and_frame0_matches_cover(tmp_path):
    p = subprocess.run([sys.executable, RENDER, '--cover', os.path.join(DEMO, 'demo_cover.png'),
                        '--config', os.path.join(DEMO, 'demo_config.json'), '--outdir', str(tmp_path), '--preview'],
                       capture_output=True, text=True, encoding='utf-8')
    assert p.returncode == 0, p.stderr
    diff = float(re.search(r'capa .*?: ([0-9.]+)', p.stdout).group(1))
    assert diff < 1.0                                       # frame 0 == capa
    assert (tmp_path / 'preview_contact_sheet.png').exists()


@pytest.mark.parametrize('tpl', ['abstract-flow', 'minimal', 'typographic-poster'])
def test_no_ai_templates_preview(tmp_path, tpl):
    cfg = os.path.join(ROOT, 'configs', 'templates', f'{tpl}.json')
    p = subprocess.run([sys.executable, RENDER, '--cover', os.path.join(DEMO, 'demo_cover.png'), '--config', cfg,
                        '--outdir', str(tmp_path), '--preview'], capture_output=True, text=True, encoding='utf-8')
    assert p.returncode == 0, p.stderr
    diff = float(re.search(r'capa .*?: ([0-9.]+)', p.stdout).group(1))
    assert diff < 1.0


def test_rejects_invalid_duration(tmp_path):
    p = subprocess.run([sys.executable, RENDER, '--cover', os.path.join(DEMO, 'demo_cover.png'), '--outdir', str(tmp_path),
                        '--duration', '5', '--preview'], capture_output=True, text=True, encoding='utf-8')
    assert p.returncode != 0
