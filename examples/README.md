# Exemplos

## `demo/` — capa de demonstração (CC0)
| Arquivo | O que é |
|---|---|
| `make_demo_cover.py` | gera a capa **ORBIT / DEMO COVER** por código (livre de direitos) |
| `demo_cover.png` | a capa gerada (2048×2048) |
| `demo_config.json` | config usando título, impacto, trincas, estilhaços, brasas, sparkles e fluxo (sem IA) |
| `demo_contact_sheet.jpg` | folha de contato do preview (6 instantes do loop) |
| `make_demo_psd.py` | gera um **PSD em camadas** (Fundo · Planeta · Titulo · Logo) para testar a importação |

### Rodar (v2)
```bash
python scripts/studio.py init examples/demo/demo_cover.png work/demo --template examples/demo/demo_config.json
python scripts/studio.py preview work/demo --sheet
python scripts/studio.py check work/demo
python scripts/studio.py render work/demo --upc 0000000000000 --formats 3x4 --outdir out
```

### PSD em camadas (3000×3000)
```bash
python examples/demo/make_demo_psd.py work/demo_layers.psd 3000
python scripts/studio.py init work/demo_layers.psd work/demo_psd --impact "[900,1300]"
python scripts/studio.py info work/demo_psd         # papéis detectados pelos nomes das camadas
python scripts/studio.py preview work/demo_psd --sheet
```

### Modo simples (v1)
```bash
python scripts/render_motion.py --cover examples/demo/demo_cover.png \
  --config examples/demo/demo_config.json --outdir out --preview
python scripts/render_motion.py --cover examples/demo/demo_cover.png \
  --config examples/demo/demo_config.json --outdir out --upc 0000000000000 --formats 3x4
python scripts/validate_motion.py out/0000000000000_3x4.mov --cover examples/demo/demo_cover.png
```
O GIF do README (`docs/assets/demo.gif`) foi gerado com `--gif`.

### Experimente os templates sem IA na mesma capa
```bash
for t in minimal abstract-flow typographic-poster; do
  python scripts/render_motion.py --cover examples/demo/demo_cover.png \
    --config configs/templates/$t.json --outdir out/$t --preview
done
```
Compare as folhas de contato para entender a diferença entre os templates.

## Como criar o seu exemplo
1. Copie um template de `configs/templates/`.
2. Ajuste as coordenadas à sua capa (`docs/02-guia-rapido.md`).
3. **Não** publique capas de terceiros/inéditas; compartilhe só o `config.json` e um GIF autorizado.
