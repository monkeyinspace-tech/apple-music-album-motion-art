# 14. Criando seus próprios efeitos (plugins)

O catálogo embutido não é o limite: **qualquer efeito pode ser escrito em Python** em ~20 linhas e usado como os demais. É assim que uma IA (ou você) cria "o que o usuário imaginou" sem esperar uma nova versão do projeto.

## Em 3 passos
```bash
python scripts/studio.py new-effect chuva_neon --kind generator --project work/proj   # 1. esqueleto
# 2. edite work/proj/plugins/chuva_neon.py
python scripts/studio.py add-layer work/proj --id chuva --effect chuva_neon           # 3. use
python scripts/studio.py check work/proj                                              #    valide
```
Plugins em `projeto/plugins/` valem para aquele projeto. Para efeitos globais, coloque `.py` em `~/.apple_music_album_motion_art/plugins/` e rode `new-effect` sem `--project` (o `render` e o `check` carregam os plugins do projeto).

## Dois tipos
### Gerador — desenha direto no quadro
```python
import math, numpy as np, cv2
from amstudio.fx import generator

@generator('pulso_radial', {
    'strength': ('float', 0.25, 'intensidade'),
    'color':    ('color', [200, 70, 255], 'cor BGR'),
}, 'Anel de luz que respira no centro do quadro.')
class PulsoRadial:
    def __init__(self, ctx, strength=0.25, color=(200, 70, 255)):
        W = ctx.W                                  # tamanho de trabalho (2048 … 3840)
        y, x = np.mgrid[0:W, 0:W].astype(np.float32)
        self.d = np.hypot(x - W / 2, y - W / 2) / ctx.sc     # distância em px do espaço 2048
        self.c, self.s, self.K = np.array(color, np.float32), strength, ctx.K

    def render(self, fr, t, e):                    # fr: float32 BGR 0..255 (W×W×3); e: 0→1→0
        ring = np.exp(-((self.d - (200 + 600 * t)) / 60) ** 2)
        fr += ring[..., None] * self.c * (self.s * self.K * e)
```

### Efeito de camada — altera os pixels de UMA camada
```python
import math, numpy as np, cv2
from amstudio.fx import layer_fx

@layer_fx('balanco_lateral', {'amp': ('float', 8.0, 'px (espaço 2048)')}, 'Balança a camada de lado a lado.')
class BalancoLateral:
    def __init__(self, ctx, layer, amp=8.0):
        self.a = amp * ctx.sc * ctx.K
    def apply(self, img, t, e):                    # img: float32 H×W×4 (BGR pré-multiplicado + alfa)
        M = np.float32([[1, 0, self.a * math.sin(2 * math.pi * t)], [0, 1, 0]])
        return cv2.warpAffine(img, M, (img.shape[1], img.shape[0]), borderMode=cv2.BORDER_REPLICATE)
```
Use: `{"type":"image", "asset":"…", "effects":[{"type":"balanco_lateral","amp":12}]}`.

## API
| Item | Para quê |
|---|---|
| `ctx.W` | tamanho de trabalho em px (2048…3840) |
| `ctx.sc` | `W/2048`. **Multiplique todo tamanho/distância em px por ele** — o mesmo efeito funciona em 2048, 3000 e 4K |
| `ctx.K` | intensidade global (0,6 / 1 / 1,5) |
| `ctx.cover` | capa achatada (BGR uint8, W×W) |
| `ctx.fps`, `ctx.dur`, `ctx.N` | fps, duração (s), nº de quadros |
| `t` | tempo normalizado 0..1 do loop |
| `e` | `(1−cos 2πt)/2`: 0 no início, 1 no meio, 0 no fim |
| `layer` (efeito de camada) | `.w .h` (px do recorte), `.x0 .y0` (origem no canvas), `.base` (pixels), `.canvas_alpha()` |
| `link(self, ctx, layers)` | opcional: roda depois que todas as camadas existem (para ler outras camadas) |

O **registro** (`@generator` / `@layer_fx`) recebe o nome, o dicionário de parâmetros `{nome: (tipo, padrão, descrição)}` e uma descrição. Isso alimenta o catálogo (`studio.py effects`) e a **validação** de parâmetros.

## As 3 regras de ouro (o `check` confere)
1. **Comece e termine em zero.** Multiplique tudo por `e` (ou use `sin(2πt)`, que vale 0 nas pontas). Senão o frame 0 ≠ capa e o `check` reprova ("frame 0 difere da capa").
2. **Nada de flashes.** Variações suaves (o `check` mede a luminância e reprova >3 transições de 10% em 1 s).
3. **Dimensione por `ctx.sc`.**

Também vale: evite alocar arrays enormes por quadro; evite deformar rostos/texto.

## Pedindo para a IA criar
> "Crie um efeito de chuva de neon rosa caindo na diagonal, bem sutil."

O agente deve: `new-effect` → escrever o `.py` → `add-layer` → `preview` → `check` → mostrar a folha de contato → ajustar com você.

## Segurança
Plugins são **código Python executado na sua máquina**. Só use plugins em que você confia.
