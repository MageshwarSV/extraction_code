import os
import sys
import subprocess

def create_service_file(service_name, description, command_args, working_dir, user="root"):
    # We construct the full command using the absolute python path and absolute script path
    python_path = os.path.join(working_dir, "venv/bin/python")
    
    # Ensure command_args uses absolute paths if it references files
    # We will assume the caller provides correct relative or absolute paths, 
    # but here we will just join them for safety in the ExecStart line if possible.
    
    service_content = f"""[Unit]
Description={description}
After=network.target

[Service]
User={user}
WorkingDirectory={working_dir}
ExecStart={python_path} {command_args}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
    file_path = f"/etc/systemd/system/{service_name}.service"
    
    if os.geteuid() != 0:
        print(f"❌ Error: This script must be run as root (sudo) to create {file_path}")
        return False
        
    try:
        with open(file_path, "w") as f:
            f.write(service_content)
        print(f"✅ Created service file: {file_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to write {file_path}: {e}")
        return False

def setup_systemd():
    print("🚀 Setting up Systemd Services (Absolute Paths)...")
    
    working_dir = os.getcwd() # e.g., /root/wbai_doc_extractor_engine-main
    print(f"📍 Working Directory: {working_dir}")

    # --- Service 1: FastAPI Main (Port 8000) ---
    # For module execution (-m), relative usage is fine because cwd is set
    cmd_main = "-m uvicorn app.main:app --host 0.0.0.0 --port 8000"
    
    if create_service_file("wbai_main", "WBAI Doc Extractor Engine (FastAPI)", cmd_main, working_dir):
        # We need to reload daemon because file changed
        os.system("systemctl daemon-reload") 
        os.system("systemctl enable wbai_main")
        os.system("systemctl restart wbai_main")
        print("   - Restarted wbai_main")

    # --- Service 2: Transformation API (Port 30019) ---
    # Use absolute path for the script to be super safe
    script_rel_path = "engine/extractors/data_transformation.py"
    script_abs_path = os.path.join(working_dir, script_rel_path)
    
    cmd_transform = f"{script_abs_path} --api --port 30019"
    
    if create_service_file("wbai_transform", "WBAI Transformation API", cmd_transform, working_dir):
        os.system("systemctl daemon-reload")
        os.system("systemctl enable wbai_transform")
        os.system("systemctl restart wbai_transform")
        print("   - Restarted wbai_transform")

    print("\n" + "="*50)
    print("STATUS INFO")
    print("="*50)
    print("Services were updated with ABSOLUTE PATHS.")
    print("Please check status again:")
    print("  systemctl status wbai_transform")
    print("="*50)

if __name__ == "__main__":
    setup_systemd()
