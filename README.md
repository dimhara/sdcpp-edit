# sdcpp-edit: Secure Serverless container for "Stable Diffusion C++"

A robust, security-focused serverless handler for [stablediffusion.cpp](https://github.com/leejet/stable-diffusion.cpp) running on RunPod.

It is designed to be **argument-agnostic**: it accepts *any* command line argument string supported by the `sd` binary, making it compatible with SD1.5, SDXL, Flux, and specialized pipelines like Qwen-Image-Edit.

## 🚀 Features

*   **Async & Resumable:** Uses RunPod's asynchronous API (`/run`) with client-side polling. If your client crashes or disconnects, you can resume the session using the Job ID.
*   **End-to-End Encryption:** Prompts and images are encrypted **locally** on the client before being sent. The server processes them in memory and returns encrypted results.
*   **Secure In-Memory Processing:** Input and Output images are stored in `/dev/shm` (RAM disk), avoiding disk I/O latency. Input images are overwritten with zero-bytes before deletion.
*   **Universal Input Handling:** Supports standard `-i` inputs as well as reconstruction (`-r`) inputs via a placeholder token (`{INPUT}`).
*   **RunPod Cache Support:** Automatically detects if models are present in the RunPod Host Cache (`/runpod-volume/huggingface-cache/hub`) to enable instant cold starts.
*   **CUDA Optimized:** Compiled with cuBLAS for NVIDIA Turing (T4), Ampere (A10/A100), and Ada (L40/4090) architectures.

---

## 🛠️ Setup

### 1. Server Configuration
Deploy the container on RunPod Serverless. You must set the following **Environment Variables**:

| Variable | Description | Example |
| :--- | :--- | :--- |
| `ENCRYPTION_KEY` | **Required.** 32-byte URL-safe base64 key for Fernet encryption. | `YOUR_GENERATED_KEY` |
| `MODELS` | Comma-separated list of Hugging Face models to download/cache. Format: `RepoID:Filename` | `leejet/sd-v1-5:model.gguf` |
| `SD_BINARY_PATH` | Path to the binary (Default provided in Dockerfile). | `/usr/local/bin/sd` |

### 2. Client Configuration
Open `client.py` and update the configuration section at the top:

```python
ENDPOINT_ID = "YOUR_ENDPOINT_ID"
API_KEY = "YOUR_API_KEY"
ENCRYPTION_KEY = "YOUR_GENERATED_KEY"  # Must match Server
```

---

## 💻 Usage

### Basic Command Structure
The client accepts a raw argument string for the `sd` binary.

```bash
python client.py "ARGUMENTS_HERE" --out result.png
```

### 1. Image-to-Image (with Input)
Use the `{INPUT}` placeholder to tell the handler where to inject the uploaded image path.

**Example: Qwen-Image-Edit**
```bash
python client.py \
  "--diffusion-model /models/qwen-image-edit.gguf \
   --vae /models/qwen_vae.safetensors \
   --llm /models/qwen_llm.gguf \
   -r {INPUT} \
   -p 'change red to blue' \
   --steps 4" \
  --img ./local_photo.png \
  --out result.png
```

**Example: Standard SD Img2Img**
If you don't specify `{INPUT}`, the handler automatically appends `-i [path]`.
```bash
python client.py \
  "-p 'anime style' --strength 0.4" \
  --img ./photo.jpg \
  --out anime.png
```

### 2. Text-to-Image (No Input)
```bash
python client.py \
  "-p 'a futuristic cyberpunk city' --steps 20 -v" \
  --out city.png
```

### 3. Resuming a Job
If your client script crashes, internet disconnects, or you accidentally close the terminal, the job continues running on the server. You can retrieve the result using the Job ID printed at the start of the previous run.

```bash
# No need to provide prompt/image arguments when resuming
python client.py --resume-id "123-abc-456-def" --out recovered_image.png
```

---


## 📦 Model Management

The container uses a smart download system via `utils.py`.

### The `MODELS` Variable
Configure the `MODELS` environment variable to ensure specific files are available.
*   **Format:** `User/Repo:Filename,User/Repo:Filename`
*   **Behavior:**
    1.  Checks `/runpod-volume/huggingface-cache` (Host Cache).
    2.  Checks `/models` (Container).
    3.  Downloads from HuggingFace if missing.

**Example Value:**
```text
leejet/Z-Image-Turbo-GGUF:z_image_turbo-Q4_K.gguf,unsloth/Qwen3-4B-Instruct-GGUF:Qwen3.gguf
```

### Baked vs. Dynamic
*   **Dynamic:** Use the standard Docker image and set `MODELS` in the RunPod console. Great for flexibility.
*   **Baked:** Use `Dockerfile.baked` to build a container with models pre-included (faster start time, larger image size).

---

## 🐛 Debugging

### SSH Debugging (Interactive)
If you need to debug paths or memory:
1.  Deploy the pod with `START_SSH=true` (or use the provided `start.sh` in Interactive template).
2.  SSH into the pod.
3.  Run the local test script to bypass the API and encryption layers:
    ```bash
    python3 test_local.py --img test.png --out result.png --args "... -p 'test'"
    ```

### Logs
*   **Server Logs:** Will show "Encrypted input received" and status updates (Downloading models, etc.). They will **not** show prompts.
*   **Client Logs:** Shows polling status and errors.
