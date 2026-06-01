# Traefik Reverse-Proxy Deployment Recipe

This guide shows how to deploy Open WebUI behind a [Traefik](https://traefik.io/) reverse proxy with automatic HTTPS via Let's Encrypt.

## Prerequisites

- A working Traefik instance (v2.10+)
- A DNS record pointing your domain to the Traefik host
- Docker & Docker Compose installed

## Docker Compose Snippet

```yaml
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-webui
    volumes:
      - open-webui:/app/backend/data
    environment:
      - 'OLLAMA_BASE_URL=http://ollama:11434'
      - 'WEBUI_SECRET_KEY='
    extra_hosts:
      - host.docker.internal:host-gateway
    restart: unless-stopped
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.open-webui.rule=Host(`openwebui.example.com`)"
      - "traefik.http.routers.open-webui.entrypoints=websecure"
      - "traefik.http.routers.open-webui.tls.certresolver=myresolver"
      - "traefik.http.services.open-webui.loadbalancer.server.port=8080"
      # Optional: middleware chain example
      - "traefik.http.routers.open-webui.middlewares=chain-open-webui@file"

volumes:
  open-webui: {}
```

## Notes

- **`certresolver=myresolver`** must match the certificate resolver name in your Traefik static configuration (`traefik.yml` or command-line flags).
- **`chain-open-webui@file`** refers to a middleware chain defined via Traefik's file provider. If you don't use a file provider, you can remove this label or replace it with inline middleware labels (e.g., `traefik.http.routers.open-webui.middlewares=compress@docker,ratelimit@docker`).
- Ensure Traefik's Docker provider is enabled so it can read container labels.

## Example Traefik Static Configuration (`traefik.yml`)

```yaml
entryPoints:
  web:
    address: ":80"
  websecure:
    address: ":443"

certificatesResolvers:
  myresolver:
    acme:
      email: admin@example.com
      storage: /letsencrypt/acme.json
      tlsChallenge: {}

providers:
  docker:
    exposedByDefault: false
  file:
    directory: /dynamic
    watch: true
```

## Example Middleware Chain (`/dynamic/middlewares.yml`)

```yaml
http:
  middlewares:
    compress:
      compress: {}
    ratelimit:
      rateLimit:
        average: 100
        burst: 50

  middlewares:
    chain-open-webui:
      chain:
        middlewares:
          - compress
          - ratelimit
```

## Usage

1. Replace `openwebui.example.com` with your actual domain.
2. Ensure the Traefik network is attached (e.g., add `networks: [traefik]` to the service and define the external network in Compose).
3. Run `docker compose up -d`.

Open WebUI will be available at `https://openwebui.example.com` with TLS terminated by Traefik.
