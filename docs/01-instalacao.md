# 1. Instalação

## Requisitos
| Item | Mínimo | Observação |
|---|---|---|
| Python | 3.9+ | testado em 3.11 |
| FFmpeg + FFprobe | 4.4+ | precisa de `libx264` e `prores_ks` (builds padrão têm) |
| RAM | 3 GB livres | medido: motor nativo a 3000 px ≈ 1,3 GB; a 3840 px (capa 4K) ≈ 1,8 GB de pico. Renderize **um formato por vez** |
| Disco | ~1 GB | modelos de IA (u2net, isnet) baixados na 1ª execução |
| CPU | qualquer | medido em **1 CPU**: 3:4 ≈ 6 min · 1:1 ≈ 10 min (12 s @ 30 fps). Em máquinas melhores é bem mais rápido (não medido) |

Dois níveis de instalação:
- **Núcleo** (`requirements.txt`): OpenCV, NumPy, Pillow e **psd-tools** (leitura de PSD). Suficiente para **PSD em camadas**, para capas **sem sujeito recortado** (templates `typographic-poster`, `abstract-flow`, `minimal`), para o validador e para o `prepare_cover`.
- **IA** (`requirements-ai.txt`): `rembg` + `onnxruntime`. Necessário quando `subject.enabled = true` (recorte da pessoa/objeto).

## Ubuntu / Debian
```bash
sudo apt update && sudo apt install -y ffmpeg python3 python3-venv git
git clone https://github.com/uaigoiano-max/album-motion-studio.git && cd album-motion-studio
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-ai.txt      # opcional (recorte de sujeito)
python scripts/validate_motion.py --help
```

## macOS
```bash
brew install ffmpeg python git
git clone https://github.com/uaigoiano-max/album-motion-studio.git && cd album-motion-studio
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -r requirements-ai.txt
```
> Não testado em macOS pelo autor. Se `onnxruntime` falhar em Apple Silicon, tente `pip install onnxruntime-silicon` ou use só o núcleo.

## Windows 10/11
Opção automática (PowerShell):
```powershell
git clone https://github.com/uaigoiano-max/album-motion-studio.git
cd album-motion-studio
powershell -ExecutionPolicy Bypass -File .\install.ps1
```
Opção manual:
```powershell
winget install Gyan.FFmpeg
winget install Python.Python.3.11
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-ai.txt
```
Feche e reabra o terminal após instalar o FFmpeg (o PATH é atualizado). Confirme com `ffmpeg -version`.
> Não testado em Windows pelo autor. Os comandos de background (`setsid nohup`) deste guia são de Linux/macOS; no Windows basta rodar o comando numa janela do PowerShell e esperar.

## Docker
```bash
docker build -t album-motion-studio .
docker run --rm -v "$PWD/work:/work" album-motion-studio \
  python scripts/render_motion.py --cover /work/capa.png --config /work/config.json --outdir /work/out --preview
```
> O `Dockerfile` não foi testado pelo autor. Os modelos de IA são baixados na 1ª execução (precisa de internet).

## Verificando a instalação
```bash
make test            # roda a suíte de testes (precisa de pytest: pip install pytest)
# ou, sem make:
python scripts/check_config.py configs/templates/*.json
python scripts/studio.py init examples/demo/demo_cover.png work/demo --template examples/demo/demo_config.json
python scripts/studio.py check work/demo
```
Esperado: `RESULTADO: OK`, com `frame0_vs_capa` baixo (< 1,5) e `rajada_flash 0`. Teste o PSD: `python examples/demo/make_demo_psd.py demo.psd 1000 && python scripts/studio.py init demo.psd work/psd`.

## Problemas comuns
| Sintoma | Causa provável | Solução |
|---|---|---|
| `ffmpeg: command not found` | FFmpeg fora do PATH | instale e reabra o terminal |
| `No module named 'rembg'` | instalou só o núcleo | `pip install -r requirements-ai.txt` |
| rembg trava ao baixar modelo | sem acesso a `github.com` | libere o acesso; os modelos vão para `~/.u2net/` |
| `Killed` durante o render 4K | falta de RAM | feche programas; renderize **um** formato por vez (o script já faz) |
| Render muito lento | CPU fraca | normal; rode em background e acompanhe o log |
