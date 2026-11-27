# Publicando no GitHub (checklist)

1. Crie o repositório **apple-music-album-motion-art** (público) em `github.com/monkeyinspace-tech`.
2. `git init && git add -A && git status` → confira que **não há** capas/PSDs/vídeos (o `.gitignore` e `tests/test_repo_privacy.py` ajudam).
3. `git commit -m "Apple Music Album Motion Art v2.1.0" && git branch -M main && git remote add origin https://github.com/monkeyinspace-tech/apple-music-album-motion-art.git && git push -u origin main`
4. Aba **Actions**: confirme os jobs `ubuntu`, `windows`, `macos` e `docker` (veja [17](17-compatibilidade.md)).
5. **About** (engrenagem): descrição — *"Estúdio de motion em Python para transformar capas (PNG/JPG/PSD, 3000² e 4K) em Apple Music Album Motion Art: camadas, keyframes, efeitos, plugins e validação."* · Website: vazio · Topics: `apple-music`, `album-motion`, `motion-graphics`, `music-release`, `psd`, `ffmpeg`, `opencv`, `python`, `claude`, `ai-agent`.
6. **Settings → General → Social preview:** envie `docs/assets/social-preview.png` (1280×640).
7. **Releases → Draft new release:** tag `v2.1.0`, título "v2.1.0 — PSD real, câmera, doctor, multi-plataforma", cole o trecho do `CHANGELOG.md`; anexe `apple-motion-art.skill` (gerado por `make skill`).
8. (Opcional) Ative *Discussions* e proteja `main` (exigir CI verde).
