import argparse
import requests
import base64
import os
import json
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
    parser.add_argument("sd_args", help="Arguments using {INPUT}")
    parser.add_argument("--img", help="Input image path")
    parser.add_argument("--out", default="output.png")
    args = parser.parse_args()

    # 1. PREPARE RAW PAYLOAD
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
    print("Sending encrypted request...")
    
    try:
        resp = requests.post(URL, json={"input": {"encrypted_input": encrypted_token}}, headers=headers, timeout=600)
        data = resp.json()
        
        if 'output' in data:
            out = data['output']
            if out.get('status') == 'success' and out.get('image'):
                with open(args.out, "wb") as f: f.write(base64.b64decode(out['image']))
                print(f"Success! Saved to {args.out}")
            else:
                print("Server Error.")
                print("Message:", out.get('message'))
                # Debug info is only printed here on client, not in server logs
                print("STDERR (Last 500 chars):", out.get('stderr')[-500:] if out.get('stderr') else "None")
        else:
            print("Unexpected response:", json.dumps(data, indent=2))
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    main()
