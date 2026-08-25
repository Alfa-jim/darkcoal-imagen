# TINY base - 50MB not 3.5GB. The old runpod/base:0.6.2 is 3.5GB and that big layer (aa0696ed) is what kept Retrying for an hour.
# python:3.10-slim is tiny. Torch cu121 wheel brings its OWN Cuda libs, host provides the driver, so we don't need a heavy Cuda base.
FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HF_HOME=/runpod-volume HF_HUB_CACHE=/runpod-volume

WORKDIR /app

# Only tiny deps - no giant cuda toolkit in base
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libsm6 libxext6 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY handler.py .

CMD ["python", "-u", "handler.py"]
