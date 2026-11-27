# 2. Guia rápido: da capa ao `.mov` validado

Tempo típico: 20–40 min de trabalho + ~16–25 min de render (1 CPU).

```
capa/PSD ─▶ init ─▶ [editar + preview ↻ com o usuário] ─▶ check ─▶ render ─▶ validate ─▶ .mov
```
> Nos exemplos, `studio.py` = `python scripts/studio.py`.

## Passo 0 — Entenda o que será animado
Responda antes de começar (ou deixe o agente perguntar — [15](15-diretor-criativo.md)): **material** (PSD? capa plana? 3000×3000 ou 4K?), **clima**, **o que se move / o que NÃO pode mover**, **intensidade**, **extras** (nome do artista animado? duração?).

## Passo 1 — Criar o projeto
```bash
mkdir -p work
# A) capa plana (PNG/JPG/TIFF 2048, 3000, 3840/4K — quadrada)
studio.py init minha_capa.png work/proj --template punk-impact --intensity bold
# B) PSD em camadas (recomendado: controle total e melhor qualidade)
studio.py init minha_capa.psd work/proj --impact "[900,1300]"
# C) sem template: só fundo + luz (depois você adiciona o que quiser)
studio.py init minha_capa.png work/proj
```
Extras do `init`: `--remove-badge` / `--badge-box x0 y0 x1 y1` (remove o selo explícito **só se o dono da arte pedir**), `--fit crop|extend` (capa não quadrada), `--duration 16`, `--key-content-y "[75,1320]"`.
O `init` avisa o tamanho da capa (ex.: "3000 px (padrão de capas de lançamento)"), se é pequena (< 2048 → 1:1 ampliado) e problemas do PSD (fundo com buracos, modo de mesclagem não suportado…).

```bash
studio.py info work/proj
```

## Passo 2 — Escolher/ajustar efeitos
Coordenadas **sempre no espaço 2048×2048** (mesmo com capa 3000/4K): `valor_2048 = valor_original × 2048 / lado_da_capa`.

| Quero… | Comando |
|---|---|
| ver os efeitos | `studio.py effects` |
| adicionar partículas/luz | `studio.py add-layer work/proj --id sweep --effect light_sweep` |
| efeito numa camada | `studio.py add-effect work/proj title glow --param radius=40` |
| mudar um valor | `studio.py set work/proj subject.transform.rotation '{"wave":"sin","amp":2}'` |
| reordenar / remover | `studio.py move work/proj sparkles 99` · `studio.py remove work/proj shards` |
| um efeito que não existe | `studio.py new-effect meu_efeito --kind generator --project work/proj` ([14](14-criar-efeitos.md)) |

## Passo 3 — Preview e iteração
```bash
studio.py preview work/proj --sheet              # folha de contato (6 instantes)
studio.py preview work/proj --t 0.5 --width 1024  # um frame
studio.py preview work/proj --gif work/preview.gif   # GIF para aprovar
```
Checklist (olhe o frame do MEIO, não só o 0): recorte limpo? título legível? linhas retas/manchas/brilho estourado? texto e rosto dentro da Área Segura (3:4: y 458–1709)? Ajuste e repita.
Se o recorte automático errou, **edite o PNG em `work/proj/assets/`** e rode o preview de novo.

## Passo 4 — Checagem automática
```bash
studio.py check work/proj
```
Reprova se: o frame 0 difere da capa, o loop tem salto, há risco de flash/strobe ou o brilho estoura. Corrija a causa e repita.

## Passo 5 — Render (um formato por vez)
```bash
studio.py render work/proj --upc 7891234567890 --formats 3x4 --outdir out
studio.py render work/proj --upc 7891234567890 --formats 1x1 --outdir out
```
Opções: `--codec prores` · `--bitrate 80M` · `--work-size auto|2048|3000|3840` · `--duration 16` · `--intensity subtle|standard|bold`.
Em Linux, para rodar em background: `setsid nohup sh -c "..." > work/render.log 2>&1 < /dev/null &` e `tail -f work/render.log` (no macOS use `nohup`).

## Passo 6 — Validar e entregar
```bash
python scripts/validate_motion.py out/7891234567890_3x4.mov out/7891234567890_1x1.mov --cover work/proj/source_flat.png
```
Tudo ✅? Então: (1) **assista aos dois vídeos inteiros em tela cheia**; (2) confira a marcação *Explicit* nos **metadados** ([09](09-direitos-e-explicito.md)); (3) envie à **distribuidora**.

---

## Modo simples (v1): config + um comando
Ainda funciona, e usa o mesmo motor:
```bash
cp configs/templates/punk-impact.json work/config.json && python scripts/check_config.py work/config.json
python scripts/render_motion.py --cover work/capa.png --config work/config.json --outdir work/out --preview
python scripts/render_motion.py --cover work/capa.png --config work/config.json --outdir out --upc SEU_UPC --formats 3x4
```
Referência das chaves do config v1: [03](03-referencia-config.md).
