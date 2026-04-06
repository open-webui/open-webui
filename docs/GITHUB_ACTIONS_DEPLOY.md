# GitHub Actions production deploy

## What happens

1. Push to `main` triggers the existing Docker image build workflow.
2. After a successful image build, `.github/workflows/deploy-production.yaml` runs automatically.
3. The deploy workflow connects to the server over SSH, updates the repository to the latest `main`, and runs `docker compose --env-file .env up --build -d`.

## Important for private repositories

The server must already have this repository cloned into `DEPLOY_PATH`, and `git pull origin main` must work there without interaction.

For a private repository, that usually means:

- add a deploy key for the repository in GitHub
- add the matching private key on the server for the deploy user
- clone the repository on the server via SSH once, for example `git@github.com:Olegg000/open-webui.git`

## Required GitHub secrets

Add these secrets in your repository settings or in the `production` environment:

- `DEPLOY_HOST`: server hostname or IP
- `DEPLOY_PORT`: SSH port, usually `22`
- `DEPLOY_USER`: SSH user
- `DEPLOY_PATH`: target directory on the server, for example `/opt/open-webui`
- `DEPLOY_SSH_KEY`: private SSH key used by GitHub Actions
- `DEPLOY_ENV_FILE`: full contents of the server `.env` file

## Minimal example for `DEPLOY_ENV_FILE`

```env
OPEN_WEBUI_PORT=3000
WEBUI_SECRET_KEY=change-me
OLLAMA_BASE_URL=http://host.docker.internal:11434
OPENAI_API_KEY=
OPENAI_API_BASE_URL=
```

## Server requirements

- Docker installed
- Docker Compose plugin available as `docker compose`
- SSH access for `DEPLOY_USER`
- Git installed
- Firewall opened for `OPEN_WEBUI_PORT`
- Repository already cloned into `DEPLOY_PATH` and `git pull origin main` works on the server
