import os
import subprocess
import secrets
import nltk
import uvicorn

def generate_secret_key():
    # Generate a random value to use as a WEBUI_SECRET_KEY in case the user didn't provide one
    return secrets.token_urlsafe(12)

def load_secret_key(key_file):
    try:
        with open(key_file, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        pass

def main():
    script_dir = os.path.dirname(__file__)
    os.chdir(script_dir)

    # Add conditional Playwright browser installation
    if os.environ.get('RAG_WEB_LOADER_ENGINE', '').lower() == 'playwright':
        if not os.environ.get('PLAYWRIGHT_WS_URI'):
            print("Installing Playwright browsers...")
            subprocess.run(['playwright', 'install', 'chromium'])
            subprocess.run(['playwright', 'install-deps', 'chromium'])

        nltk.download('punkt_tab')

    key_file = '.webui_secret_key'
    webui_secret_key = os.environ.get('WEBUI_SECRET_KEY', load_secret_key(key_file))

    if webui_secret_key is None:
        print("Loading WEBUI_SECRET_KEY from file, not provided as an environment variable.")

        if not os.path.exists(key_file):
            print("Generating WEBUI_SECRET_KEY")
            webui_secret_key = generate_secret_key()
            with open(key_file, 'w') as f:
                f.write(webui_secret_key)

        print(f"Loading WEBUI_SECRET_KEY from {key_file}")
        with open(key_file, 'r') as f:
            webui_secret_key = f.read().strip()

    port = int(os.environ.get('PORT', 8080))
    host = os.environ.get('HOST', '0.0.0.0')

    use_ollama = os.environ.get('USE_OLLAMA_DOCKER', '').lower() == 'true'
    if use_ollama:
        print("USE_OLLAMA is set to true, starting ollama serve.")
        subprocess.Popen(['ollama', 'serve'])

    use_cuda = os.environ.get('USE_CUDA_DOCKER', '').lower() == 'true'
    if use_cuda:
        print("CUDA is enabled, appending LD_LIBRARY_PATH to include torch/cudnn & cublas libraries.")
        os.environ['LD_LIBRARY_PATH'] += ':/usr/local/lib/python3.11/site-packages/torch/lib:/usr/local/lib/python3.11/site-packages/nvidia/cudnn/lib'

    space_id = os.environ.get('SPACE_ID')
    if space_id:
        print("Configuring for HuggingFace Space deployment")
        admin_user_email = os.environ.get('ADMIN_USER_EMAIL')
        admin_user_password = os.environ.get('ADMIN_USER_PASSWORD')
        if admin_user_email and admin_user_password:
            print("Admin user configured, creating")
            uvicorn.run(
                'open_webui.main:app',
                host=host,
                port=port,
                forwarded_allow_ips='*',
            )
            subprocess.run([
                'curl',
                '-X', 'POST',
                f'http://localhost:{port}/api/v1/auths/signup',
                '-H', 'accept: application/json',
                '-H', 'Content-Type: application/json',
                '-d', f'{{ "email": "{admin_user_email}", "password": "{admin_user_password}", "name": "Admin" }}',
            ])

        webui_url = os.environ.get('SPACE_HOST')
        if webui_url:
            os.environ['WEBUI_URL'] = webui_url

    # Set environment variable WEBUI_SECRET_KEY
    os.environ['WEBUI_SECRET_KEY'] = webui_secret_key

    uvicorn.run(
        'open_webui.main:app',
        host=host,
        port=port,
        forwarded_allow_ips='*',
    )

if __name__ == '__main__':
    main()