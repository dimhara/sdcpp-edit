import runpod
import subprocess
import os
import base64
import shlex
import sys
import json
import time
from cryptography.fernet import Fernet

# CONFIGURATION
SD_BINARY_PATH = os.environ.get("SD_BINARY_PATH", "/usr/local/bin/sd")
OUTPUT_PATH = "/dev/shm/output.png"
INPUT_PATH = "/dev/shm/input.png"
INPUT_PLACEHOLDER = "{INPUT}"

# SECURITY KEY
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")

def secure_delete(path):
    if os.path.exists(path):
        try:
            length = os.path.getsize(path)
            with open(path, "wb") as f:
                f.write(b'\0' * length)
                f.flush()
                os.fsync(f.fileno())
            os.remove(path)
        except Exception:
            if os.path.exists(path): os.remove(path)

def cleanup():
    secure_delete(INPUT_PATH)
    secure_delete(OUTPUT_PATH)

def list_directory(path):
    """Helper to print dir contents to logs"""
    if os.path.exists(path):
        print(f"📁 Listing {path}:", flush=True)
        try:
            print(os.listdir(path), flush=True)
        except Exception as e:
            print(f"Error reading {path}: {e}", flush=True)
    else:
        print(f"❌ Path not found: {path}", flush=True)

def ensure_models_downloaded():
    """Checks/Downloads models on Cold Start."""
    
    # TARGET DIRECTORY FOR SERVERLESS
    model_dir = "/models"

    # Check if directory exists AND is not empty
    if os.path.exists(model_dir) and len(os.listdir(model_dir)) > 0:
        print(f"--- ✅ Found files in {model_dir}, skipping download. ---", flush=True)
        return 

    print(f"--- 📥 Triggering Model Download to {model_dir} (utils.py) ---", flush=True)
    try:
        # Stream output so you don't stare at a blank log
        process = subprocess.Popen(
            ["python", "utils.py"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(f"[utils.py] {output.strip()}", flush=True)
                
        rc = process.poll()
        if rc != 0:
            print(f"CRITICAL: utils.py failed with return code {rc}", flush=True)
            # Print stderr if it failed
            print(f"STDERR: {process.stderr.read()}", flush=True)
        else:
            print("--- ✅ Model Download Complete ---", flush=True)

    except Exception as e:
        print(f"CRITICAL: Failed to execute utils.py: {e}", flush=True)

def handler(job):
    # 1. DECRYPT PAYLOAD
    try:
        if not ENCRYPTION_KEY:
            return {"status": "error", "message": "Server ENCRYPTION_KEY not set."}
        
        f = Fernet(ENCRYPTION_KEY.encode())
        encrypted_input = job['input'].get('encrypted_input')
        
        if not encrypted_input:
            return {"status": "error", "message": "No encrypted_input found."}

        decrypted_json_str = f.decrypt(encrypted_input.encode()).decode()
        job_input = json.loads(decrypted_json_str)
        
    except Exception as e:
        print("Security Error: Decryption failed.", flush=True)
        return {"status": "error", "message": "Decryption failed or invalid key."}

    # --- 🔍 DEBUG TRAP DOOR START ---
    if job_input.get("debug_sleep") is True:
        print("\n\n=== 🕵️ DEBUG SLEEP MODE ACTIVATED ===", flush=True)
        print("Printing File System State...", flush=True)
        
        list_directory("/workspace")
        list_directory("/workspace/models")
        list_directory("/models")
        list_directory(".") # Current dir
        
        print("\n=== ENTERING INFINITE SLEEP ===", flush=True)
        print("You can now SSH into this worker.", flush=True)
        
        while True:
            time.sleep(60)
            # Keeping connection alive
    # --- DEBUG TRAP DOOR END ---

    # 2. PARSE ARGUMENTS
    cmd_args_input = job_input.get('cmd_args', "")
    if isinstance(cmd_args_input, str):
        args = shlex.split(cmd_args_input)
    elif isinstance(cmd_args_input, list):
        args = cmd_args_input
    else:
        return {"error": "cmd_args must be a string or list"}

    cleanup()

    try:
        # 3. SAVE INPUT IMAGE
        has_input_image = False
        if 'init_image' in job_input and job_input['init_image']:
            try:
                with open(INPUT_PATH, "wb") as f:
                    f.write(base64.b64decode(job_input['init_image']))
                has_input_image = True
            except Exception as e:
                return {"status": "error", "message": "Failed to write secure input image."}

        # 4. CONSTRUCT COMMAND
        final_args = []
        replaced_placeholder = False

        for arg in args:
            if arg == INPUT_PLACEHOLDER:
                if has_input_image:
                    final_args.append(INPUT_PATH)
                    replaced_placeholder = True
                else:
                    return {"status": "error", "message": "{INPUT} used but no image sent."}
            else:
                final_args.append(arg)

        if has_input_image and not replaced_placeholder:
            final_args = final_args + ["-i", INPUT_PATH]

        final_cmd = [SD_BINARY_PATH] + final_args + ["-o", OUTPUT_PATH]

        # 5. EXECUTE
        result = subprocess.run(
            final_cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        response = {
            "stdout": result.stdout,
            "stderr": result.stderr
        }

        if result.returncode != 0:
            response["status"] = "error"
            response["message"] = "Binary execution failed"
        else:
            if os.path.exists(OUTPUT_PATH):
                with open(OUTPUT_PATH, "rb") as image_file:
                    response["image"] = base64.b64encode(image_file.read()).decode('utf-8')
                response["status"] = "success"
            else:
                response["status"] = "error"
                response["message"] = "No output image generated"
        
        return response

    except Exception as e:
        print(f"Handler Exception: {str(e)}", flush=True)
        return {"status": "error", "message": str(e)}
    finally:
        cleanup()

if __name__ == "__main__":
    # Ensure logs flush immediately
    sys.stdout.reconfigure(line_buffering=True)
    ensure_models_downloaded()
    if not os.path.exists(SD_BINARY_PATH):
        print(f"Error: Binary not found at {SD_BINARY_PATH}", flush=True)
        sys.exit(1)
    runpod.serverless.start({"handler": handler})
