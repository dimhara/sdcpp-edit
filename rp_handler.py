import runpod
import subprocess
import os
import base64
import shlex
import sys
import json
from cryptography.fernet import Fernet

# CONFIGURATION
SD_BINARY_PATH = os.environ.get("SD_BINARY_PATH", "/usr/local/bin/sd")
OUTPUT_PATH = "/dev/shm/output.png"
INPUT_PATH = "/dev/shm/input.png"
INPUT_PLACEHOLDER = "{INPUT}"

# SECURITY KEY
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")

def secure_delete(path):
    """Overwrites file with zeros before deletion."""
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

def ensure_models_downloaded():
    """Checks/Downloads models on Cold Start."""
    if os.path.exists("/workspace/models") or os.path.exists("/models"):
        return # Assume ready
    print("--- 📥 Triggering Model Download (utils.py) ---")
    try:
        subprocess.run(["python", "utils.py"], check=False)
    except Exception as e:
        print(f"Warning: Model setup check failed: {e}")

def handler(job):
    # 1. DECRYPT PAYLOAD
    try:
        if not ENCRYPTION_KEY:
            return {"status": "error", "message": "Server ENCRYPTION_KEY not set."}
        
        f = Fernet(ENCRYPTION_KEY.encode())
        encrypted_input = job['input'].get('encrypted_input')
        
        if not encrypted_input:
            return {"status": "error", "message": "No encrypted_input found."}

        # Decrypt -> JSON Decode
        decrypted_json_str = f.decrypt(encrypted_input.encode()).decode()
        job_input = json.loads(decrypted_json_str)
        
    except Exception as e:
        # We print a generic error, but NOT the payload content
        print("Security Error: Decryption failed.")
        return {"status": "error", "message": "Decryption failed or invalid key."}

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

        # 5. EXECUTE (SECURE LOGGING)
        # We do NOT print 'final_cmd' to avoid leaking prompts to system logs
        print(f"--- 🚀 Starting Diffusion Process ({len(final_args)} args) ---")

        result = subprocess.run(
            final_cmd,
            capture_output=True, # Capture stdout/stderr internally
            text=True,
            check=False
        )

        # 6. RETURN RESULT
        # Stdout/Stderr is returned to the client inside the encrypted HTTPS response
        # It is NOT printed to the RunPod system log.
        
        response = {
            "stdout": result.stdout,
            "stderr": result.stderr
        }

        if result.returncode != 0:
            print("--- ❌ Binary Execution Failed (See client response for details) ---")
            response["status"] = "error"
            response["message"] = "Binary execution failed"
        else:
            if os.path.exists(OUTPUT_PATH):
                with open(OUTPUT_PATH, "rb") as image_file:
                    response["image"] = base64.b64encode(image_file.read()).decode('utf-8')
                response["status"] = "success"
                print("--- ✅ Generation Success ---")
            else:
                response["status"] = "error"
                response["message"] = "No output image generated"
                print("--- ⚠️ Finished, but no output file found ---")
        
        return response

    except Exception as e:
        print(f"--- 💥 Handler Exception: {str(e)} ---")
        return {"status": "error", "message": str(e)}
    finally:
        cleanup()

if __name__ == "__main__":
    ensure_models_downloaded()
    if not os.path.exists(SD_BINARY_PATH):
        print(f"Error: Binary not found at {SD_BINARY_PATH}")
        sys.exit(1)
    runpod.serverless.start({"handler": handler})
