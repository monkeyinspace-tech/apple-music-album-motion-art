PY ?= python3
.PHONY: help install install-ai test demo demo-psd demo-gif effects-doc check-configs skill clean

help:
	@echo "make install        - instala o núcleo (OpenCV, NumPy, Pillow, psd-tools)"
	@echo "make install-ai     - instala também rembg/onnxruntime (recorte de sujeito em capa plana)"
	@echo "make test           - roda a suíte de testes (precisa de requirements-dev.txt)"
	@echo "make demo           - cria o projeto de demonstração e gera a folha de contato"
	@echo "make demo-psd       - gera um PSD de demonstração 3000x3000 e importa"
	@echo "make demo-gif       - GIF da demo (docs/assets/demo.gif)"
	@echo "make effects-doc    - regenera docs/12-catalogo-de-efeitos.md a partir do código"
	@echo "make check-configs  - valida os templates (config v1)"
	@echo "make skill          - gera dist/apple-motion-art.skill"

install:
	$(PY) -m pip install -r requirements.txt

install-ai:
	$(PY) -m pip install -r requirements-ai.txt

test:
	$(PY) -m pytest -q

demo:
	$(PY) scripts/studio.py init examples/demo/demo_cover.png work/demo --template examples/demo/demo_config.json
	$(PY) scripts/studio.py preview work/demo --sheet
	$(PY) scripts/studio.py check work/demo

demo-psd:
	$(PY) examples/demo/make_demo_psd.py work/demo_layers.psd 3000
	$(PY) scripts/studio.py init work/demo_layers.psd work/demo_psd --impact "[900,1300]"
	$(PY) scripts/studio.py preview work/demo_psd --sheet

demo-gif: demo
	$(PY) scripts/studio.py preview work/demo --gif docs/assets/demo.gif

effects-doc:
	@{ echo "# 12. Catálogo de efeitos"; echo; echo "> Gerado automaticamente por \`python scripts/studio.py effects --md\` — não edite à mão. Plugins seus aparecem com \`--project <pasta>\`."; echo; echo "Valores do tipo **spec** aceitam números, ondas, envelopes, tremor ou keyframes (veja [11](11-formato-da-cena.md#valores-animáveis)). Coordenadas em px do espaço 2048×2048."; $(PY) scripts/studio.py effects --md; } > docs/12-catalogo-de-efeitos.md

check-configs:
	$(PY) scripts/check_config.py configs/templates/*.json examples/demo/demo_config.json

skill:
	$(PY) tools/build_skill.py

clean:
	rm -rf out work dist .pytest_cache
