"""Ollama Diagnostic Tool - Tests connectivity and functionality of Ollama installation

This script checks:
1. If Ollama process is running
2. If Ollama API is accessible
3. Available models
4. Model functionality with a simple test
5. System resources
"""

import subprocess
import json
import re
import requests
import platform
import psutil
import os
import sys
from datetime import datetime

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f" {text}")
    print("=" * 60)

def print_info(label, value):
    """Print a formatted info line"""
    print(f"{label.ljust(25)}: {value}")

def run_command(cmd):
    """Run a shell command and return the output"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip(), result.returncode == 0
    except Exception as e:
        return str(e), False

def check_process():
    """Check if Ollama process is running"""
    print_header("CHECKING OLLAMA PROCESS")
    
    # Try different methods to find the process
    if platform.system() == "Windows":
        output, success = run_command(["tasklist", "/FI", "IMAGENAME eq ollama.exe"])
        running = "ollama.exe" in output
    else:
        output, success = run_command(["pgrep", "ollama"])
        running = success
    
    if running:
        print_info("Ollama Process", "RUNNING ✓")
        
        # Get more info about the process
        if platform.system() != "Windows":
            pid_output, _ = run_command(["pgrep", "ollama"])
            if pid_output:
                try:
                    pid = int(pid_output.split()[0])
                    process = psutil.Process(pid)
                    
                    # Process information
                    print_info("Process ID", pid)
                    print_info("Running Since", datetime.fromtimestamp(process.create_time()).strftime('%Y-%m-%d %H:%M:%S'))
                    print_info("Memory Usage", f"{process.memory_info().rss / (1024 * 1024):.2f} MB")
                    print_info("CPU Usage", f"{process.cpu_percent(interval=0.1)}%")
                except Exception as e:
                    print(f"Error getting process details: {e}")
    else:
        print_info("Ollama Process", "NOT RUNNING ✗")
        print("\nTry starting Ollama with: ollama serve")

def check_api():
    """Check if Ollama API is accessible"""
    print_header("CHECKING OLLAMA API")
    
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print_info("API Status", "ACCESSIBLE ✓")
            return response.json()
        else:
            print_info("API Status", f"ERROR (Status code: {response.status_code}) ✗")
            print_info("Response", response.text)
            return None
    except requests.exceptions.ConnectionError:
        print_info("API Status", "CONNECTION REFUSED ✗")
        print("\nThe Ollama API is not accessible. Make sure Ollama is running with 'ollama serve'")
        return None
    except Exception as e:
        print_info("API Status", f"ERROR: {str(e)} ✗")
        return None

def check_models(api_data):
    """Check available models"""
    print_header("CHECKING AVAILABLE MODELS")
    
    if not api_data:
        print("Cannot check models - API is not accessible")
        return []
    
    models = api_data.get("models", [])
    if models:
        print(f"Found {len(models)} models:")
        for model in models:
            print(f"  - {model['name']} (Size: {model.get('size', 'unknown')})")
        return [model["name"] for model in models]
    else:
        print("No models found. Try pulling a model with:")
        print("  ollama pull tinyllama:latest")
        return []

def test_model(model_name):
    """Test if a model works with a simple prompt"""
    print_header(f"TESTING MODEL: {model_name}")
    
    try:
        # First try with num_gpu: 0 (CPU only)
        payload = {
            "model": model_name,
            "prompt": "Hello, please respond with a single word.",
            "options": {"num_gpu": 0}
        }
        
        print("Testing with CPU only mode...")
        response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print_info("Model Test (CPU)", "SUCCESS ✓")
            print_info("Response", data.get("response", "").strip())
            return True
        
        # If it fails with CPU only, try without that option (may use GPU)
        print("CPU-only test failed, trying without GPU restrictions...")
        payload = {
            "model": model_name,
            "prompt": "Hello, please respond with a single word."
        }
        
        response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print_info("Model Test (Default)", "SUCCESS ✓")
            print_info("Response", data.get("response", "").strip())
            return True
        else:
            print_info("Model Test", "FAILED ✗")
            print_info("Status Code", response.status_code)
            print_info("Error", response.text)
            return False
            
    except Exception as e:
        print_info("Model Test", f"ERROR: {str(e)} ✗")
        return False

def check_system():
    """Check system resources"""
    print_header("CHECKING SYSTEM RESOURCES")
    
    # Memory
    mem = psutil.virtual_memory()
    print_info("Total Memory", f"{mem.total / (1024**3):.2f} GB")
    print_info("Available Memory", f"{mem.available / (1024**3):.2f} GB")
    print_info("Memory Usage", f"{mem.percent}%")
    
    # Disk
    disk = psutil.disk_usage('/')
    print_info("Total Disk Space", f"{disk.total / (1024**3):.2f} GB")
    print_info("Available Disk Space", f"{disk.free / (1024**3):.2f} GB")
    print_info("Disk Usage", f"{disk.percent}%")
    
    # CPU
    print_info("CPU Cores", psutil.cpu_count(logical=False))
    print_info("CPU Threads", psutil.cpu_count(logical=True))
    print_info("CPU Usage", f"{psutil.cpu_percent()}%")
    
    # Check for NVIDIA GPU
    if platform.system() != "Windows":
        nvidia_smi, success = run_command(["nvidia-smi"])
        if success:
            print_info("NVIDIA GPU", "DETECTED ✓")
            # Extract GPU info
            gpu_info = re.search(r"NVIDIA-SMI.*?(\d+\.\d+)", nvidia_smi)
            if gpu_info:
                print_info("NVIDIA Driver Version", gpu_info.group(1))
                
            # Extract GPU memory
            memory_info = re.findall(r"(\d+)MiB\s*/\s*(\d+)MiB", nvidia_smi)
            if memory_info:
                for i, (used, total) in enumerate(memory_info):
                    print_info(f"GPU {i} Memory", f"{used}MB / {total}MB")
        else:
            print_info("NVIDIA GPU", "NOT DETECTED ✗")

def check_ollama_config():
    """Check Ollama configuration"""
    print_header("CHECKING OLLAMA CONFIGURATION")
    
    config_paths = [
        os.path.expanduser("~/.ollama/config.json"),
        "/etc/ollama/config.json",
        "C:\\Users\\%USERNAME%\\.ollama\\config.json"
    ]
    
    config_found = False
    for path in config_paths:
        if os.path.exists(path):
            print_info("Config File", path)
            config_found = True
            try:
                with open(path, 'r') as f:
                    config = json.load(f)
                    print(json.dumps(config, indent=2))
                    
                    # Check for GPU settings
                    if "gpu" in config:
                        if config["gpu"] == False:
                            print_info("GPU Mode", "DISABLED (CPU only)")
                        else:
                            print_info("GPU Mode", "ENABLED")
            except Exception as e:
                print_info("Error Reading Config", str(e))
    
    if not config_found:
        print("No Ollama configuration file found.")
        print("\nTo create a configuration file with CPU-only mode:")
        print("mkdir -p ~/.ollama")
        print("echo '{\"gpu\": false}' > ~/.ollama/config.json")

def suggest_fixes():
    """Suggest fixes based on the diagnostic results"""
    print_header("SUGGESTIONS")
    
    print("If you're experiencing issues with Ollama, try these steps:")
    print("")
    print("1. Restart Ollama:")
    print("   killall ollama  # or equivalent for your OS")
    print("   ollama serve")
    print("")
    print("2. Try CPU-only mode:")
    print("   Create or edit ~/.ollama/config.json:")
    print("   {\"gpu\": false}")
    print("")
    print("3. Re-pull the model:")
    print("   ollama rm tinyllama")
    print("   ollama pull tinyllama:latest --insecure")
    print("")
    print("4. Check for permission issues:")
    print("   sudo chown -R $(whoami) ~/.ollama")
    print("")
    print("5. Check disk space and memory:")
    print("   Make sure you have at least 2GB free RAM and 2GB disk space")
    print("")
    print("6. For more help, visit:")
    print("   https://github.com/ollama/ollama/issues")

def main():
    """Main diagnostic function"""
    print("\nOllama Diagnostic Tool")
    print("-" * 80)
    print(f"Date and Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"System: {platform.system()} {platform.release()}")
    print(f"Python Version: {platform.python_version()}")
    print("-" * 80)
    
    check_process()
    api_data = check_api()
    models = check_models(api_data)
    
    # Test models
    if models:
        if "tinyllama" in models:
            test_model("tinyllama")
        else:
            # Test the first available model
            test_model(models[0])
    
    check_system()
    check_ollama_config()
    suggest_fixes()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDiagnostic interrupted.")
    except Exception as e:
        print(f"\nError running diagnostics: {e}")
        
    print("\nDiagnostic complete.")