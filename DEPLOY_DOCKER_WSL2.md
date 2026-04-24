# Deploy Open WebUI with Docker (Windows + WSL2)

This guide helps you run **Open WebUI** using **Docker Desktop** from inside a **WSL2** terminal.

## Prerequisites

- Windows 10/11
- WSL2 installed (e.g., Ubuntu on WSL)
- Docker Desktop installed

## 1) Enable Docker Desktop WSL2 integration

1. Open **Docker Desktop**.
2. Go to **Settings** → **General**
   - Ensure **Use the WSL 2 based engine** is enabled.
3. Go to **Settings** → **Resources** → **WSL Integration**
   - Enable **Enable integration with my default WSL distro**
   - Also enable integration for the distro you’re using (e.g., **Ubuntu**)
4. Apply & restart Docker Desktop if prompted.

### Verify from WSL

In your WSL terminal, these should work:

```bash
docker --version
docker compose version
```

If Docker is not detected in WSL, double-check the **WSL Integration** toggles above.

## 2) Deploy using this repo’s Docker Compose

From **WSL**, run the following from the repository root (the folder that contains `docker-compose.yaml`):

```bash
# from the repo root
pwd
ls docker-compose.yaml

# pull prebuilt images (recommended)
docker compose -f docker-compose.yaml pull

# start the stack
# NOTE: --no-build avoids building the frontend locally
# (local builds can fail on low-memory machines)
docker compose -f docker-compose.yaml up -d --no-build

# confirm containers are running
docker compose -f docker-compose.yaml ps

# follow logs if needed
docker compose -f docker-compose.yaml logs -f open-webui
```

### Confirm it’s working

```bash
# health check
curl http://localhost:3000/health

# or open in a browser
# http://localhost:3000
```

Expected health response:

```json
{"status": true}
```

## 3) Stop / reset

```bash
# stop containers (keeps volumes/data)
docker compose -f docker-compose.yaml down

# stop + remove volumes (DELETES persistent data)
docker compose -f docker-compose.yaml down -v
```

## Notes / common issues

### A) “docker: command not found” inside WSL

This almost always means Docker Desktop **WSL Integration** is not enabled for your distro.
Re-check: **Docker Desktop → Settings → Resources → WSL Integration**.

### B) `docker compose up --build` fails with Node “heap out of memory”

Use the prebuilt images instead:

```bash
docker compose -f docker-compose.yaml up -d --no-build
```

### C) First startup can take a while

The first run may download models/dependencies and run DB migrations. If the UI isn’t reachable immediately, wait a minute and check:

```bash
docker compose -f docker-compose.yaml logs -f open-webui
```
