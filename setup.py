import os
import sys
import subprocess
import venv

def main():
    print("========================================")
    print("   Setting up Prodapt_Agent Project     ")
    print("========================================")

    # 1. Create Virtual Environment
    venv_dir = "venv"
    if not os.path.exists(venv_dir):
        print(f"\n[1/5] Creating virtual environment '{venv_dir}'...")
        venv.create(venv_dir, with_pip=True)
    else:
        print(f"\n[1/5] Virtual environment '{venv_dir}' already exists.")

    # Determine the venv python executable
    if sys.platform == "win32":
        venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        venv_python = os.path.join(venv_dir, "bin", "python")

    if not os.path.exists(venv_python):
        print(f"Error: Could not find Python executable in the virtual environment: {venv_python}")
        sys.exit(1)

    # 2. Install python libraries
    req_file = "requirements.txt"
    if os.path.exists(req_file):
        print(f"\n[2/5] Installing dependencies from {req_file} into '{venv_dir}'...")
        try:
            subprocess.check_call([venv_python, "-m", "pip", "install", "-r", req_file])
            print("Dependencies installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error installing dependencies: {e}")
            sys.exit(1)
    else:
        print(f"\n[2/5] Warning: {req_file} not found. Skipping dependency installation.")

    # 3. Setup .env file
    env_file = ".env"
    print(f"\n[3/5] Setting up {env_file} file...")
    if not os.path.exists(env_file):
        with open(env_file, "w") as f:
            f.write('TAVILY_API_KEY="your_tavily_api_key_here"\n')
            f.write('GEMINI_API_KEY="your_gemini_api_key_here"\n')
        print(f"Created {env_file} template. Please update it with your actual API keys later.")
    else:
        print(f"{env_file} already exists. Skipping creation to avoid overwriting your keys.")

    # 4. Download the embedding model
    print("\n[4/5] Downloading the embedding model (all-MiniLM-L6-v2)...")
    
    # We must run this using the venv's python because sentence_transformers is installed there
    download_script = (
        "try:\n"
        "    from sentence_transformers import SentenceTransformer\n"
        "    SentenceTransformer('all-MiniLM-L6-v2')\n"
        "    print('Embedding model downloaded and cached successfully.')\n"
        "except Exception as e:\n"
        "    print(f'Error downloading the model: {e}')\n"
    )

    try:
        subprocess.check_call([venv_python, "-c", download_script])
    except subprocess.CalledProcessError as e:
        print(f"Error executing model download script: {e}")

    # 5. Ingest unstructured data
    print("\n[5/5] Ingesting unstructured data from dataset/unstructured...")
    unstructured_dir = os.path.join("dataset", "unstructured")
    
    if os.path.exists(unstructured_dir):
        txt_files = [os.path.join(unstructured_dir, f) for f in os.listdir(unstructured_dir) if f.endswith('.txt')]
        if txt_files:
            try:
                ingest_args = [venv_python, "-m", "tools.ingest.ingest"] + txt_files
                subprocess.check_call(ingest_args)
                print("Unstructured data ingested successfully.")
            except subprocess.CalledProcessError as e:
                print(f"Error ingesting unstructured data: {e}")
        else:
            print("No .txt files found in dataset/unstructured.")
    else:
        print("Directory dataset/unstructured not found. Skipping ingestion.")

    print("\n========================================")
    print(" Setup Complete! ")
    print("========================================")
    print("Next steps:")
    if sys.platform == "win32":
        print(f"1. Activate the virtual environment: {venv_dir}\\Scripts\\activate")
    else:
        print(f"1. Activate the virtual environment: source {venv_dir}/bin/activate")
    print("2. Update the .env file with your valid API keys.")
    print("3. Run python run.py to start the agent!")

if __name__ == "__main__":
    main()
