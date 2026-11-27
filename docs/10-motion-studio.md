# 10. Motion Studio — o editor por trás de tudo (`studio.py`)

A versão 2 deixa de ser um "pipeline com config" e vira um **mini-editor de motion** (a ideia do After Effects/Premiere, em linha de comando): um **projeto** com **camadas**, **keyframes**, **efeitos** e **plugins**. Você (ou uma IA) edita o projeto, vê o preview e renderiza.

## Modelo mental
```
projeto/
├── scene.json          ← o "arquivo de projeto": camadas, animações, efeitos, saída
├── source_flat.png     ← a capa achatada (referência do frame 0)
├── assets/             ← cada camada como PNG (abra e edite no Photoshop/GIMP!)
│   ├── bg.png  title.png  subject.png ...
├── plugins/            ← seus efeitos personalizados (opcional)
└── preview/            ← folhas de contato / stills
```
- **Camadas** são empilhadas de baixo (primeira) para cima (última). Tipos: `image`, `text`, `generator` (efeito que desenha sozinho), `lock` (trava regiões).
- **Animação** de qualquer número: constante, onda, envelope, tremor suave ou **keyframes**. Sempre em **loop fechado**.
- **Efeitos** (de camada ou geradores) vêm de um **catálogo** (`studio.py effects`) e você pode **criar os seus** (`new-effect`).
- **Coordenadas** sempre no espaço **2048×2048**, qualquer que seja a capa (2048, 3000, 4K): a mesma cena serve para todas.
- **Qualidade garantida:** `check` confere frame 0 = capa, fechamento do loop, flashes e brilho estourado.

## Comandos
| Comando | O que faz |
|---|---|
| `init <capa ou .psd> <projeto>` | cria o projeto. Capa PNG/JPG/TIFF (2048/3000/4K…) → camadas automáticas (IA); PSD → uma camada por layer |
| `info <projeto>` | lista camadas, efeitos e transformações |
| `effects [--md]` | catálogo de efeitos e parâmetros |
| `add-layer <projeto> --effect X --id Y --param k=v` | adiciona um gerador (ou `--json` para qualquer camada) |
| `add-effect <projeto> <camada> <efeito> --param k=v` | adiciona efeito a uma camada de imagem |
| `set <projeto> <caminho> <json>` | edita qualquer valor (ex.: `subject.transform.rotation`) |
| `remove` / `move` | remove ou reordena camadas |
| `preview <projeto> [--sheet] [--t 0 .5] [--gif f.gif]` | folha de contato (6 instantes), frames isolados ou GIF |
| `check <projeto>` | validação + render rápido de todos os quadros: frame 0, loop, flash, brilho |
| `render <projeto> --upc X --formats 3x4` | gera `[UPC]_3x4.mov` / `[UPC]_1x1.mov` |
| `new-effect <nome> --kind generator\|layer` | cria o esqueleto de um efeito seu |

Todas as edições são **validadas antes de salvar**: se algo for inválido (efeito inexistente, keyframes que não fecham o loop…), nada é gravado.

## Sessões típicas

### A) Capa plana (PNG/JPG, 3000×3000 ou 4K)
```bash
python scripts/studio.py init minha_capa.png work/proj --template punk-impact --intensity bold
python scripts/studio.py preview work/proj --sheet           # abra work/proj/preview/contact_sheet.png
python scripts/studio.py add-effect work/proj title glow --param radius=40
python scripts/studio.py set work/proj subject.transform.rotation '{"wave":"sin","amp":2}'
python scripts/studio.py check work/proj
python scripts/studio.py render work/proj --upc 7891234567890 --formats 3x4 --outdir out
python scripts/studio.py render work/proj --upc 7891234567890 --formats 1x1 --outdir out
```
O `init` separa a capa em **fundo limpo / título / sujeito** por IA (precisa de `requirements-ai.txt` se houver sujeito). Os PNGs ficam em `assets/` — se o recorte não ficou perfeito, **edite o PNG** e rode `preview` de novo.

### B) PSD em camadas (melhor qualidade)
```bash
python scripts/studio.py init minha_capa.psd work/proj --intensity standard --impact "[900,1300]"
python scripts/studio.py info work/proj
```
Veja [13-photoshop-psd.md](13-photoshop-psd.md).

### C) Do zero, só com efeitos
```bash
python scripts/studio.py init capa.png work/proj          # sem template: só fundo + luz
python scripts/studio.py add-layer work/proj --id sweep --effect light_sweep
python scripts/studio.py add-layer work/proj --id wash --effect color_wash --param 'color=[60,120,255]' --param strength=0.15
python scripts/studio.py add-layer work/proj --id vig --effect vignette
```

## Resolução e capas 3000×3000 / 4K
- O `init` guarda **assets na resolução nativa** da capa.
- O formato **3:4** (2048 px de largura) usa o motor em 2048.
- O formato **1:1** usa o motor **nativo até 3840 px** (`--work-size auto`): capa 3000 → motor 3000 → 3840 (ampliação de só 1,28×, em vez de 1,87×). Capa 4K roda nativa. Medido: motor em 3000 px usa ~1,3 GB de RAM de pico.
- Escolha manual: `--work-size 2048|3000|3840` (menor = mais rápido).

## Intensidade
`--intensity subtle|standard|bold` (0,6× / 1× / 1,5×) escala deslocamentos, rotações, quantidades e brilhos. Pode ser definida no `init`, no `preview`, no `check` ou no `render`.

## Sobre o loop
Cada valor animável é avaliado em `t = 0` e `t = 1`; se diferirem, a edição é recusada. Todo efeito multiplicado pelo envelope `e(t) = (1−cos 2πt)/2` começa e termina em zero. O `check` ainda testa na prática (renderiza todos os quadros).
