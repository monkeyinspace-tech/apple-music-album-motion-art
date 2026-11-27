# 16. Desempenho: quanto tempo leva o render?

**Resposta curta:** de **3 a ~25 minutos por formato** para um clipe de 12 s @ 30 fps (360 quadros), dependendo do tamanho da arte e da complexidade. Cenas simples em 3:4 levam poucos minutos; PSDs complexos em 1:1 com motor 4K levam mais. O seu computador provavelmente é **mais rápido** que o ambiente de medição (1 CPU).

## Medido de verdade (1 CPU, ~4 GB RAM, Linux · H.264 80 Mbps · 360 quadros)
| Material | Formato / motor | Camadas | s por quadro | Tempo estimado |
|---|---|:-:|:-:|:-:|
| Capa plana simples (fundo + luz) | 3:4 · 2048 | 2 | 0,56 | **~3,4 min** |
| Capa plana completa (título, ondas, estilhaços, brasas…) | 3:4 · 2048 | 8 | 0,68 | **~4,2 min** |
| Capa real com pessoa recortada por IA | 3:4 · 2048 | 9 | 0,66 | **~4,1 min** |
| PSD de demonstração 3000² (11 camadas) | 3:4 · 2048 | 11 | 0,66 | **~4,1 min** |
| Capa plana completa | 1:1 · motor 2048 | 8 | 1,22–1,58 | **~7,5–9,6 min** |
| PSD de demonstração 3000² | 1:1 · motor 3000 | 11 | 1,85 | **~11,4 min** |
| Capa 4096² | 1:1 · motor 3840 | 8 | 2,71 | **~17 min** |
| **PSD real 3000² (16 camadas, ajustes)** | 3:4 · 2048 | 16 | 1,43 | **~8,8 min** |
| **PSD real 2000² (30 camadas, smart objects)** | 3:4 · 2048 | 30 | 1,37 | **~8,4 min** |
| **PSD real 2000²** | 1:1 · motor 2048 | 30 | 1,40 | **~8,6 min** |
| **PSD real 3000²** | 1:1 · motor 3000 | 16 | 3,12 | **~19 min** |
| **PSD real 4000²** | 1:1 · motor 3840 | 13 | 3,69 | **~23 min** (pico de **2,8 GB** de RAM) |

> "PSD real" = arquivos de lançamentos reais, usados só para medir (nenhum conteúdo é publicado). Dobre o total se renderizar os **dois** formatos.

## O que deixa mais rápido ou mais lento
| Mais rápido | Mais lento |
|---|---|
| Menos camadas e efeitos | Muitas camadas (PSD complexo ≈ 2× uma cena simples) |
| 3:4 (2048 px) | 1:1 com motor nativo 3000/3840 px |
| `--work-size 2048` no 1:1 (reamostra para 3840) | Capa/PSD 4K (4000 px) |
| Duração curta (8–12 s) | 35 s = ~3× mais quadros que 12 s |
| CPU moderna com vários núcleos | Pouca RAM (swap) |

Dica: use `preview`/`check` (segundos) para iterar e renderize **uma vez** no final.

## Estime para a SUA máquina
```bash
python scripts/studio.py doctor --bench
```
Mede a sua velocidade e imprime uma tabela como esta (cena leve · completa · PSD complexo), com faixa de ±35%. Calibrado contra as medições acima. Para medir um projeto seu: `python tools/benchmark.py meu=work/proj:3x4`.
