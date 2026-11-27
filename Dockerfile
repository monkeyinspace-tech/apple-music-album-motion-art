# Album Motion Studio — imagem de uso. Núcleo por padrão; recorte de sujeito (rembg) com --build-arg WITH_AI=1.
#   docker build -t album-motion-studio .
#   docker build -t album-motion-studio --build-arg WITH_AI=1 .
# Uso (monte a sua pasta em /app/ws):
#   docker run --rm -v "$PWD:/app/ws" -w /app/ws --user "$(id -u):$(id -g)" album-motion-studio init capa.png work/proj
FROM python:3.11-slim
ARG WITH_AI=0
ENV PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 HOME=/tmp U2NET_HOME=/tmp/.u2net
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt requirements-ai.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
 && if [ "$WITH_AI" = "1" ]; then pip install --no-cache-dir -r requirements-ai.txt; fi
COPY . .
ENTRYPOINT ["python", "scripts/studio.py"]
CMD ["doctor"]
