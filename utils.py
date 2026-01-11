import os
import glob
from huggingface_hub import hf_hub_download

# Defined in RunPod docs
RUNPOD_CACHE_DIR = "/runpod-volume/huggingface-cache/hub"

def get_model_map():
    """
    Parses the MODELS environment variable.
    Format: repo_id:filename,repo_id:filename
    Example: leejet/Z-Image-Turbo-GGUF:z_image_turbo-Q4_K.gguf,Comfy-Org/z_image_turbo:split_files/vae/ae.safetensors
    """
    models_env = os.environ.get("MODELS", "")
    if not models_env:
        return []
    
    model_list = []
    # Split by comma for multiple models
    entries = models_env.split(",")
    for entry in entries:
        if ":" in entry:
            repo_id, filename = entry.strip().split(":", 1)
            model_list.append((repo_id.strip(), filename.strip()))
            
    return model_list

def resolve_path(repo_id, filename, download_dir):
    """
    1. Checks RunPod cache (fastest).
    2. Checks if file already exists in download_dir.
    3. Downloads from HF if missing.
    """
    
    # --- 1. Check RunPod Cache ---
    # Convert repo/name to models--repo--name
    safe_repo = repo_id.replace("/", "--")
    cache_path_root = os.path.join(RUNPOD_CACHE_DIR, f"models--{safe_repo}", "snapshots")
    
    if os.path.exists(cache_path_root):
        # Find the snapshot hash folder (usually just one)
        snapshots = os.listdir(cache_path_root)
        if snapshots:
            # We take the first snapshot folder found
            snapshot_path = os.path.join(cache_path_root, snapshots[0])
            full_path = os.path.join(snapshot_path, filename)
            
            if os.path.exists(full_path):
                print(f"[Cache] Found {filename} in RunPod cache: {full_path}")
                return full_path

    # --- 2. Download / Local Check ---
    print(f"[Download] Cache miss for {repo_id}/{filename}. Checking/Downloading to {download_dir}...")
    
    # hf_hub_download checks local dir first automatically if local_dir is set
    try:
        path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=download_dir
        )
        return path
    except Exception as e:
        print(f"Error downloading {repo_id}/{filename}: {e}")
        raise e

def prepare_models(target_dir):
    """
    Iterates through env vars and ensures all models are ready.
    Returns a dict mapping 'filename' -> 'absolute_path'
    """
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    model_list = get_model_map()
    resolved_paths = {}

    print(f"--- Resolving {len(model_list)} models from env var ---")

    for repo_id, filename in model_list:
        # Handle cases where filename has subdirectories (e.g. split_files/vae/ae.safetensors)
        # We generally map the basename to the full path for easier referencing in the handler
        abs_path = resolve_path(repo_id, filename, target_dir)
        
        # We store the mapping using the basename of the file for easier lookup
        # e.g. "ae.safetensors" -> "/path/to/ae.safetensors"
        base_name = os.path.basename(filename)
        resolved_paths[base_name] = abs_path
        
    return resolved_paths

if __name__ == "__main__":
    # Allow running this script standalone to populate a folder
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "/models"
    prepare_models(target)
