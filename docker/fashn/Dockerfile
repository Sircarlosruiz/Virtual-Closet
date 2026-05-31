# FASHN VTON v1.5 inference server. Requiere CUDA (Turing+; ejecuta fp32 en TITAN RTX).
# Imagen base: PyTorch 2.4.1 con CUDA 12.1 y cuDNN 9, variant runtime (sin herramientas de build)
FROM pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime

# Directorio de trabajo para la aplicación
WORKDIR /app

# Instala dependencias del sistema:
# - git/curl: para clonar repos y bajar archivos
# - libglib2.0-0, libgl1, libsm6, libxrender1, libxext6: dependencias de OpenCV
#   (requeridas por fashn-vton para procesamiento de imágenes)
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl \
        libglib2.0-0 libgl1 libsm6 libxrender1 libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Instala torchvision compatible con CUDA antes de fashn-vton.
# Esto evita que la dependencia torchvision>=0.15 de fashn-vton
# descargue una versión CPU o incompatible con la versión de CUDA.
RUN pip install --no-cache-dir torchvision==0.19.1 \
        --index-url https://download.pytorch.org/whl/cu121

# Copia requirements.txt e instala dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala FASHN VTON v1.5 desde el código fuente de GitHub.
# Esto instala: fashn_vton, fashn-human-parser, onnxruntime-gpu, opencv-python, einops, etc.
RUN git clone --depth 1 https://github.com/fashn-AI/fashn-vton-1.5.git /opt/fashn-vton \
    && pip install --no-cache-dir -e /opt/fashn-vton

# Copia los archivos de aplicación al contenedor
COPY main.py garment_clip.py postprocess.py ./

# Variables de entorno para configuración por defecto
ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/app/model_cache \
    FASHN_WEIGHTS_DIR=/app/weights \
    FASHN_STEPS=30 \
    FASHN_GUIDANCE=1.5 \
    FASHN_GARMENT_PHOTO_TYPE=flat-lay \
    FASHN_LEG_POSTPROCESS=true \
    FASHN_PRESERVE_LIMBS=true

# Expone el puerto del servidor FastAPI
EXPOSE 8000

# Comando de inicio: los pesos (~2 GB) se descargan al iniciar si no existen,
# luego el servidor escucha en el puerto 8000.
# --timeout-keep-alive 300: evita timeouts en conexiones de inferencia largas.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "300"]
