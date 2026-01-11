import runpod
import subprocess
import os
import uuid
import sys
from cryptography.fernet import Fernet
import utils # Import our new utils module

# --- CONFIGURATION ---
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "YOUR_GENERATED_KEY_HERE").encode()
cipher_suite = Fernet(ENCRYPTION_KEY)

BINARY_PATH = "/usr/local/bin/sd"
MODEL_DIR = "/models"
OUTPUT_DIR = "/tmp"

# --- DYNAMIC MODEL LOADER ---
# This runs once when the container starts (Cold Start)
try:
    # 1. Ensure models exist (Cache or Download)
    # Returns dict: {'filename.gguf': '/full/path/to/filename.gguf'}
    resolved_paths = utils.prepare_models(MODEL_DIR)

    # 2. Map generic file paths to SD specific arguments via Env Vars
    # The user must provide these env vars to tell us which file is which
    # Example Env: SD_DIFFUSION_FILE="z_image_turbo-Q4_K.gguf"
    
    diffusion_file = os.environ.get("SD_DIFFUSION_FILE", "z_image_turbo-Q4_K.gguf")
    llm_file = os.environ.get("SD_LLM_FILE", "Qwen3-4B-Instruct-2507-Q4_K_M.gguf")
    vae_file = os.environ.get("SD_VAE_FILE", "ae.safetensors")

    # Look up the absolute paths
    DIFFUSION_MODEL_PATH = resolved_paths.get(diffusion_file)
    LLM_MODEL_PATH = resolved_paths.get(llm_file)
    VAE_MODEL_PATH = resolved_paths.get(vae_file)
    
    # Fallback: if not in the list, assume it might be a direct path or user forgot to put it in MODELS
    if not DIFFUSION_MODEL_PATH: DIFFUSION_MODEL_PATH = os.path.join(MODEL_DIR, diffusion_file)
    if not LLM_MODEL_PATH: LLM_MODEL_PATH = os.path.join(MODEL_DIR, llm_file)
    if not VAE_MODEL_PATH: VAE_MODEL_PATH = os.path.join(MODEL_DIR, vae_file)

    print("--- Model Paths Configured ---")
    print(f"Diffusion: {DIFFUSION_MODEL_PATH}")
    print(f"LLM: {LLM_MODEL_PATH}")
    print(f"VAE: {VAE_MODEL_PATH}")

except Exception as e:
    print(f"CRITICAL: Model setup failed: {e}")
    sys.exit(1)


def handler(job):
    job_input = job['input']
    
    # --- DECRYPT PROMPT ---
    encrypted_prompt = job_input.get("encrypted_prompt")
    if not encrypted_prompt:
        return {"error": "No encrypted_prompt provided"}

    try:
        prompt = cipher_suite.decrypt(encrypted_prompt.encode()).decode()
    except Exception as e:
        return {"error": "Failed to decrypt prompt", "details": str(e)}

    # Standard params
    cfg_scale = str(job_input.get("cfg_scale", 1.0))
    width = str(job_input.get("width", 512))
    height = str(job_input.get("height", 1024))
    steps = str(job_input.get("steps", 8))
    seed = str(job_input.get("seed", -1))
    
    unique_id = str(uuid.uuid4())
    output_filename = f"{unique_id}.png"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    command = [
        BINARY_PATH,
        "--diffusion-model", DIFFUSION_MODEL_PATH,
        "--vae", VAE_MODEL_PATH,
        "--llm", LLM_MODEL_PATH,
        "-p", prompt,
        "--cfg-scale", cfg_scale,
        "--steps", steps,
        "-H", height,
        "-W", width,
        "--rng", "cuda",
        "--diffusion-fa",
        "-s", seed,
        "-o", output_path
    ]

    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if os.path.exists(output_path):
            with open(output_path, "rb") as image_file:
                raw_image_bytes = image_file.read()
            
            # Encrypt image
            encrypted_image_bytes = cipher_suite.encrypt(raw_image_bytes)
            encrypted_image_str = encrypted_image_bytes.decode('utf-8')
            
            os.remove(output_path)

            return {
                "status": "success",
                "encrypted_image": encrypted_image_str
            }
        else:
            return {"error": "Output file missing"}

    except Exception as e:
        return {"error": str(e)}

if __name__ == '__main__':
    runpod.serverless.start({"handler": handler})
