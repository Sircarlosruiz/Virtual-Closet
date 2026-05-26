# transformers>=4.45 requires PyTorch>=2.4; 2.3.x causes it to disable torch entirely.
FROM pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime

WORKDIR /app

# Minimal system deps for Pillow, OpenCV headless, and healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libglib2.0-0 libsm6 libxrender1 libxext6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# torchvision is not bundled in the runtime image; install CUDA-matched wheels.
# gfpgan/realesrgan pull opencv-python (needs libGL); keep only headless for cv2.
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir torchvision==0.19.1 \
        --index-url https://download.pytorch.org/whl/cu121 \
    && pip uninstall -y opencv-python \
    && pip install --no-cache-dir --force-reinstall opencv-python-headless

COPY main.py garment_clip.py .

ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/app/model_cache \
    CATVTON_STEPS=50 \
    CATVTON_GUIDANCE=30.0

EXPOSE 8000

# Models are downloaded on first request and cached in HF_HOME (volume mount).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "300"]
