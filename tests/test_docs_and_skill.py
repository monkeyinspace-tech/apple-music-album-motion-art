import os, subprocess, sys, zipfile
from conftest import ROOT

STUDIO = os.path.join(ROOT, 'scripts', 'studio.py')


def test_effects_catalog_doc_is_in_sync():
    cat = subprocess.run([sys.executable, STUDIO, 'effects', '--md'], capture_output=True, text=True, encoding='utf-8', check=True).stdout
    doc = open(os.path.join(ROOT, 'docs', '12-catalogo-de-efeitos.md'), encoding='utf-8').read()
    assert cat.strip() in doc, 'rode `make effects-doc`'


def test_skill_package_is_self_contained(tmp_path):
    subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'build_skill.py')], check=True, capture_output=True)
    z = zipfile.ZipFile(os.path.join(ROOT, 'dist', 'apple-motion-art.skill'))
    names = set(z.namelist())
    for must in ('SKILL.md', 'scripts/studio.py', 'scripts/amstudio/engine.py', 'scripts/amstudio/fx/builtin_gen.py',
                 'configs/punk-impact.json', 'references/scene-format.md', 'references/custom-effects.md', 'requirements.txt'):
        assert must in names, must
    z.extractall(tmp_path)
    p = subprocess.run([sys.executable, str(tmp_path / 'scripts' / 'studio.py'), 'effects'], capture_output=True, text=True, encoding='utf-8')
    assert p.returncode == 0 and 'embers' in p.stdout and 'flow' in p.stdout
    # frontmatter do skill
    head = (tmp_path / 'SKILL.md').read_text(encoding='utf-8').split('---')[1]
    assert 'name: apple-motion-art' in head and 'description:' in head


def test_no_private_art_in_repo():
    bad = ('faella', 'desenroladas', 'COVER2_FINAL')
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in ('.git', 'dist', '.pytest_cache', '__pycache__')]
        for f in fn:
            if f.endswith(('.md', '.json', '.py', '.yml', '.txt', '.svg', '.ps1')) and f != 'test_docs_and_skill.py':
                txt = open(os.path.join(dp, f), encoding='utf-8', errors='ignore').read().lower()
                assert not any(b.lower() in txt for b in bad), (f, [b for b in bad if b.lower() in txt])
