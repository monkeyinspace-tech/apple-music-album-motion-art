# 18. Privacidade: testando com arte inédita sem vazar nada

Capas e PSDs inéditos são sigilosos. Este projeto permite testar com material real **sem** que ele chegue ao GitHub.

## O que há dentro de um projeto (`work/proj/`)
| Arquivo | Contém arte? |
|---|---|
| `assets/*.png`, `source_flat.png`, `preview/*`, GIFs, `.mov` | **SIM** (resolução nativa) |
| `scene.json` | indireto: nomes de camada (ex.: título do lançamento) e posições |

👉 **Nunca versione a pasta de trabalho.** `work/`, `out/`, `private/`, `*.psd`, `*.mov`… já estão no `.gitignore`.

## Travas automáticas
1. `.gitignore` bloqueia PSD/PSB/TIFF, vídeos, `work/`, `out/`, `private/`.
2. `tests/test_repo_privacy.py` **reprova** se aparecer imagem/vídeo fora da lista autorizada (arte procedural da demo e ilustrações dos docs) — roda no CI.
3. Exemplos do README usam **arte própria (CC0)** gerada por código; nunca capas de terceiros.
4. `doctor`, `benchmark.py` e as tabelas de tempo guardam **só números**.

## Boas práticas
- Trabalhe numa pasta **fora** do repositório.
- Em *issues*, cole `doctor`, erros e números. **Não anexe** `assets/`, previews, GIFs nem `scene.json` com nomes sensíveis.
- Antes de `git add -A`, confira `git status`.
- Com IA (Claude etc.): os arquivos que você envia ficam naquela conversa/ambiente; em caso de dúvida use versão reduzida ou com marca d'água.
- Para validar só o software, prefira PSDs gerados por código (`examples/demo/make_demo_psd.py`).

Tudo é processado **localmente**; a única rede usada é o download dos modelos de IA do `rembg` na 1ª execução.
