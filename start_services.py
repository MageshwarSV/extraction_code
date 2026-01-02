import os
import sys
import subprocess
import shutil

def is_tool_installed(name):
    return shutil.which(name) is not None

def start_services():
    # 1. Check for screen/tmux
    use_screen = is_tool_installed("screen")
    
    if not use_screen:
        print("❌ 'screen' is not installed. Please install it first:")
        print("   sudo apt-get install screen")
        return

    print("🚀 Starting Services in detached SCREEN sessions...")

    # --- Service 1: FastAPI (Main Engine) on Port 8000 ---
    # We use 'bash -c' to ensure the venv is activated inside the screen session
    cmd_main = "source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    
    # Check if session exists
    check_main = subprocess.run(["screen", "-ls", "wbai_main"], capture_output=True, text=True)
    if "wbai_main" in check_main.stdout:
        print("⚠️  Service 'wbai_main' (Port 8000) seems to be already running.")
    else:
        # Launch detached screen session
        subprocess.run(["screen", "-dmS", "wbai_main", "bash", "-c", cmd_main])
        print("✅ Started 'wbai_main' (Port 8000)")

    # --- Service 2: Transformation API on Port 30019 ---
    cmd_transform = "source venv/bin/activate && python engine/extractors/data_transformation.py --api --port 30019"
    
    check_trans = subprocess.run(["screen", "-ls", "wbai_transform"], capture_output=True, text=True)
    if "wbai_transform" in check_trans.stdout:
        print("⚠️  Service 'wbai_transform' (Port 30019) seems to be already running.")
    else:
        subprocess.run(["screen", "-dmS", "wbai_transform", "bash", "-c", cmd_transform])
        print("✅ Started 'wbai_transform' (Port 30019)")

    print("\n" + "="*50)
    print("STATUS INFO")
    print("="*50)
    print("Services are running in background 'screen' sessions.")
    print("To view/monitor a service:")
    print("  screen -r wbai_main       (For Port 8000)")
    print("  screen -r wbai_transform  (For Port 30019)")
    print("\nTo detach from viewing (leave it running):")
    print("  Press 'Ctrl + A', then 'D'")
    print("\nTo stop a service:")
    print("  screen -X -S wbai_main quit")
    print("="*50)

if __name__ == "__main__":
    start_services()
