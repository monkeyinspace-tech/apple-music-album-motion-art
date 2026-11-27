# 3. Referência do `config.json` (modo simples v1)

> Este é o **config v1**, usado por `render_motion.py` e pelos templates em `configs/templates/` (o `studio.py init --template` também o aceita e o **compila para uma cena v2**). Para o controle total (camadas, keyframes, plugins) veja [10](10-motion-studio.md) e [11](11-formato-da-cena.md).

- Todas as coordenadas estão no espaço **2048 × 2048 px** (origem no canto superior esquerdo; X→direita, Y→baixo). A capa de entrada é redimensionada para 2048 internamente.
- Chaves que começam com `_` (ex.: `_comment`) são ignoradas — use para anotações.
- Chaves ausentes assumem os padrões abaixo.
- Valide com `python scripts/check_config.py seu.json`.

## Visão geral
```jsonc
{
  "key_content_y": [75, 1320],
  "impact": [742, 1325],
  "subject":   { "enabled": true, "pivot": [1500,1500], "bbox_origin": [640,150], "isnet_boxes": [[...]], "sway_deg": 1.3, "float_px": 10, "shift_px": 8 },
  "title":     { "box": [40,90,1470,965], "texture_thr": 55 },
  "hot_cracks":{ "roi": [150,900,1250,1700] },
  "flow_protect": [ { "center": [380,1400], "axes": [560,600] } ],
  "light_leaks": true, "rings": true, "shards": 26, "embers": 130,
  "sparkles": [ { "box": [1480,420,1900,760], "count": 7 } ],
  "leak_colors": [[170,60,255],[40,110,255]],
  "lock_boxes": [],
  "seed": 11
}
```

## Chaves

### `key_content_y` — `[y_topo, y_base]` · padrão `[75, 1320]`
Faixa vertical da capa (px 2048) que **precisa caber na Art Safe Area do 3:4**. O script centraliza essa faixa em y 458–1709 do canvas 3:4 (2732 px de altura) e estende o fundo em cima/embaixo. A Safe Area tem ~1251 px de altura: `check_config` avisa se sua faixa for maior. Itens fora dela podem ficar sob a interface do app.

### `impact` — `[x, y]` ou `null` · padrão `null`
Ponto de "energia" (explosão, golpe, centro de luz). Habilita **ondas de choque, estilhaços, brasas e trincas**. Sem `impact`, esses efeitos não são desenhados.

### `subject` — recorte da pessoa/objeto (precisa de `requirements-ai.txt`)
| Campo | Tipo | Padrão | O que faz |
|---|---|---|---|
| `enabled` | bool | `true` | `false` = sem recorte, sem IA |
| `pivot` | `[x,y]` | `[1500,1500]` | ponto de apoio do balanço (cintura/quadril/base). Mexa-o para o movimento parecer ancorado |
| `bbox_origin` | `[x,y]` | `[640,150]` | canto superior esquerdo da área processada como camada (do ponto até o canto inferior direito da capa). Deve **envolver** todo o sujeito |
| `isnet_boxes` | lista de `[x0,y0,x1,y1]` | `[]` | regiões onde a máscara do modelo `isnet` (objetos finos: taco, microfone, guitarra) é somada à do `u2net` (corpo). Vazio = só `u2net` |
| `sway_deg` | número | `1.3` | ângulo máximo do balanço (graus) |
| `float_px` | número | `10` | flutuação vertical máxima (px) |
| `shift_px` | número | `8` | deslocamento horizontal máximo (px) |

> Movimentos grandes expõem o fundo reconstruído por inpainting (borrado). Mantenha pequenos.

### `title` — `{ "box": [x0,y0,x1,y1], "texture_thr": 55 }` ou `null`
Anima lettering em peças de papel/adesivos: "respira" (±1,6 px, trocado 6×/s) e recebe uma faixa de brilho diagonal. `box` deve cobrir todo o lettering; a máscara é obtida por **cor + textura**.
- `texture_thr` (10–200, padrão 55): quanto menor, mais área é considerada "título". Letras finas/claras → 35. Pegou fumaça/fundo → 80.

### `hot_cracks` — `{ "roi": [x0,y0,x1,y1] }` ou `null`
Pixels **laranja/amarelo saturados** dentro da região viram brilho que pulsa (3 pulsos por loop). Requer `impact`.

### `flow_protect` — lista de `{ "center": [x,y], "axes": [a,b] }`
Elipses onde a "fumaça" **não** deforma (globo, produto, rosto ilustrado). A região do sujeito já é protegida automaticamente.

### `light_leaks` — bool · padrão `true`
Dois blobs de luz coloridos passeando atrás dos elementos.

### `leak_colors` — `[[B,G,R],[B,G,R]]` ou omitido
Cores (ordem **BGR** do OpenCV, 0–255). Omitido → extraídas da própria capa por k-means.

### `rings` — bool · padrão `true`
3 ondas de choque por loop a partir de `impact`.

### `shards` — int · padrão `26` · `embers` — int · padrão `130`
Quantidade de estilhaços/brasas (multiplicada pela intensidade). Acima de ~300 fica lento.

### `sparkles` — lista de `{ "box": [x0,y0,x1,y1], "count": n }`
Estrelas de 4 pontas em posições aleatórias (fixas pela `seed`) dentro de cada caixa. Cada uma aparece e some suavemente (~2,6 s).

### `lock_boxes` — lista de `[x0,y0,x1,y1]`
Regiões **restauradas da capa original em todo frame**. Use para logos, texto legal, créditos, qualquer coisa que não possa se mexer/brilhar.

### `seed` — int · padrão `11`
Semente das posições aleatórias. Troque para outra "coreografia".

## Parâmetros de linha de comando (`render_motion.py`)
| Flag | Padrão | Descrição |
|---|---|---|
| `--cover` | (obrigatório) | capa quadrada (use a saída do `prepare_cover`) |
| `--config` | — | `config.json` (sem ele, usa os padrões: só fluxo + luz) |
| `--outdir` | `out` | pasta de saída (e cache `.cache/`) |
| `--upc` | `UPC` | prefixo dos arquivos: `[UPC]_3x4.mov` |
| `--formats` | `3x4,1x1` | lista; **prefira um por vez** (RAM) |
| `--duration` | `12` | segundos, **8–35** |
| `--fps` | `30` | |
| `--intensity` | `standard` | `subtle` (0,6×) · `standard` · `bold` (1,5×) |
| `--codec` | `h264` | `h264` ou `prores` (ProRes 422) |
| `--bitrate` | `80M` | alvo H.264; a Apple exige **45–100 Mbps** |
| `--preview` | — | só gera `preview_contact_sheet.png` |
| `--gif CAMINHO` | — | só gera um GIF leve de pré-visualização |
| `--test-frames N` | — | renderiza só N frames (teste de codificação) |

## Intensidade — o que escala
`bold`/`subtle` multiplicam: balanço do sujeito, amplitude do fluxo, brilho dos vazamentos, pulso das trincas, "boil" do título (máx. 2,4 px), quantidade de estilhaços/brasas/sparkles (sparkles e rings têm teto de 1,3×). Nenhuma intensidade usa flashes.
