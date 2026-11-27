# 6. Validação e troubleshooting

## `studio.py check` (antes de renderizar)
```bash
python scripts/studio.py check work/proj
```
Valida a cena e renderiza **todos os quadros em 320 px** (rápido). Reprova (❌) se:
- **frame 0 difere da capa** (>1,5/255 após suavizar bordas; em projetos vindos de **PSD** o limite de erro é 6/255 e 1,5–6 vira aviso, pois ajustes/efeitos são aproximados) → algum efeito não começa em zero, ou o recorte/PSD não bate com o achatado;
- **risco de flash/strobe** (>3 transições de luminância >10% em 1 s);
- a cena é inválida (efeito/parâmetro desconhecido, keyframes que não fecham o loop, asset ausente).
Avisos (⚠️): salto no fechamento do loop maior que o normal; luminância média > 1,6× a do frame 0 (possível brilho estourado — **abra o preview do meio do loop**).

## `validate_motion.py` (depois de renderizar)
```bash
python scripts/validate_motion.py out/UPC_3x4.mov out/UPC_1x1.mov --cover work/capa.png [--json]
```
Retorna **código 1** se houver ❌ (útil em CI/automação). O formato (`1x1`/`3x4`) é deduzido do **nome do arquivo**.

| Checagem | Reprova (❌) quando… |
|---|---|
| Resolução | diferente de 3840² (1:1) ou 2048×2732 (3:4) |
| Container | não é MOV/QuickTime |
| Pixel quadrado | SAR ≠ 1:1 |
| Duração | fora de 8–35 s |
| Bitrate H.264 | fora de 45–100 Mbps |
| ProRes | perfil não é 422/4444 |
| Áudio | existe stream de áudio |
| Flash/strobe | mais de 3 transições de luminância > 10% em 1 s (aproximação da regra WCAG 2.3.1) |
| Frames sólidos | algum frame de cor uniforme |
| Primeiro frame | difere da capa (média > 6/255) — só com `--cover` |
| ⚠️ Loop | salto último→primeiro frame > 3× o salto típico |

> É uma **checagem prévia local**. Não substitui a validação oficial da distribuidora/Apple.

## Erros reais já encontrados e como corrigir
| Mensagem / sintoma | Causa | Correção |
|---|---|---|
| "O vídeo deve ter uma proporção de pixel quadrado" | SAR não marcado | já resolvido: filtro `setsar=1`. Se usar outro encoder: `-vf setsar=1` |
| "A taxa de bits (15.4 Mbps) deve ser maior que 45 e menor que 100" | bitrate baixo (alvo 15M) | `--bitrate 80M` ou `--codec prores` |
| Brilho estourando para branco no meio do loop | somar cor já em 0–255 e multiplicar por 255 de novo | revise a escala; **sempre veja um frame do meio** |
| Moldura borrada nas laterais do 3:4 | capa centralizada num canvas vertical | largura total + extensão só em cima/embaixo |
| Linha reta horizontal no meio da arte | máscara do título pegou fumaça e terminou na borda da caixa | máscara por **cor + textura**; ajuste `title.box`/`texture_thr` |
| Frame 0 ≠ capa | o fundo reconstruído aparece fora da área da camada | o inpainting só deve existir onde a camada tem alfa 1 |
| Selo/logo parece torto | brilho aditivo passando por cima | `lock_boxes` |
| Anel de onda de choque cortado em retângulo | região de cálculo menor que o raio | corrigido na v1.0 (`RING_R`) |
| Recorte da pessoa com pedaços faltando (taco, microfone) | `u2net` ignora objetos finos | `subject.isnet_boxes` cobrindo o objeto |
| Rastro/fantasma ao redor do sujeito | movimento grande demais | reduza a amplitude de `subject.transform` (rotação, x, y) |
| `check`: "frame 0 difere da capa" num PSD | camada de ajuste/smart object/estilo não renderizados igual ao achatado, ou onda com fase sem `from_zero` | rasterize no Photoshop; use `"from_zero": true` em ondas com `phase` |
| `check`: "frame 0 difere da capa" após adicionar texto/logo/camada nova | o elemento novo aparece já no frame 0 | `set <camada>.transform.opacity '{"env":true}'` (surge e some) |
| `keyframes não fecham o loop` | último keyframe ≠ primeiro | repita o primeiro valor em `t = 1` |
| `fundo ... tem áreas transparentes` (PSD) | a camada de fundo tem buraco atrás da pessoa | preencha o fundo no PSD |
| `RuntimeError ... requirements-ai.txt` | recorte de sujeito sem rembg | `pip install -r requirements-ai.txt` ou desligue o sujeito |
| `O PSD não é quadrado` | canvas do PSD não 1:1 | Photoshop: Imagem → Tamanho da Tela (quadrado) |
| Plugin não aparece / erro ao carregar | arquivo fora de `projeto/plugins/` ou erro de sintaxe | `studio.py effects --project work/proj` mostra o que carregou |

## Problemas de ambiente
| Problema | Solução |
|---|---|
| `Killed` na codificação 4K | pouca RAM: um formato por vez; feche apps; lookahead já reduzido (`rc-lookahead=10`) |
| Job em background morre ao fechar a sessão | `setsid nohup ... > log 2>&1 < /dev/null &` |
| `pkill -f render_motion` derruba o próprio shell | use `pgrep -f ...` e `kill <PID>` |
| `mkdir -p a/{b,c}` falha no `sh` | brace expansion é do bash; crie as pastas uma a uma |
| Comando longo é interrompido pela ferramenta | divida em `sleep 280; tail log` |
