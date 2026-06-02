# TryOff garment extraction inference server.
# Modelo: FLUX.2-klein-base-9B + virtual-tryoff-lora — extracción de prendas desde fotos de personas.
# Imagen base: PyTorch 2.5.1 con CUDA 12.1 y cuDNN 9 (diffusers 0.37+ / Flux2Klein).
# Requiere ~24 GB VRAM (GPU dedicada, no compartida con FASHN).
FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./

ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/app/model_cache \
    TRYOFF_WEIGHTS_DIR=/app/weights \
    TRYOFF_STEPS=28 \
    TRYOFF_GUIDANCE=5.0 \
    TRYOFF_HEIGHT=1024 \
    TRYOFF_WIDTH=768

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "300"]
