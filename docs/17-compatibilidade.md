# 17. Compatibilidade: Linux, Windows, macOS e Docker

> **Resumo honesto:** desenvolvido e testado em **Linux**. Windows, macOS e Docker estão **preparados** (código endurecido, CI e `doctor`), mas **ainda não foram executados** nesses sistemas pelo autor. O CI do GitHub faz isso no primeiro *push* — veja "Como confirmar".

| Sistema | Status | Como foi verificado |
|---|---|---|
| **Linux** (Ubuntu) | ✅ testado | suíte automatizada, renders completos, benchmarks reais |
| **Windows 10/11** | 🟡 preparado | correções de portabilidade + simulação de console legado em Linux; CI `windows-latest` |
| **macOS** (Intel/Apple Silicon) | 🟡 preparado | CI `macos-latest` |
| **Docker** | 🟡 preparado | `Dockerfile` + job de CI (build + `doctor --selftest`) |

## Endurecido para Windows/macOS
- **Caminhos com acento/espaço** (`C:\Users\João\Área de Trabalho\…`): `cv2.imread/imwrite` falham em silêncio com não-ASCII no Windows → todo acesso a imagem usa `amstudio/compat.py` (numpy + `imdecode/imencode`). Testado em Linux com pastas acentuadas.
- **Console legado** (cp1252) quebra com `✅ ❌ ⚠️` → UTF-8 forçado com substituição segura (testado simulando `cp1252/ascii`).
- `scene.json` usa `/` nos caminhos; texto sempre `encoding='utf-8'`; sem `setsid`/bash no código.

## Riscos que só um teste real confirma
FFmpeg no PATH e encoders (`libx264`/`prores_ks`) · Windows: caminhos > 260 caracteres (use `C:\motion\proj`) e antivírus · macOS Apple Silicon: `onnxruntime` (só p/ recorte por IA) · Docker: permissões de volume.

## Confirme no SEU computador (2 min)
```bash
python scripts/studio.py doctor --selftest     # Python, FFmpeg, bibliotecas, RAM, acentos + mini fluxo (init → check → render → ffprobe)
python scripts/studio.py doctor --bench        # estima o tempo de render da sua máquina
```
Esperado: tudo ✅ e `AMBIENTE OK`. Cole a saída numa *issue* se algo falhar (não contém conteúdo das suas capas).

## Confirme no GitHub (automático)
Após o primeiro `git push`, aba **Actions**: `tests · ubuntu py3.9/3.12`, `windows py3.11`, `macos py3.11` e `docker · build + doctor`. Se algum ficar vermelho, abra uma issue com o log.

## Docker
```bash
docker build -t album-motion-studio .                          # núcleo (PSD e capas sem recorte por IA)
docker build -t album-motion-studio --build-arg WITH_AI=1 .     # + rembg/onnxruntime
docker run --rm album-motion-studio                            # doctor
docker run --rm -v "$PWD:/app/ws" -w /app/ws --user "$(id -u):$(id -g)" album-motion-studio init capa.psd work/proj
```
No PowerShell: `"${PWD}:/app/ws"` e sem `--user`.
