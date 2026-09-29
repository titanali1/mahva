# Mahva — build long videos from text + images with zero API cost.
#
#   docker build -t mahva .
#   docker run --rm -p 8000:8000 -v "$PWD/out:/app/out" mahva          # web UI
#   docker run --rm -v "$PWD:/data" mahva \
#       python -m mahva render /data/examples/demo-fa.md -o /data/out/demo.mp4
#
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MAHVA_HOME=/app/out \
    MPLCONFIGDIR=/tmp/matplotlib

# espeak-ng gives a fully offline Persian voice; fonts-free fallback covers the rest
RUN apt-get update \
 && apt-get install -y --no-install-recommends espeak-ng \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt pyproject.toml README.md ./
COPY mahva ./mahva
COPY app.py ./
COPY assets ./assets
COPY docs ./docs
COPY examples ./examples
COPY tests ./tests

RUN pip install --upgrade pip \
 && pip install -r requirements.txt \
 && pip install -e . \
 && python -c "import mahva, PIL, arabic_reshaper, bidi; print('mahva ready')"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/health').read()"

CMD ["python", "-m", "mahva", "serve", "--host", "0.0.0.0", "--port", "8000", "--work", "/app/out/web"]
