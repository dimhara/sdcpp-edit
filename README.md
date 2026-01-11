# sdcpp-edit

A generic, secure, and high-performance sdcpp pipeline for RunPod Serverless, built on [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp).

## Features

*   **End-to-End Encryption**: Prompts are encrypted on the client, processed in memory, and the resulting image is encrypted before leaving the worker.
*   **Generic Model Loading**: The Docker image is model-agnostic. You define which models to load via Environment Variables.
*   **RunPod Cache Support**: Automatically detects if models are present in the RunPod Host Cache (`/runpod-volume/huggingface-cache/hub`) to enable instant cold starts. If not found, it downloads them automatically.
*   **CUDA Optimized**: Compiled with cuBLAS for NVIDIA Turing (T4), Ampere (A10/A100), and Ada (L40/4090) architectures.

## Configuration (Environment Variables)

When deploying this image on RunPod (Serverless or Pod), you must configure the following Environment Variables. This tells the worker what to download and how to use it.

### 1. Model Definitions
**`MODELS`**
A comma-separated list of Hugging Face repositories and filenames to ensure are present (either via Cache or Download).
*   Format: `RepoID:Filename,RepoID:Filename`
*   Example:
    ```text
    leejet/Z-Image-Turbo-GGUF:z_image_turbo-Q4_K.gguf,unsloth/Qwen3-4B-Instruct-2507-GGUF:Qwen3-4B-Instruct-2507-Q4_K_M.gguf,Comfy-Org/z_image_turbo:split_files/vae/ae.safetensors
    ```

### 2. Pipeline Mapping
Since `MODELS` is just a list of files, you must explicitly tell `sdcpp` which file serves which role in the pipeline. Use the **filename** (basename) only.

| Variable | Description | Example Value |
| :--- | :--- | :--- |
| `SD_DIFFUSION_FILE` | The main diffusion model (GGUF) | `z_image_turbo-Q4_K.gguf` |
| `SD_LLM_FILE` | The LLM used for prompt adherence (GGUF) | `Qwen3-4B-Instruct-2507-Q4_K_M.gguf` |
| `SD_VAE_FILE` | The VAE model (SafeTensors/GGUF) | `ae.safetensors` |

### 3. Security
**`ENCRYPTION_KEY`**
A 32-byte URL-safe base64-encoded key used for Fernet symmetric encryption.
*   Generate one locally using Python:
    ```python
    from cryptography.fernet import Fernet
    print(Fernet.generate_key().decode())
    ```
*   **Important:** This same key must be used in your local `client.py`.

## Deployment

### Option A: Serverless (Production)
Use the `ghcr.io/dimhara/dimhara-sdcpp-edit:serverless` image.

1.  Create a RunPod Serverless Endpoint.
2.  Select the Docker Image.
3.  Enter the Environment Variables defined above.
4.  (Optional) Enable **FlashBoot** or **Model Caching** in RunPod settings for faster startups. The `utils.py` script automatically checks the specific RunPod cache paths.

### Option B: Interactive Pod (Development)
Use the `ghcr.io/dimhara/dimhara-sdcpp-edit:latest` image.

1.  Deploy a GPU Pod.
2.  Set the environment variables in the template (or export them in the terminal).
3.  The container starts `start.sh`, which will:
    *   Parse `MODELS`.
    *   Check runpod cache: `/runpod-volume/huggingface-cache`.
    *   Download missing files to `/workspace/models`.
4.  Connect via Web Terminal or SSH and run the `sd` command manually.

## Client Usage

Use `client.py` to interact with the endpoint securely.

```bash
# Install dependencies
pip install requests cryptography

# Run generation
python client.py "A cyberpunk city in the rain, neon lights" output.png
```

**Note:** You must edit `client.py` to set `API_KEY`, `ENDPOINT_ID`, and the matching `ENCRYPTION_KEY`.

## Directory Structure

*   `/usr/local/bin/sd`: The compiled binary.
*   `/utils.py`: Logic for checking RunPod Cache vs HF Download.
*   `/rp_handler.py`: Serverless entry point.
*   `/start.sh`: Interactive entry point.
