# Contribuindo

Obrigado por querer ajudar! Este projeto é pequeno e direto: mudanças pequenas e bem testadas são as melhores.

## Ambiente de desenvolvimento
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt        # núcleo + pytest
pip install -r requirements-ai.txt         # opcional: recorte de sujeito
make test
```

## Formas de contribuir
1. **Templates** (`configs/templates/*.json`) — o jeito mais fácil. Crie um para um estilo de capa novo (ex.: foto de show, ilustração infantil, trap sombrio).
   - Inclua `_template`, `_for` e `_how_to_adapt`.
   - Rode `python scripts/check_config.py seu.json` e o `--preview` na capa de demonstração (ou em uma capa **sua e liberada**).
2. **Efeitos** — um plugin em `scripts/amstudio/fx/` (veja [docs/14](docs/14-criar-efeitos.md)). Siga as regras abaixo e rode `make effects-doc` para atualizar o catálogo.
3. **Validações** (`scripts/validate_motion.py`) — novas regras reais da Apple/distribuidora, com a mensagem de erro original em `docs/06`.
4. **Docs/traduções** — correções, exemplos, tradução para outros idiomas.
5. **Relatos de reprovação** — abra uma issue com a mensagem exata do validador.

## Regras para efeitos novos
1. **Nascem e morrem em zero.** Multiplique por `e(t) = (1 − cos 2πt)/2` ou use `sin 2πt`. O teste `frame0 == capa` precisa continuar passando.
2. **Sem flashes/strobe/cortes rápidos.** Variação suave; o validador deve continuar aprovando.
3. **Sem deformar rosto/texto.** Use `flow_protect`/`lock_boxes` quando necessário.
4. **Configurável e desligável** via `config.json` + documentado em `docs/03`.
5. **Memória sob controle:** o render roda com 3 GB de RAM; evite arrays enormes extras por frame.
6. **Olhe um frame do MEIO do loop**, não só o 0 (bugs de brilho estourado só aparecem ali).

## Arte e direitos
Não envie capas inéditas ou de terceiros em PRs/issues. Use `examples/demo` (CC0) ou mostre só coordenadas/config.

## Commits e PRs
- Mensagens no imperativo, curtas (`Adiciona template portrait-warm`).
- Preencha o checklist do PR.
- Uma mudança lógica por PR.

## Código de conduta
Seja respeitoso. Críticas ao código, nunca às pessoas.
