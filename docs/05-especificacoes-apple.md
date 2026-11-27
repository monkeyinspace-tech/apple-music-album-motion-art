# 5. Especificações da Apple Music (Album Page Motion)

Fonte: *Album Page Motion Toolkit — At a Glance* (PDF do toolkit oficial da Apple) e motivos de reprovação reais retornados por uma validação de distribuidora. Sempre confira a documentação mais recente da Apple/distribuidora: regras podem mudar.

## Formatos
| Formato | Resolução | Observação |
|---|---|---|
| 1:1 Quadrado | **3840 × 3840** | toda a tela é Área Segura |
| 3:4 Vertical | **2048 × 2732** | Safe Area menor + interface sobreposta |

## Arquivo
| Regra | Valor |
|---|---|
| Duração | **8 a 35 s**, loop contínuo (sem frames de cor sólida) |
| Container | `.mov` (o PDF aceita `.mov` ou `.mp4`; o validador de distribuidora exibe "QuickTime / MOV"). **Use `.mov`** |
| Codec | **H.264** *ou* **Apple ProRes 422 / 4444**. Sem canal alfa (somente RGB) |
| Bitrate (H.264) | **entre 45 e 100 Mbps** — (reprovado na prática com 15 Mbps) |
| Pixel | **quadrado (SAR 1:1)** — precisa estar marcado no arquivo |
| Cor | Rec. 709 / sRGB |
| Áudio | **desligado / mudo** |
| Nome | `[UPC]_1x1.mov` e `[UPC]_3x4.mov` (UPC do álbum) |
| Entrega | via **distribuidora** (não direto à Apple) |

## Fontes oficiais e divergências entre distribuidoras
- Apple Music Style Guide — *Motion Album Artwork*: <https://help.apple.com/itc/musicstyleguide/en.lproj/itc7d4b161d8.html>
- Apple (iTunes Partner) — *Album Motion Art Delivery*: <https://itunespartner.apple.com/music/support/5245-album-motion-art-delivery>
- Toolkit "Album Page Motion Toolkit" (PDF com as medidas usadas aqui).

| Tema | O que dizem as fontes | O que este projeto faz |
|---|---|---|
| **Selo Parental Advisory** | a arte de motion **não pode** exibir o selo (a marcação explícita vai nos **metadados**) | `init --remove-badge` remove; `init` **avisa** se detectar o selo |
| **Duração** | toolkit: **8–35 s**; várias distribuidoras citam **15–35 s** | padrão 12 s + **aviso** (<15 s) no `check`/validador. Confirme com a sua |
| **Codec/contêiner** | ProRes 422/4444 em `.mov` é aceito em todas; H.264 exige 45–100 Mbps e algumas esperam `.mp4` | `--codec prores`; `--container mp4` para H.264 |
| **Frame rate** | 23.976 / 24 / 25 / 29.97 / 30 | padrão 30; validador checa |
| **PNG estático** | algumas pedem 2048×2732 e 3840² estáticos | `render --static` salva o frame 0 (== capa) |
| **Cortes/edições múltiplas** | evitar; basear-se na capa original | um único loop contínuo, sem cortes |
| **Integridade visual** | sem distorções (ex.: artefatos de IA) | recorte revisável; `check` + preview |

## Tamanho da arte de entrada
- Capas de lançamento costumam ter **3000×3000**; também aceitas: 2048, 3840 (4K), 4096 e PSD quadrado. Quanto maior, melhor a nitidez do 1:1 (3840 px).
- A Apple pede a **saída** em 3840×3840 (1:1) e 2048×2732 (3:4), independente do tamanho da capa de entrada.
- Este projeto guarda os assets em resolução **nativa** e renderiza o 1:1 com motor nativo até 3840 px.

## Áreas do 3:4 (em px do canvas 2048×2732)
- **Artwork Area**: o canvas inteiro. A arte vai de ponta a ponta — **sem bordas ou espaço** em volta.
- **Art Safe Area ≈ x 49–2003, y 458–1709** (≈ 1954 × 1251; medida a partir do template do toolkit). Texto, logos e elementos-chave **devem** ficar aqui.
- Fora da Safe Area, botões/texto do app podem cobrir a arte (topo e, principalmente, o terço inferior com gradiente escuro).

## Diretrizes de estilo da Apple
1. **O primeiro frame deve ser igual à capa estática.** Evite múltiplas edições; baseie a sequência na arte original.
2. **Faça loop.** A animação toca continuamente; evite quadros de cor sólida.
3. **Seja sutil.** Sem luzes piscando, cortes rápidos ou strobing (acessibilidade).
4. **Seja intencional.** Confira texto/rostos/membros distorcidos (cuidado com ferramentas de IA).

## Checklist de exportação (do PDF)
- [x] Áudio mudo
- [x] Apenas RGB (sem alfa)
- [x] Nome com UPC
- [x] Entrega via distribuidora

## Como este projeto garante cada regra
| Regra | Onde |
|---|---|
| SAR 1:1 | `setsar=1` no filtro do FFmpeg (`render_motion.py`) |
| 45–100 Mbps | `-b:v 80M -minrate 80M -maxrate 95M`; verificado no `validate_motion.py` |
| Rec. 709 | `scale=out_color_matrix=bt709` + tags `-colorspace/-color_primaries/-color_trc bt709` |
| Mudo | `-an` |
| 1º frame == capa | todos os efeitos em zero em t=0 + checagem `--cover` no validador |
| Loop | efeitos periódicos + checagem do salto de fechamento |
| Sem moldura no 3:4 | largura total; extensão só vertical |
