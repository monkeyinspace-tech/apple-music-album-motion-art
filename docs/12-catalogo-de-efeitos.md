# 12. Catálogo de efeitos

> Gerado automaticamente por `python scripts/studio.py effects --md` — não edite à mão. Plugins seus aparecem com `--project <pasta>`.

Valores do tipo **spec** aceitam números, ondas, envelopes, tremor ou keyframes (veja [11](11-formato-da-cena.md#valores-animáveis)). Coordenadas em px do espaço 2048×2048.


## Efeitos de camada

### `blur`
Desfoque gaussiano animável (foco/desfoco, "respiração" de lente).

| parâmetro | tipo | padrão | descrição |
|---|---|---|---|
| `radius` | spec | `{"env": true, "amp": 8}` | raio do desfoque (px, animável) |

### `boil`
Tremor estilo "boil"/zine: cada peça de papel/letra balança de leve, em passos discretos. O passo 0 é neutro.

| parâmetro | tipo | padrão | descrição |
|---|---|---|---|
| `amp` | float | `1.6` | tremor em px (espaço 2048). Limitado a max_amp por acessibilidade |
| `max_amp` | float | `2.4` | teto do tremor (px) |
| `cell` | float | `70` | tamanho das "peças" que tremem independentes (px) |
| `rate` | float | `6.0` | trocas por segundo (estilo stop-motion/zine) |
| `seed` | int | `100` | semente |

### `chroma`
Aberração cromática: separa levemente os canais de cor (efeito de lente/VHS), sem piscar.

| parâmetro | tipo | padrão | descrição |
|---|---|---|---|
| `shift` | spec | `{"env": true, "amp": 4}` | separação dos canais R/B (px, animável) |

### `flow`
Deforma suavemente a camada com campos de ruído periódicos (fumaça, água, tecido). Zero em t=0 e t=1.

| parâmetro | tipo | padrão | descrição |
|---|---|---|---|
| `amp` | float | `13.0` | deslocamento máximo em px (espaço 2048). Fumaça viva / ondulação orgânica |
| `amp2` | float | `null` | amplitude do 2º campo (padrão 0.85×amp) |
| `cell` | float | `220` | escala do 1º campo (px). Maior = movimentos mais largos |
| `cell2` | float | `300` | escala do 2º campo |
| `seed` | int | `1` | semente |
| `protect` | list | `null` | elipses que NÃO deformam: [{"center":[x,y],"axes":[a,b]}] |
| `protect_layers` | list | `null` | ids de camadas cujo contorno também fica protegido (ex.: ["subject"]) |

### `glow`
Bloom: as áreas claras da camada irradiam luz. Intensidade animável (pulsar).

| parâmetro | tipo | padrão | descrição |
|---|---|---|---|
| `radius` | float | `30` | raio do bloom (px) |
| `threshold` | float | `0.65` | luminância mínima (0..1) que brilha |
| `strength` | spec | `{"env": true, "amp": 0.6}` | intensidade animável |

### `shine`
Faixa de luz diagonal que varre a camada uma vez por loop (como brilho em letreiro/metal).

| parâmetro | tipo | padrão | descrição |
|---|---|---|---|
| `width` | float | `170` | largura da faixa de brilho (px) |
| `strength` | float | `0.4` | intensidade (0..1) |
| `slope` | float | `0.6` | inclinação da faixa |
| `color` | color | `[255, 235, 255]` | cor BGR do brilho |
| `start` | float | `-700` | posição inicial da faixa (fora da peça) |
| `inset` | float | `15` | recuo (px) para brilhar só no miolo opaco da camada |

### `tint`
Correção de cor animável: gire o matiz, pulse a saturação ou o brilho (respire a cor).

| parâmetro | tipo | padrão | descrição |
|---|---|---|---|
| `hue` | spec | `0` | rotação de matiz (graus, animável) |
| `sat` | spec | `0` | delta de saturação (-1..1) |
| `bright` | spec | `0` | delta de brilho (-1..1) |

### `wave`
Ondulação senoidal (bandeira, água, calor). Zero em t=0 e t=1.

| parâmetro | tipo | padrão | descrição |
|---|---|---|---|
| `amp` | float | `6.0` | amplitude (px) |
| `wavelength` | float | `300` | comprimento de onda (px) |
| `cycles` | int | `1` | ondas que "passam" por loop |
| `axis` | str | `"x"` | "x" desloca colunas de pixels ao longo de y; "y" o inverso |


## Geradores

### `camera`
Movimento de CÂMERA sobre tudo que está abaixo dele na pilha (push-in suave + deriva). Dá vida a qualquer capa, mesmo sem camadas móveis.

| parâmetro | tipo | padrão | descrição |
|---|---|---|---|
| `zoom` | float | `0.02` | push-in máximo (0.02 = 2%). Vale 0 nas pontas do loop |
| `drift` | list | `[0, 0]` | [dx, dy] deriva máxima em px (espaço 2048) |
| `rotate` | float | `0.0` | rotação máxima da câmera (graus) |
| `pivot` | list | `null` | [x, y] centro do movimento (opcional; padrão: centro do quadro) |

### `color_wash`
Banho de cor que sobe e desce (clima: quente, frio, neon) — modo "screen", sem estourar.

| parâmetro | tipo | padrão | descrição |
|---|---|---|---|
| `color` | color | `[200, 70, 255]` | cor BGR |
| `strength` | float | `0.12` | intensidade |

### `embers`
Brasas/faíscas subindo de um ponto, com brilho. Nascem e morrem em zero.

| parâmetro | tipo | padrão | descrição |
|---|---|---|---|
| `origin` | point | `null` | [x,y] de onde saem as brasas |
| `count` | int | `130` | quantidade |
| `spread` | float | `760` | alcance máximo (px) |
| `seed` | int | `3` | semente |

### `grain`
Grão de filme sutil (sobe e desce com o loop; zero nas pontas).

| parâmetro | tipo | padrão | descrição |
|---|---|---|---|
| `amount` | float | `4.0` | intensidade do grão de filme (níveis 0..255) |

### `hot_pulse`
Faz as áreas quentes da arte (trincas de lava, brasas, neon laranja) pulsarem como se respirassem.

| parâmetro | tipo | padrão | descrição |
|---|---|---|---|
| `roi` | box | `null` | [x0,y0,x1,y1] região onde buscar pixels laranja/amarelos "quentes" (lava, brasa, neon) |
| `pulses` | int | `3` | pulsos por loop |
| `strength` | float | `0.42` | intensidade |
| `exclude_layers` | list | `null` | ids de camadas a excluir (ex.: ["subject"]) |

### `light_leaks`
Dois blobs de luz coloridos que passeiam atrás do conteúdo (clima/atmosfera).

| parâmetro | tipo | padrão | descrição |
|---|---|---|---|
| `colors` | list | `null` | [[B,G,R],[B,G,R]]; omitido = cores vivas extraídas da própria capa |
| `amp1` | float | `0.1` | intensidade do 1º vazamento |
| `amp2` | float | `0.08` | intensidade do 2º |

### `light_sweep`
Faixa de luz suave varrendo o quadro todo uma vez por loop (reflexo de holofote/vidro).

| parâmetro | tipo | padrão | descrição |
|---|---|---|---|
| `strength` | float | `0.14` | intensidade |
| `width` | float | `300` | largura da faixa (px) |
| `slope` | float | `0.6` | inclinação |
| `color` | color | `[255, 235, 255]` | cor BGR |

### `rings`
Ondas de choque suaves expandindo de um ponto (impacto, batida, pulso).

| parâmetro | tipo | padrão | descrição |
|---|---|---|---|
| `center` | point | `null` | [x,y] origem das ondas (espaço 2048) |
| `count` | int | `3` | ondas por loop |
| `max_radius` | float | `720` | raio máximo (px) |
| `strength` | float | `0.3` | intensidade |
| `color` | color | `[210, 120, 255]` | cor BGR |

### `shards`
Estilhaços/pedaços escuros em trajetória balística com borda luminosa (explosão, quebra).

| parâmetro | tipo | padrão | descrição |
|---|---|---|---|
| `origin` | point | `null` | [x,y] do impacto |
| `count` | int | `26` | quantidade |
| `seed` | int | `4` | semente |
| `rim` | color | `[120, 90, 255]` | cor BGR da borda |

### `sparkles`
Estrelas de 4 pontas que surgem e somem suavemente (~2,6 s), nunca piscando.

| parâmetro | tipo | padrão | descrição |
|---|---|---|---|
| `zones` | list | `null` | [{"box":[x0,y0,x1,y1],"count":n}] onde surgem os brilhos |
| `seed` | int | `5` | semente |
| `color` | color | `[255, 235, 255]` | cor BGR |

### `vignette`
Vinheta que respira: as bordas escurecem de leve e voltam (foco no centro).

| parâmetro | tipo | padrão | descrição |
|---|---|---|---|
| `strength` | float | `0.35` | escurecimento máximo das bordas (0..1) |

