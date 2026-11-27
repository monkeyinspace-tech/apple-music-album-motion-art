# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [2.2.0] — 2026-11-27
### Adicionado
- **Instalador one-click**: `install.sh` (Linux/macOS) e `install.ps1` (Windows) que criam o venv, instalam dependências, instalam o FFmpeg (winget/brew/apt) se faltar e rodam o autoteste.
- **Workflow de release**: `.github/workflows/release.yml` gera o `.skill` e cria GitHub Release automaticamente em tags `v*`.
- **Badges no README**: release, CI, licença, Python, FFmpeg.
- **Seção de instalação one-click** no README com comandos para Linux/macOS e Windows.
- **CHANGELOG** atualizado com esta versão.

### Alterado
- Links do README atualizados para a organização `monkeyinspace-tech`.

## [2.1.0] — 2026-11-22
### Adicionado
- **PSD real**: papéis por tipo/nome/grupo (waves, floater, sun, drift, overlay, credit), fase coerente por grupo, movimento padrão seguro, camada **`camera`** (push-in/deriva) e camada **`adjust`/`grade`** que reconcilia camadas de ajuste com a prévia do Photoshop (erro ~5–11 → ~1–2,5/255). Testado com 3 PSDs reais (2000², 3000², 4000²).
- **`studio.py doctor [--bench] [--selftest]`**: diagnóstico de ambiente, mini fluxo ponta a ponta e estimativa de tempo de render calibrada em medições reais.
- **Portabilidade Windows/macOS**: E/S de imagem com caminhos Unicode (`compat.py`), console UTF-8, CI em Ubuntu/Windows/macOS e job Docker; `Dockerfile` e `.dockerignore`.
- **Recorte automático** (`subject.auto`): `portrait-clean` deriva caixa, pivô e Safe Area da máscara (testado em capa real).
- **Conformidade Apple**: `--container mp4`, `--static` (PNG do frame 0), aviso de selo Parental Advisory, aviso de duração <15 s, checagem de frame rate, aviso H.264 em `.mov`.
- **Privacidade**: `tests/test_repo_privacy.py` (allowlist de mídia) + `.gitignore` para PSD/vídeos/`private/`.
- Docs 16 (desempenho), 17 (compatibilidade), 18 (privacidade), `github-setup.md`, ilustrações originais e README redesenhado.
### Alterado
- Extensão do 3:4: sem listras verticais e sem escurecer demais capas claras.
- `check`: frame 0 > 6/255 reprova; 1,5–6 vira aviso (PSDs aproximam ajustes).

## [2.0.0] — 2026-11-05
Salto de "pipeline com config" para **motor de composição / editor de motion**.

### Adicionado
- **Motor de composição** (`scripts/amstudio/`): camadas `image`, `text`, `generator`, `lock`; transformações com **keyframes/expressões** (`wave`, `env`, `wiggle`, `keys`, `from_zero`) sempre em loop fechado; blend modes (`normal`, `add`, `screen`, `multiply`, `lighten`); pivô, opacidade.
- **`studio.py`** (CLI): `init`, `info`, `effects`, `add-layer`, `add-effect`, `set`, `remove`, `move`, `preview` (folha, frames, GIF), `check`, `render`, `new-effect`. Toda edição é validada antes de salvar.
- **Entrada flexível**: PNG/JPG/TIFF quadrados de qualquer tamanho (2048, **3000**, 3840/**4K**, 4096…) com `--fit crop|extend` para não quadrados; **PSD em camadas** (cada layer vira PNG + camada, papéis por nome, movimento inicial automático).
- **Resolução nativa**: assets em resolução original; o 1:1 usa o motor em até 3840 px (`--work-size`).
- **Catálogo**: 8 efeitos de camada (`flow`, `boil`, `shine`, `wave`, `blur`, `glow`, `tint`, `chroma`) e 10 geradores (`light_leaks`, `rings`, `hot_pulse`, `embers`, `shards`, `sparkles`, `vignette`, `light_sweep`, `grain`, `color_wash`).
- **Plugins em Python** (`new-effect`, `projeto/plugins/`) com registro, catálogo e validação de parâmetros.
- **`studio.py check`**: renderiza todos os quadros em baixa resolução e reprova frame 0 ≠ capa, salto de loop, flash/strobe e brilho estourado.
- Skill e agentes reescritos: conduzem **direção criativa** (perguntas ao usuário), preview/iteração, criação de efeitos, check, render e validação.
- Docs 10–15 (editor, formato da cena, catálogo gerado, PSD, plugins, diretor criativo) e 35 testes.

### Alterado
- `render_motion.py` virou adaptador: config v1 → cena v2 → motor novo (templates e docs v1 continuam válidos).
- `prepare_cover.py` aceita PSD/TIFF e tamanhos nativos; seleção de `--fit`.
- Anel de onda de choque: raio máximo 720 px (antes 900), sem corte retangular.
- `requirements.txt` inclui `psd-tools`.

### Corrigido
- Fase de onda que não valia zero em t=0 (frame 0 ≠ capa) — agora `from_zero`.
- `check` ignora diferenças de antialiasing nas bordas de camadas.

## [1.0.0] — 2026-11-04
- Pipeline v1: `prepare_cover.py` → `render_motion.py` → `validate_motion.py`, 5 templates, skill/agentes, testes e CI.

## Roadmap
- [ ] Teste com PSDs reais complexos (smart objects, estilos) e `.psb`.
- [ ] Modo `--auto-config` (sugerir coordenadas por visão computacional).
- [ ] Mais templates e efeitos (chuva, partículas de poeira, ondas de calor).
- [ ] Máscaras/track mattes por camada e parenting (como no After Effects).
- [ ] Testes em Windows/macOS e imagem Docker validada.
- [ ] Validador: checagem de Art Safe Area por detecção de texto.
