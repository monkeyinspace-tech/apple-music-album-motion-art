#!/usr/bin/env python3
"""Gera dist/apple-motion-art.skill (zip) a partir do repositório.

Estrutura: SKILL.md · scripts/ (studio.py, amstudio/…, validate/prepare/check) · configs/ (templates) ·
           references/ (copiadas de docs/) · requirements*.txt
"""
import os, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = {  # destino em references/  <-  origem em docs/
    'apple-specs.md': 'docs/05-especificacoes-apple.md',
    'motion-studio.md': 'docs/10-motion-studio.md',
    'scene-format.md': 'docs/11-formato-da-cena.md',
    'effects-catalog.md': 'docs/12-catalogo-de-efeitos.md',
    'psd-guide.md': 'docs/13-photoshop-psd.md',
    'custom-effects.md': 'docs/14-criar-efeitos.md',
    'director-guide.md': 'docs/15-diretor-criativo.md',
    'config-reference.md': 'docs/03-referencia-config.md',
    'troubleshooting.md': 'docs/06-validacao-e-troubleshooting.md',
}


def main():
    out_dir = os.path.join(ROOT, 'dist')
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, 'apple-motion-art.skill')
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(ROOT, 'claude', 'SKILL.md'), 'SKILL.md')
        for dp, dn, fn in os.walk(os.path.join(ROOT, 'scripts')):
            dn[:] = [d for d in dn if d != '__pycache__']
            for f in sorted(fn):
                if f.endswith('.py'):
                    p = os.path.join(dp, f)
                    z.write(p, os.path.relpath(p, ROOT))
        for f in sorted(os.listdir(os.path.join(ROOT, 'configs', 'templates'))):
            z.write(os.path.join(ROOT, 'configs', 'templates', f), f'configs/{f}')
        for req in ('requirements.txt', 'requirements-ai.txt'):
            z.write(os.path.join(ROOT, req), req)
        for dst, src in REFS.items():
            z.write(os.path.join(ROOT, src), f'references/{dst}')
    print('ok ->', out, f'({os.path.getsize(out) / 1024:.0f} KB)')


if __name__ == '__main__':
    sys.exit(main())
