# Open WebUI SSH Server Deployment Guide

## Scope

This document records the complete deployment process for the current `Open WebUI`
project from a Windows laptop to a remote Linux server through SSH.

It covers:

- local preparation on Windows
- SSH key verification and re-creation
- uploading files to the server
- deployment with the current `compose.yaml` + `.env`
- deployment with `compose.pgvector.yaml` + `.env.pgvector`
- update, backup, restore, verification, and troubleshooting

The repository paths used in this guide are:

- Local: `c:\Roy\Software\Git\open-webui\`
- Server: `/home/royluo/open-webui/`
- Server hostname: `cnt-aisrvp01`

Key files:

- `compose.yaml` + `.env`
- `compose.pgvector.yaml` + `.env.pgvector`

## Current Server Status

- **Server**: `cnt-aisrvp01` (`10.224.10.12`), user `royluo`
- **Deployment directory**: `/home/royluo/open-webui/`
- **Running version**: **Version A** (`compose.yaml` + `.env`)
- **Container**: `open-webui` (image: `ghcr.io/open-webui/open-webui:main`)
- **Port**: `3000` → container `8080`
- **Status**: Up 6+ weeks, healthy

### What `compose.yaml` does

Defines a single `open-webui` service container:

- Pulls the `ghcr.io/open-webui/open-webui:main` image (latest development build)
- Maps host port `3000` to container port `8080` (HTTP web UI)
- Mounts `./data` → `/app/backend/data` inside the container (persistent storage for uploaded files, RAG documents, SQLite database, etc.)
- Passes all configuration from `.env` as environment variables
- Sets `restart: unless-stopped` so the container auto-restarts on crash or host reboot

### What `.env` does

Provides runtime configuration via environment variables, organized into four groups:

**1. vLLM Inference (model backend)**
- `VLLM_OPENAI_BASE_URL`: Two vLLM endpoints (`8203` and `8202`), semicolon-separated, for load distribution / failover
- `VLLM_OPENAI_API_KEY`: API keys for both endpoints

**2. LDAP Authentication**
- `ENABLE_LDAP=true`: Enables company AD login (`cnt-dcp03.luxgroup.net`)
- `LDAP_APP_DN` / `LDAP_APP_PASSWORD`: Service account for binding to AD
- `LDAP_SEARCH_BASE=DC=LUXGROUP,DC=NET`: Search scope (entire domain)
- `LDAP_ATTRIBUTE_FOR_USERNAME=sAMAccountName`: Uses Windows login name
- `DEFAULT_USER_ROLE=user` + `DEFAULT_GROUP_ID`: Auto-activates new LDAP users and assigns them to a group
- `ENABLE_SIGNUP=false`: Blocks self-registration (LDAP-only login)

**3. RAG (Retrieval-Augmented Generation)**
- `RAG_EMBEDDING_ENGINE=openai` + `RAG_EMBEDDING_MODEL=Qwen3-Embedding-0.6B`: External embedding endpoint at `10.224.10.31:8203` for document vectorization
- `CHUNK_SIZE=1200`, `CHUNK_OVERLAP=100`: Document splitting parameters
- `ENABLE_MEMORIES=true`: Enables conversation memory feature

**4. Security**
- `WEBUI_SECRET_KEY`: JWT signing key for session tokens

## Current Architecture

### Version A: Current Single-Service Version

Files:

- `compose.yaml`
- `.env`

Characteristics:

- one `open-webui` container
- two external `vLLM` inference endpoints (`10.224.10.12:8203` and `10.224.10.12:8202`, semicolon-separated)
- external embedding endpoint for RAG (`10.224.10.31:8203`)
- LDAP login enabled
- local persistent data mounted to `./data`
- no external PostgreSQL database
- default vector database remains the built-in default path used by `Open WebUI`
- local signup disabled (`ENABLE_SIGNUP=false`)

Container and port:

- container name: `open-webui`
- local port mapping: `3000:8080`

### Version B: PostgreSQL + pgvector Version

Files:

- `compose.pgvector.yaml`
- `.env.pgvector`

Characteristics:

- one `postgres` container using `pgvector/pgvector:pg16`
- one `open-webui` container
- external `vLLM` inference endpoints
- external embedding endpoint for RAG
- LDAP login enabled
- `Open WebUI` main database stored in PostgreSQL
- RAG vector storage stored in `pgvector`
- PostgreSQL data mounted to `./pgdata`
- application data still mounted to `./data`

Containers and ports:

- container name: `open-webui-postgres`
- container name: `open-webui-pg`
- local port mapping: `3001:8080`

## Local Files

### `.env`

Main points in the current version:

- `VLLM_OPENAI_BASE_URL=http://10.224.10.12:8203/v1;http://10.224.10.12:8202/v1`
- `VLLM_OPENAI_API_KEY=<key1>;<key2>`
- `LDAP_SEARCH_FILTERS=(objectCategory=person)(objectClass=user)`
- `DEFAULT_USER_ROLE=user`
- `DEFAULT_GROUP_ID=eb3a7cf8-3b65-40b3-95dd-c8e8e3df2598`
- `ENABLE_SIGNUP=false`
- external embedding endpoint enabled for RAG (`RAG_EMBEDDING_ENGINE=openai`, `RAG_EMBEDDING_MODEL=Qwen3-Embedding-0.6B`)

