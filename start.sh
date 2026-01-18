#!/bin/bash

# Enable fast download transfer
export HF_HUB_ENABLE_HF_TRANSFER=1
MODEL_DIR="/workspace/models"

mkdir -p $MODEL_DIR

echo "---------------------------------------------------"
echo "Initializing Models from Environment Variable..."
echo "MODELS: $MODELS"
echo "---------------------------------------------------"

# Use the shared utils script to download/cache/link models
python3 /utils.py "$MODEL_DIR"

echo "---------------------------------------------------"
echo "Models ready in $MODEL_DIR"
echo "---------------------------------------------------"
echo "Example Command (Update filenames as needed):"
echo 'sd --diffusion-model models/z_image_turbo-Q4_K.gguf --vae models/ae.safetensors --llm models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf -p "test" -o out.png'
echo "---------------------------------------------------"

##############################################################

# Ported extra stuff from runpod's start.sh

execute_script() {
    local script_path=$1
    local script_msg=$2
    if [[ -f ${script_path} ]]; then
        echo "${script_msg}"
        bash ${script_path}
    fi
}

## Setup ssh server
setup_ssh() {
    if [[ $PUBLIC_KEY ]]; then
        echo "Setting up SSH..."
        mkdir -p ~/.ssh
        echo "$PUBLIC_KEY" >> ~/.ssh/authorized_keys
        chmod 700 -R ~/.ssh

        if [ ! -f /etc/ssh/ssh_host_ed25519_key ]; then
            ssh-keygen -t ed25519 -f /etc/ssh/ssh_host_ed25519_key -q -N ''
            echo "ED25519 key fingerprint:"
            ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
        fi

        service ssh start

        echo "SSH host keys:"
        for key in /etc/ssh/*.pub; do
            echo "Key: $key"
            ssh-keygen -lf $key
        done
    fi
}


echo "Pod started. Starting SSH"
setup_ssh
###########################################################


# Keep container running
sleep infinity
