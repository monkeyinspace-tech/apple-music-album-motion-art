# 8. FAQ

**Preciso saber After Effects?** Não. O projeto é um editor de motion por comandos (camadas, keyframes, efeitos, plugins) e gera os vídeos por código. Se você prefere a rota artesanal, o After Effects com o `.aep` da Apple continua existindo — e o PSD em camadas funciona nos dois mundos.

**Funciona com qualquer capa?** Funciona com qualquer capa **quadrada**. A qualidade do resultado depende do config (coordenadas) e, para capas com pessoa, da qualidade do recorte por IA. Capas muito poluídas pedem mais iteração.

**Funciona com capa 3000×3000 (padrão de lançamento), 4K e PSD?** Sim: PNG/JPG/TIFF quadrados em qualquer tamanho e PSD em camadas. Os assets ficam em resolução nativa e o 1:1 usa o motor **nativo até 3840 px** (medido: ~1,3 GB de RAM a 3000 px; ~1,8 GB com capa 4096). Capa menor que 2048 px é ampliada no 1:1.

**Posso criar qualquer animação? Existe limite?** O catálogo tem 8 efeitos de camada e 11 geradores, e você pode **escrever os seus** em Python (`new-effect`). Os limites reais são regras da Apple (sem flashes/strobe, loop 8–35 s, mudo) e honestidade técnica (recorte por IA, PSD complexo). O agente **pergunta** o que você quer antes de criar.

**O agente decide sozinho a animação?** Não: ele conduz uma conversa de direção criativa ([15](15-diretor-criativo.md)), mostra previews e só renderiza com a sua aprovação.

**Posso usar sem IA (recorte)?** Sim: PSD em camadas não precisa de IA; em capa plana use templates sem sujeito (ou nenhum) e instale só `requirements.txt`.

**PSD do Photoshop com smart objects/estilos funciona?** Camadas de pixels, opacidade e modos Normal/Add/Screen/Multiply/Lighten, sim. Smart objects, estilos avançados e camadas de ajuste podem não sair idênticos — rasterize antes ([13](13-photoshop-psd.md)).

**H.264 ou ProRes?** H.264 (80 Mbps) gera arquivos de ~120 MB. ProRes 422 evita a regra de bitrate, mas os arquivos ficam bem maiores. Confirme com sua distribuidora o que ela aceita.

**O validador aprova = Apple aprova?** Não. É uma checagem prévia. A aprovação vem da distribuidora/Apple.

**Quanto tempo leva?** Medido em 1 CPU: 3:4 ≈ 6 min, 1:1 ≈ 10 min (12 s a 30 fps). Preview: ~1 min.

**Posso mudar a duração?** Sim, `--duration` de 8 a 35 s. Durações maiores = mais tempo de render e arquivos maiores.

**Posso usar nos meus lançamentos comerciais?** O código é MIT. Os modelos baixados pelo `rembg` têm licenças próprias — confira. A capa e a música são **seus** direitos/da sua gravadora.

**Como remover o selo "Parental Advisory"?** `studio.py init … --remove-badge` (ou `prepare_cover.py --remove-badge`). Leia [09](09-direitos-e-explicito.md) antes.

**O selo explícito some, e a marcação "Explicit" da faixa?** Ela é um **metadado** do lançamento na distribuidora — não depende da arte. Confirme que está correta.

**O vídeo ficou "tremendo" no título.** Use `--intensity subtle` ou `"title": null`.

**Apareceu um "fantasma" em volta da pessoa.** Reduza `sway_deg`/`float_px`/`shift_px`, ou melhore `isnet_boxes`.

**Posso rodar em servidor sem tela?** Sim, tudo é linha de comando.

**Como contribuo com um template novo?** Veja [`CONTRIBUTING.md`](../CONTRIBUTING.md).
