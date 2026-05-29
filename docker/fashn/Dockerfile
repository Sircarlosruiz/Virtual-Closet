# FASHN VTON v1.5 inference server. Needs CUDA (Turing+; runs fp32 on TITAN RTX).
FROM pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime

WORKDIR /app

# git to clone the model repo; libGL/glib for opencv (pulled by fashn-vton).
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl \
        libglib2.0-0 libgl1 libsm6 libxrender1 libxext6 \
    && rm -rf /var/lib/apt/lists/*

# torchvision is not bundled in the runtime image; install the CUDA-matched wheel
# BEFORE the fashn-vton install so its torchvision>=0.15 dependency is satisfied
# without pulling a CPU/mismatched build.
RUN pip install --no-cache-dir torchvision==0.19.1 \
        --index-url https://download.pytorch.org/whl/cu121

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install FASHN VTON v1.5 from source. Brings fashn_vton, fashn-human-parser,
# onnxruntime-gpu, opencv-python, einops, etc.
RUN git clone --depth 1 https://github.com/fashn-AI/fashn-vton-1.5.git /opt/fashn-vton \
    && pip install --no-cache-dir -e /opt/fashn-vton

COPY main.py garment_clip.py ./

ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/app/model_cache \
    FASHN_WEIGHTS_DIR=/app/weights \
    FASHN_STEPS=30 \
    FASHN_GUIDANCE=1.5 \
    FASHN_GARMENT_PHOTO_TYPE=flat-lay \
    FASHN_SEGMENTATION_FREE=true

EXPOSE 8000

# Weights (~2 GB) download on startup into the mounted volume; subsequent starts use the cache.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "300"]
