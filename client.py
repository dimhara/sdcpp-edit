import argparse
import requests
import base64
import os
import json
import time
from cryptography.fernet import Fernet

# CONFIGURATION
ENDPOINT_ID = "YOUR_ENDPOINT_ID"
API_KEY = "YOUR_API_KEY"
URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync"

# SECURITY - Must match Server
ENCRYPTION_KEY = "YOUR_GENERATED_KEY_HERE"

def encode_file(path):
    if not os.path.exists(path): raise FileNotFoundError(path)
    with open(path, "rb") as f: return base64.b64encode(f.read()).decode('utf-8')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sd_args", nargs='?', help="Arguments using {INPUT}")
    parser.add_argument("--img", help="Input image path")
    parser.add_argument("--out", default="output.png")
    parser.add_argument("--debug-ssh", action="store_true", help="Send sleep command to server for SSH debugging")
    args = parser.parse_args()

    # 1. PREPARE PAYLOAD
    if args.debug_ssh:
        print("⚠️  Preparing DEBUG SLEEP payload...")
        payload = {"debug_sleep": True}
    else:
        if not args.sd_args:
            print("Error: sd_args are required unless using --debug-ssh")
            return
        payload = {"cmd_args": args.sd_args}
        if args.img:
            payload['init_image'] = encode_file(args.img)

    # 2. ENCRYPT PAYLOAD
    try:
        f = Fernet(ENCRYPTION_KEY.encode())
        json_bytes = json.dumps(payload).encode()
        encrypted_token = f.encrypt(json_bytes).decode()
    except Exception as e:
        print(f"Client Encryption Failed: {e}")
        return

    # 3. SEND REQUEST
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    if args.debug_ssh:
        print("Sending debug command. The client will hang/timeout while the server sleeps.")
        print("Go to RunPod Web Console now to check logs and SSH.")
    else:
        print("Sending encrypted request...")
    
    try:
        # We use a short timeout for debug mode because we don't expect a reply
        timeout = 5 if args.debug_ssh else 600
        
        resp = requests.post(URL, json={"input": {"encrypted_input": encrypted_token}}, headers=headers, timeout=timeout)
        
        # If we are here in debug mode, something weird happened (server returned early)
        data = resp.json()
        
        if 'output' in data:
            out = data['output']
            if out.get('status') == 'success' and out.get('image'):
                with open(args.out, "wb") as f: f.write(base64.b64decode(out['image']))
                print(f"Success! Saved to {args.out}")
            else:
                print("Server Error / Log:")
                print("Message:", out.get('message'))
                print("STDERR:", out.get('stderr'))
        else:
            print("Response:", json.dumps(data, indent=2))
            
    except requests.exceptions.Timeout:
        if args.debug_ssh:
            print("\n✅ Timeout reached (Expected).")
            print("The server should now be sleeping. Check RunPod logs.")
        else:
            print("Error: Request timed out.")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    main()
