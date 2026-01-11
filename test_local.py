"""
=============================================================================
LOCAL / INTERACTIVE TEST SCRIPT
=============================================================================
Use this script to test rp_handler.py inside an Interactive RunPod session
 or locally.

It mimics the RunPod Serverless behavior by:
1. Setting up the necessary environment variables.
2. Encrypting a prompt (Acting as Client).
3. Invoking the handler directly (Acting as Server).
4. Decrypting the result (Acting as Client).

--- SETUP INSTRUCTIONS ---

1. Install Dependencies (should be installed in the docker image):
   pip install cryptography runpod huggingface_hub

2. Set Environment Variables in your terminal or runpod:

   # A. Set the Encryption Key (Must match the one used in this script below)
   export ENCRYPTION_KEY="YOUR_GENERATED_KEY_HERE"

   # B. Define the Models to Download/Check. Format is modelpath:filepath,...
   export MODELS="leejet/Z-Image-Turbo-GGUF:z_image_turbo-Q4_K.gguf,unsloth/Qwen3-4B-Instruct-2507-GGUF:Qwen3-4B-Instruct-2507-Q4_K_M.gguf,Comfy-Org/z_image_turbo:split_files/vae/ae.safetensors"

   # C. Set the Directory (In interactive RunPod, use /workspace/models)
   export MODEL_DIR="/workspace/models"

   # D. Map the files (Optional if defaults match, but recommended)
   export SD_DIFFUSION_FILE="z_image_turbo-Q4_K.gguf"
   export SD_LLM_FILE="Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
   export SD_VAE_FILE="ae.safetensors"

3. Run the Test:
   python3 test_local.py
=============================================================================
"""

import os
import sys
import uuid
from cryptography.fernet import Fernet

# Ensure we can import rp_handler from the current directory
sys.path.append(os.getcwd())

# --- 1. SETUP SECURITY (MOCKING CLIENT) ---
key_str = os.environ.get("ENCRYPTION_KEY")
if not key_str:
    print("❌ Error: ENCRYPTION_KEY env var not set.")
    print("Run: export ENCRYPTION_KEY='...'")
    sys.exit(1)

try:
    cipher_suite = Fernet(key_str.encode())
except Exception as e:
    print(f"❌ Error initializing encryption: {e}")
    sys.exit(1)

# --- 2. PREPARE INPUT (MOCKING RUNPOD API) ---
raw_prompt = "A futuristic city with neon lights, 8k resolution, cinematic lighting"
print(f"🔹 Encrypting Prompt: '{raw_prompt}'")

encrypted_prompt = cipher_suite.encrypt(raw_prompt.encode()).decode()

# This mimics the JSON payload RunPod sends to the handler
fake_job = {
    "id": str(uuid.uuid4()),
    "input": {
        "encrypted_prompt": encrypted_prompt,
        "width": 512,
        "height": 512, # Keep small for faster testing
        "steps": 6,
        "cfg_scale": 1.0,
        "seed": 42
    }
}

# --- 3. RUN HANDLER (MOCKING SERVER) ---
print("\n🔸 Importing rp_handler (This will trigger model checks)...")
try:
    import rp_handler
except ImportError:
    print("❌ Error: Could not import rp_handler.py. Are you in the right directory?")
    sys.exit(1)

print("\n🔸 Executing Handler...")
# This calls the actual logic used in production
result = rp_handler.handler(fake_job)

# --- 4. PROCESS RESULT (MOCKING CLIENT) ---
print("\n🔹 Processing Result...")

if isinstance(result, dict) and 'error' in result:
    print(f"❌ Job Failed: {result['error']}")
    if 'details' in result:
        print(f"   Details: {result['details']}")
        
elif isinstance(result, dict) and 'encrypted_image' in result:
    print("✅ Job Success! Encrypted image received.")
    
    try:
        encrypted_image_str = result['encrypted_image']
        decrypted_image_bytes = cipher_suite.decrypt(encrypted_image_str.encode())
        
        output_filename = "test_output.png"
        with open(output_filename, "wb") as f:
            f.write(decrypted_image_bytes)
            
        print(f"✅ Image saved successfully to: {os.path.abspath(output_filename)}")
        
    except Exception as e:
        print(f"❌ Decryption/Save Failed: {e}")
else:
    print(f"❌ Unknown response format: {result}")
