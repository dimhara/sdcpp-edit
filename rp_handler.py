import runpod
import subprocess
import os
import base64
import shlex
import sys

# CONFIGURATION
SD_BINARY_PATH = os.environ.get("SD_BINARY_PATH", "/usr/local/bin/sd")

# STORAGE (RAM Disk - Security)
OUTPUT_PATH = "/dev/shm/output.png"
INPUT_PATH = "/dev/shm/input.png"

# TOKEN to look for in arguments to replace with actual path
INPUT_PLACEHOLDER = "{INPUT}"

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
        except Exception as e:
            print(f"Warning: Failed to secure delete {path}: {e}")
            if os.path.exists(path):
                os.remove(path)

def cleanup():
    secure_delete(INPUT_PATH)
    secure_delete(OUTPUT_PATH)

def save_input_image(b64_string):
    try:
        with open(INPUT_PATH, "wb") as f:
            f.write(base64.b64decode(b64_string))
        return True
    except Exception as e:
        print(f"Error saving input image: {e}")
        return False

def encode_output_image():
    if not os.path.exists(OUTPUT_PATH):
        return None
    with open(OUTPUT_PATH, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def handler(job):
    job_input = job['input']
    cmd_args_input = job_input.get('cmd_args', "")
    
    # Parse arguments into a list
    if isinstance(cmd_args_input, str):
        args = shlex.split(cmd_args_input)
    elif isinstance(cmd_args_input, list):
        args = cmd_args_input
    else:
        return {"error": "cmd_args must be a string or list"}

    cleanup() # Clean slate

    try:
        # Handle Input Image
        has_input_image = False
        if 'init_image' in job_input and job_input['init_image']:
            if save_input_image(job_input['init_image']):
                has_input_image = True
            else:
                return {"status": "error", "message": "Failed to write image to RAM."}

        # Argument Substitution Logic
        # 1. Check if user explicitly put "{INPUT}" in their command string
        # 2. If yes, replace it with the actual /dev/shm path
        # 3. If no, but an image was provided, append standard "-i" flag
        
        final_args = []
        replaced_placeholder = False

        for arg in args:
            if arg == INPUT_PLACEHOLDER:
                if has_input_image:
                    final_args.append(INPUT_PATH)
                    replaced_placeholder = True
                else:
                    return {"status": "error", "message": "Command used {INPUT} placeholder but no image provided."}
            else:
                final_args.append(arg)

        # Fallback: User sent image but didn't specify where it goes -> assume standard -i
        if has_input_image and not replaced_placeholder:
            final_args = final_args + ["-i", INPUT_PATH]

        # Force Output Path
        # We assume the binary accepts -o. If your binary uses something else, 
        # you can add an {OUTPUT} placeholder logic similar to above.
        final_cmd = [SD_BINARY_PATH] + final_args + ["-o", OUTPUT_PATH]

        print(f"Executing: {' '.join(final_cmd)}")

        result = subprocess.run(
            final_cmd,
            capture_output=True,
            text=True,
            check=False # We handle return codes manually to capture stderr
        )

        if result.returncode != 0:
             return {
                "status": "error",
                "message": "Binary returned non-zero exit code",
                "stderr": result.stderr,
                "stdout": result.stdout
            }
        
        img_b64 = encode_output_image()
        
        if img_b64:
            return {
                "status": "success",
                "image": img_b64,
                "stdout": result.stdout
            }
        else:
            return {
                "status": "error",
                "message": "No output image generated.",
                "stderr": result.stderr,
                "stdout": result.stdout
            }

    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        cleanup() # Secure wipe


def ensure_models_downloaded():
    """
    Runs utils.py to download models if they don't exist.
    """
    print("--- Checking/Downloading Models ---")
    try:
        subprocess.run(["python3", "utils.py"], check=True)
        print("--- Model Download/Setup Complete ---")
    except subprocess.CalledProcessError as e:
        print(f"CRITICAL: Failed to download models using utils.py. Error: {e}")
    except Exception as e:
        print(f"CRITICAL: Unexpected error during model setup: {e}")

if __name__ == "__main__":
    ensure_models_downloaded()
    runpod.serverless.start({"handler": handler})
