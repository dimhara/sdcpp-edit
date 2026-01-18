# ==========================================
# STAGE 1: BUILDER
# Compiles the C++ code (cached).
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
# STAGE 2: RUNTIME
# ==========================================
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04 AS final
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 1. Install Runtime Deps + Python + Pip
RUN apt-get update && apt-get install -y \
    wget curl git libgomp1 libcurl4 openssh-server \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 2. Copy binary from builder (Rename sd-cli -> sd)
COPY --from=builder /app/stable-diffusion.cpp/build/bin/sd-cli /usr/local/bin/sd

# 3. Install Python Dependencies
RUN pip3 install --no-cache-dir runpod huggingface_hub cryptography

# 4. Setup Directories
# /models = Default for Serverless
# /workspace = Default for Interactive
RUN mkdir -p /models && mkdir -p /workspace

# 5. Environment Variables
ENV HF_HUB_ENABLE_HF_TRANSFER=1
ENV MODEL_DIR=/models

# 6. Copy Scripts
WORKDIR /
COPY utils.py /utils.py
COPY rp_handler.py /rp_handler.py
COPY start.sh /start.sh
RUN chmod +x /start.sh

# DEFAULT CMD: Serverless Handler
# For Interactive: Override Docker Command to ["/start.sh"]
CMD ["python3", "-u", "/rp_handler.py"]
