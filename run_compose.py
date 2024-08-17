import argparse
import subprocess
import os
import sys
import re
import time
import threading

# ANSI color codes
BOLD = "\033[1m"
GREEN = "\033[1;32m"
WHITE = "\033[1;37m"
RED = "\033[0;31m"
NC = "\033[0m"  # No Color
TICK = "\u2713"


def get_gpu_driver():
    # Detect NVIDIA GPUs
    try:
        subprocess.run(
            ["nvidia-smi"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return "nvidia"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Detect AMD GPUs
    try:
        gpu_info = subprocess.check_output(["lspci"], universal_newlines=True)
        if "amd" in gpu_info.lower():
            gcn_and_later = [
                "Radeon HD 7000",
                "Radeon HD 8000",
                "Radeon R5",
                "Radeon R7",
                "Radeon R9",
                "Radeon RX",
            ]
            for model in gcn_and_later:
                if model.lower() in gpu_info.lower():
                    return "amdgpu"
            return "radeon"
    except subprocess.CalledProcessError:
        pass

    # Detect Intel GPUs
    try:
        gpu_info = subprocess.check_output(["lspci"], universal_newlines=True)
        if "intel" in gpu_info.lower():
            return "i915"
    except subprocess.CalledProcessError:
        pass

    return "Unknown or unsupported GPU driver"


def show_loading(stop_event):
    spin = "-\\|/"
    i = 0
    sys.stdout.write(" ")
    sys.stdout.flush()
    while not stop_event.is_set():
        i = (i + 1) % 4
        sys.stdout.write(f"\b{spin[i]}")
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write(f"\b{GREEN}{TICK}{NC}")
    sys.stdout.flush()


def usage():
    print("Usage: python script.py [OPTIONS]")
    print("Options:")
    print("  --enable-gpu[count=COUNT]  Enable GPU support with the specified count.")
    print(
        "  --enable-api[port=PORT]    Enable API and expose it on the specified port."
    )
    print("  --webui[port=PORT]         Set the port for the web user interface.")
    print(
        "  --data[folder=PATH]        Bind mount for ollama data folder (by default will create the 'ollama' volume)."
    )
    print(
        "  --build                    Build the docker image before running the compose project."
    )
    print("  --drop                     Drop the compose project.")
    print("  -q, --quiet                Run script in headless mode.")
    print("  -h, --help                 Show this help message.")
    print("")
    print("Examples:")
    print("  python script.py --drop")
    print("  python script.py --enable-gpu[count=1]")
    print("  python script.py --enable-gpu[count=all]")
    print("  python script.py --enable-api[port=11435]")
    print(
        "  python script.py --enable-gpu[count=1] --enable-api[port=12345] --webui[port=3000]"
    )
    print(
        "  python script.py --enable-gpu[count=1] --enable-api[port=12345] --webui[port=3000] --data[folder=./ollama-data]"
    )
    print(
        "  python script.py --enable-gpu[count=1] --enable-api[port=12345] --webui[port=3000] --data[folder=./ollama-data] --build"
    )
    print("")
    print(
        "This script configures and runs a docker-compose setup with optional GPU support, API exposure, and web UI configuration."
    )
    print(
        "About the gpu to use, the script automatically detects it using the 'lspci' command."
    )
    print(f"In this case the gpu detected is: {get_gpu_driver()}")


def extract_value(arg):
    match = re.search(r"\[(.*?)=(.*?)\]", arg)
    if match:
        return match.group(2)
    return None


def parse_arguments():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--drop", action="store_true")
    parser.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("-h", "--help", action="store_true")

    args, unknown = parser.parse_known_args()

    # Process unknown arguments for more flexible parsing
    for arg in unknown:
        if arg.startswith("--enable-gpu"):
            args.enable_gpu = extract_value(arg) or "1"
        elif arg.startswith("--enable-api"):
            args.enable_api = extract_value(arg) or "11435"
        elif arg.startswith("--webui"):
            args.webui = extract_value(arg) or "3000"
        elif arg.startswith("--data"):
            args.data = extract_value(arg) or "./ollama-data"

    # Add these attributes if they don't exist
    if not hasattr(args, "enable_gpu"):
        args.enable_gpu = None
    if not hasattr(args, "enable_api"):
        args.enable_api = None
    if not hasattr(args, "webui"):
        args.webui = None
    if not hasattr(args, "data"):
        args.data = None

    return args


def main():
    args = parse_arguments()

    if args.help:
        usage()
        return

    if args.drop:
        subprocess.run(["docker", "compose", "down", "--remove-orphans"])
        print(f"{GREEN}{BOLD}Compose project dropped successfully.{NC}")
        return

    compose_command = ["docker", "compose", "-f", "docker-compose.yaml"]

    if args.enable_gpu:
        os.environ["OLLAMA_GPU_DRIVER"] = get_gpu_driver()
        os.environ["OLLAMA_GPU_COUNT"] = args.enable_gpu
        compose_command.extend(["-f", "docker-compose.gpu.yaml"])

    if args.enable_api:
        compose_command.extend(["-f", "docker-compose.api.yaml"])
        os.environ["OLLAMA_WEBAPI_PORT"] = args.enable_api

    if args.data:
        compose_command.extend(["-f", "docker-compose.data.yaml"])
        os.environ["OLLAMA_DATA_DIR"] = args.data

    if args.webui:
        os.environ["OPEN_WEBUI_PORT"] = args.webui

    compose_command.extend(["up", "-d", "--remove-orphans", "--force-recreate"])

    if args.build:
        compose_command.append("--build")

    print(f"\n{WHITE}{BOLD}Current Setup:{NC}")
    print(
        f"   {GREEN}{BOLD}GPU Driver:{NC} {os.environ.get('OLLAMA_GPU_DRIVER', 'Not Enabled')}"
    )
    print(
        f"   {GREEN}{BOLD}GPU Count:{NC} {os.environ.get('OLLAMA_GPU_COUNT', 'Not Enabled')}"
    )
    print(
        f"   {GREEN}{BOLD}WebAPI Port:{NC} {os.environ.get('OLLAMA_WEBAPI_PORT', 'Not Enabled')}"
    )
    print(f"   {GREEN}{BOLD}Data Folder:{NC} {args.data or 'Using ollama volume'}")
    print(f"   {GREEN}{BOLD}WebUI Port:{NC} {args.webui or '3000'}")
    print()

    if not args.quiet:
        choice = input(
            f"{WHITE}{BOLD}Do you want to proceed with current setup? (Y/n): {NC}"
        )
        if choice.lower() not in ["", "y", "yes"]:
            print("Aborted.")
            return

    stop_event = threading.Event()
    loading_thread = threading.Thread(target=show_loading, args=(stop_event,))
    loading_thread.start()

    try:
        subprocess.run(compose_command, check=True)
        stop_event.set()
        loading_thread.join()
        print(f"\n{GREEN}{BOLD}Compose project started successfully.{NC}")
    except subprocess.CalledProcessError:
        stop_event.set()
        loading_thread.join()
        print(f"\n{RED}{BOLD}There was an error starting the compose project.{NC}")


if __name__ == "__main__":
    main()
