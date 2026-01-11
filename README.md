# sdcpp-edit

A generic, secure, and high-performance sdcpp for RunPod Serverless, built on [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp).

## Features

*   **End-to-End Encryption**: Prompts are encrypted on the client, processed in memory, and the resulting image is encrypted before leaving the worker.
*   **Generic Model Loading**: The Docker image is model-agnostic. You define which models to load via Environment Variables.
*   **RunPod Cache Support**: Automatically detects if models are present in the RunPod Host Cache (`/runpod-volume/huggingface-cache/hub`) to enable instant cold starts.
*   **CUDA Optimized**: Compiled with cuBLAS for NVIDIA Turing (T4), Ampere (A10/A100), and Ada (L40/4090) architectures.

## Configuration (Environment Variables)

Configure these variables to tell the worker what to download and how to use it.

### 1. Model Definitions
**`MODELS`**
A comma-separated list of Hugging Face repositories and filenames to ensure are present (either via Cache or Download).
*   Format: `RepoID:Filename,RepoID:Filename`
*   Example:
    ```text
    leejet/Z-Image-Turbo-GGUF:z_image_turbo-Q4_K.gguf,unsloth/Qwen3-4B-Instruct-2507-GGUF:Qwen3-4B-Instruct-2507-Q4_K_M.gguf,Comfy-Org/z_image_turbo:split_files/vae/ae.safetensors
    ```

### 2. Pipeline Mapping
Map specific files to their roles using their **filenames**.

| Variable | Description | Example Value |
| :--- | :--- | :--- |
| `SD_DIFFUSION_FILE` | The main diffusion model (GGUF) | `z_image_turbo-Q4_K.gguf` |
| `SD_LLM_FILE` | The LLM used for prompt adherence (GGUF) | `Qwen3-4B-Instruct-2507-Q4_K_M.gguf` |
| `SD_VAE_FILE` | The VAE model (SafeTensors/GGUF) | `ae.safetensors` |

### 3. Settings & Security
| Variable | Description |
| :--- | :--- |
| `ENCRYPTION_KEY` | **Required.** 32-byte URL-safe base64 key for Fernet encryption. |
| `MODEL_DIR` | Directory to store models. Default: `/models` (Serverless) or `/workspace/models` (Interactive). |

## Deployment

This project uses a **single container image** (`:latest`) for both Serverless and Interactive modes. The behavior is controlled by the **CMD** command.

### Option A: Serverless (Production)
1.  Create a RunPod Serverless Endpoint.
2.  **Docker Command**: Leave Blank (Default).
    *   *The container runs `rp_handler.py` automatically.*
3.  Set Environment Variables defined above.

### Option B: Interactive Pod (Development)
1.  Deploy a GPU Pod.
2.  **Docker Command**: `/start.sh`
    *   *This script initializes models and keeps the container running for SSH.*
3.  Set Environment Variables (either in the template or via terminal after connecting).

## Testing Locally (or via SSH)

You can test the handler logic without deploying a serverless endpoint using the included `test_local.py`.

1.  **Connect to your Pod** via SSH.
2.  **Export variables**:
    ```bash
    export ENCRYPTION_KEY="your_matching_key_here"
    export MODEL_DIR="/workspace/models" # Important for interactive pods
    
    # Define models
    export MODELS="leejet/Z-Image-Turbo-GGUF:z_image_turbo-Q4_K.gguf,..."
    
    # Map files
    export SD_DIFFUSION_FILE="z_image_turbo-Q4_K.gguf"
    export SD_LLM_FILE="Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
    export SD_VAE_FILE="ae.safetensors"
    ```
3.  **Run the test**:
    ```bash
    python3 test_local.py
    ```
    *   This will encrypt a prompt, trigger `rp_handler.py`, generate an image to `/dev/shm`, encrypt it, and save the decrypted result to `test_output.png`.

## Directory Structure

*   `/usr/local/bin/sd`: The compiled binary.
*   `/utils.py`: Logic for checking RunPod Cache vs HF Download.
*   `/rp_handler.py`: Serverless entry point (Default CMD).
*   `/start.sh`: Interactive entry point (Optional CMD).
*   `/test_local.py`: Script for local integration testing.
