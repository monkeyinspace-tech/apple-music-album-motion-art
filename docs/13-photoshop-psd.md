# 13. Trabalhando com Photoshop (PSD em camadas)

Com um PSD em camadas você controla **exatamente** o que se move — sem depender de recorte por IA.

```bash
python scripts/studio.py init minha_capa.psd work/proj --impact "[900,1300]"
python scripts/studio.py info work/proj
python scripts/studio.py preview work/proj --sheet
```

## Preparando o PSD
1. **Tela quadrada** (3000×3000 é o padrão de lançamento; 2048, 3840 e 4096 também servem). PSD não quadrado é recusado com instruções.
2. **Nomeie as camadas** — o nome define o movimento inicial (pode trocar depois):

| Nome contém (pt/en) | Papel | Movimento inicial |
|---|---|---|
| `fundo`, `background`, `bg`, `smoke`, `cenario`, `base` | fundo | fumaça viva (`flow`) + respiração de zoom |
| `pessoa`, `artista`, `person`, `subject`, `model`, `cantor`, `character` | sujeito | balanço, flutuação, pivô na base |
| `titulo`, `title`, `texto`, `text`, `lettering`, `nome`, `typo` | título | tremor "zine" + brilho varrendo |
| `logo`, `legal`, `credito`, `parental`, `selo`, `copyright` | **trava** | **sem movimento** (e restaurado a cada quadro) |
| qualquer outro | genérico | flutuação suave |

Se nenhuma camada se chama "fundo", a camada de baixo que cobre ~toda a tela é tratada como fundo.
3. **Complete o fundo atrás da pessoa/objetos** (clone/preenchimento). Quando a pessoa se mexe, o que está atrás aparece. O importador avisa se o fundo tem buracos.
4. **Rasterize** textos, smart objects e estilos de camada que forem essenciais (clique direito → *Rasterizar*). Camadas que o leitor não consegue renderizar são ignoradas com aviso.
5. Camadas **ocultas** e **grupos** são ignorados como unidade (as camadas dentro dos grupos visíveis são importadas individualmente).

## O que é importado
- Cada camada de pixels vira um PNG em `assets/` (resolução nativa) + uma camada `image` no `scene.json`.
- Posição → `bbox` (convertida para o espaço 2048). Opacidade e modo de mesclagem **Normal, Linear Dodge (Add), Screen, Multiply, Lighten**. Outros modos viram *normal* com aviso.
- A composição achatada do PSD vira `source_flat.png` (referência do frame 0).

## Depois da importação (edite como quiser)
```bash
python scripts/studio.py set work/proj pessoa.transform.rotation '{"wave":"sin","amp":2}'
python scripts/studio.py add-effect work/proj titulo glow --param radius=40
python scripts/studio.py move work/proj sparkles 99          # manda para o topo
```
Para mudar a arte: **edite o PNG em `assets/`** (ou re-exporte o PSD e rode `init` de novo).

## Limitações honestas
- Testado com PSDs **gerados por código** (psd-tools) e com camadas simples. PSDs complexos feitos no Photoshop (smart objects, estilos de camada avançados, máscaras vetoriais, camadas de ajuste) **podem não renderizar idênticos** — rasterize antes.
- Camadas de ajuste (curvas, níveis…) não são aplicadas individualmente; o achatado (`source_flat.png`) as inclui, o que pode gerar diferença no check do frame 0.
- Sem suporte a `.psb` gigantes além da memória disponível.
- Texto vivo (camada de tipo) depende de pré-visualização embutida; prefira rasterizar.

## Gerar um PSD de exemplo
```bash
python examples/demo/make_demo_psd.py demo_layers.psd 3000
python scripts/studio.py init demo_layers.psd work/demo --impact "[900,1300]"
```


---
## Atualização v2.1 — o que aprendemos com PSDs reais
Testamos três PSDs de lançamentos reais (2000², 3000² e 4000²): com **smart objects aninhados em grupos, camadas de texto, Curves, Brightness/Contrast, Hue/Saturation, máscaras e efeitos**. O importador agora:
- **Papéis por tipo, nome e GRUPO:** camadas de texto viram `title`; uma camada sem nome útil **herda o papel do grupo pai** (ex.: grupo "ondas e barco"). Novos papéis: `waves`, `floater`, `sun`, `drift`, `overlay`, `credit`.
- **Movimento padrão seguro:** o que não é reconhecido (e overlays de tela cheia) fica **parado**; as peças de um mesmo grupo se movem **juntas** (mesma fase).
- **Camadas de ajuste:** não são animáveis, mas a cor é **reconciliada** com a prévia do Photoshop por uma camada `grade` (curva por canal + correção suave). Erro típico vs. Photoshop: de ~5–11/255 para ~1–2,5/255.
- **Câmera:** um push-in suave é adicionado para garantir movimento visível mesmo quando quase tudo fica parado.
- **Prévia embutida:** o achatado vem da prévia do Photoshop; sem "Maximizar compatibilidade" o importador avisa.
- **Memória:** PSD 4000² com motor 3840 usa ~**2,8 GB** de RAM; use `--work-size 2048/3000` em máquinas menores.