### `.env.pgvector`

Main points in the PostgreSQL version:

- `POSTGRES_DB=openwebui`
- `POSTGRES_USER=openwebui`
- `POSTGRES_PASSWORD=...`
- `DATABASE_URL=postgresql://...@postgres:5432/openwebui`
- `VECTOR_DB=pgvector`
- `PGVECTOR_DB_URL=postgresql://...@postgres:5432/openwebui`
- `PGVECTOR_CREATE_EXTENSION=true`
- two `vLLM` endpoints separated by `;`
- external embedding endpoint enabled for RAG

Important notes:

- `POSTGRES_PASSWORD`, `DATABASE_URL`, and `PGVECTOR_DB_URL` must use matching credentials.
- `DEFAULT_USER_ROLE` and `DEFAULT_GROUP_ID` should be set explicitly if you want new users to be auto-activated and auto-added to the expected group.

## SSH Key Setup On Windows

### Check Existing SSH Key Files

Run in PowerShell:

```powershell
Get-ChildItem "$env:USERPROFILE\.ssh"
```

Expected useful files:

- `id_ed25519`
- `id_ed25519.pub`
- `known_hosts`
- optionally `config`

### Create SSH Key Pair If Needed

If the key does not exist, create one:

```powershell
ssh-keygen -t ed25519 -C "open-webui-deploy" -f "$env:USERPROFILE\.ssh\id_ed25519"
```

This creates:

- private key: `C:\Users\<your-user>\.ssh\id_ed25519`
- public key: `C:\Users\<your-user>\.ssh\id_ed25519.pub`

### View Public Key Content

```powershell
Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub"
```

You should see one line similar to:

```text
ssh-ed25519 AAAAC3... open-webui-deploy
```

That full line must be installed into the server account's `authorized_keys`.

## Verify Existing SSH Access

### Check Whether The Host Fingerprint Exists

```powershell
Select-String -Path "$env:USERPROFILE\.ssh\known_hosts" -Pattern '10\.224\.10\.12'
```

Meaning:

- if there is output, the laptop has connected to this host before
- this does not prove passwordless login still works

### Test Key Login

```powershell
ssh -i "$env:USERPROFILE\.ssh\id_ed25519" -o IdentitiesOnly=yes -o BatchMode=yes royluo@10.224.10.12 "whoami && hostname && echo ok"
```

### Debug SSH If Login Fails

```powershell
ssh -vvv -i "$env:USERPROFILE\.ssh\id_ed25519" -o IdentitiesOnly=yes royluo@10.224.10.12
```

Look for:

- `Offering public key`
- `Server accepts key`
- `Permission denied`

## Rebuild Passwordless SSH Access

Use this section if key login fails but you still know the server password or have console access.

### Method 1: Install Public Key To `royluo`

Copy the public key to the server:

```powershell
scp "$env:USERPROFILE\.ssh\id_ed25519.pub" royluo@10.224.10.12:/tmp/id_ed25519.pub
```

Then log in with password:

```powershell
ssh royluo@10.224.10.12
```

Run on the server:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
cat /tmp/id_ed25519.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
rm -f /tmp/id_ed25519.pub
```

Verify SSH daemon settings:

```bash
grep -E '^(PubkeyAuthentication|PermitRootLogin|AuthorizedKeysFile)' /etc/ssh/sshd_config
```

Recommended values:

```conf
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
```

Restart SSH service:

```bash
systemctl restart sshd || systemctl restart ssh
```

Re-test from the laptop:

```powershell
ssh -i "$env:USERPROFILE\.ssh\id_ed25519" -o IdentitiesOnly=yes -o BatchMode=yes royluo@10.224.10.12 "whoami && hostname && echo ok"
```

### Method 2: Install Public Key To A Normal User Such As `royluo`

Copy the public key:

```powershell
scp "$env:USERPROFILE\.ssh\id_ed25519.pub" royluo@10.224.10.12:/tmp/id_ed25519.pub
```

Log in:

```powershell
ssh royluo@10.224.10.12
```

Run on the server:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
cat /tmp/id_ed25519.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
rm -f /tmp/id_ed25519.pub
```

