import requests
import argparse
import sys
import os
from cryptography.fernet import Fernet

# --- CONFIGURATION ---
API_KEY = "YOUR_API_KEY"
ENDPOINT_ID = "YOUR_ENDPOINT_ID"
# MUST match the key used in the handler
ENCRYPTION_KEY = "YOUR_GENERATED_KEY_HERE".encode() 

cipher_suite = Fernet(ENCRYPTION_KEY)

def generate_secure(prompt, output_filename):
    url = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    print(f"--- Encrypting Prompt ---")
    # Encrypt: string -> bytes -> encrypt -> decode to string
    encrypted_prompt = cipher_suite.encrypt(prompt.encode()).decode()

    payload = {
        "input": {
            "encrypted_prompt": encrypted_prompt, # Sending ONLY encrypted data
            "width": 512,
            "height": 1024,
            "steps": 8,
            "cfg_scale": 1.0,
            "seed": -1
        }
    }

    print(f"Sending encrypted payload...")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=600)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == 'COMPLETED':
            output = data.get('output', {})
            
            if 'encrypted_image' in output:
                print("Received encrypted image. Decrypting...")
                
                encrypted_image_str = output['encrypted_image']
                
                # Decrypt: string -> bytes -> decrypt -> raw image bytes
                try:
                    decrypted_image_bytes = cipher_suite.decrypt(encrypted_image_str.encode())
                    
                    with open(output_filename, "wb") as f:
                        f.write(decrypted_image_bytes)
                    print(f"Success! Decrypted image saved to: {output_filename}")
                    
                except Exception as e:
                    print(f"Decryption failed: {e}")
            
            elif 'error' in output:
                print(f"Worker Error: {output['error']}")
        else:
            print(f"Job Status: {data.get('status')}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", type=str)
    parser.add_argument("filename", type=str)
    args = parser.parse_args()
    
    generate_secure(args.prompt, args.filename)
