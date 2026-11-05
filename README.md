# Rubber Duck WebUI

Rubber Duck WebUI is our customized fork of [Open WebUI](https://github.com/open-webui/open-webui), a self-hosted web interface for language models. It can connect to Ollama and OpenAI-compatible APIs.

## Getting started (Docker)

Docker is the easiest way to run the app. It includes the runtimes and dependencies, so you do not need to install Python, Node.js, or `uv`.

On Windows, install Docker Desktop with [winget](https://learn.microsoft.com/windows/package-manager/winget/) (it should be preinstalled with Windows 11):

```powershell
winget install --id Docker.DockerDesktop -e
```

If prompted, restart Windows to finish installation. Docker Desktop needs virtualization support for Linux containers. `winget` installs Docker Desktop but cannot turn on Windows features. If Docker reports that **Virtual Machine Platform** is disabled, open **PowerShell as Administrator** and run:

```powershell
wsl --install --no-distribution
```

Restart Windows when the command finishes. If WSL setup does not enable the feature, enable it directly from Administrator PowerShell:

```powershell
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
```

Restart Windows after enabling the features. Hardware virtualization must also be enabled in your PC's BIOS/UEFI settings.

Before running the app, launch Docker Desktop and sign in to your Docker account when prompted. Wait until Docker Desktop reports that its engine is running.

From the repository root (You can open a terminal in VS Code), build and start the app:

```powershell
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000). The default Compose configuration starts both the WebUI and Ollama. On first use, select or download a model in Ollama through the WebUI.

Stop the containers with `Ctrl+C`, or run:

```powershell
docker compose down
```

The Compose setup stores WebUI data and Ollama models in Docker volumes, so they persist when you stop the containers. Avoid `docker compose down --volumes` unless you intend to delete that data.

After changing source code, rerun `docker compose up --build` to rebuild the local image. This builds from the checked-out repository; it does not pull the stock Open WebUI image.

## Develop the frontend and backend

This optional setup is for students who are actively changing code. The frontend refreshes as you edit it, and the backend reloads when its Python code changes. Both run on your computer, but each needs its own terminal. For the simplest way to run the app, use Docker above.

Install Python 3.11, `uv`, and [fnm](https://github.com/Schniz/fnm). fnm lets you use the project's supported Node.js 22 without uninstalling an existing Node.js installation:

```powershell
winget install --id Python.Python.3.11 -e
winget install --id astral-sh.uv -e
winget install Schniz.fnm
```

After installation, open a new PowerShell terminal in the repository root. Activate fnm in that terminal, then install and select Node.js 22:

```powershell
fnm env --shell powershell | Out-String | Invoke-Expression
fnm install 22
fnm use 22
node --version
```

Check that the version starts with `v22.`. Run the fnm activation and `fnm use 22` commands in each new terminal where you use Node.js. Then, from the repository root, install the project dependencies:

```powershell
uv sync --locked --group dev
npm ci
```

Start the backend in one terminal:

```powershell
cd backend
$env:CORS_ALLOW_ORIGIN = "http://localhost:5173;http://localhost:8080"
uv run uvicorn open_webui.main:app --host 0.0.0.0 --port 8080 --reload
```

In another terminal, activate fnm, select Node.js 22, and start the frontend from the repository root:

```powershell
fnm env --shell powershell | Out-String | Invoke-Expression
fnm use 22
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). For local models, keep Ollama running separately; alternatively, configure an OpenAI-compatible provider in the WebUI.

## License and upstream

This project is based on Open WebUI. It contains code under multiple licenses; see [LICENSE](./LICENSE) and [LICENSE_HISTORY](./LICENSE_HISTORY) for the applicable terms and history. Please preserve applicable notices when modifying or redistributing the project.