Verify:

```powershell
ssh -i "$env:USERPROFILE\.ssh\id_ed25519" -o IdentitiesOnly=yes -o BatchMode=yes royluo@10.224.10.12 "whoami && hostname && echo ok"
```

### Optional: Add SSH Config On Windows

Create `C:\Users\<your-user>\.ssh\config`:

```sshconfig
Host owui-10
    HostName 10.224.10.12
    User royluo
    IdentityFile C:\Users\royluo\.ssh\id_ed25519
    IdentitiesOnly yes
```

Then use:

```powershell
ssh -o BatchMode=yes owui-10 "echo ok"
```

## Prepare The Linux Server

Connect to the server:

```powershell
ssh royluo@10.224.10.12
```

### Create The Deployment Directory

On the server:

```bash
mkdir -p /home/royluo/open-webui
cd /home/royluo/open-webui
```

### Install Docker And Compose Plugin

If Docker is not installed:

```bash
apt-get update
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable docker
systemctl start docker
docker version
docker compose version
```

## Upload Project Files To The Server

### Option A: Upload The Whole Project Directory

Run from Windows:

```powershell
scp -r "c:\Roy\Software\Git\open-webui" royluo@10.224.10.12:/home/royluo/
```

This creates:

- `/home/royluo/open-webui`

### Option B: Upload Only Required Deployment Files

If the server only needs deployment files:

```powershell
scp "c:\Roy\Software\Git\open-webui\compose.yaml" royluo@10.224.10.12:/home/royluo/open-webui/
scp "c:\Roy\Software\Git\open-webui\.env" royluo@10.224.10.12:/home/royluo/open-webui/
scp "c:\Roy\Software\Git\open-webui\compose.pgvector.yaml" royluo@10.224.10.12:/home/royluo/open-webui/
scp "c:\Roy\Software\Git\open-webui\.env.pgvector" royluo@10.224.10.12:/home/royluo/open-webui/
```

### Verify Uploaded Files On The Server

```bash
cd /home/royluo/open-webui
ls -la
```

## Deploy Version A: Current `compose.yaml` + `.env`

### Configuration Summary

This version uses:

- two external `vLLM` endpoints at `10.224.10.12:8203` and `10.224.10.12:8202` (semicolon-separated in `VLLM_OPENAI_BASE_URL`)
- external embedding endpoint at `10.224.10.31:8203`
- LDAP login
- auto user activation and default group assignment if configured in `.env`
- local persistent mount `./data:/app/backend/data`
- local signup disabled (`ENABLE_SIGNUP=false`)

### Start The Service

On the server:

```bash
cd /home/royluo/open-webui
docker compose --env-file .env -f compose.yaml up -d
```

### Check Container Status

```bash
docker compose --env-file .env -f compose.yaml ps
docker ps
```

### Check Logs

```bash
docker compose --env-file .env -f compose.yaml logs -f
```

### Verify Port Access

On the server:

```bash
ss -lntp | grep 3000
```

From a browser:

- `http://<server-ip>:3000`

## Deploy Version B: `compose.pgvector.yaml` + `.env.pgvector`

### Configuration Summary

This version uses:

- PostgreSQL as the main database
- `pgvector` as the vector database
- external `vLLM` endpoints at `10.224.10.12:8203` and `10.224.10.12:8202`
- external embedding endpoint at `10.224.10.31:8203`
- LDAP login
- local application data in `./data`
- PostgreSQL data in `./pgdata`

### Important Checks Before Starting

Check these items in `.env.pgvector`:

- `POSTGRES_PASSWORD` is set
- `DATABASE_URL` and `PGVECTOR_DB_URL` use the same username and password
- `DEFAULT_USER_ROLE=user` if you want new LDAP users to auto-activate
- `DEFAULT_GROUP_ID=<group-id>` if you want new LDAP users to enter the target group
- special characters in database passwords should be avoided unless URL-encoded

### Start The Service

On the server:

