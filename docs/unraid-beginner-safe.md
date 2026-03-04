# Open WebUI on Unraid (beginner-safe)

This guide is for first-time Unraid users who want a stable Open WebUI Docker setup with persistent data and straightforward upgrades.

## What this guide covers

- Creating an Open WebUI container template in Unraid.
- Correct persistent volume mapping (to avoid losing your data).
- Connecting to Ollama from the container.
- Upgrading safely.
- Troubleshooting common reverse proxy and volume issues.

## Prerequisites

- Unraid with Docker enabled.
- A folder for app data, for example: `/mnt/user/appdata/open-webui`
- Optional: an Ollama instance either:
  - on the Unraid host, or
  - on another machine reachable from Unraid.

## 1. Create the container in Unraid

1. Open `Docker` in the Unraid web UI.
2. Click `Add Container`.
3. Set these core fields:

| Field          | Value                                |
| -------------- | ------------------------------------ |
| Name           | `open-webui`                         |
| Repository     | `ghcr.io/open-webui/open-webui:main` |
| Network Type   | `bridge`                             |
| Restart Policy | `always`                             |
| Container Port | `8080`                               |
| Host Port      | `3000` (or any free port)            |

4. Add a path mapping:

| Config Type | Container Path      | Host Path                      |
| ----------- | ------------------- | ------------------------------ |
| Path        | `/app/backend/data` | `/mnt/user/appdata/open-webui` |

This path is required for persistent user data and settings.

## 2. Configure Ollama connectivity

Choose one option:

### Ollama runs on the Unraid host

- Add Extra Parameters:
  - `--add-host=host.docker.internal:host-gateway`
- Add environment variable:
  - `OLLAMA_BASE_URL=http://host.docker.internal:11434`

### Ollama runs on another machine

- Add environment variable:
  - `OLLAMA_BASE_URL=http://<ollama-lan-ip>:11434`

### Ollama runs in another Docker container

- Put both containers on the same custom Docker network.
- Use the Ollama container name as host:
  - `OLLAMA_BASE_URL=http://<ollama-container-name>:11434`

## 3. First start and validation

1. Start the container.
2. Open `http://<unraid-ip>:3000`.
3. Complete the initial admin setup.
4. In Open WebUI, verify Ollama from `Settings` -> `Connections`.
5. Confirm models load in the model selector.

## 4. Persistent volume notes

- Open WebUI state lives in `/app/backend/data`.
- If this path is not mapped to a host folder, data will reset when the container is recreated.
- Use a directory mapping, not a file mapping.
- If data still does not persist, verify Unraid folder permissions on `/mnt/user/appdata/open-webui`.

## 5. Upgrade steps (safe workflow)

1. Back up `/mnt/user/appdata/open-webui`.
2. In `Docker`, update the image for `open-webui` (or pull the new tag manually).
3. Start the container with the same template and same `/app/backend/data` mapping.
4. Verify login history/settings/chats are still present.
5. If needed, roll back to the previous image tag and restore the backup.

## Troubleshooting

### Cannot reach Ollama from Open WebUI

Symptoms:

- `Connection error` in the UI.
- No models listed, or model pull/list fails.

Fixes:

- Confirm `OLLAMA_BASE_URL` points to a reachable host from inside the container.
- If using host Ollama, ensure `--add-host=host.docker.internal:host-gateway` is set.
- If `host.docker.internal` fails, use the Unraid host LAN IP instead.
- Check Ollama is listening on `11434` and accessible from the Unraid host/network.

### `host.docker.internal` does not resolve

Fixes:

- Add `--add-host=host.docker.internal:host-gateway` to the container template.
- Restart the container after saving template changes.
- Fall back to `OLLAMA_BASE_URL=http://<unraid-lan-ip>:11434` if needed.

### Reverse proxy subpath issues (`/openwebui`)

Symptoms:

- Login page or static assets return `404`.
- WebSocket disconnects, live responses fail, or the UI loops on loading.

Fixes:

- Ensure the reverse proxy forwards WebSocket upgrades.
- Ensure subpath routing is consistent:
  - either strip `/openwebui` before forwarding to Open WebUI, or
  - rewrite `/openwebui/...` to `/...` upstream.
- Set `WEBUI_URL` to the external URL when using a proxy, for example:
  - `WEBUI_URL=https://example.com/openwebui`
- If subpath behavior is still unstable, use a dedicated subdomain instead (for example `https://ai.example.com`).

### Data disappeared after update/redeploy

Fixes:

- Recheck mapping is exactly `/app/backend/data` -> your persistent host folder.
- Confirm the container was recreated with the same host path.
- Ensure no typo created a second empty folder (for example `open-web-ui` vs `open-webui`).
