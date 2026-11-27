# 11. Formato da cena (`scene.json` v2)

```jsonc
{
  "version": 2,
  "name": "meu-lancamento",
  "source": { "flat": "source_flat.png", "psd": null },
  "output": { "duration": 12, "fps": 30, "intensity": 1.0, "key_content_y": [75, 1320] },
  "layers": [ /* de baixo para cima */ ]
}
```
Coordenadas: **espaço de referência 2048×2048**, origem no canto superior esquerdo (X→direita, Y→baixo).

## `output`
| Chave | Padrão | Descrição |
|---|---|---|
| `duration` | 12 | segundos (**8–35**, regra Apple) |
| `fps` | 30 | |
| `intensity` | 1.0 | multiplicador global (0,6 / 1 / 1,5) |
| `key_content_y` | `[75,1320]` | faixa vertical (da capa) que deve caber na Safe Area do 3:4 |

## Valores animáveis
Qualquer número animável aceita:
| Forma | Exemplo | Valor |
|---|---|---|
| número | `6` | constante |
| onda | `{"wave":"sin","amp":3,"base":0,"cycles":1,"phase":0,"from_zero":false}` | `base + amp·onda(2π(cycles·t+phase))`. `sin`/`cos`/`tri`. `from_zero` subtrai o valor em t=0 (permite fase livre começando em zero) |
| envelope | `{"env":true,"amp":-10,"base":0,"cycles":1}` | `base + amp·(1−cos 2πnt)/2` — **0 nas pontas** |
| tremor | `{"wiggle":{"amp":4,"freq":2,"seed":7}}` | tremor suave periódico, zero em t=0 |
| keyframes | `{"keys":[[0,0],[0.4,12],[1,0]],"ease":"inout"}` ou `[[0,0],[1,0]]` | `t` de 0 a 1; `ease`: `linear`, `inout`, `in`, `out`, `hold` |

> **Regra do loop:** v(0) deve ser igual a v(1). Keyframes abertos (ex.: `[[0,0],[1,5]]`) são **recusados** na validação.

## Camadas

### `image` — camada de imagem (PNG com alfa)
```jsonc
{ "id": "subject", "type": "image", "asset": "assets/subject.png",
  "bbox": [640,150,2048,2048],       // onde fica (espaço 2048). Omitido = tela cheia
  "pivot": [1500,1500],              // centro de rotação/escala
  "blend": "normal",                 // normal | add | screen | multiply | lighten
  "opacity": 1.0, "visible": true,
  "transform": { "x": {...}, "y": {...}, "rotation": {...}, "scale": {...}, "opacity": {...} },
  "effects": [ {"type":"boil","amp":1.6}, {"type":"shine"} ] }
```
`transform`: `x`,`y` (px do espaço 2048), `rotation` (graus), `scale` (1 = normal), `opacity` (multiplicador). A intensidade global multiplica x/y/rotação e `(scale−1)`.
`effects`: efeitos de camada aplicados em ordem (veja [12-catalogo-de-efeitos.md](12-catalogo-de-efeitos.md)).

### `text` — texto
```jsonc
{ "id": "nome", "type": "text", "text": "NOME DO ARTISTA", "font": "C:/Windows/Fonts/impact.ttf", "size": 220,
  "color": "#ff4fa3", "stroke": "#000000", "stroke_width": 6, "position": [1024, 300], "align": "center",
  "transform": {...}, "effects": [...] }
```
`font` é o caminho de um arquivo `.ttf/.otf` (se ausente, usa uma fonte padrão do sistema). Funciona como camada de imagem.

> ⚠️ **Elementos que NÃO existem na capa (texto novo, logo, partículas) não podem aparecer no frame 0** — a Apple exige o primeiro frame igual à capa estática. Faça-os surgir com `"opacity": {"env": true}` em `transform` (0 → 1 → 0). O `check` reprova se o frame 0 for diferente da capa.

### `generator` — efeito que desenha sozinho
```jsonc
{ "id": "embers", "type": "generator", "effect": "embers", "params": {"origin":[742,1325],"count":130} }
```
### `lock` — restaurar regiões da capa
```jsonc
{ "id": "locks", "type": "lock", "boxes": [[40,1700,420,1900]] }
```
Em todo quadro, essas caixas voltam a ser a capa original (logos, texto legal, créditos).

## Efeitos de camada × geradores
- **Efeito de camada**: vive em `layers[i].effects[]`, altera os pixels daquela camada (`flow`, `boil`, `shine`, `wave`, `blur`, `glow`, `tint`, `chroma`).
- **Gerador**: é uma camada própria (`type: generator`) que desenha por cima do que está abaixo dela na pilha.
- Lista completa de parâmetros: [12-catalogo-de-efeitos.md](12-catalogo-de-efeitos.md). Para ver na hora: `python scripts/studio.py effects`.

## Ordem importa
A pilha é composta de baixo para cima. Ex.: `light_leaks` entre o fundo e o sujeito fica **atrás** dele; `sparkles` no fim fica **na frente** de tudo. Reordene com `studio.py move`.

## Validação
`studio.py check` (e todo comando que edita) valida: tipos, ids únicos, assets existentes, efeitos e parâmetros conhecidos (inclusive plugins), parâmetros obrigatórios, valores animáveis e **fechamento do loop**.