```bash
cd /home/royluo/open-webui
docker compose --env-file .env.pgvector -f compose.pgvector.yaml up -d
```

### Check Container Status

```bash
docker compose --env-file .env.pgvector -f compose.pgvector.yaml ps
docker ps
```

### Check Logs

```bash
docker compose --env-file .env.pgvector -f compose.pgvector.yaml logs -f
```

### Verify Port Access

On the server:

```bash
ss -lntp | grep 3001
```

From a browser:

- `http://<server-ip>:3001`

## Data Persistence

### Version A

Persistent path:

- `/home/royluo/open-webui/data`

This directory stores the local `Open WebUI` application data mounted by:

```yaml
./data:/app/backend/data
```

### Version B

Persistent paths:

- `/home/royluo/open-webui/data`
- `/home/royluo/open-webui/pgdata`

Meaning:

- `data` stores application-side persistent files
- `pgdata` stores PostgreSQL database files

## Update Procedure

### Update Version A

```bash
cd /home/royluo/open-webui
docker compose --env-file .env -f compose.yaml pull
docker compose --env-file .env -f compose.yaml up -d
docker compose --env-file .env -f compose.yaml ps
```

### Update Version B

```bash
cd /home/royluo/open-webui
docker compose --env-file .env.pgvector -f compose.pgvector.yaml pull
docker compose --env-file .env.pgvector -f compose.pgvector.yaml up -d
docker compose --env-file .env.pgvector -f compose.pgvector.yaml ps
```

## Stop And Restart

### Stop Version A

```bash
cd /home/royluo/open-webui
docker compose --env-file .env -f compose.yaml down
```

### Restart Version A

```bash
cd /home/royluo/open-webui
docker compose --env-file .env -f compose.yaml up -d
```

### Stop Version B

```bash
cd /home/royluo/open-webui
docker compose --env-file .env.pgvector -f compose.pgvector.yaml down
```

### Restart Version B

```bash
cd /home/royluo/open-webui
docker compose --env-file .env.pgvector -f compose.pgvector.yaml up -d
```

## Backup

### Backup Version A

```bash
cd /home/royluo/open-webui
tar -czf open-webui-data-backup-$(date +%F).tar.gz data
```

### Backup Version B

```bash
cd /home/royluo/open-webui
tar -czf open-webui-pg-backup-$(date +%F).tar.gz data pgdata
```

## Restore

### Restore Version A

```bash
cd /home/royluo/open-webui
docker compose --env-file .env -f compose.yaml down
tar -xzf open-webui-data-backup-YYYY-MM-DD.tar.gz
docker compose --env-file .env -f compose.yaml up -d
```

### Restore Version B

```bash
cd /home/royluo/open-webui
docker compose --env-file .env.pgvector -f compose.pgvector.yaml down
tar -xzf open-webui-pg-backup-YYYY-MM-DD.tar.gz
docker compose --env-file .env.pgvector -f compose.pgvector.yaml up -d
```

## Verification Checklist After Deployment

### Base Health Checks

Run on the server:

```bash
docker ps
docker compose --env-file .env -f compose.yaml ps
docker compose --env-file .env.pgvector -f compose.pgvector.yaml ps
```

Check:

- expected containers are running
- the required ports are listening
- there are no restart loops

### Functional Checks For Version A

Check:

- open `http://<server-ip>:3000`
- admin login works
- LDAP login works with a valid domain account
- invalid LDAP user does not pass LDAP login
- model list is visible to the correct group
- RAG upload and retrieval work

### Functional Checks For Version B

Check:

- open `http://<server-ip>:3001`
- admin login works
- LDAP login works with a valid domain account
- PostgreSQL container is healthy
- RAG upload and retrieval work
- newly created data is visible after container restart

## LDAP Notes

Current LDAP settings are based on:

- `LDAP_ATTRIBUTE_FOR_USERNAME=sAMAccountName`
- `LDAP_ATTRIBUTE_FOR_MAIL=mail`
- `LDAP_SEARCH_BASE=DC=LUXGROUP,DC=NET`
- `LDAP_SEARCH_FILTERS=(objectCategory=person)(objectClass=user)`

Important note:

- do not wrap `LDAP_SEARCH_FILTERS` with another outer `(&...)`
- `Open WebUI` already builds the full LDAP filter internally

## Signup And Local Account Notes

Enabling LDAP does not automatically disable local signup.

If you want to prevent fake local accounts such as `abc@abc.com`, add this to the env file used by the running deployment:

```env
ENABLE_SIGNUP=false
```

Meaning:

