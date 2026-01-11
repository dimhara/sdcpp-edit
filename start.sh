#!/bin/bash

# Enable fast download transfer
export HF_HUB_ENABLE_HF_TRANSFER=1
MODEL_DIR="/workspace/models"

mkdir -p $MODEL_DIR

echo "---------------------------------------------------"
echo "Initializing Models from Environment Variable..."
echo "MODELS: $MODELS"
echo "---------------------------------------------------"

# Use the shared utils script to download/cache/link models
python3 /utils.py "$MODEL_DIR"

echo "---------------------------------------------------"
echo "Models ready in $MODEL_DIR"
echo "---------------------------------------------------"
echo "Example Command (Update filenames as needed):"
echo 'sd --diffusion-model models/z_image_turbo-Q4_K.gguf --vae models/ae.safetensors --llm models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf -p "test" -o out.png'
echo "---------------------------------------------------"

# Keep container running
sleep infinity
