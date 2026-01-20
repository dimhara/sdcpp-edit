import argparse
import requests
import base64
import os
import json

# CONFIGURATION
ENDPOINT_ID = "YOUR_ENDPOINT_ID"
API_KEY = "YOUR_API_KEY"
URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync"

def encode_file(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Input file not found: {path}")
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def main():
    parser = argparse.ArgumentParser(description="SD Client")
    parser.add_argument("sd_args", type=str, help="Arguments. Use {INPUT} as placeholder for image path.")
    parser.add_argument("--img", type=str, help="Path to local input image")
    parser.add_argument("--out", type=str, default="output.png", help="Output filename")
    
    args = parser.parse_args()

    payload_input = {"cmd_args": args.sd_args}

    if args.img:
        payload_input['init_image'] = encode_file(args.img)
        print(f"Loaded image: {args.img}")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    print(f"Sending: {args.sd_args}")
    try:
        response = requests.post(URL, json={"input": payload_input}, headers=headers, timeout=600)
        data = response.json()
        
        if 'output' in data:
            out = data['output']
            if out.get('status') == 'success' and out.get('image'):
                with open(args.out, "wb") as f:
                    f.write(base64.b64decode(out['image']))
                print(f"Saved: {args.out}")
            else:
                print("Error:", out.get('message'))
                print("Stderr:", out.get('stderr'))
        else:
            print(json.dumps(data, indent=2))
            
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    main()
