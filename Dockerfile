FROM runpod/base:0.6.2-cuda12.1.0
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HF_HOME=/runpod-volume HF_HUB_CACHE=/runpod-volume
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt
COPY handler.py .
CMD ["python", "-u", "handler.py"]
