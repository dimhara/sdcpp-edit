# sdcpp-edit

This repository contains a robust, security-focused serverless handler for [stablediffusion.cpp](https://github.com/leejet/stable-diffusion.cpp) on RunPod. 

It is designed to be **argument-agnostic**: it accepts *any* command line argument string supported by the `sd` binary, making it compatible with SD1.5, SDXL, Flux, and specialized pipelines like Qwen-Image-Edit.

## Features

*   **Full CLI Flexibility:** Pass arguments exactly as you would in the terminal (e.g., `--diffusion-model`, `--offload-to-cpu`, `--flow-shift`).
*   **Secure In-Memory Processing:** Input and Output images are stored in `/dev/shm` (RAM disk), avoiding disk I/O latency. Input images are overwritten with zero-bytes before deletion.
*   **Universal Input Handling:** Supports standard `-i` inputs as well as reconstruction (`-r`) inputs via a placeholder token.
*   **End-to-End Encryption**: Prompts are encrypted on the client, processed in memory, and the resulting image is encrypted before leaving the worker.
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



---

## 1. Setup

### Server (`rp_handler.py`)
Ensure your Docker container has `stablediffusion.cpp` compiled. Set the environment variable in your Dockerfile or RunPod template:

```bash
ENV SD_BINARY_PATH="/usr/local/bin/sd"
```

### Client (`client.py`)
Update the top of `client.py` with your credentials:

```python
ENDPOINT_ID = "YOUR_ENDPOINT_ID"
API_KEY = "YOUR_API_KEY"
```

---

## 2. Usage

### The `{INPUT}` Placeholder
Different models use different flags for input images (e.g., standard SD uses `-i`, Qwen-Edit uses `-r`). 

*   **Mechanism:** When you send an image via the client, the server saves it to RAM.
*   **Usage:** Use `{INPUT}` in your argument string. The handler will replace `{INPUT}` with the actual path (`/dev/shm/input.png`).
*   **Fallback:** If you do not specify `{INPUT}` but send an image, the handler automatically appends `-i /dev/shm/input.png` to your arguments.

### Important: Absolute Paths
Since the handler runs in a specific directory, **always use absolute paths** for your models.
*   ❌ `--model ./qwen.gguf`
*   ✅ `--model /workspace/models/qwen.gguf`

---

## 3. Examples

### A. Qwen-Image-Edit (Complex Pipeline)
Qwen requires loading a Diffusion model, a VAE, and an LLM. It uses `-r` for the input image.

```bash
python client.py \
  "--diffusion-model /workspace/models/qwen-image-edit-2511-Q4_K_M.gguf \
   --vae /workspace/models/qwen_image_vae.safetensors \
   --llm /workspace/models/qwen_2.5_vl_7b.safetensors \
   --sampling-method euler -v --offload-to-cpu --diffusion-fa --flow-shift 3 \
   -r {INPUT} \
   -p 'change red to blue' \
   --qwen-image-zero-cond-t --steps 4 --cfg-scale 1.0" \
  --img ./local_photo.png \
  --out result.png
```

### B. Using LoRAs
Use `--lora-model-dir` to point to your folder, and invoke the LoRA in the prompt using angle brackets.

**Note:** Watch your quoting! Wrap the whole argument string in double quotes `"` and the prompt in single quotes `'`.

```bash
python client.py \
  "--diffusion-model /workspace/models/sd-v1-5.gguf \
   --lora-model-dir /workspace/models/loras \
   -p 'a photograph of a cat <lora:pixel-art:1.0>' \
   --steps 20" \
  --out cat_pixel.png
```

### C. Standard Text-to-Image (No Input Image)

```bash
python client.py \
  "-p 'a futuristic cyberpunk city' --steps 20 -v" \
  --out city.png
```

### D. Standard Image-to-Image (Implicit -i)
If you don't use `{INPUT}`, the handler appends `-i` automatically.

```bash
python client.py \
  "-p 'make it anime style' --strength 0.4" \
  --img ./photo.jpg \
  --out anime.png
```

---

## 4. Local Testing (`test_local.py`)

You can test the handler inside your running Pod (via SSH or Web Terminal) without triggering an API call. This is useful for debugging paths and memory issues.

1.  SSH into your Pod.
2.  Run the test script:

```bash
python3 test_local.py \
  --img test_input.png \
  --out test_result.png \
  --args "--diffusion-model /workspace/models/qwen.gguf ... -r {INPUT} -p 'test'"
```

This verifies:
1.  Image saving to `/dev/shm`.
2.  Argument parsing and `{INPUT}` replacement.
3.  Binary execution.
4.  Secure deletion of the input file.

---

## 5. Security Details

This handler is designed for privacy:
1.  **RAM-Only:** Input and Output images are written to `/dev/shm`, which is a RAM disk. Data is never written to persistent storage (HDD/SSD).
2.  **Secure Wipe:** After execution (success or failure), the `secure_delete` function overwrites the input file with `\x00` (zeros) before unlinking the file, ensuring the image data is unrecoverable from memory buffers.



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

