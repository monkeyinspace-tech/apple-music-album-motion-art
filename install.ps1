# One-click installer for Apple Music Album Motion Art (Windows / PowerShell)
$ErrorActionPreference = 'Stop'

$PY = if ($env:PY) { $env:PY } else { 'python' }
Write-Host "🎬 Apple Music Album Motion Art — instalador" -ForegroundColor Cyan

# 1. Python
if (-not (Get-Command $PY -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python 3.9+ não encontrado. Instale em https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}
$PYVER = & $PY -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'
Write-Host "✅ Python $PYVER" -ForegroundColor Green

# 2. FFmpeg
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue) -or -not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
    Write-Host "⚠️  FFmpeg/FFprobe não encontrados." -ForegroundColor Yellow
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "   Instalando via winget..."
        winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
    } else {
        Write-Host "   Instale manualmente: https://ffmpeg.org/download.html" -ForegroundColor Red
        exit 1
    }
}
$FFVER = (ffmpeg -version 2>&1 | Select-Object -First 1) -replace 'ffmpeg version ', ''
Write-Host "✅ FFmpeg $FFVER" -ForegroundColor Green

# 3. venv
if (-not (Test-Path .venv)) {
    Write-Host "📦 Criando virtualenv..."
    & $PY -m venv .venv
}
& .\.venv\Scripts\Activate.ps1

# 4. deps
Write-Host "📦 Instalando dependências..."
python -m pip install --upgrade pip
pip install -r requirements.txt
Write-Host "   (opcional) pip install -r requirements-ai.txt  # para recorte de sujeito em capa plana" -ForegroundColor DarkGray

# 5. self-test
Write-Host "🩺 Rodando autoteste..."
python scripts/studio.py doctor --selftest

Write-Host ""
Write-Host "✅ Instalação concluída!" -ForegroundColor Green
Write-Host "   Ative o venv:  .\.venv\Scripts\Activate.ps1"
Write-Host "   Demo:          python scripts/studio.py init examples/demo/demo_cover.png work/demo --template examples/demo/demo_config.json"
Write-Host "   Preview:       python scripts/studio.py preview work/demo --sheet"
Write-Host "   Check:         python scripts/studio.py check work/demo"
Write-Host "   Render:        python scripts/studio.py render work/demo --upc 0000000000000 --formats 3x4 --outdir out"
Write-Host "   Validar:       python scripts/validate_motion.py out/0000000000000_3x4.mov --cover work/demo/source_flat.png"
Write-Host ""
Write-Host "📖 Documentação: docs/01-instalacao.md" -ForegroundColor DarkGray