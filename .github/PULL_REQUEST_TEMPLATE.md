## O que muda
<!-- resumo curto -->

## Tipo
- [ ] Novo template (`configs/templates/`)
- [ ] Novo efeito / melhoria no render
- [ ] Correção de bug
- [ ] Documentação

## Checklist
- [ ] `pytest -q` passa
- [ ] `python scripts/check_config.py configs/templates/*.json` passa
- [ ] Efeitos novos **começam e terminam em zero** (frame 0 == capa; loop sem salto)
- [ ] Sem flashes/strobe; sem deformar texto/rosto
- [ ] Docs atualizadas (`docs/03` se mudou o config)
- [ ] Não incluí arte de terceiros/inédita (use `examples/demo`)
