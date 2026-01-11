# ==========================================
# STAGE 1: BUILDER (Shared)
# Compiles the code (cached).
# ==========================================
FROM nvidia/cuda:12.2.0-devel-ubuntu22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

# Install build tools
RUN apt-get update && apt-get install -y \
    git cmake build-essential libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*
    
WORKDIR /app
RUN git clone --recursive https://github.com/leejet/stable-diffusion.cpp

WORKDIR /app/stable-diffusion.cpp
RUN mkdir build
WORKDIR /app/stable-diffusion.cpp/build


# 75 = RTX 20-series (Turing)
# 86 = RTX 30-series / A4000 / A5000 / A6000 (Ampere)
# 89 = RTX 40-series / RTX 6000 Ada / RTX 4000 SFF Ada (Ada Lovelace)
# SD_CUBLAS=ON
RUN cmake .. -DSD_CUDA=ON -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES="75;86;89" && \
    cmake --build . --config Release -- -j$(nproc)

# ==========================================
# STAGE 2: BASE RUNTIME (Shared)
# Holds the binary and common dependencies.
# ==========================================

FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04 AS base_runtime
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 1. Install Runtime Deps + Python + Pip
RUN apt-get update && apt-get install -y \
    wget curl git libgomp1 libcurl4 \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Copy binary from builder
COPY --from=builder /app/stable-diffusion.cpp/build/bin/sd /usr/local/bin/sd

# ==========================================
# STAGE 3: FULL (Web Terminal / Dev)
# ==========================================
FROM base_runtime AS full

# Install CLI tools for downloading models at runtime
RUN pip3 install -U huggingface_hub

WORKDIR /workspace
COPY start.sh /start.sh
RUN chmod +x /start.sh
CMD ["/start.sh"]

# ==========================================
# STAGE 4: SERVERLESS (Production)
# ==========================================
FROM base_runtime AS serverless
# Install RunPod SDK
RUN pip3 install --no-cache-dir runpod huggingface_hub cryptography

WORKDIR /

# Create model directory
RUN mkdir -p /models

# BAKING IN MODELS (This takes time, but happens in parallel/after compile)
ENV HF_HUB_ENABLE_HF_TRANSFER=1

RUN hf download leejet/Z-Image-Turbo-GGUF z_image_turbo-Q4_K.gguf \
    --local-dir /models
    
RUN hf download unsloth/Qwen3-4B-Instruct-2507-GGUF Qwen3-4B-Instruct-2507-Q4_K_M.gguf \
    --local-dir /models
    
RUN hf download Comfy-Org/z_image_turbo split_files/vae/ae.safetensors \
    --local-dir /models  && \
    mv /models/split_files/vae/ae.safetensors /models/ae.safetensors && \
    rm -rf /models/split_files

COPY rp_handler.py /rp_handler.py
CMD ["python3", "-u", "/rp_handler.py"]
