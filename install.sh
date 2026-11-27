#!/usr/bin/env bash
# One-click installer for Album Motion Studio (Linux/macOS)
set -euo pipefail

PY=${PY:-python3}
echo "🎬 Album Motion Studio — instalador"

# 1. Python
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "❌ Python 3.9+ não encontrado. Instale em https://www.python.org/downloads/"
  exit 1
fi
PYVER=$("$PY" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Python $PYVER"

# 2. FFmpeg
if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  echo "⚠️  FFmpeg/FFprobe não encontrados."
  if command -v brew >/dev/null 2>&1; then
    echo "   Instalando via Homebrew..."
    brew install ffmpeg
  elif command -v apt-get >/dev/null 2>&1; then
    echo "   Instalando via apt..."
    sudo apt-get update && sudo apt-get install -y ffmpeg
  else
    echo "   Instale manualmente: https://ffmpeg.org/download.html"
    exit 1
  fi
fi
echo "✅ FFmpeg $(ffmpeg -version | head -1 | cut -d' ' -f3)"

# 3. venv
if [ ! -d .venv ]; then
  echo "📦 Criando virtualenv..."
  "$PY" -m venv .venv
fi
source .venv/bin/activate

# 4. deps
echo "📦 Instalando dependências..."
pip install --upgrade pip
pip install -r requirements.txt
echo "   (opcional) pip install -r requirements-ai.txt  # para recorte de sujeito em capa plana"

# 5. self-test
echo "🩺 Rodando autoteste..."
python scripts/studio.py doctor --selftest

echo ""
echo "✅ Instalação concluída!"
echo "   Ative o venv:  source .venv/bin/activate"
echo "   Demo:          python scripts/studio.py init examples/demo/demo_cover.png work/demo --template examples/demo/demo_config.json"
echo "   Preview:       python scripts/studio.py preview work/demo --sheet"
echo "   Check:         python scripts/studio.py check work/demo"
echo "   Render:        python scripts/studio.py render work/demo --upc 0000000000000 --formats 3x4 --outdir out"
echo "   Validar:       python scripts/validate_motion.py out/0000000000000_3x4.mov --cover work/demo/source_flat.png"
echo ""
echo "📖 Documentação: docs/01-instalacao.md"