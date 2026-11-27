# 15. Diretor criativo: perguntando o que o usuário quer

O agente **não escolhe sozinho** a animação: ele **conduz uma conversa curta** para entender a ideia e só então monta o projeto. Isto também vale para você, se estiver planejando uma animação sem IA.

## Roteiro de perguntas (no máximo 1–3 por vez)
1. **Material:** "Você tem o PSD em camadas ou só a capa plana? Qual o tamanho (3000×3000, 4K)?"
2. **Clima / sensação:** "Qual a vibe? *elegante e sutil* · *cinematográfico* · *caótico/punk* · *sonhador/etéreo* · *energético/dance* · *sombrio*"
3. **O que deve se mover?** "Pessoa/objeto · título · fundo · partículas · luzes · tudo."
4. **O que NÃO pode se mover?** "Logo, texto legal, rosto, produto…"
5. **Referências / ideias livres:** "Tem uma cena em mente? (ex.: *chuva de neon*, *explosão*, *neblina*, *glitch suave*, *letras pulsando*)."
6. **Intensidade:** *discreto · médio · ousado*.
7. **Extras:** "Quer texto/nome do artista animado? Duração (8–35 s)?"
8. **Depois do preview:** "O que mudar? Mais/menos movimento, cores, outro efeito?"

> Se o usuário já disse algo (ou a resposta é óbvia pela capa), **não pergunte de novo**. Com ferramenta de perguntas com botões, use-a; senão, pergunte em texto, objetivamente.

## Biblioteca de ideias (clima → receita)
| Clima | Receita no Motion Studio |
|---|---|
| **Elegante / sutil** | `--intensity subtle`; `flow` leve no fundo; `light_leaks`; `vignette`; sparkles pequenos |
| **Cinematográfico** | `vignette` + `light_sweep` + `grain` + leve `glow`; zoom lento (`scale` env 0.02) |
| **Caótico / punk / zine** | `boil` + `shine` no título; `shards`, `embers`, `rings` no ponto de impacto; `bold` |
| **Sonhador / etéreo** | `flow` amplo; `blur` animado leve (env); `color_wash` pastel; sparkles |
| **Energético / dance** | `rings` pulsando; `tint` (matiz girando devagar); `chroma` suave; `light_sweep` |
| **Sombrio** | `vignette` forte; `grain`; `flow` lento; `color_wash` frio de baixa intensidade |
| **Tipográfica** | `title` com `shine` e `boil`; `wave` leve; `glow` pulsando |
| **Retrô / VHS** | `chroma` + `grain` + `wave` fraca (sem glitch/flash) |

## Pedido → como fazer
| O usuário diz | Faça |
|---|---|
| "O título brilhando em neon" | `add-effect title glow` + `tint` (bright env) |
| "A pessoa balançando mais" | `set subject.transform.rotation '{"wave":"sin","amp":2.2}'` |
| "Quero fumaça no fundo" | `flow` com `amp` maior no fundo |
| "Escurece nas bordas" | `add-layer --effect vignette` |
| "Pulsar nas batidas" | `rings` com `count` coerente; `glow` com `strength` env; (sem sincronizar com áudio — o vídeo é mudo) |
| "Adicione o nome do artista" | camada `text` com `"opacity": {"env": true}` (surge e some; o frame 0 tem de ser a capa) + `shine`/`glow` |
| "Algo que não existe no catálogo" | **crie um plugin** (`new-effect`) — ver [14](14-criar-efeitos.md) |
| "Tá piscando/forte demais" | reduzir `intensity`, `strength`, `amp`; o `check` mostra flashes |

## Limites que o agente deve explicar
- O vídeo é **mudo** (regra Apple): não dá para sincronizar com a música por áudio; dá para escolher ritmos de loop.
- Efeitos "rápidos demais" são **recusados** por acessibilidade (flashes/strobe).
- O que está no PSD é o que se move bem. Capa plana depende de recorte por IA (pode errar em cabelo/objetos finos).
