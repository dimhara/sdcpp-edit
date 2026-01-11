import runpod
import subprocess
import os
import base64
import uuid
from cryptography.fernet import Fernet

# --- CONFIGURATION ---
# In production, pass this via RunPod Env Variables. For now, hardcoding or reading env.
# MUST match the key generated in Step 0
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "YOUR_GENERATED_KEY_HERE").encode()
cipher_suite = Fernet(ENCRYPTION_KEY)

# Paths to the baked-in models
BINARY_PATH = "/usr/local/bin/sd"
MODEL_DIR = "/models"
DIFFUSION_MODEL = os.path.join(MODEL_DIR, "z_image_turbo-Q4_K.gguf")
LLM_MODEL = os.path.join(MODEL_DIR, "Qwen3-4B-Instruct-2507-Q4_K_M.gguf")
VAE_MODEL = os.path.join(MODEL_DIR, "ae.safetensors")
OUTPUT_DIR = "/tmp"

def handler(job):
    job_input = job['input']
    
    # --- 1. DECRYPT THE PROMPT ---
    encrypted_prompt = job_input.get("encrypted_prompt")
    
    if not encrypted_prompt:
        return {"error": "No encrypted_prompt provided"}

    try:
        # Decrypt: bytes -> bytes -> decode to string
        prompt = cipher_suite.decrypt(encrypted_prompt.encode()).decode()
        print("Prompt decrypted successfully") # Don't print the actual prompt to logs!
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
        "--diffusion-model", DIFFUSION_MODEL,
        "--vae", VAE_MODEL,
        "--llm", LLM_MODEL,
        "-p", prompt,  # Using the decrypted prompt
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
            
            # --- 2. ENCRYPT THE IMAGE ---
            # Instead of standard base64, we encrypt the raw bytes first
            encrypted_image_bytes = cipher_suite.encrypt(raw_image_bytes)
            
            # Convert encrypted bytes to string for JSON transport
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
