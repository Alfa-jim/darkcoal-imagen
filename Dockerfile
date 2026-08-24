FROM runpod/pytorch:2.1.0-py3.10-cuda12.1.0-devel-ubuntu22.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HF_HOME=/runpod-volume HF_HUB_CACHE=/runpod-volume
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt
COPY handler.py .
# Clean pip cache + apt lists + torch cuda extras we don't need to keep image smaller
RUN pip cache purge 2>/dev/null; rm -rf /root/.cache /tmp/*; apt-get clean; rm -rf /var/lib/apt/lists/*
CMD ["python", "-u", "handler.py"]
