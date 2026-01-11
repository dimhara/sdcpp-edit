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

# Architectures: 75 (Turing), 86 (Ampere), 89 (Ada)
RUN cmake .. -DSD_CUDA=ON -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES="75;86;89" && \
    cmake --build . --config Release -- -j$(nproc)

# ==========================================
# STAGE 2: BASE RUNTIME (Shared)
# ==========================================

FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04 AS base_runtime
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 1. Install Runtime Deps + Python + Pip
RUN apt-get update && apt-get install -y \
    wget curl git libgomp1 libcurl4 \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Copy binary from builder (note "sd-cli" is renamed to "sd")

COPY --from=builder /app/stable-diffusion.cpp/build/bin/sd-cli /usr/local/bin/sd
# ==========================================
# STAGE 3: FULL (Web Terminal / Dev)
# ==========================================
FROM base_runtime AS full

# Install CLI tools and util deps
RUN pip3 install -U huggingface_hub

WORKDIR /workspace
COPY utils.py /utils.py
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

# Create model directory (will be populated at runtime)
RUN mkdir -p /models
ENV HF_HUB_ENABLE_HF_TRANSFER=1

ENV MODEL_DIR=/models

# Copy logic files
COPY utils.py /utils.py
COPY rp_handler.py /rp_handler.py

CMD ["python3", "-u", "/rp_handler.py"]
