import os
import sys
import base64
import json
import argparse

# 1. MOCK ENVIRONMENT
# Set the binary path as expected in the container
os.environ["SD_BINARY_PATH"] = "/usr/local/bin/sd"

# Import the handler from your server script
try:
    from rp_handler import handler
except ImportError:
    print("Error: Could not find rp_handler.py in the current directory.")
    sys.exit(1)


def encode_file(path):
    if not os.path.exists(path):
        print(f"Error: Input file not found at {path}")
        sys.exit(1)
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def main():
    parser = argparse.ArgumentParser(description="Local Test Runner for SD Handler")
    parser.add_argument(
        "--img", type=str, required=True, help="Path to input image (e.g., input.png)"
    )
    parser.add_argument(
        "--args", type=str, required=True, help="SD arguments (exclude the binary name)"
    )
    parser.add_argument(
        "--out",
        type=str,
        default="test_result.png",
        help="Where to save the output image",
    )

    args = parser.parse_args()

    print(f"--- Setting up Test ---")
    print(f"Binary Path: {os.environ['SD_BINARY_PATH']}")
    print(f"Input Image: {args.img}")

    # 2. PREPARE PAYLOAD
    # This simulates what RunPod sends to the handler
    job_input = {"cmd_args": args.args, "init_image": encode_file(args.img)}

    # Wrap it in the standard job structure
    mock_job = {"id": "test-job-123", "input": job_input}

    print("\n--- Running Handler ---")

    # 3. EXECUTE HANDLER
    # This calls the function directly, bypassing the HTTP server part
    result = handler(mock_job)

    # 4. PROCESS RESULT
    print("\n--- Result Analysis ---")

    if result.get("status") == "success":
        print("Status: SUCCESS")

        # Save output image
        if result.get("image"):
            with open(args.out, "wb") as f:
                f.write(base64.b64decode(result["image"]))
            print(f"Image Saved: {args.out}")
        else:
            print("Warning: Success reported, but no image data returned.")

        print("\n[STDOUT from Binary]:")
        print(
            result.get("stdout")[:500] + "... (truncated)"
            if result.get("stdout")
            else "None"
        )

    else:
        print("Status: FAILED")
        print(f"Message: {result.get('message')}")
        print("\n[STDERR]:")
        print(result.get("stderr"))
        print("\n[STDOUT]:")
        print(result.get("stdout"))

    # 5. VERIFY SECURITY CLEANUP
    print("\n--- Security Check ---")
    if os.path.exists("/dev/shm/input.png"):
        print("[FAIL] /dev/shm/input.png still exists!")
    else:
        print("[PASS] /dev/shm/input.png was successfully cleaned up.")

    if os.path.exists("/dev/shm/output.png"):
        print("[FAIL] /dev/shm/output.png still exists!")
    else:
        print("[PASS] /dev/shm/output.png was successfully cleaned up.")


if __name__ == "__main__":
    main()
