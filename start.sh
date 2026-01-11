#!/bin/bash

# Enable fast download transfer
export HF_HUB_ENABLE_HF_TRANSFER=1

mkdir -p /workspace/models
cd /workspace/models

# --- MODEL 1: Diffusion Model (Z-Image Turbo) ---
if [ ! -f "z_image_turbo-Q4_K.gguf" ]; then
    echo "Downloading Diffusion Model..."
    hf download leejet/Z-Image-Turbo-GGUF z_image_turbo-Q4_K.gguf --local-dir .
else
    echo "Diffusion Model found. Skipping download."
fi

# --- MODEL 2: LLM (Qwen) ---
if [ ! -f "Qwen3-4B-Instruct-2507-Q4_K_M.gguf" ]; then
    echo "Downloading LLM..."
    hf download unsloth/Qwen3-4B-Instruct-2507-GGUF Qwen3-4B-Instruct-2507-Q4_K_M.gguf \
        --local-dir .
else
    echo "LLM found. Skipping download."
fi

# --- MODEL 3: VAE ---
if [ ! -f "ae.safetensors" ]; then
    echo "Downloading VAE..."
    # We download to a temp folder to handle the subdirectory structure
    hf download Comfy-Org/z_image_turbo split_files/vae/ae.safetensors \
        --local-dir .
    echo "Moving VAE to models root..."
    mv split_files/vae/ae.safetensors .
    rm -rf split_files
else
    echo "VAE found. Skipping download."
fi

echo "---------------------------------------------------"
echo "All models ready in /workspace/models/"
echo "---------------------------------------------------"
echo "Example Command:"
echo 'sd --diffusion-model models/z_image_turbo-Q4_K.gguf --vae models/ae.safetensors --llm models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf -p "a beautiful castle on a hill" --cfg-scale 1.0 --diffusion-fa -H 1024 -W 512 -o output.png'
echo "---------------------------------------------------"

# Keep container running
sleep infinity
