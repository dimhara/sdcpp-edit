import argparse
import requests
import base64
import os
import json
import time
from cryptography.fernet import Fernet

# ==============================================================================
# CONFIGURATION
# ==============================================================================
ENDPOINT_ID = "YOUR_ENDPOINT_ID"
API_KEY = "YOUR_API_KEY"

# We use the /run endpoint (async) instead of /runsync (blocking)
BASE_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# SECURITY - Must match the Server's ENCRYPTION_KEY
# This ensures that even the RunPod API infrastructure cannot read your prompts.
ENCRYPTION_KEY = "YOUR_GENERATED_KEY_HERE"

# ==============================================================================
# HELPERS
# ==============================================================================

def encode_file(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Input image not found: {path}")
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def encrypt_payload(payload_dict):
    """
    Encrypts the JSON payload locally so no plaintext leaves this machine.
    """
    try:
        f = Fernet(ENCRYPTION_KEY.encode())
        json_bytes = json.dumps(payload_dict).encode()
        encrypted_token = f.encrypt(json_bytes).decode()
        return encrypted_token
    except Exception as e:
        print(f"❌ Encryption Error: {e}")
        print("Check if your ENCRYPTION_KEY is correct (32-byte base64).")
        exit(1)

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Secure Async Client for SDCPP")
    parser.add_argument("sd_args", help="Arguments passed to sd binary (e.g. -p 'prompt')")
    parser.add_argument("--img", help="Path to input image (optional)")
    parser.add_argument("--out", default="output.png", help="Path to save output image")
    parser.add_argument("--poll-interval", type=int, default=2, help="Seconds between status checks")
    args = parser.parse_args()

    # 1. PREPARE RAW DATA (Sensitive)
    # --------------------------------
    # This data stays in memory and is never printed or sent in plaintext.
    payload = {"cmd_args": args.sd_args}
    if args.img:
        print(f"🔒 Encoding image: {args.img}")
        payload['init_image'] = encode_file(args.img)

    # 2. ENCRYPT DATA
    # --------------------------------
    # We encrypt the entire payload blob.
    encrypted_token = encrypt_payload(payload)

    # 3. SUBMIT JOB (Async)
    # --------------------------------
    print(f"🚀 Submitting encrypted job to {ENDPOINT_ID}...")
    
    # We purposefully strictly define the JSON structure here.
    # We do NOT merge 'payload' into the root. We only send 'encrypted_input'.
    req_body = {
        "input": {
            "encrypted_input": encrypted_token
        }
    }

    try:
        run_resp = requests.post(f"{BASE_URL}/run", json=req_body, headers=HEADERS)
        run_resp.raise_for_status()
        job_data = run_resp.json()
        job_id = job_data.get("id")
        
        if not job_id:
            print(f"❌ Error: API did not return a Job ID. Response: {job_data}")
            return
            
        print(f"✅ Job submitted successfully. ID: {job_id}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network Error submitting job: {e}")
        return

    # 4. POLL FOR STATUS
    # --------------------------------
    print(f"⏳ Polling status every {args.poll_interval}s...")
    
    start_time = time.time()
    
    while True:
        try:
            status_resp = requests.get(f"{BASE_URL}/status/{job_id}", headers=HEADERS)
            status_resp.raise_for_status()
            data = status_resp.json()
            
            status = data.get("status")
            
            # --- COMPLETED ---
            if status == "COMPLETED":
                duration = round(time.time() - start_time, 2)
                print(f"\n✅ Job Completed in {duration}s")
                
                output = data.get("output", {})
                
                # Check for Handler-level errors (decryption fail, binary fail)
                if isinstance(output, dict) and output.get("status") == "error":
                    print("❌ Worker Error:")
                    print(f"Message: {output.get('message')}")
                    # stderr is safe to print locally, it's coming from the encrypted response
                    if output.get('stderr'):
                        print(f"STDERR: {output.get('stderr')}")
                
                # Check for Success
                elif isinstance(output, dict) and output.get("image"):
                    with open(args.out, "wb") as f:
                        f.write(base64.b64decode(output['image']))
                    print(f"💾 Image saved to: {args.out}")
                else:
                    print("⚠️ Unknown response format or no image returned.")
                    print(json.dumps(output, indent=2))
                
                break

            # --- FAILED (System Level) ---
            elif status == "FAILED":
                print(f"\n❌ Job Failed (RunPod System Error): {data.get('error')}")
                break

            # --- IN QUEUE / IN PROGRESS ---
            else:
                # Print a dot to show activity without flooding console
                print(".", end="", flush=True)
                time.sleep(args.poll_interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Polling stopped by user. The job might still be running on server.")
            break
        except Exception as e:
            print(f"\n⚠️ Polling Error: {e}")
            time.sleep(args.poll_interval)

if __name__ == "__main__":
    main()
