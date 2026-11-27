"""Trava de privacidade: o repositório só pode conter imagens/vídeos AUTORIZADOS (arte própria da demo e ilustrações dos docs).

Se você adicionar uma imagem nova (ex.: ilustração do README), inclua-a na ALLOW abaixo DE PROPÓSITO.
Qualquer capa, PSD, TIFF ou vídeo que não esteja na lista reprova o teste — evita vazar arte inédita por acidente.
"""
import fnmatch, os
from conftest import ROOT

ALLOW = ['docs/assets/*', 'examples/demo/demo_cover.png', 'examples/demo/demo_contact_sheet.jpg',
         'docs/assets/demo_evc_1x1.gif', 'docs/assets/demo_evc_3x4.gif',
         'docs/assets/demo_upc_1x1.gif', 'docs/assets/demo_upc_3x4.gif',
         'docs/assets/cover_voce_chegou.jpg', 'docs/assets/cover_ekanta.png']
BINARY = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.psd', '.psb', '.tif', '.tiff', '.mov', '.mp4', '.mkv', '.avi', '.bmp', '.heic')
SKIP_DIRS = {'.git', '__pycache__', '.pytest_cache', 'dist', 'work', 'out', '.cache', 'node_modules', '.venv'}


def test_only_authorized_binary_assets_are_in_the_repo():
    bad = []
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            if f.lower().endswith(BINARY):
                rel = os.path.relpath(os.path.join(dp, f), ROOT).replace(os.sep, '/')
                if not any(fnmatch.fnmatch(rel, pat) for pat in ALLOW):
                    bad.append(rel)
    assert not bad, f'mídia não autorizada no repositório (arte privada?): {bad}'


def test_private_dirs_are_gitignored():
    gi = open(os.path.join(ROOT, '.gitignore'), encoding='utf-8').read()
    for must in ('*.psd', 'private/', '*.mov'):
        assert must in gi
