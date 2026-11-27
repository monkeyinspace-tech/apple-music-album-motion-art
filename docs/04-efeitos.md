# 4. Efeitos e receitas

> Este documento explica os **princípios** (loop, zero nas pontas) e o fluxo do modo simples v1. O catálogo completo e atual de efeitos (com parâmetros) está em [12-catalogo-de-efeitos.md](12-catalogo-de-efeitos.md); o editor em [10](10-motion-studio.md).

**Princípio mestre.** Seja `e(t) = (1 − cos 2πt) / 2`, que vale **0 em t = 0 e t = 1** e 1 no meio. Todo efeito aditivo é multiplicado por `e(t)` (ou usa `sin 2πt`). Resultado: o **frame 0 é a capa** e o **último frame fecha no primeiro** — sem corte no loop.

## Camadas (de baixo para cima)
1. **Fundo "limpo"** — a capa com sujeito e título removidos por inpainting. Onde nenhuma camada cobre, o fundo é exatamente a capa original.
2. **Fluxo de fumaça** — deslocamento suave periódico (`A·sin + B·e`) por campos de ruído; peso 0 em `flow_protect` e sobre o sujeito.
3. **Vazamentos de luz** — dois blobs radiais em trajetória de Lissajous.
4. **Trincas pulsando** + **ondas de choque**.
5. **Título** — peças tremem ±1,6 px (6 trocas/s) + brilho diagonal varrendo.
6. **Estilhaços** — polígonos escuros com borda rosa/laranja em trajetória balística.
7. **Sujeito** — balança, flutua, respira (+1%).
8. **Brasas** e **sparkles** — por cima de tudo.
9. **Travas** (`lock_boxes`) — restauram logos/texto da capa original.

## O que ajustar quando…
| Quero… | Faça |
|---|---|
| Mais visível | `--intensity bold`; mais `shards`/`embers`; `sway_deg` 1.8 |
| Mais elegante | `--intensity subtle`; `shards: 0`; `embers: 0`; `rings: false` |
| Menos "tremida" no título | reduza intensidade ou desligue `title` |
| Mais sparkles | mais caixas em `sparkles` com `count` maior |
| Outra coreografia | mude `seed` |
| Loop mais longo | `--duration 20` (cada efeito dá um ciclo por loop, então o movimento fica mais lento e calmo) |
| Elemento que não pode se mexer | `lock_boxes` + `flow_protect` |
| Capa sem pessoa | `"subject": {"enabled": false}` |
| Capa sem lettering | `"title": null` |

## Regras de acessibilidade/Apple que o projeto respeita
- Sem flashes, strobe ou cortes rápidos (o validador mede a variação de luminância).
- Movimentos suaves; "boil" do título limitado a ±2,4 px.
- Sem deformar rosto/texto: fluxo protegido sobre o sujeito, `lock_boxes` para texto crítico.
- Primeira imagem == capa estática.

## Extensão do formato 3:4
A capa é quadrada (2048) e o 3:4 tem 2048×2732. A capa fica com **largura total** (sem moldura) e o fundo é estendido só **em cima e embaixo** com a textura da borda borrada; embaixo escurece gradualmente (zona onde a interface do app aplica seu próprio gradiente). `key_content_y` define onde ela fica verticalmente.

> **Nunca** centralize a capa quadrada num canvas vertical estendendo as laterais: vira uma "moldura" borrada, proibida pela Apple (arte de ponta a ponta).