- LDAP login remains enabled
- local signup is disabled
- random users cannot self-register with any valid-looking email format

Note: The current deployment already has `ENABLE_SIGNUP=false` configured.

## PostgreSQL Migration Notes

If you switch from Version A to Version B:

- the new PostgreSQL database starts empty unless you migrate old data
- users, groups, permissions, model grants, and chat history are not automatically copied from the old SQLite-backed setup

You likely need migration if you want to preserve:

- existing users
- existing groups
- existing model access grants
- historical chat data

If you only need a fresh new environment:

- no migration is required
- but the target group must exist before `DEFAULT_GROUP_ID` can work as expected

## Troubleshooting

### `docker: command not found`

Meaning:

- Docker is not installed on the machine where you are running commands
- or Docker is not present in `PATH`

Fix:

- install Docker on the server
- run deployment commands on the server, not on a Windows machine without Docker

### `Permission denied (publickey,password)`

Meaning:

- the SSH key is not accepted by the target account
- or you are using the wrong username
- or the server does not allow the selected login mode

Fix:

- install the public key again
- confirm the correct login user
- confirm `PubkeyAuthentication yes`
- confirm `PermitRootLogin` if using `root`

### LDAP Works But Fake Emails Can Register

Meaning:

- local signup is still enabled

Fix:

- set `ENABLE_SIGNUP=false`
- restart the service

### New LDAP Users Are Not Auto-Activated

Meaning:

- `DEFAULT_USER_ROLE` is empty or not passed to the container

Fix:

```env
DEFAULT_USER_ROLE=user
```

### New LDAP Users Are Not Added To The Expected Group

Meaning:

- `DEFAULT_GROUP_ID` is empty
- or the target group ID does not exist in the active database

Fix:

```env
DEFAULT_GROUP_ID=eb3a7cf8-3b65-40b3-95dd-c8e8e3df2598
```

Also confirm:

- the group exists in the active database
- for PostgreSQL deployments, old SQLite group IDs are not automatically present without migration

### PostgreSQL URL Issues

Meaning:

- database password contains reserved URL characters such as `#` or `@`

Fix:

- use a simpler password without reserved URL characters
- or URL-encode the password in `DATABASE_URL` and `PGVECTOR_DB_URL`

## Adding New Environment Variables

**Critical**: `compose.yaml` uses an **explicit `environment:` list**, **not `env_file:`**.

This means:

- adding a variable to `.env` alone is **NOT enough**
- you must also add the corresponding `${VAR_NAME}` entry to the `environment:` section in `compose.yaml`
- otherwise the container will never receive the new variable, even after `docker compose up -d`

Example: To enable OpenAI-compatible API access:

```env
# .env
ENABLE_API_KEYS=True
USER_PERMISSIONS_FEATURES_API_KEYS=true
```

```yaml
# compose.yaml (environment section)
- ENABLE_API_KEYS=${ENABLE_API_KEYS}
- USER_PERMISSIONS_FEATURES_API_KEYS=${USER_PERMISSIONS_FEATURES_API_KEYS}
```

After updating both files:

```bash
docker compose --env-file .env -f compose.yaml up -d --force-recreate
```

Note: regular `up -d` does **not** reload env vars for running containers. Use `--force-recreate` or `down && up -d`.

## Recommended Operating Sequence

For a fresh safe rollout:

1. verify SSH key login to the server
2. install Docker on the server if needed
3. upload deployment files
4. decide whether to use Version A or Version B
5. verify the env file values before startup
6. start the selected compose stack
7. verify logs and port access
8. verify LDAP login and RAG behavior
9. disable local signup if only LDAP users should be allowed
10. make a backup after successful deployment

## Quick Command Reference

### Version A

```bash
cd /home/royluo/open-webui
docker compose --env-file .env -f compose.yaml up -d
docker compose --env-file .env -f compose.yaml logs -f
docker compose --env-file .env -f compose.yaml ps
docker compose --env-file .env -f compose.yaml pull
docker compose --env-file .env -f compose.yaml down
```

### Version B

```bash
cd /home/royluo/open-webui
docker compose --env-file .env.pgvector -f compose.pgvector.yaml up -d
docker compose --env-file .env.pgvector -f compose.pgvector.yaml logs -f
docker compose --env-file .env.pgvector -f compose.pgvector.yaml ps
docker compose --env-file .env.pgvector -f compose.pgvector.yaml pull
docker compose --env-file .env.pgvector -f compose.pgvector.yaml down
```
