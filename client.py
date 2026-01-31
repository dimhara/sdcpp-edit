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

BASE_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# SECURITY KEY
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
    try:
        f = Fernet(ENCRYPTION_KEY.encode())
        json_bytes = json.dumps(payload_dict).encode()
        return f.encrypt(json_bytes).decode()
    except Exception as e:
        print(f"❌ Encryption Error: {e}")
        exit(1)

# ==============================================================================
# MAIN
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Secure Async Client")
    
    # We make sd_args optional (nargs='?') because if we are Resuming, we don't need them.
    parser.add_argument("sd_args", nargs='?', help="Arguments for SD (e.g. -p 'prompt')")
    parser.add_argument("--img", help="Path to input image")
    parser.add_argument("--out", default="output.png", help="Output filename")
    
    # Updated default to 5 seconds
    parser.add_argument("--poll-interval", type=int, default=5, help="Seconds between checks")
    
    # NEW: Resume Argument
    parser.add_argument("--resume-id", type=str, help="Skip submission and poll this existing Job ID")

    args = parser.parse_args()

    job_id = None

    # ---------------------------------------------------------
    # PATH A: RESUME EXISTING JOB
    # ---------------------------------------------------------
    if args.resume_id:
        job_id = args.resume_id
        print(f"🔄 Resuming session for Job ID: {job_id}")
        print(f"   (Ignoring new arguments/images, checking server status only)")

    # ---------------------------------------------------------
    # PATH B: NEW JOB SUBMISSION
    # ---------------------------------------------------------
    else:
        # Validation: If not resuming, we need arguments
        if not args.sd_args:
            print("❌ Error: sd_args are required for new jobs.")
            return

        # 1. Prepare Payload (In Memory)
        payload = {"cmd_args": args.sd_args}
        if args.img:
            print(f"🔒 Encoding image: {args.img}")
            payload['init_image'] = encode_file(args.img)

        # 2. Encrypt
        encrypted_token = encrypt_payload(payload)

        # 3. Submit
        print(f"🚀 Submitting new job...")
        try:
            req_body = {"input": {"encrypted_input": encrypted_token}}
            run_resp = requests.post(f"{BASE_URL}/run", json=req_body, headers=HEADERS)
            run_resp.raise_for_status()
            
            job_data = run_resp.json()
            job_id = job_data.get("id")
            
            if not job_id:
                print(f"❌ API Error: No ID returned. {job_data}")
                return

            print("="*60)
            print(f"✅ JOB SUBMITTED SUCCESSFULLY")
            print(f"🆔 JOB ID: {job_id}")
            print(f"   (Save this ID! If you crash, run: python client_async.py --resume-id {job_id})")
            print("="*60)

        except Exception as e:
            print(f"❌ Submission Failed: {e}")
            return

    # ---------------------------------------------------------
    # POLLING LOOP (Common to both paths)
    # ---------------------------------------------------------
    print(f"⏳ Polling status every {args.poll_interval}s...")
    
    while True:
        try:
            # Check Status
            status_resp = requests.get(f"{BASE_URL}/status/{job_id}", headers=HEADERS)
            status_resp.raise_for_status()
            data = status_resp.json()
            
            status = data.get("status")

            if status == "COMPLETED":
                print(f"\n✅ Job Completed!")
                output = data.get("output", {})
                
                # Case 1: Handler Error (Decryption fail, binary fail)
                if isinstance(output, dict) and output.get("status") == "error":
                    print("❌ Worker Error:")
                    print(f"   Message: {output.get('message')}")
                    if output.get('stderr'):
                        print(f"   STDERR: {output.get('stderr')}")

                # Case 2: Success
                elif isinstance(output, dict) and output.get("image"):
                    try:
                        with open(args.out, "wb") as f:
                            f.write(base64.b64decode(output['image']))
                        print(f"💾 Image successfully saved to: {args.out}")
                    except Exception as e:
                        print(f"❌ Error saving file: {e}")

                # Case 3: Weird format
                else:
                    print(f"⚠️ Unexpected output format: {json.dumps(output)}")
                
                break # Exit Loop

            elif status == "FAILED":
                print(f"\n❌ Job Failed (RunPod Error): {data.get('error')}")
                break

            elif status == "CANCELLED":
                print("\n🚫 Job was cancelled.")
                break

            else:
                # IN_QUEUE or IN_PROGRESS
                print(".", end="", flush=True)
                time.sleep(args.poll_interval)

        except KeyboardInterrupt:
            print(f"\n\n🛑 Polling stopped. Job is STILL running on server.")
            print(f"To resume later, use: python client_async.py --resume-id {job_id}")
            break
        except Exception as e:
            print(f"\n⚠️ Network/Polling Error: {e}")
            print("Retrying in 10s...")
            time.sleep(10)

if __name__ == "__main__":
    main()
